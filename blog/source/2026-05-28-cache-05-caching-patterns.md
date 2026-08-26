# Caching Patterns

*Knowing to cache is one thing; wiring the cache into your application correctly is another. Should the application manage the cache itself, or should the cache sit transparently in front of the source? Should writes go to the cache, the database, or both — and in what order? These questions have standard answers — the caching patterns — and choosing the right one shapes your consistency, performance, and complexity. Getting the pattern right is how caching goes from "store some stuff" to a coherent, correct design.*

**Caching patterns** are the standard ways applications interact with a cache — how reads and writes flow between the application, the cache, and the source. This post covers the main read patterns (**cache-aside**, **read-through**) and write patterns (**write-through**, **write-back**, **write-around**), their tradeoffs, and how to choose. These patterns structure the read/write flow around a cache, building on the fundamentals (hits/misses) and invalidation (consistency) from earlier posts.

## Cache-aside (lazy loading)

The most common caching pattern is **cache-aside** (also "lazy loading") — the *application* manages the cache explicitly, loading data into it on misses:

- **The application manages the cache.** In cache-aside, the *application code* checks the cache, and on a miss, fetches from the source and populates the cache itself. The cache sits "aside" the source, and the app orchestrates the flow: *check cache → if hit, use it → if miss, fetch from source, store in cache, use it*. The application is in control of reading from and writing to the cache. It's explicit, app-managed caching.

```text
   Cache-aside read:
     app checks cache → HIT: use cached value
                      → MISS: app fetches from source → app stores in cache → use
```

- **Lazy loading: cache on demand.** Data is loaded into the cache *lazily* — only when it's actually requested (and missed). The cache fills up with data as it's accessed, holding just what's been requested. This means only *used* data gets cached (efficient — no caching of unrequested data), but the *first* access to any item always misses (a "cold" cache is all misses). Lazy loading populates the cache on demand.
- **Its tradeoffs.** Cache-aside is *simple, common, and resilient* (if the cache fails, the app can still go to the source directly — the cache is optional to the flow). Its downsides: the application code must *handle the caching logic* (check/populate — more app complexity), the *first access misses* (cold-start latency), and cached data can go *stale* (the app must handle invalidation — the previous post). Cache-aside is the default pattern for many applications because of its simplicity and resilience. It's the one you'll use most.

Cache-aside (lazy loading) — the application explicitly checks the cache, and on a miss fetches from the source and populates the cache — is the most common caching pattern: simple, resilient (cache-optional), and efficient (caches only used data), at the cost of app-side caching logic and first-access misses. A related pattern moves that logic into the cache itself.

## Read-through and write patterns

Beyond cache-aside, other patterns move caching logic into the cache layer or define how *writes* flow. The main ones:

- **Read-through: the cache loads on miss.** In *read-through*, the *cache itself* (not the application) handles loading from the source on a miss — the app just asks the cache, and the cache transparently fetches from the source if it doesn't have the data. This is like cache-aside but with the load logic *in the cache layer* (transparent to the app), simplifying application code (the app just reads from the cache). Read-through moves the miss-handling into the cache. (It requires cache infrastructure that supports this.)
- **Write-through: write to cache and source together.** For *writes*, *write-through* writes data to *both* the cache and the source *synchronously* (together) on every write — keeping the cache *consistent* with the source (no staleness, since both are updated together) and warm (written data is cached). Its cost: *every write is slower* (writing two places) and writes to data that may not be read (writing-through unread data). Write-through prioritizes consistency (cache always current) at write-cost. (This is a key invalidation strategy from the previous post.)
- **Write-back (write-behind): write to cache, source later.** *Write-back* writes to the *cache first* (fast) and to the *source later* (asynchronously, batched). This makes *writes fast* (only the cache synchronously) and can batch source writes efficiently — but risks *data loss* (if the cache fails before writing back to the source, unwritten data is lost) and adds complexity. Write-back prioritizes *write performance* at the cost of durability risk and complexity. It's used where write speed matters and some loss risk is acceptable.
- **Write-around: write to source, skip cache.** *Write-around* writes directly to the *source*, *bypassing the cache* (the cache is only populated on reads, cache-aside style). This avoids caching write-heavy data that may not be read (not polluting the cache with unread writes) — but means recently-written data *misses* on first read (it wasn't cached on write). Write-around suits write-heavy data that's not immediately re-read. It keeps the cache for read-hot data.

Read-through (the cache loads on miss, transparent to the app) and the write patterns — write-through (write cache+source together — consistent but slower writes), write-back (write cache first, source async — fast writes but loss risk), and write-around (write to source, bypass cache — avoids caching unread writes) — structure how reads and writes flow around the cache. Each makes different consistency/performance tradeoffs.

## Understanding the tradeoffs

The patterns differ along a few key dimensions — understanding these tradeoffs is how you reason about them:

- **Who manages the cache: app vs cache layer.** Cache-aside puts caching logic in the *application* (more app code, but flexible and resilient); read-through/write-through put it in the *cache layer* (simpler app code, but requires cache infrastructure support and couples you to it). Where the logic lives is one axis — app-managed (cache-aside) vs cache-managed (read/write-through). Cache-aside's app-management is more explicit and resilient; through-patterns are more transparent.
- **Consistency vs write performance (write patterns).** The write patterns trade *consistency* against *write performance*: write-through = consistent (cache always current) but slower writes; write-back = fast writes but risk of loss/staleness; write-around = avoids caching unread writes but recently-written data misses. Choosing a write pattern is choosing where on the consistency/write-performance spectrum to sit. Different write patterns for different write/consistency needs.
- **What gets cached: eager vs lazy, read vs write.** Patterns differ in *what* populates the cache: lazy (cache-aside/read-through — cache on read miss, only accessed data) vs eager on write (write-through — cache written data); and whether writes populate the cache (write-through) or not (write-around). This affects the cache's contents and hit rate for different access patterns. Match to whether written data is soon re-read.

The patterns' tradeoffs turn on *who manages the cache* (app vs cache layer), *consistency vs write performance* (the write patterns' spectrum), and *what gets cached* (lazy vs eager, whether writes populate). Understanding these axes lets you reason about which pattern fits — rather than memorizing patterns, understand the tradeoffs they make. Then choosing follows from the workload.

