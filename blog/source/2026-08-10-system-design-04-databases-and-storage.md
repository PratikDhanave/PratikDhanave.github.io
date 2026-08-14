# Databases and Storage

*Choosing and scaling the data layer without cargo-culting: how to pick relational versus NoSQL by access pattern, why every index is a tax on writes, and why your shard key is the highest-stakes decision you will make.*

---

Every system eventually becomes a database problem. The application code changes weekly; the data model outlives three rewrites. Choose the storage engine well and most of your scaling worries stay boring. Choose it badly — the wrong shape, the wrong index strategy, the wrong shard key — and you inherit a migration project that ships once a year and terrifies everyone.

This is the data-layer chapter of the System Design Fundamentals series, and it is deliberately trade-off-driven: there is no "best" database, only one that fits *this* access pattern. We will walk the decisions that matter most — the data model, indexing, normalization, replication, and partitioning — then close with why transactions are the hardest thing to keep once data spans machines.

---

## Start from the access pattern, not the logo

The most expensive mistake in system design is picking a database because it is popular, then reshaping the problem to fit it. Do the reverse. Write down how the data is actually read and written *before* you name an engine:

- What are the top few queries by volume and by latency sensitivity?
- Do you read by primary key, or filter and sort on many fields?
- What is the read-to-write ratio — 100:1 (a content site) or 1:1 (a ledger)?
- How large does a single record get, and does it fan out into related records?
- What consistency does the business actually require — can a user tolerate a slightly stale value?

Answer those and the model usually chooses itself. A few honest defaults:

- **Relational (Postgres, MySQL)** fits almost everything with structured, related data and ad-hoc queries — joins, transactions, secondary indexes, and a mature query planner for free. Modern Postgres also has first-class `JSONB` columns, so "some of my data is schemaless" is *not* on its own a reason to leave. Reach for relational first and make NoSQL earn its place.
- **Document (MongoDB, DynamoDB)** fits self-contained aggregates you fetch and store whole — a product with its variants, a user profile with its settings. If you never join across documents and always load the whole thing by id, a document store maps cleanly.
- **Key-value (Redis, DynamoDB)** fits pure lookup by a known key: sessions, feature flags, caches, rate-limit counters. Blazing on `GET`/`PUT`, useless when you must ask "which keys match this filter."
- **Wide-column (Cassandra, Bigtable, ScyllaDB)** fits massive write volume and queries you can express as "give me this partition, sorted by this clustering key" — time series, event logs, feeds. You design the table around one query and it serves that query at enormous scale; ask a second, unplanned query and you are stuck.
- **Graph (Neo4j)** fits data where the *relationships* are the query: "friends of friends who liked X," fraud rings, dependency graphs. If you find yourself writing recursive self-joins, a graph engine may pay off.

**The gotcha:** "NoSQL = scalable" is a myth. NoSQL engines scale by making you commit to your access pattern up front — you trade the query flexibility of SQL (and often strong consistency) for horizontal throughput. That is a real trade, not a free upgrade. A well-indexed Postgres instance on a big box serves a shocking amount of traffic and still answers questions you did not anticipate at design time. Don't leave that behind until a specific access pattern forces you to.

---

## Indexing: the read/write bargain

An index is a secondary data structure that lets the engine find rows without scanning the whole table. How the common ones work tells you when each helps.

**B-tree** is the default in Postgres and MySQL (InnoDB). It keeps keys sorted in a balanced tree, so lookups, range scans (`WHERE created_at > ...`), and `ORDER BY` on the indexed column are all fast — roughly logarithmic. This is the workhorse; when in doubt, it is a B-tree.

**Hash** indexes map a key through a hash function to a bucket, answering exact-match equality (`WHERE id = ?`) in near-constant time but doing no ranges or ordering — the hash destroys sort order. Niche compared to B-trees.

