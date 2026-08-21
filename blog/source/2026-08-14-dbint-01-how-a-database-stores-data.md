# How a Database Stores Data

*A database is not magic — it's a program that turns your rows into bytes on a disk and finds them again quickly, correctly, and without losing them when the power fails. Understanding the machine underneath the SQL is what separates someone who writes queries from someone who knows why they're slow.*

You type `SELECT * FROM users WHERE id = 42` and a row comes back in a millisecond. Between that query and the answer is a remarkable amount of engineering: a storage engine, pages, a buffer pool, a write-ahead log, indexes, a transaction manager, and a query planner. This series opens each of those boxes. It starts here, with the most fundamental question — how does a database actually keep your data on disk and get it back? — because every later topic is a refinement of this answer.

## The core problem

A database has to satisfy a set of requirements that are individually easy and collectively hard:

- **Persistence** — data must survive process restarts and, crucially, crashes and power loss.
- **Speed** — reads and writes must be fast even when the data is far larger than memory.
- **Correctness under concurrency** — many clients read and write at once without corrupting each other's data.
- **Efficient querying** — you can find the rows you want without scanning everything.

The tension at the heart of it all is the gap between **memory and disk**. Memory (RAM) is fast but volatile — it vanishes on power loss — and too small to hold most datasets. Disk (SSD/HDD) is durable and large but *orders of magnitude* slower than memory, especially for random access. Every design decision in a database is, at bottom, a strategy for getting durable storage on slow disk to *behave* like fast memory. Hold that framing and the rest of the series clicks into place.

## The layers of a database

It helps to see the whole stack before diving into any layer. A request flows top to bottom:

```text
        SQL query
           │
   ┌───────▼────────┐
   │ Query planner  │  parse, plan, optimize  →  execution plan
   ├────────────────┤
   │ Execution      │  run the plan: scans, joins, filters
   ├────────────────┤
   │ Transaction &  │  ACID: isolation, concurrency control (MVCC/locks)
   │ concurrency    │
   ├────────────────┤
   │ Storage engine │  B-tree / LSM: how rows become pages
   ├────────────────┤
   │ Buffer pool    │  cache of disk pages in memory
   ├────────────────┤
   │ Disk (files)   │  pages + write-ahead log, durably stored
   └────────────────┘
```

The bottom half — storage engine, buffer pool, disk, and the write-ahead log alongside them — is *how data is stored*, and it's the focus of the first half of this series. The top half — transactions, planning, execution — is *how data is accessed correctly and efficiently*, the second half. This post surveys the bottom.

## The storage engine

The **storage engine** is the component that actually reads and writes data on disk. It's a deliberately separable layer: the same SQL front-end can sit on different engines (MySQL famously supports several, like InnoDB), because "how do I lay bytes on disk and retrieve them" is a self-contained problem. The storage engine answers: how are rows grouped into on-disk structures, how are they found again, and how are writes made durable?

Two dominant families of storage engine exist, and the choice between them shapes a database's entire performance character:

- **B-tree engines** (the traditional default — PostgreSQL, InnoDB, most relational databases) update data *in place* in a balanced tree structure, optimized for reads and range scans.
- **LSM-tree engines** (log-structured merge trees — Cassandra, RocksDB, LevelDB) *append* writes and merge them later, optimized for high write throughput.

The next post is dedicated to this fork, because it's the single most consequential decision in a storage engine. For now: the engine's job is to map your logical rows onto physical on-disk structures and retrieve them efficiently.

## Everything is pages

Databases do not read and write your data one row or one byte at a time. They work in fixed-size blocks called **pages** (typically 4–16 KB). A page is the unit of transfer between disk and memory: to read one row, the database reads the *entire page* that row lives on; to change one row, it modifies the page in memory and eventually writes the whole page back.

Why pages? Because disk I/O has high fixed cost per operation — reading 8 KB costs almost the same as reading 100 bytes, since the expense is in *making the request*, not the bytes. Batching data into pages amortizes that cost. This single fact explains an enormous amount of database behavior: why row layout matters, why an index that lets you touch fewer pages is so valuable, and why "random" access patterns that scatter reads across many pages are so much slower than sequential ones that read pages in a row. When you optimize a database, you are very often really optimizing *how many pages it has to touch*.

## Memory as a cache: the buffer pool

Since disk is slow and pages are the unit of I/O, databases keep recently-used pages in memory in a cache called the **buffer pool** (or page cache). A read first checks the buffer pool; a **hit** is served from fast memory, and only a **miss** goes to disk (and loads that page into the pool for next time). Writes modify pages *in the buffer pool* first — marking them "dirty" — and flush to disk later, batched.

This is the mechanism that makes disk behave like memory: a well-tuned database serves the overwhelming majority of its reads from the buffer pool, hitting disk only for cache misses. The buffer pool's hit rate is one of the most important numbers in database performance, and it's why "just add more RAM" so often speeds up a database — more RAM means more of the working set fits in the pool. A later post details how the pool decides which pages to keep and evict.

## Durability lives in the log

There's a catch in "write to the buffer pool first, flush later": if the database crashes after acknowledging a write but before flushing the dirty page to disk, that write is *gone* — violating persistence. The solution, foundational enough to get its own post, is the **write-ahead log (WAL)**: before a change is considered done, the database appends a record of it to a sequential log file and flushes *that* to disk. The log is append-only (fast sequential writes) and is the source of truth for recovery — after a crash, the database replays the log to reconstruct any changes that hadn't yet reached their data pages. This is why a database can be both *fast* (defer the expensive random page writes) and *durable* (the cheap sequential log write already happened). The pattern — write the intent to a log first — recurs throughout systems engineering.

## Where the series goes

From this foundation, the first half of the series drills into storage: B-trees vs LSM-trees (the engine fork), pages and the buffer pool (memory management), and the write-ahead log (durability and crash recovery). The second half moves up the stack: indexes (finding rows without scanning), transactions and isolation (correctness under concurrency), MVCC (how modern databases isolate without blocking reads), and query planning (turning SQL into an efficient execution plan). Throughout, the recurring lens is the one from this post — memory is fast and scarce, disk is slow and durable, and a database is the art of reconciling the two.

## Key takeaways

- A database is a program that stores rows durably on slow disk and retrieves them quickly, correctly, and safely under concurrency — every design decision reconciles fast/volatile memory with slow/durable disk.
- The stack layers top-to-bottom: query planner → execution → transactions/concurrency → storage engine → buffer pool → disk (pages + WAL); the bottom half is "how data is stored," the top half "how it's accessed."
- The storage engine maps rows onto on-disk structures; the two dominant families are in-place B-tree engines (read/scan-optimized) and append-only LSM-tree engines (write-optimized).
- Databases read and write in fixed-size pages (not rows/bytes) to amortize the high fixed cost of disk I/O — so much optimization is really about minimizing how many pages get touched.
- The buffer pool caches pages in memory (serving most reads from RAM), and the write-ahead log makes deferred writes durable by recording the change sequentially before acknowledging — enabling a database to be both fast and crash-safe.

## Further reading

- [PostgreSQL documentation — Database Physical Storage](https://www.postgresql.org/docs/current/storage.html)
- [SQLite — How SQLite works / file format](https://www.sqlite.org/fileformat.html)
- [System Design Fundamentals series](/blog/series/system-design-fundamentals/)
