---
title: "Globe: Building a 30K+ TPS Transaction Engine — Idempotency, Ledgers, and Error Orchestration"
description: "High-throughput transaction engine design: 30K+ TPS, idempotency patterns, distributed ledgers, error orchestration, and Kubernetes-native transaction processing."
keywords: ["transaction engine", "high-throughput", "idempotency", "distributed ledger", "TPS", "fintech", "payment systems", "error handling"]
author: "Pratik Dhanave"
date: "2026-06-04"
readtime: "10-15 min"
canonical: "https://pratikdhanave.github.io/articles/34-globe-30k-tps/"
schema: {
  "@context": "https://schema.org",
  "@type": "BlogPosting",
  "headline": "Globe: Building a 30K+ TPS Transaction Engine",
  "description": "Architecture guide for building high-throughput transaction engines with 30K+ transactions per second",
  "author": {"@type": "Person", "name": "Pratik Dhanave", "url": "https://pratikdhanave.github.io"},
  "datePublished": "2026-06-04",
  "dateModified": "2026-06-04",
  "image": "https://pratikdhanave.github.io/og-default.png",
  "keywords": ["transaction engine", "high-throughput", "idempotency", "distributed systems"],
  "articleSection": "High-Performance Systems"
}
---

# Globe: Building a 30K+ TPS Transaction Engine — Idempotency, Ledgers, and Error Orchestration

**30,000 transactions per second.** That's 2.6 billion transactions per day. At that scale, traditional database transactions don't work anymore — you need a distributed ledger mindset: every transaction is logged durably *before* it's executed, and idempotency isn't optional, it's the foundation.

**Cross-reference:** [PSD2 payments](/articles/32-psd2-agent-orchestration/) | [Latency optimization](/articles/35-picnic-latency/) | [Cloud Spanner](/articles/36-cloud-spanner/) | [Observability](/articles/40-observability-scale/)

Globe is a Kubernetes-native transaction platform built to handle telecom and fintech at scale. Here's what we learned about building systems that don't lose money even when they break.

---

## The 30K+ TPS Problem

## Ledger-First Architecture

Ledger-first architecture is a pattern where every transaction is written to an immutable log BEFORE execution. The log becomes the source of truth, enabling idempotency, recovery, and audit compliance at any scale.

Traditional architecture:
```
Request → Database Transaction → Response
```

At 30K TPS, this breaks in three ways:

1. **Database can't keep up** — Even with connection pooling and caching, coordinating 30K concurrent transactions overwhelms the database
2. **Network failures hide errors** — Request succeeds on the server but the response is lost. Did the transaction execute? You don't know.
3. **Partial failures propagate** — One step fails mid-transaction, leaving the system in an inconsistent state

### **Solution: Ledger-First Architecture**

```
Request → Write to Log (durable) → Execute → Update Ledger → Response
```

Every transaction is immutable from the moment it enters the system. The log is the source of truth.

---

## Core Patterns

### **Pattern 1: Idempotency Keys**

Every request gets a unique idempotency key. If the same key arrives twice, the system returns the cached result without re-executing:

```python
import hashlib
import uuid
from datetime import datetime

class IdempotentTransaction:
    def __init__(self, request_id: str, payload: dict):
        self.request_id = request_id  # Provided by caller
        self.idempotency_key = hashlib.sha256(
            f"{request_id}{payload}".encode()
        ).hexdigest()
        self.status = "pending"
        self.result = None
        self.created_at = datetime.now()
        self.executed_at = None

def process_transaction(idempotency_key: str, payload: dict) -> dict:
    """
    If we've seen this key before, return the cached result.
    Otherwise, execute and cache.
    """
    # Check cache (Redis, in-process cache)
    cached = cache.get(idempotency_key)
    if cached:
        audit_log.record(f"Idempotent retry: {idempotency_key}")
        return cached
    
    # Not seen before — execute
    result = execute_transaction(payload)
    
    # Cache with TTL (keep for 24-48 hours per fintech standards)
    cache.set(idempotency_key, result, ttl=timedelta(hours=48))
    
    return result
```

**Why it works:** Network hiccup? Caller retries with the same key. System returns the same result without double-charging the customer.

---

### **Pattern 2: Three-Layer Ledger System**

```
Layer 1: Write-Ahead Log (WAL)
         ↓ (proven durable)
Layer 2: Transactional Ledger
         ↓ (balanced and verified)
Layer 3: Reconciliation Log
         ↓ (proof for auditors)
```

```python
class LedgerEntry:
    def __init__(self, transaction_id: str, amount: float, account: str):
        self.id = transaction_id
        self.amount = amount
        self.account = account
        self.status = "pending"
        self.debit_entry = None
        self.credit_entry = None
        self.created_at = datetime.now()

def process_with_ledger(transaction: LedgerEntry):
    """
    Step 1: Write to immutable log (don't execute yet)
    """
    wal_entry = {
        "transaction_id": transaction.id,
        "payload": transaction.to_dict(),
        "timestamp": datetime.now().isoformat(),
    }
    append_to_wal(wal_entry)  # Append-only, immutable
    
    """
    Step 2: Execute (now safe because we have proof it happened)
    """
    # Debit source account
    ledger.debit(transaction.account, transaction.amount)
    
    # Credit destination
    ledger.credit(destination_account, transaction.amount)
    
    # Mark as executed
    transaction.status = "completed"
    transaction.executed_at = datetime.now()
    
    """
    Step 3: Reconciliation (prove to auditors this happened)
    """
    reconciliation_log.append({
        "transaction_id": transaction.id,
        "debit": {"account": transaction.account, "amount": transaction.amount},
        "credit": {"account": destination_account, "amount": transaction.amount},
        "timestamp": datetime.now().isoformat(),
        "balance_after": ledger.get_balance(transaction.account),
    })
```