**LSM-tree** (log-structured merge-tree) powers Cassandra, RocksDB, and LevelDB. Instead of updating in place, it buffers writes in memory (a memtable), then flushes them as immutable sorted files (SSTables) merged in the background (compaction). Writes are fast because they are sequential appends; reads may check several files, mitigated by Bloom filters. This is why write-heavy stores absorb huge ingest rates — they turn random writes into sequential ones.

The mental model: **B-trees favor reads and in-place updates; LSM-trees favor write throughput at the cost of read and compaction overhead.**

Two index shapes earn their keep in relational systems. A **composite index** covers multiple columns in order, and order matters — an index on `(tenant_id, created_at)` serves `WHERE tenant_id = ? ORDER BY created_at` and `WHERE tenant_id = ?`, but *not* a query filtering on `created_at` alone (the leftmost-prefix rule). A **covering index** includes every column a query needs, so the engine answers straight from the index without touching the table (an "index-only scan" in Postgres, via `INCLUDE`).

```sql
-- Serve the hot query: a tenant's recent orders, newest first,
-- returning only the columns the list view needs.
CREATE INDEX idx_orders_tenant_recent
    ON orders (tenant_id, created_at DESC)
    INCLUDE (status, total_cents);

-- This query is now index-only: no heap fetch.
SELECT status, total_cents
FROM orders
WHERE tenant_id = 42
ORDER BY created_at DESC
LIMIT 20;
```

**The gotcha:** every index you add speeds *some* reads but taxes *every* write and costs storage. On each `INSERT`/`UPDATE`/`DELETE` the engine must also update every affected index, and each index is a full extra copy of its columns on disk. Index the queries you actually run, measure with `EXPLAIN ANALYZE`, and delete indexes nothing uses — an unused index is pure cost.

---

## Normalization versus denormalization

Normalization means storing each fact exactly once and referencing it by key. A normalized schema has a `users` table and an `orders` table with a `user_id` foreign key; a user's email lives in one place. This keeps writes cheap and correct — change the email once and every order reflects it — and it is the right default for transactional systems.

The price is that reads reassemble data with joins. When one page needs a user, their orders, each order's line items, and each item's product, you join five tables per request. At low volume the planner handles this effortlessly; at high volume, on data spread across shards, those joins get expensive or become impossible.

**Denormalization** trades storage and write complexity for read speed: you duplicate data so a read touches one place. Store the product name *inside* each order line so rendering an order needs no product join. Precompute a follower count instead of `COUNT(*)`-ing a relationship table on every profile view. Wide-column and document stores lean into this hard — one table per query, the same fact living in several tables.

The cost is drift. Rename a product and every denormalized copy is stale until you update it, and keeping copies in sync is your job, not the database's. Denormalize deliberately, for a measured read hotspot, and be explicit about how the copies get refreshed.

**The gotcha:** normalize first, denormalize later with evidence. Premature denormalization sprinkles duplicate fields everywhere "for speed," and you spend the rest of the project fixing consistency bugs where the copies disagree. Start correct and single-sourced; duplicate only the specific fields feeding a proven-hot read path.

---

## Replication: read scale and availability, with a catch

Replication keeps copies of your data on multiple machines, for two reasons: **availability** (a replica takes over if the primary dies) and **read scale** (spread reads across copies). Three topologies exist, differing in where writes are allowed.

**Leader-follower** (primary-replica, single-leader) is the common case: one node accepts all writes and streams its change log to read-only followers. Postgres streaming replication, MySQL replication, and most managed databases default to this. It is simple and gives strong ordering, because a single node decides the order of all writes. The limit is write throughput — one leader — and failover, where promoting a follower after the leader dies needs care to avoid split-brain.

**Multi-leader** allows writes on more than one node, typically one leader per region so each writes locally. It improves write availability and local latency but introduces **conflicts**: two leaders can edit the same row concurrently, so you need a reconciliation rule — last-write-wins, application merge, CRDTs. Use it when geographic write locality genuinely matters and you can tolerate that.

