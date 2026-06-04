---
title: "Minimal-Downtime Database Migrations: The HarbourBridge Pattern"
description: "Production-grade technical deep-dive on Minimal-DowntimeDatabaseMigrations:TheHarbourBridgePattern"
keywords: ["43-database-migrations"]
author: "Pratik Dhanave"
date: "2026-06-04"
readtime: "10-15 min"
---

# Minimal-Downtime Database Migrations: The HarbourBridge Pattern

**You can't take your database offline for 2 hours when 1M+ users depend on it.** HarbourBridge (Google's open-source Spanner migration tool) pioneered a pattern for moving massive databases with zero downtime.

The key: **dual-write** during migration, then flip the switch.

---

## The HarbourBridge Pattern

```
Phase 1: Bulk Load
  Source (MySQL) → Bulk Export → Target (Cloud Spanner)
  
Phase 2: Dual-Write
  All writes go to BOTH MySQL (source of truth) and Spanner (target)
  Continuously validate consistency
  
Phase 3: Verify
  Run checksums on every table
  Ensure row counts, checksums match
  
Phase 4: Flip
  Switch read/write to Spanner
  Keep MySQL as fallback for 48 hours
  
Phase 5: Cleanup
  Sunset MySQL (after monitoring Spanner for issues)
```

---

## Phase 1: Bulk Load

```python
import os
from google.cloud import bigquery, spanner

def bulk_migrate_table(source_table: str, target_table: str):
    """Export from MySQL to GCS, then import to Spanner."""
    
    # Export to GCS (fast, parallelizable)
    os.system(f"""
        mysqldump {source_table} \
          --tab=/tmp/dump \
          --fields-terminated-by=',' \
          --no-create-info
    """)
    
    # Load into Spanner
    spanner_client = spanner.Client()
    instance = spanner_client.instance("prod-instance")
    database = instance.database("production")
    
    with database.batch() as batch:
        with open(f"/tmp/dump/{source_table}.txt") as f:
            for line in f:
                fields = line.strip().split(',')
                batch.insert(target_table, columns=[...], values=[fields])
```

---

## Phase 2: Dual-Write with CDC

```python
from datastream import stream_change_data

def enable_dual_write():
    """Stream changes from source and apply to target."""
    
    # Set up Datastream (CDC from MySQL)
    datastream = stream_change_data(
        source="mysql-prod",
        target="gcs://spanner-cdc/",
    )
    
    # Process CDC events
    for event in datastream.read_events():
        if event.operation == "INSERT":
            spanner_insert(event.table, event.data)
        elif event.operation == "UPDATE":
            spanner_update(event.table, event.data)
        elif event.operation == "DELETE":
            spanner_delete(event.table, event.key)
        
        # Validate consistency
        assert count_source(event.table) == count_target(event.table)

def apply_writes_to_both(table: str, data: dict):
    """Every application write hits both databases."""
    
    mysql.insert(table, data)     # Source (primary)
    spanner.insert(table, data)   # Target (duplicate)
    
    # Verify they match
    assert mysql.count(table) == spanner.count(table)
```

---

## Phase 3: Validation

```python
def validate_migration():
    """Checksums on every table must match before flip."""
    
    for table in list_tables():
        source_checksum = mysql.query(f"""
            SELECT MD5(CONCAT_WS(',', *)) FROM {table}
        """)
        target_checksum = spanner.query(f"""
            SELECT STRING_AGG(CAST(* AS STRING)) FROM {table}
        """)
        
        if source_checksum != target_checksum:
            raise Exception(f"{table} checksums don't match!")
        
        print(f"✓ {table} validated")
    
    print("✅ All tables validated. Safe to flip.")
```

---

## Phase 4: Flip (The Scary Part)

```python
def flip_to_target(rollback_window_hours: int = 48):
    """Switch traffic. Keep source as fallback."""
    
    # Update application config (atomic)
    dns_client.update_cname(
        "database.prod",
        "spanner.googleapis.com"
    )
    
    # Applications now read/write to Spanner
    # MySQL is the fallback (untouched for 48 hours)
    
    # Monitor Spanner for issues
    monitor_spanner(duration=timedelta(hours=rollback_window_hours))
    
    # If something breaks, flip back instantly
    if detect_anomalies():
        dns_client.update_cname("database.prod", "mysql.prod")
        # Spanner → MySQL fallback (takes ~30 seconds)
```

---

## Phase 5: Cleanup

```python
def cleanup_source():
    """After 48 hours, sunset MySQL."""
    
    time.sleep(timedelta(hours=48))
    
    # Final validation
    assert spanner.count_all_rows() == mysql.count_all_rows()
    
    # Turn off replication
    mysql.stop_replication()
    
    # Archive MySQL (don't delete yet)
    backup_mysql_to_archive_storage()
    
    # Optional: Keep MySQL for disaster recovery (cold backup)
    mysql.shutdown()
```

---

**Tags:** #DatabaseMigration #CDC #Spanner #ZeroDowntime #Reliability

**Published:** June 2026  
**Author:** Pratik Dhanave  
**Related Projects:** HarbourBridge, Spanner migrations
