# MVCC and Concurrency Control

*The reason a long analytics query doesn't block every writer in your database — and vice versa — is a single elegant idea: never overwrite data, keep multiple versions, and give each transaction a consistent snapshot in time. MVCC is how nearly every modern database delivers isolation without readers and writers fighting over locks.*

The previous post established that isolation is a spectrum and that databases must let many transactions run concurrently without corrupting each other. This post covers *how* they do it. The naive approach — lock everything — works but destroys concurrency. The approach that actually powers PostgreSQL, MySQL/InnoDB, Oracle, and most modern databases is **Multi-Version Concurrency Control (MVCC)**, and its central trick is keeping old versions of rows so that readers never block writers and writers never block readers.

## The problem with locks

The simplest way to enforce isolation is **locking**: before reading or writing a row, acquire a lock so no one else can touch it. Two-phase locking (2PL) using shared (read) and exclusive (write) locks can even provide serializability. But pure locking has a crippling cost: **readers and writers block each other.** A transaction writing a row holds an exclusive lock, so anyone wanting to *read* that row must wait — and a long-running read (a report, an analytics scan) holding read locks can block *all* writers to those rows.

In a system with mixed read and write traffic, this is disastrous: one slow query stalls everything it touches. The insight behind MVCC is that most of this contention is unnecessary, because a reader doesn't actually need the *latest* value — it needs a *consistent* value.

## The MVCC idea: keep versions

**MVCC keeps multiple versions of each row.** When a transaction updates a row, the database does *not* overwrite the old value in place — it creates a **new version** and leaves the old one intact. Each version is stamped with the transaction that created it. A reader is then served the version that was current *as of when its transaction (or statement) started* — a consistent **snapshot** of the database frozen at a point in time.

The consequence is the property that makes MVCC transformative:

- **Readers don't block writers.** A reader sees a snapshot of old committed versions and doesn't need a lock; a writer can create new versions concurrently.
- **Writers don't block readers.** The writer's new version doesn't disturb the old version the reader is looking at.
- **Writers still coordinate with writers.** Two transactions writing the *same* row must still be serialized (one waits or one aborts) — MVCC removes read/write contention, not write/write contention.

```text
Row "balance":
   v1 (=100, by txn 10, committed)   ← reader in snapshot ≤ txn 15 sees this
   v2 (=90,  by txn 20, committed)   ← reader in snapshot ≥ txn 20 sees this
A reader started at txn 15 reads v1 (100) even while txn 20 wrote v2 (90).
No locks, no blocking.
```

This is why you can run a big read-only report against a live transactional database and neither freeze the writers nor see a smeared, half-updated picture — the report reads a stable snapshot while writers march on creating new versions.

## Snapshots and visibility

The heart of MVCC is the **visibility rule**: given a row's versions, which one does *this* transaction see? Each version records the transaction ID that created it (and, on update/delete, the transaction that superseded it). A transaction takes a **snapshot** — essentially "which transactions had committed at my start" — and a version is visible to it if it was created by a transaction that had committed as of the snapshot and not yet superseded by another committed version in that snapshot.

This is exactly how isolation levels from the previous post are *implemented*:

- **Read Committed** typically takes a fresh snapshot at the start of *each statement*, so each new statement sees recently-committed data (allowing non-repeatable reads across statements).
- **Repeatable Read / Snapshot isolation** takes *one* snapshot at the *transaction's* start and uses it throughout, so the transaction sees a stable view — the same row reads the same value all transaction long.

So MVCC isn't a separate feature from isolation levels — it's the machinery that provides them, with the level determining *when* snapshots are taken. Snapshot isolation (Repeatable Read in Postgres) is a direct, natural product of MVCC.

## The cost: old versions must be cleaned up

MVCC's elegance has a price that every operator of these databases eventually meets: **old versions accumulate.** Every update leaves a dead prior version; every delete leaves a version that's invisible to new transactions but not yet physically removed. If nothing cleaned them up, the database would grow without bound and slow down as it wades through dead versions. So MVCC databases run a **garbage collection** process to reclaim space from versions no longer visible to *any* live transaction:

- In **PostgreSQL**, this is **VACUUM** (and autovacuum): it removes dead tuples and makes their space reusable. Neglecting it causes **table bloat** (tables physically larger than their live data, hurting cache and scan performance) and, in the extreme, **transaction ID wraparound** — a serious failure mode. Tuning autovacuum is a core Postgres operational skill precisely because of MVCC.
- In **MySQL/InnoDB**, old versions live in the **undo log** and are purged by a background thread; a long-running transaction that holds back purge causes the undo log to balloon.

Two operational lessons follow directly:

- **Long-running transactions are costly under MVCC.** A transaction that stays open holds back garbage collection — the database must retain every version that transaction *might* still need to see, so dead versions pile up cluster-wide. This is why an idle-in-transaction connection or a forgotten long report can bloat a whole database. Keep transactions short.
- **Update-heavy workloads generate version churn.** Frequent updates to the same rows create many versions and lots of cleanup work; it's a real cost of the "readers never block" benefit.

## The full picture: MVCC plus some locking

MVCC handles read/write concurrency, but databases still use **locks** for the parts MVCC alone can't cover:

- **Write/write conflicts** — two transactions updating the same row are serialized with row-level locks (or, under snapshot/serializable isolation, one may be *aborted* with a serialization error to retry — the "first committer wins" rule).
- **Explicit locking** — `SELECT ... FOR UPDATE` lets an application deliberately lock rows it intends to update, preventing lost updates (the defense mentioned in the previous post).
- **Serializable isolation** on MVCC databases often adds a layer — PostgreSQL's **Serializable Snapshot Isolation (SSI)** detects dangerous read/write dependency cycles among snapshots and aborts a transaction to preserve true serializability, giving serializable guarantees while keeping MVCC's non-blocking reads.

So the modern concurrency-control picture is: **MVCC for read/write concurrency (snapshots, no read locks), plus targeted locking or abort-and-retry for write/write conflicts and serializability.** That combination is what lets a database be simultaneously highly concurrent and correct — the goal the whole correctness half of this series has been building toward.

## Key takeaways

- Pure locking enforces isolation but makes readers and writers block each other, so one long query can stall everything — MVCC removes that contention by keeping multiple row versions instead of overwriting.
- MVCC serves each transaction a consistent snapshot of committed versions as of its start, so readers don't block writers and writers don't block readers (write/write conflicts still serialize).
- Isolation levels are implemented via snapshot timing: Read Committed takes a snapshot per statement; Repeatable Read/snapshot isolation takes one at transaction start — MVCC is the machinery behind the levels.
- The cost is version accumulation: dead versions must be garbage-collected (Postgres VACUUM/autovacuum, InnoDB undo-log purge), and neglect causes bloat; long-running transactions hold back cleanup and bloat the whole database, so keep transactions short.
- Modern databases combine MVCC (non-blocking reads) with targeted locking/abort-retry for write/write conflicts, explicit SELECT FOR UPDATE, and serializable layers like Postgres SSI — delivering high concurrency and correctness together.

## Further reading

- [PostgreSQL documentation — Concurrency Control (MVCC)](https://www.postgresql.org/docs/current/mvcc.html)
- [Transactions and isolation (previous post)](/blog/posts/dbint-06-transactions-and-isolation.html)
- [Distributed Systems: Consistency Models](/blog/posts/distsys-02-consistency-models.html)
