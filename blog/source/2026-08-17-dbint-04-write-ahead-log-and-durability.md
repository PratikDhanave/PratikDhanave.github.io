# The Write-Ahead Log and Durability

*Durability — the promise that a committed transaction survives a crash — comes down to one deceptively simple rule: write down what you're about to do before you do it. The write-ahead log is that rule made concrete, and it's the reason a database can be both fast and crash-safe, two goals that otherwise pull in opposite directions.*

The last two posts left a loose end: databases modify pages in memory and flush them to disk *later*, which is fast but seems to risk losing writes in a crash. This post resolves it. The **write-ahead log (WAL)** is how a database guarantees that a committed change is never lost, even if the machine loses power a microsecond after the commit — and how it recovers a consistent state afterward. It's arguably the most important durability mechanism in all of data systems.

## The durability problem

Recall the setup: a write modifies a page in the buffer pool and marks it dirty; the dirty page is flushed to disk later, in a batch, to avoid slow random I/O per write. The danger is the gap between *acknowledging* a write to the client and *flushing* the page. If the database says "committed" and then crashes before the dirty page reaches disk, the change exists only in now-vanished RAM. That would violate **durability** — the D in ACID, the promise that once a transaction commits, it stays committed.

You could flush every changed page immediately, but that throws away the entire performance benefit of the buffer pool and turns every commit into random disk I/O. The WAL is the way to have durability *without* paying that price.

## The write-ahead rule

The principle is one line: **write the change to a log on disk before applying it to the data pages.** Concretely, before a transaction is acknowledged as committed:

1. A record describing the change (enough to redo it) is appended to the **WAL**.
2. That log record is **flushed to disk** (an `fsync`, forcing the OS to actually persist it, not just buffer it).
3. Only then is the commit acknowledged to the client.

The dirty *data* pages can still be written lazily, later. The magic is in what the log gives you: the log write is a small, **sequential append**, which is dramatically faster than the random page writes it defers — yet it's fully durable. So at commit time you pay for one cheap sequential fsync instead of several expensive random writes, and durability is still absolute.

```text
commit path:
   change → append record to WAL → fsync(WAL) → ACK client   ← durable HERE
                                                    │
   (data pages flushed to disk lazily, later, in batches)
```

Because the log records the *intent* of every change and is persisted first, the actual data pages on disk are allowed to lag — the log is the source of truth that can always reconstruct them.

## Crash recovery: replaying the log

The WAL's payoff comes at restart after a crash. On startup, the database doesn't know which dirty pages made it to disk and which didn't. So it **recovers** by consulting the log, using two conceptual passes drawn from the classic ARIES recovery approach:

- **Redo** — replay log records forward from the last checkpoint, re-applying every logged change to the data pages. This guarantees that every *committed* change is present on disk, including ones whose dirty pages never got flushed before the crash.
- **Undo** — roll back any changes belonging to transactions that were *in progress* (not committed) at the crash, so no partial transaction survives. This preserves **atomicity** — a transaction is all-or-nothing.

After redo + undo, the database is in a consistent state reflecting exactly the committed transactions and nothing else. This is why you can pull the power on a well-built database mid-write and it comes back correct: the log had already recorded enough to finish the committed work and unwind the unfinished work.

**Checkpoints** bound this recovery cost. A checkpoint flushes dirty pages up to a point and records "everything before here is safely on disk," so recovery only needs to replay log *after* the last checkpoint rather than from the beginning of time. The tuning tension from the previous post reappears: frequent checkpoints → fast recovery but steady write I/O; infrequent → less routine I/O but slower recovery.

## fsync: where durability actually happens

The entire guarantee hinges on one system call: **fsync** (or equivalent), which forces data through the operating system's cache and any disk buffers onto the physical storage medium. A plain `write()` only hands bytes to the OS page cache — they can sit there, unpersisted, and vanish in a power loss. Durability requires the fsync to *return* before the commit is acknowledged.

This is subtle and historically a source of real data-loss bugs:

- **fsync is expensive.** It's a genuine round-trip to durable storage, so it dominates commit latency. This is why committing many tiny transactions is slow (one fsync each) while batching work into fewer, larger transactions is faster (fsync amortized).
- **Group commit** is the standard optimization: the database batches the log flushes of many concurrent transactions into a *single* fsync, so throughput scales even though each commit still waits for durability.
- **Lying hardware breaks the guarantee.** If a disk or controller acknowledges an fsync before the data is truly persistent (e.g. a volatile write cache without power protection), the durability guarantee is silently void — a classic cause of "the database said committed but the data was gone after a power cut."

The lesson: durability is only as strong as the fsync actually reaching stable storage, which is why database and storage configuration around write caching and flushing matters so much in production.

## The WAL is more than durability

Once a database has a reliable, ordered log of every change, that log becomes useful far beyond crash recovery — a theme worth noticing because it recurs across data systems:

- **Replication** — followers can consume the primary's WAL to stay in sync (PostgreSQL streaming replication ships WAL records); the log *is* the replication stream, connecting directly to the [replication](/blog/posts/distsys-05-replication.html) mechanics from the distributed-systems series.
- **Point-in-time recovery** — archiving the WAL lets you restore a backup and replay the log up to any chosen moment, e.g. just before a bad `DELETE`.
- **Change data capture** — downstream systems (search indexes, caches, analytics) can tail the WAL to react to every change, turning the database's log into an event stream.

This is the same insight as Kafka's log or a distributed consensus log: an ordered, durable record of *what happened* is a foundational primitive you can build many things on. The WAL started as a durability trick and became the backbone of durability, replication, and integration all at once.

## Key takeaways

- Durability (committed changes survive crashes) conflicts with the speed of deferring dirty-page flushes; the write-ahead log resolves it by recording changes before applying them.
- The write-ahead rule: append a change record to the WAL and fsync it to disk *before* acknowledging the commit — a cheap sequential write that provides full durability while the expensive random data-page writes happen lazily.
- Crash recovery replays the log: redo re-applies committed changes whose pages may not have flushed (durability), and undo rolls back in-progress transactions (atomicity), leaving a consistent state; checkpoints bound how much log must be replayed.
- Durability physically depends on fsync reaching stable storage — it's expensive (dominating commit latency), optimized via group commit, and silently defeated by hardware that acknowledges flushes it hasn't persisted.
- An ordered durable log is a general primitive: the WAL also powers replication (followers consume it), point-in-time recovery, and change data capture — the same insight behind Kafka and consensus logs.

## Further reading

- [PostgreSQL documentation — Write-Ahead Logging (WAL)](https://www.postgresql.org/docs/current/wal-intro.html)
- [Pages and the buffer pool (previous post)](/blog/posts/dbint-03-pages-and-the-buffer-pool.html)
- [Distributed Systems: Replication](/blog/posts/distsys-05-replication.html)