## Choosing a pattern

Selecting caching patterns depends on the read/write workload and consistency needs — practical guidance:

- **Cache-aside is the common default.** For most applications, *cache-aside* (lazy loading) is the sensible default — simple, resilient (cache-optional), and efficient (caches only accessed data). Start with cache-aside unless you have a specific reason for another pattern. It handles the common read-heavy case well. When in doubt, cache-aside.
- **Choose write patterns by consistency and write load.** For writes: use *write-through* when *consistency* matters (cache must stay current — worth the slower writes); *write-back* when *write performance* is critical and some loss risk is acceptable; *write-around* for *write-heavy data not soon re-read* (avoid polluting the cache). Match the write pattern to your consistency needs and write/read pattern. Consistency-critical → write-through; write-speed-critical → write-back; write-heavy-not-reread → write-around.
- **Combine patterns as needed.** Real systems often *combine* patterns — e.g. cache-aside for reads plus write-through or explicit invalidation for writes (to keep the cache consistent on updates). The read and write handling can be chosen somewhat independently. Combine to fit your reads and writes. It's not always one pure pattern.
- **Match to read/write balance and consistency.** Overall: read-heavy + staleness-tolerant → cache-aside with TTL (simple, effective); read-heavy + needs-freshness → cache-aside + explicit invalidation, or write-through; write-heavy → consider write-back (speed) or write-around (avoid cache pollution). The right pattern follows from your read/write balance and consistency requirements — the recurring theme of matching the approach to the workload.

Caching patterns — cache-aside (the common default: app-managed, lazy, resilient), read-through (cache-managed loading), and the write patterns write-through (consistent), write-back (fast writes), and write-around (bypass cache on write) — structure read/write flow around a cache with different consistency/performance/complexity tradeoffs, chosen by workload. Next: distributed caching — caching across multiple machines (Redis, Memcached).

## Key takeaways

- Cache-aside (lazy loading) is the most common pattern: the *application* checks the cache and on a miss fetches from the source and populates the cache itself — simple, resilient (the cache is optional to the flow, so the app survives cache failure), and efficient (caches only accessed data), at the cost of app-side caching logic and first-access misses.
- Read-through moves the miss-handling into the *cache layer* (the cache transparently loads from the source on a miss), simplifying app code but requiring supporting cache infrastructure.
- The write patterns trade consistency vs write performance: write-through (write cache+source together — cache always consistent but slower writes), write-back/write-behind (write cache first, source async — fast writes but risk of data loss if the cache fails), and write-around (write to source, bypass cache — avoids caching unread writes, but recently-written data misses on first read).
- The patterns differ along key axes — who manages the cache (app via cache-aside vs cache layer via through-patterns), consistency vs write performance (the write patterns' spectrum), and what gets cached (lazy on read vs eager on write) — so understand the tradeoffs rather than memorizing patterns.
- Choose by workload: cache-aside as the common default; write-through for consistency-critical writes, write-back for write-speed-critical (with loss risk), write-around for write-heavy-not-soon-reread data; combine read and write patterns as needed, matching read/write balance and consistency requirements.

## Further reading

- [Cache (computing) — read/write patterns (Wikipedia)](https://en.wikipedia.org/wiki/Cache_(computing))
- [Cache invalidation — write-through and consistency (previous post)](/blog/posts/cache-04-cache-invalidation.html)
- [Database Internals — buffer pools and write strategies](/blog/series/database-internals/)
