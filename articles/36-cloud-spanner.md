---
title: "Cloud Spanner: Schema Design, Write Hotspots, and Minimal-Downtime Migrations"
description: "Cloud Spanner architecture guide: schema design, write hotspot prevention, primary key patterns, interleaving, and zero-downtime migrations for globally distributed databases."
keywords: ["Cloud Spanner", "database design", "schema design", "write hotspots", "distributed database", "primary key", "interleaving", "database migration"]
author: "Pratik Dhanave"
date: "2026-06-04"
readtime: "10-15 min"
canonical: "https://pratikdhanave.github.io/articles/36-cloud-spanner/"
schema: {
  "@context": "https://schema.org",
  "@type": "BlogPosting",
  "headline": "Cloud Spanner: Schema Design, Write Hotspots, and Minimal-Downtime Migrations",
  "description": "Production guide to Cloud Spanner schema design, avoiding write hotspots, and executing zero-downtime migrations",
  "author": {"@type": "Person", "name": "Pratik Dhanave", "url": "https://pratikdhanave.github.io"},
  "datePublished": "2026-06-04",
  "dateModified": "2026-06-04",
  "image": "https://pratikdhanave.github.io/og-default.png",
  "keywords": ["Cloud Spanner", "database design", "schema design", "distributed database"],
  "articleSection": "Cloud Infrastructure"
}
---

# Cloud Spanner: Schema Design, Write Hotspots, and Minimal-Downtime Migrations

**Cloud Spanner is Google's globally distributed SQL database that looks like a relational database but thinks like a distributed system.** It offers ACID transactions across continents, millisecond latency, and 99.999% availability — but only if you design your schema for it.

The moment you put a monotonically increasing counter in your primary key, Spanner's performance drops from 10K TPS to 100 TPS. This is the story of what we learned migrating systems onto Spanner and why primary key design is the most critical performance lever you have.

---

## The Write Hotspot Problem

Traditional databases: Primary key determines the server your data lands on.

```sql
CREATE TABLE orders (
  order_id INT64 PRIMARY KEY,  -- ❌ BAD: Sequential IDs cause hotspots
  customer_id INT64,
  amount FLOAT64,
  created_at TIMESTAMP,
) PRIMARY KEY(order_id);
```

**What happens:**
- `INSERT` order #1000001 → Server A
- `INSERT` order #1000002 → Server A (same server, because sequential)
- `INSERT` order #1000003 → Server A
- All writes queue on a single server ← **Write hotspot**

Result: 100s of TPS instead of 1000s.

### **Solution: Design Primary Keys for Distribution**

```sql
CREATE TABLE orders (
  customer_id INT64 NOT NULL,  -- Customer determines shard
  order_id INT64 NOT NULL,      -- Ordering within customer
  amount FLOAT64,
  created_at TIMESTAMP,
) PRIMARY KEY(customer_id, order_id);
```

Now writes are distributed by customer, not by time:
- `INSERT (customer=123, order=1)` → Server A
- `INSERT (customer=456, order=1)` → Server B
- `INSERT (customer=789, order=1)` → Server C

Result: Full parallelism, 10K+ TPS.

---

## Interleaving: When to Use It

Spanner allows child tables to be "interleaved" under parent tables. Rows from the same customer are stored physically close, making queries fast.

```sql
CREATE TABLE customers (
  customer_id INT64 PRIMARY KEY,
  name STRING,
) PRIMARY KEY(customer_id);

CREATE TABLE orders (
  customer_id INT64 NOT NULL,
  order_id INT64 NOT NULL,
  amount FLOAT64,
) PRIMARY KEY(customer_id, order_id),
  INTERLEAVE IN PARENT customers ON DELETE CASCADE;
```

**Benefits:**
- Query `SELECT * FROM orders WHERE customer_id = 123` is lightning fast (data is co-located)
- `ON DELETE CASCADE` automatically cleans up orphan rows

**When NOT to use:**
- When the parent-child cardinality is 1:N with N > 10K
- When child rows are updated independently of the parent

---

## CDC (Change Data Capture) for Minimal-Downtime Migrations

You have data on MySQL. You need to move to Spanner. Downtime is not acceptable.

Strategy:
1. Set up CDC to stream changes from MySQL
2. Bulk-load existing data to Spanner
3. Stream changes to Spanner in real-time
4. Verify consistency
5. Flip the switch (no data loss)

```python
from google.cloud import spanner, dataflow

def migrate_mysql_to_spanner(mysql_table: str, spanner_table: str):
    """
    Minimal-downtime migration using Dataflow + Spanner CDC.
    """
    
    # Step 1: Bulk load existing data
    dataflow_job = dataflow.run_template(
        "gs://dataflow-templates/mysql-to-spanner",
        parameters={
            "sourceConnectionUrl": "jdbc:mysql://...",
            "sourceQuery": f"SELECT * FROM {mysql_table}",
            "spannerId": "projects/...",
            "databaseId": "production",
            "table": spanner_table,
        }
    )
    dataflow_job.wait_until_finish()
    
    # Step 2: Stream ongoing changes with Datastream
    datastream_stream = datastream.create_stream(
        source_config={
            "sourceType": "MySQL",
            "connectionProfile": "mysql-prod",
            "mysqlSourceConfig": {
                "includedTables": [mysql_table],
            },
        },
        destination_config={
            "destinationType": "GCS",
            "gcsDestinationConfig": {
                "bucket": "gs://spanner-cdc-stream/",
            },
        },
    )
    datastream_stream.start()
    
    # Step 3: Continuously sync CDC events to Spanner
    while datastream_stream.is_active():
        events = datastream_stream.read_events(batch_size=1000)
        for event in events:
            if event.op == "INSERT":
                spanner_client.insert(spanner_table, event.data)
            elif event.op == "UPDATE":
                spanner_client.update(spanner_table, event.data)
            elif event.op == "DELETE":
                spanner_client.delete(spanner_table, event.key)
    
    # Step 4: Verify consistency before switching
    mysql_count = mysql_client.query(f"SELECT COUNT(*) FROM {mysql_table}")
    spanner_count = spanner_client.query(f"SELECT COUNT(*) FROM {spanner_table}")
    
    if mysql_count != spanner_count:
        raise Exception("Data mismatch! Do not switch.")
    
    # Step 5: Switch production traffic
    dns.update_cname("database.prod", "spanner.googleapis.com")
    
    # Step 6: Monitor for 24 hours, then sunset MySQL
    monitor_for_errors(duration=timedelta(hours=24))
    mysql_client.drop_table(mysql_table)
```

**Result:** Zero-downtime migration. Data consistency guaranteed.

---

## Production Checklist

- [ ] **Primary key is distributed** (not sequential)
- [ ] **Interleaving is used only for 1:N with N < 10K**
- [ ] **Queries include filter on partition key** (not full table scans)
- [ ] **Hot rows are cached** (Spanner + Redis for high-frequency updates)
- [ ] **CDC validates consistency** before flip-over
- [ ] **Monitoring is in place** for write latency and throughput

---

**Tags:** #CloudSpanner #DatabaseMigration #CDC #Distributed #HighPerformance

**Published:** June 2026  
**Author:** Pratik Dhanave  
**Related Projects:** HarbourBridge migrations, Globe, Picnic