**Leaderless** (Dynamo-style, as in Cassandra and DynamoDB) drops the leader entirely: clients write to several replicas and read from several, using quorums to decide what is current. If you write to `W` replicas and read from `R` out of `N`, and `W + R > N`, a read overlaps a recent write and sees it. This buys excellent availability and tunable consistency, at the cost of client-side complexity and repair mechanisms that converge divergent replicas.

Whatever the topology, replication is asynchronous by default, which means **replication lag**: a follower runs some milliseconds — or, under load, seconds — behind the leader. Write a value, immediately read it from a lagging follower, and you may not see your own write.

**The gotcha:** replication gives you read scale and high availability, but the lag means followers serve *stale reads*. That is not a bug to fix; it is a consistency choice you make, often implicitly, the moment you route reads to replicas. Whether "read your own writes," "monotonic reads," or "eventual is fine" is acceptable is a business decision — and exactly the subject of the next post in this series on consistency models. Decide it on purpose, not by accident of your connection pool.

---

## Partitioning and sharding: the highest-stakes decision

Replication copies the whole dataset to each node. **Partitioning** (sharding) splits it so each node holds only a slice. You shard when one machine can no longer hold the data or serve the write volume — no replica helps, because every replica still holds everything. The decisive question is: how do you split the rows? That choice is the *shard key*.

**Range partitioning** splits by contiguous key ranges — users A–F on shard 1, G–M on shard 2. Range scans within a partition stay efficient because related keys sit together. The danger is hotspots: if the key is a timestamp, all of *today's* writes land on the newest partition while the rest idle. Bigtable and HBase partition by key range and manage this by splitting hot ranges.

**Hash partitioning** runs the key through a hash and assigns by the result, scattering rows evenly — what Cassandra and DynamoDB do by default (via a partition key). The trade-off is you lose efficient range scans: adjacent keys land on different nodes, so "give me all records between X and Y" becomes a scatter-gather across every shard.

Choosing the shard key is where systems live or die. A good key spreads both **data and load** evenly and keeps the queries you run most on a single shard. A poor key creates a **hot shard** — one node drowning while the others idle — usually from low cardinality (sharding orders by `country` when 60% are one country) or a skewed access pattern (sharding by `celebrity_user_id` when one account gets millions of reads). Skew, not average load, is what pages you at 3 a.m.

And here is the part people underestimate: **resharding is brutal.** Changing the shard key, or splitting one shard into two, means moving enormous volumes of live data while still serving traffic, often via a dual-write-and-backfill migration that runs for weeks with no clean rollback. Consistent hashing (Dynamo-style) makes *adding nodes* far less painful by moving only a fraction of keys — but changing the shard *key itself* is still a migration from scratch.

**The gotcha:** the shard key is the highest-stakes decision in your data layer, and the wrong one is extraordinarily expensive to change later. Choose it for the access pattern you will have at scale, not at launch: prefer a high-cardinality key that colocates your dominant query, and model your top few queries against candidate keys on paper *before* you commit. If two query patterns genuinely conflict, that tension is a signal to reconsider the whole storage choice, not to pick a key and hope.

---

## Transactions: ACID, and why "distributed" breaks it

A transaction groups operations so they succeed or fail together. The classic guarantee is **ACID**:

- **Atomicity** — all operations commit or none do; no half-applied transfer.
- **Consistency** — the transaction moves the database from one valid state to another, respecting constraints.
- **Isolation** — concurrent transactions do not step on each other; the result is as if they ran in some serial order (weaker isolation levels trade strictness for concurrency).
- **Durability** — once committed, it survives a crash.

A single-node relational database gives you all four almost for free — a large part of why relational systems remain the sane default. The trouble starts when a transaction must span multiple nodes or services: two shards, or a database plus a message queue.

The textbook cross-node answer is **two-phase commit (2PC)**: a coordinator asks every participant to *prepare* (promise they can commit), and only if all say yes does it tell them to *commit*. It is correct, but costly. Participants hold locks from prepare until commit, so throughput suffers under contention, and the coordinator is a failure point — if it dies after prepare, participants are stuck holding locks, uncertain whether to commit or abort ("in-doubt"). It works, but it does not scale gracefully, which is why high-throughput systems avoid it.