---

### **Pattern 3: Error-Code Orchestration with Exponential Backoff + DLQ**

When something fails, it doesn't disappear. It's routed to a Dead Letter Queue (DLQ) with a strategy:

```python
from enum import Enum
from datetime import datetime, timedelta
import random

class ErrorCode(Enum):
    TEMPORARY_FAILURE = "temp_fail"  # Retry
    INSUFFICIENT_FUNDS = "insuf_funds"  # Human review
    INVALID_ACCOUNT = "invalid_acct"  # Reject
    SYSTEM_UNAVAILABLE = "unavail"  # Retry with backoff

class RetryStrategy:
    def __init__(self, error_code: ErrorCode):
        self.error_code = error_code
        self.attempt = 0
        self.next_retry = None
    
    def should_retry(self) -> bool:
        """Decide if we should retry this error."""
        return self.error_code in [
            ErrorCode.TEMPORARY_FAILURE,
            ErrorCode.SYSTEM_UNAVAILABLE,
        ]
    
    def calculate_backoff(self) -> timedelta:
        """Exponential backoff with jitter."""
        base_delay = 2 ** self.attempt  # 1, 2, 4, 8, 16 seconds
        jitter = random.uniform(0, base_delay * 0.1)
        return timedelta(seconds=base_delay + jitter)
    
    def get_next_retry_time(self) -> datetime:
        """When should we retry?"""
        self.attempt += 1
        if self.attempt > 5:  # Max 5 retries
            return None
        delay = self.calculate_backoff()
        return datetime.now() + delay

def handle_transaction_error(
    transaction_id: str,
    error: Exception,
    error_code: ErrorCode,
):
    """Route errors intelligently."""
    strategy = RetryStrategy(error_code)
    
    if not strategy.should_retry():
        # Not retryable — send to human review
        human_review_queue.append({
            "transaction_id": transaction_id,
            "error": str(error),
            "error_code": error_code.value,
            "timestamp": datetime.now(),
        })
        audit_log.record(f"Transaction {transaction_id} queued for review")
        return
    
    # Retryable — schedule retry
    next_retry = strategy.get_next_retry_time()
    if next_retry is None:
        # Max retries exceeded
        dlq.append({
            "transaction_id": transaction_id,
            "error": str(error),
            "attempts": strategy.attempt,
            "timestamp": datetime.now(),
        })
        audit_log.record(f"Transaction {transaction_id} moved to DLQ after {strategy.attempt} retries")
        return
    
    # Schedule for retry
    retry_queue.schedule(transaction_id, next_retry)
    audit_log.record(f"Transaction {transaction_id} scheduled for retry at {next_retry}")
```

---

## Kubernetes Integration: Running at Scale

Globe runs on Kubernetes because you can't run 30K TPS on a single server.

```yaml
apiVersion: apps/v1
kind: Deployment
metadata:
  name: globe-transaction-processor
spec:
  replicas: 50  # 50 replicas, each doing 600 TPS
  strategy:
    type: RollingUpdate
    rollingUpdate:
      maxUnavailable: 5  # Never drop below 45 replicas
  template:
    spec:
      containers:
      - name: processor
        image: globe:latest
        resources:
          requests:
            cpu: "2"
            memory: "4Gi"
          limits:
            cpu: "4"
            memory: "8Gi"
        env:
        - name: LEDGER_DB
          valueFrom:
            secretKeyRef:
              name: globe-credentials
              key: ledger-connection
        - name: CACHE_REDIS
          value: "redis-cluster:6379"
        - name: PARTITION_KEY  # Each replica handles a subset of accounts
          valueFrom:
            fieldRef:
              fieldPath: metadata.name
      affinity:
        podAntiAffinity:
          preferredDuringSchedulingIgnoredDuringExecution:
          - weight: 100
            podAffinityTerm:
              labelSelector:
                matchExpressions:
                - key: app
                  operator: In
                  values:
                  - globe-transaction-processor
              topologyKey: kubernetes.io/hostname
```

**Key ideas:**
- **Replicas** — 50 instances, 600 TPS each = 30K TPS total
- **Rolling updates** — Never kill all replicas at once
- **Anti-affinity** — Spread across different nodes (fault isolation)
- **Partition keys** — Each replica handles certain accounts (reduces hot-spotting)

---

## Production Checklist

- [ ] **Idempotency keys cached** for 48+ hours
- [ ] **Write-Ahead Log is append-only** (never modified)
- [ ] **Ledger entries are immutable** once created
- [ ] **Error orchestration routes intelligently** (retry vs. review vs. DLQ)
- [ ] **Exponential backoff prevents thundering herd** 
- [ ] **DLQ is monitored** (alerts for transactions stuck > 1 hour)
- [ ] **Reconciliation logs match ledger** (daily audit)
- [ ] **Kubernetes rollouts never drop capacity** (rolling updates)

---

## My Takeaway

30K TPS doesn't come from throwing more hardware at a monolithic app. It comes from architectural clarity:

1. **Ledger-first thinking** — Log before you execute
2. **Idempotency everywhere** — Same key = same result
3. **Error as a first-class concern** — Not an afterthought
4. **Immutable audit trails** — Proof for regulators and customers

With these foundations, your system can survive: network failures, database hiccups, deployments, and human mistakes.

---

**Tags:** #HighThroughput #Transactions #Ledger #Kubernetes #Idempotency #ErrorHandling #FinTech

**Published:** June 2026  
**Author:** Pratik Dhanave  
**Related Projects:** Globe telecom/fintech platform
