# Transactions and Isolation

*A transaction is a promise that a group of operations happens all-or-nothing and doesn't get corrupted by everyone else doing the same thing at once. Most developers know the word ACID; far fewer know that the "I" — isolation — is a dial with several settings, and that the default setting in most databases allows anomalies they've never heard of.*

So far the series has covered how a database stores and finds data. This post moves to *correctness under concurrency*: how a database lets many clients read and write simultaneously without producing garbage. The mechanism is the **transaction**, and the subtle, consequential part is **isolation** — how much concurrent transactions are allowed to see of each other's in-progress work. Getting this wrong causes bugs that are intermittent, data-dependent, and nearly impossible to reproduce.

## ACID: what a transaction guarantees

A **transaction** groups operations into a single logical unit with four guarantees, abbreviated ACID:

- **Atomicity** — all operations succeed or none do. A transaction that fails partway is rolled back entirely; there's no "half a transfer." (This is the undo half of the WAL recovery from the earlier post.)
- **Consistency** — a transaction moves the database from one valid state to another, preserving declared rules (constraints, foreign keys). Note this "C" is *application/schema* consistency, distinct from the "consistency" of distributed systems.
- **Isolation** — concurrent transactions don't interfere; the result is *as if* they ran one at a time (to a degree set by the isolation level — the heart of this post).
- **Durability** — once committed, it survives crashes. (The WAL, from the previous post.)

Atomicity and durability come largely from the WAL. Consistency is enforced by constraints. **Isolation is the hard, tunable one**, because perfect isolation is expensive, so databases offer *levels* that trade correctness for concurrency.

## Why isolation is a dial, not a switch

Ideal isolation — **serializability** — means the outcome of running transactions concurrently is identical to *some* serial (one-at-a-time) order. That's the strongest, most intuitive guarantee: you can reason about each transaction as if it had the database to itself. But enforcing it requires heavy coordination (locking or validation) that limits how much can run in parallel, hurting throughput.

So the SQL standard defines weaker **isolation levels** that permit specific **anomalies** in exchange for more concurrency. The engineering reality: **most databases do not default to serializable** — they default to a weaker level (often Read Committed, sometimes Repeatable Read), meaning your application is, by default, exposed to certain anomalies. Knowing which anomalies your level allows is not academic; it's the difference between correct and subtly-broken code.

## The anomalies

Each anomaly is a specific way concurrent transactions can interfere. They form a ladder — weaker levels permit more of them:

- **Dirty read** — reading data another transaction has written but *not yet committed*. If that other transaction rolls back, you read a value that never officially existed. Almost always undesirable.
- **Non-repeatable read** — reading the same row twice in one transaction and getting *different* values, because another transaction committed a change in between. Your transaction sees the world shift under it.
- **Phantom read** — re-running the same *query* (a range/predicate, e.g. "all orders over $100") and getting a *different set of rows*, because another transaction inserted or deleted matching rows in between. Like a non-repeatable read but for a set rather than a single row.
- **Lost update** — two transactions read a value, both modify it based on what they read, and both write back — the second silently overwrites the first. Classic in "read balance, add, write balance" patterns.
- **Write skew** — a subtler one: two transactions read an overlapping set, each makes a decision based on it, and each writes to *different* rows such that together they violate an invariant that each alone preserved (e.g. two doctors each going off-call because "the other is still on," leaving none). Serializable prevents it; weaker levels may not.

These aren't exotic — lost updates and write skew in particular cause real money bugs (double-spends, oversold inventory, negative balances) in applications that assumed the database "just handles concurrency."

## The isolation levels

The SQL standard defines four levels, each preventing more anomalies:

```text
Level              Dirty read  Non-repeatable  Phantom
Read Uncommitted   allowed     allowed         allowed
Read Committed     prevented   allowed         allowed
Repeatable Read    prevented   prevented       allowed*
Serializable       prevented   prevented       prevented
```

- **Read Uncommitted** — the weakest; allows dirty reads. Rarely useful.
- **Read Committed** — you only see committed data (no dirty reads), but the same row can change between two reads in your transaction. **The default in PostgreSQL, Oracle, SQL Server** — and it allows non-repeatable reads, phantoms, and lost updates. Most applications run here.
- **Repeatable Read** — rows you've read won't change within your transaction. The **default in MySQL/InnoDB**. (\*The standard allows phantoms here, but some implementations, like PostgreSQL's snapshot-based Repeatable Read, prevent many of them — implementations differ, which is a crucial caveat.)
- **Serializable** — full isolation; behaves as if transactions ran one at a time, preventing all anomalies including write skew. The safest and the most expensive.

The critical, practical caveat: **isolation levels are not implemented identically across databases.** PostgreSQL's Repeatable Read (snapshot-based) behaves differently from the standard's minimum; "Serializable" in one database may use locking and in another use optimistic validation with different performance and failure modes. You must know what *your specific database* does at your chosen level, not just the standard's table.

## Choosing a level, and defending against anomalies

Because higher isolation costs concurrency, the choice is a real trade-off — but it's one you must make *deliberately*, not by accepting a default you don't understand:

- **Understand your default and its allowed anomalies.** If you're on Read Committed (likely), you're exposed to lost updates and non-repeatable reads. Ask whether any of your logic assumes they can't happen.
- **Raise the level where correctness demands it.** For logic sensitive to write skew or phantoms (financial invariants, inventory, scheduling), use **Serializable** for that transaction and accept the cost. Correctness first.
- **Or defend explicitly at a lower level.** Rather than global serializable, prevent specific anomalies where they matter: `SELECT ... FOR UPDATE` (pessimistic locking) to prevent lost updates, atomic single-statement updates (`UPDATE ... SET balance = balance - 10`) instead of read-modify-write, unique constraints to prevent duplicate phantoms, or optimistic concurrency with a version column.
- **Handle serialization failures.** Serializable (and snapshot) isolation can *abort* a transaction that would violate isolation, expecting the application to **retry**. Code that uses these levels must be prepared to catch the error and retry the transaction.

The overarching lesson: transactions give strong guarantees, but *isolation is a spectrum you configure*, and the common defaults trade safety for speed in ways that bite applications assuming the database serialized everything. The next post explains the mechanism most modern databases use to provide isolation efficiently — MVCC — which is why your reads usually don't block even at higher isolation levels.

## Key takeaways

- A transaction provides ACID: atomicity and durability come largely from the WAL, consistency from constraints, and isolation is the hard, tunable guarantee that concurrent transactions don't corrupt each other.
- Perfect isolation (serializability = as-if-serial order) is expensive, so databases offer weaker levels that permit specific anomalies for more concurrency — and most databases do NOT default to serializable.
- The anomalies form a ladder: dirty read, non-repeatable read, phantom read, lost update, and write skew — the latter two cause real money/inventory bugs in apps that assumed the database "handles concurrency."
- The four levels (Read Uncommitted → Read Committed → Repeatable Read → Serializable) each prevent more anomalies; defaults vary (Read Committed in Postgres/Oracle/SQL Server, Repeatable Read in MySQL), and implementations differ from the standard — know what YOUR database does.
- Choose deliberately: understand your default's allowed anomalies, raise to Serializable where correctness demands (and retry on serialization failures), or defend specific anomalies with SELECT FOR UPDATE, atomic updates, constraints, or version columns.

## Further reading

- [PostgreSQL documentation — Transaction Isolation](https://www.postgresql.org/docs/current/transaction-iso.html)
- [Indexes (previous post)](/blog/posts/dbint-05-indexes.html)
- [Distributed Systems: Consistency Models](/blog/posts/distsys-02-consistency-models.html)