The common alternative is the **saga**: instead of one atomic distributed transaction, model the workflow as a sequence of *local* transactions, each with a compensating action that undoes it. Book the flight, charge the card, reserve the hotel — and if the hotel step fails, run compensations to refund the card and cancel the flight. Sagas give you availability and loose coupling, but they surrender isolation: intermediate states are visible (the card was briefly charged), and you must design every compensation, including the awkward cases where an action cannot be cleanly undone. You trade a strong guarantee for a workable one.

| Approach | Guarantee | Cost / trade-off | Fits |
|---|---|---|---|
| Single-node ACID | Full ACID | Bounded by one machine | Default; most OLTP |
| Two-phase commit | Atomic across nodes | Locks held across phases; coordinator is a failure point | Few participants, low contention |
| Saga | Eventual, per-step atomic | No isolation; must write compensations | Long, cross-service workflows |

**The gotcha:** distributed transactions are hard because atomicity across independent machines fights availability — the more nodes that must agree synchronously, the more ways the whole thing stalls or fails. Keep data that must change together on the *same* node whenever you can (another argument for a well-chosen shard key), so a plain local transaction covers it. Reach for 2PC only with few participants and low contention, and for sagas when a workflow genuinely spans services and you can define clean compensations.

---

## Key takeaways

- **Pick the database by access pattern, not popularity.** Write down your top queries, read/write ratio, and consistency needs first; relational-with-JSON covers most systems, and NoSQL must earn its place by a specific pattern.
- **Every index is a bargain.** It speeds some reads but taxes every write and costs storage — index the queries you run, use composite and covering indexes deliberately, and drop what nothing uses.
- **Normalize first, denormalize with evidence.** Single-source your data for correctness; duplicate only the fields feeding a measured, hot read path, and own the sync.
- **Replication buys read scale and availability — and lag.** Stale reads from followers are a consistency choice, not a bug; decide it on purpose (see the next post).
- **The shard key is the decision that outlives everything.** Choose for scale-era load, avoid low-cardinality and skewed keys, and remember resharding is a weeks-long migration with no clean undo.
- **Keep data that changes together on one node.** Local ACID beats 2PC's locks and sagas' lost isolation whenever your data layout allows it.

---

## Further reading

- [PostgreSQL Documentation: Indexes](https://www.postgresql.org/docs/current/indexes.html) — the authoritative reference on B-tree, hash, and other index types, plus index-only scans.
- [PostgreSQL Documentation: Data Partitioning](https://www.postgresql.org/docs/current/ddl-partitioning.html) — range and hash partitioning in a relational engine, from the source.
- [Dynamo: Amazon's Highly Available Key-value Store (2007)](https://www.allthingsdistributed.com/files/amazon-dynamo-sosp2007.pdf) — the paper behind leaderless replication, consistent hashing, and quorum reads/writes.
- [Bigtable: A Distributed Storage System for Structured Data (2006)](https://research.google/pubs/bigtable-a-distributed-storage-system-for-structured-data/) — Google's wide-column design and the origin of the SSTable/LSM lineage.
- [Apache Cassandra Documentation: Storage Engine](https://cassandra.apache.org/doc/latest/cassandra/architecture/storage-engine.html) — memtables, SSTables, and compaction: LSM-trees in a production engine.
- [Amazon DynamoDB Developer Guide: Partitions and Data Distribution](https://docs.aws.amazon.com/amazondynamodb/latest/developerguide/HowItWorks.Partitions.html) — how partition keys map to storage and why key choice governs hot partitions.
- [The Log-Structured Merge-Tree (O'Neil et al., 1996)](https://www.cs.umb.edu/~poneil/lsmtree.pdf) — the original LSM-tree paper explaining the write-optimized structure.
