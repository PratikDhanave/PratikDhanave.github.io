# Pages and the Buffer Pool

*The buffer pool is where a database spends most of its memory and wins or loses most of its performance. It's a cache of disk pages in RAM, and the difference between a query that hits it and one that misses is the difference between a microsecond and a millisecond — a thousandfold gap that decides whether your database feels fast.*

The first post established that databases move data in fixed-size **pages** and cache them in memory in the **buffer pool**. This post opens that machinery: how a page is laid out, how the buffer pool decides what to keep in precious RAM and what to evict, and how dirty pages get safely back to disk. Everything here applies to both B-tree and LSM engines, because both ultimately read and write pages through a buffer pool.

## Anatomy of a page

A **page** (typically 8 KB in PostgreSQL, 16 KB in InnoDB) is the atomic unit of storage and I/O. Inside, it's not a raw dump of rows — it has structure that lets the database find and manage rows efficiently:

```text
┌──────────────────────────────────────────┐
│ header  (checksum, free-space pointers)   │
├──────────────────────────────────────────┤
│ slot array → → →                          │  pointers to each row
├───────────────────────┬──────────────────┤
│  free space           │                   │
├───────────────────────┴──────────────────┤
│      ← ← ←  row data (grows upward)        │
└──────────────────────────────────────────┘
```

Two design choices matter. First, the **slot array (slotted page)**: a small array of pointers to the actual rows, which lets rows vary in size and move within the page (during compaction) without invalidating references — the slot number stays stable. Second, the page tracks its own **free space**, so the engine knows whether a new row fits. This layout is why a row's physical location is really "page number + slot," and why databases can reorganize a page internally without the rest of the database noticing.

A practical consequence: **row size affects how many rows fit per page**, which affects how many pages a query touches. Wide rows (many columns, large values) mean fewer rows per page, more pages per scan, and more I/O. This is part of why selecting only the columns you need, and keeping rows lean, matters for performance.

## Why the buffer pool exists

Disk is slow; RAM is fast; the dataset is bigger than RAM. The **buffer pool** resolves this by keeping a subset of pages — ideally the *hot* ones — in memory. Every page access goes through it:

- **Read a page:** if it's in the pool (a **hit**), return it from RAM immediately. If not (a **miss**), read it from disk *into* the pool, evicting something if the pool is full, then return it.
- **Write a page:** modify the copy in the pool and mark it **dirty**; the actual disk write happens later (see below).

The **buffer pool hit ratio** — the fraction of page accesses served from memory — is one of the most important health metrics a database has. A high hit ratio means the working set fits in RAM and the database rarely touches disk; a low one means it's constantly paging from disk and will feel sluggish. This is the concrete reason "add more RAM" so reliably speeds up a database: a larger pool holds more of the working set, lifting the hit ratio.

## Eviction: deciding what to keep

The pool is finite, so when a miss needs to load a page and the pool is full, the database must **evict** an existing page to make room. Which one? The goal is to evict the page *least likely to be needed soon*, keeping hot pages resident.

The classic policy is **LRU (least recently used)** — evict the page unused for the longest — on the assumption that recently-used pages will be used again. But naive LRU has a notorious failure mode in databases: a single large sequential scan (e.g. a full-table scan for analytics) reads a flood of pages *once*, and pure LRU would let that flood evict the genuinely hot pages that serve normal traffic — the scan "pollutes" the cache. Real databases defend against this with smarter variants:

- **LRU-K / segmented LRU** — track the last *K* accesses, so a page touched once (a scan) isn't treated as hot; only pages accessed repeatedly earn protection.
- **Clock / second-chance** — an approximation of LRU that's cheaper to maintain at scale, giving each page a "recently used" bit and a second chance before eviction.
- **Scan-resistant designs** (e.g. PostgreSQL's ring buffers for large scans) — confine a big sequential scan to a small portion of the pool so it can't evict the whole working set.

The theme: eviction policy is where a database protects its hot working set from being flushed out by one-off bulk access — and it's why an occasional analytics query on a transactional database can temporarily hurt everyone else if the pool isn't scan-resistant.

## Dirty pages and flushing

When a write modifies a page in the pool, that page is now **dirty** — its in-memory version is newer than the disk version. Writing every dirty page to disk immediately would destroy write performance (random I/O per write) and throw away the benefit of batching. So databases **defer** flushing dirty pages and write them out in the background, in batches, at opportune times — a process often called **checkpointing**.

This is safe *only because of the write-ahead log* (the next post). The moment a change is made, its record is already in the WAL on disk, so even if the dirty page hasn't been flushed and the database crashes, the change can be recovered from the log. This decoupling is the key trick:

- The **WAL** provides durability with cheap *sequential* writes, immediately.
- The **buffer pool + deferred flushing** provides speed, batching the expensive *random* data-page writes and letting many changes to the same page coalesce into one flush.

A **checkpoint** periodically forces dirty pages to disk and records a safe recovery point, bounding how much log has to be replayed after a crash. There's a tuning tension here: frequent checkpoints mean fast recovery but more constant write I/O; infrequent checkpoints mean less steady I/O but longer crash recovery and larger I/O bursts when a checkpoint finally runs.

## What this means in practice

The buffer pool is where several practical performance truths originate:

- **Size the buffer pool to your working set.** The single biggest memory lever; enough RAM to hold the hot pages transforms performance. (Both PostgreSQL's `shared_buffers` and InnoDB's buffer pool size are among the first things to tune.)
- **Lean rows and narrow reads pay off.** Fewer bytes per row → more rows per page → fewer pages touched → higher effective cache density.
- **Beware cache-polluting scans.** A big one-off scan on a live OLTP database can evict the hot set; scan-resistant pools mitigate it, but it's a real cause of "why did the whole app slow down when that report ran?"
- **Understand your hit ratio.** A falling buffer-pool hit ratio is an early warning that your working set has outgrown RAM.

With pages and the buffer pool understood, the durability half of the story — how deferred writes survive a crash — is the write-ahead log, next.

## Key takeaways

- A page is a structured fixed-size block (8–16 KB) with a header, a slot array pointing to rows (so rows can vary in size and move internally), and tracked free space — and row width determines rows-per-page, hence how many pages a query touches.
- The buffer pool caches disk pages in RAM: reads are hits (from memory) or misses (fetched from disk into the pool); the buffer-pool hit ratio is a top performance metric, which is why more RAM reliably speeds up a database.
- When full, the pool evicts a page; naive LRU is polluted by one-off large scans, so databases use LRU-K/segmented LRU, clock/second-chance, or scan-resistant ring buffers to protect the hot working set.
- Writes dirty a page in memory and are flushed to disk later in batches (checkpointing), which is safe only because the WAL already recorded the change durably — decoupling cheap sequential durability from expensive deferred random data-page writes.
- Practically: size the buffer pool to the working set, keep rows lean, guard against cache-polluting scans, and watch the hit ratio as an early warning that the working set outgrew RAM.

## Further reading

- [PostgreSQL documentation — Database Page Layout](https://www.postgresql.org/docs/current/storage-page-layout.html)
- [B-Trees vs LSM-Trees (previous post)](/blog/posts/dbint-02-btrees-vs-lsm-trees.html)
- [System Design Fundamentals series](/blog/series/system-design-fundamentals/)
