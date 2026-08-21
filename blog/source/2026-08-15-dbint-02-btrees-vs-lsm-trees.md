# B-Trees vs LSM-Trees

*Almost every database on earth stores its data in one of two structures: a B-tree that updates in place, or an LSM-tree that only ever appends. This one choice ripples through everything — read speed, write speed, space usage, and latency predictability — so knowing which your database uses tells you more about its behavior than almost anything else.*

The last post introduced the storage engine as the layer that puts rows on disk. Now we look at *how* — the two structures that dominate storage engines. A **B-tree** modifies data where it lives; an **LSM-tree** never modifies anything, only appends and merges. These aren't just implementation details: they produce databases with opposite performance personalities, and understanding the trade-off is the single most useful thing you can know about a storage engine.

## The B-tree: update in place

The **B-tree** (specifically the B+tree in most databases) is the traditional workhorse — the engine behind PostgreSQL, MySQL's InnoDB, SQL Server, and most relational databases. It's a balanced tree of pages, kept sorted by key:

```text
                 ┌─────────────┐
                 │  root page  │        (keys guide the search)
                 └──────┬──────┘
            ┌───────────┼───────────┐
      ┌─────▼────┐ ┌────▼─────┐ ┌───▼──────┐   internal pages
      │  keys →  │ │  keys →  │ │  keys →  │
      └────┬─────┘ └────┬─────┘ └────┬─────┘
       ┌───▼──┐    ┌────▼──┐    ┌────▼──┐
       │ rows │ .. │ rows  │ .. │ rows  │        leaf pages (actual data)
       └──────┘    └───────┘    └───────┘
```

To find a key, you start at the root and follow pointers down to the leaf — a handful of page reads even for a huge table, because the tree is *shallow and wide* (each page holds hundreds of keys, so a tree of depth 3–4 addresses billions of rows). To *change* a row, the B-tree finds the leaf page and modifies it **in place**.

The consequences:

- **Excellent reads.** A lookup is a few page reads; because leaves are sorted and linked, **range scans** are efficient — read consecutive leaf pages in order.
- **Writes cause random I/O.** Updating a row means finding and rewriting *its* page, wherever it happens to live on disk. Many writes to scattered keys mean many scattered page writes — random I/O, the slow kind.
- **Write amplification from page splits.** When a page fills, it must **split** into two, occasionally cascading up the tree, and every change is also written to the WAL first — so one logical row write can cause several physical writes.

The B-tree's bias is clear: it's optimized for **reads and range queries**, at the cost of write-time random I/O.

## The LSM-tree: only ever append

The **log-structured merge tree** (LSM-tree) — behind Cassandra, RocksDB, LevelDB, ScyllaDB, and many write-heavy stores — takes the opposite stance: **never update in place, only append.** Writes go to an in-memory sorted structure and a sequential log; the structure is periodically flushed to disk and merged in the background.

```text
write → [ memtable ]  (in-memory, sorted)  + append to WAL
             │  (when full, flush to disk as an immutable file)
             ▼
        SSTable L0 ──┐
        SSTable L0   │  background compaction merges & sorts
        SSTable L1 ──┘  →  fewer, larger, sorted files
        SSTable L2 ...
```

The pieces:

- **Memtable** — an in-memory sorted structure that absorbs writes (fast, no disk seek). A WAL append makes each write durable immediately.
- **SSTables** — when the memtable fills, it's flushed to disk as an immutable, sorted file (a Sorted String Table). SSTables are *never modified* after being written.
- **Compaction** — a background process merges SSTables, discarding overwritten and deleted keys, keeping the number of files bounded and the data sorted.

Because all writes are sequential appends (memtable + log, then sequential SSTable flushes), LSM-trees achieve **very high write throughput** — sequential I/O is far faster than the B-tree's random page updates.

The costs land on reads and background work:

- **Reads can touch multiple files.** A key might be in the memtable or *any* SSTable, so a read may check several places. **Bloom filters** (compact probabilistic sets) make this cheap by quickly ruling out SSTables that definitely don't contain the key, but reads are still generally more work than a B-tree lookup.
- **Compaction is ongoing overhead.** Merging SSTables consumes disk I/O and CPU in the background and can cause **latency spikes** when a big compaction competes with live traffic — a real operational consideration.
- **Deletes are tombstones.** You can't modify an SSTable to remove a key, so a delete writes a **tombstone** marker; the space is reclaimed only at the next compaction.

The LSM-tree's bias is the mirror image: optimized for **writes**, at the cost of read amplification and background compaction.

## Write amplification, read amplification, space amplification

The two designs trade along three "amplification" axes worth naming, because they're how you reason about the choice:

- **Read amplification** — how many physical reads per logical read. B-trees: low (one path down the tree). LSM-trees: higher (potentially several SSTables, mitigated by Bloom filters).
- **Write amplification** — how many physical bytes written per logical byte. B-trees: page rewrites + splits + WAL. LSM-trees: rewrite data repeatedly during compaction. Both amplify; which is worse depends on workload.
- **Space amplification** — extra disk beyond the logical data size. B-trees: pages are often partly empty (fragmentation from splits). LSM-trees: hold overwritten/deleted data until compaction reclaims it.

There is no free lunch: you cannot minimize all three at once, so each engine picks a point in the trade-off space. This is *why* two databases with identical SQL can behave completely differently under load.

## Choosing (or rather, understanding what you chose)

You rarely pick a raw storage structure directly — you pick a database, and it comes with one. But knowing which you have tells you how it will behave and how to use it well:

- **B-tree databases** (PostgreSQL, MySQL/InnoDB, most SQL databases) — reach for these when reads and range queries dominate, when you need strong single-row read latency and predictability, and for general-purpose workloads. This is the right default for most applications.
- **LSM-tree databases** (Cassandra, RocksDB-backed systems, ScyllaDB) — reach for these when write throughput is the binding constraint: heavy ingest, time-series, event logging, high-volume telemetry. Expect to account for compaction overhead and occasional latency spikes.

The deeper point for this series: the storage structure is the *root cause* of a database's performance character. When a database is surprisingly fast at ingest but variable on tail latency, that's an LSM-tree talking. When it's rock-steady on reads but you're fighting write throughput and bloat, that's a B-tree. The next posts — pages/buffer pool and the WAL — apply to *both* families, because both still work in pages and both still log ahead for durability.

## Key takeaways

- Storage engines are dominated by two structures: B-trees (update in place) and LSM-trees (append-only + background merge) — and the choice defines a database's whole performance personality.
- B-trees are shallow, sorted, balanced page-trees: excellent point reads and range scans, but writes cause random page I/O plus splits and write amplification — optimized for reads.
- LSM-trees absorb writes in an in-memory memtable + WAL, flush to immutable sorted SSTables, and compact in the background: very high (sequential) write throughput, but reads may touch multiple files (mitigated by Bloom filters) and compaction adds ongoing overhead and latency spikes.
- The trade-off is captured by three amplifications — read, write, and space — and no engine minimizes all three; each picks a point, which is why identical SQL behaves differently across databases.
- Choose B-tree databases (Postgres, InnoDB) for read/range-heavy general-purpose workloads (the usual default); choose LSM-tree databases (Cassandra, RocksDB) when write throughput is the binding constraint (ingest, time-series, logging).

## Further reading

- [PostgreSQL documentation — B-Tree indexes](https://www.postgresql.org/docs/current/btree.html)
- [How a database stores data (previous post)](/blog/posts/dbint-01-how-a-database-stores-data.html)
- [Event-Driven Architecture with Kafka series](/blog/series/event-driven-architecture-with-kafka/)
