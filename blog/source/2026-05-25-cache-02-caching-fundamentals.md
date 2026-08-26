# Caching Fundamentals

*A cache lives or dies by one number: its hit rate. Every cache access is a small bet — that the data will be there (a hit, served fast) rather than missing (a miss, served slow, plus the overhead of caching it). Whether caching helps at all comes down to how often that bet pays off, and understanding hits, misses, and hit rate — and what you should and shouldn't cache — is the foundation of using caches effectively. Get these fundamentals right, and the rest of caching makes sense.*

Building on why caching exists, this post covers the **fundamentals** — the mechanics every cache shares: **hits and misses**, the crucial **hit rate**, how a basic cache works (the lookup flow), and what makes data *cacheable* (what to cache and what not to). These concepts underlie all the specific caching topics that follow (eviction, invalidation, patterns, distributed, web). Understanding them is understanding how caches actually behave.

## Hits and misses

The fundamental events in any cache are **hits** and **misses** — whether requested data is found in the cache:

- **Cache hit: found in the cache.** A *hit* is when requested data *is* in the cache — so it's served *fast* from the cache, avoiding the slow source. Hits are the whole point: they're where caching delivers its benefit (fast access, avoided expensive work). More hits = more benefit.
- **Cache miss: not in the cache.** A *miss* is when requested data is *not* in the cache — so it must be fetched from the *slow source* (recomputed, queried, fetched), and typically *added to the cache* for next time. A miss is slower than *no cache at all* (you check the cache, fail, then go to the source, then store it) — miss overhead is real. Misses are where caching costs without benefiting.
- **The basic lookup flow.** A cache read follows: *check the cache* → if *hit*, return the cached value (fast) → if *miss*, fetch from the source, *store it in the cache*, and return it (slow, but now cached for next time). This check-then-hit-or-miss flow is the fundamental cache operation. (Whether the application or the cache handles the fetch-on-miss defines caching *patterns* — a later post.)

```text
   Cache read:
     check cache → HIT?  → return cached value (fast)
                 → MISS? → fetch from source (slow) → store in cache → return
```

Hits (found, served fast — the benefit) and misses (not found, fetched slowly and cached — the cost) are the fundamental cache events, with the basic flow being check-cache → hit-or-miss. The *balance* of hits to misses determines whether caching helps — which is measured by the hit rate.

## Hit rate: the key metric

The single most important cache metric is the **hit rate** — the fraction of accesses that are hits — because it determines whether (and how much) caching helps:

- **Hit rate = hits / total accesses.** The hit rate is the proportion of cache accesses that *hit* (found in cache) rather than miss. A high hit rate (most accesses hit) means the cache is *effective* — serving most requests fast. A low hit rate (most miss) means the cache is *ineffective* — rarely helping, mostly adding miss overhead. Hit rate is the headline measure of a cache's value. (The complement is the miss rate.)
- **Hit rate determines the benefit.** Caching's benefit is *proportional to the hit rate*: high hit rate → most requests served fast → big benefit; low hit rate → few requests helped → little benefit (and possibly net harm from miss overhead). A cache only helps if its hit rate is high enough that the hits' savings outweigh the misses' overhead. So *maximizing hit rate* is the central goal of cache design. Everything (what to cache, cache size, eviction) aims at a high hit rate.
- **What drives hit rate.** Hit rate depends on *locality* (how reused/skewed the access is — from the previous post: skewed access enables high hit rates), *cache size* (bigger cache holds more, higher hit rate — with diminishing returns), and *eviction policy* (keeping the *right* data cached — the next post). Understanding hit rate means understanding these drivers. A well-designed cache (right data, adequate size, good eviction) achieves a high hit rate on workloads with good locality. Poor locality or a too-small/badly-managed cache yields a low hit rate.

Hit rate (hits / total accesses) is the key cache metric — it determines whether caching helps (high hit rate = effective, low = ineffective or harmful), so maximizing it is the central goal, driven by locality, cache size, and eviction policy. Measuring and optimizing hit rate is fundamental to caching. Achieving a high hit rate starts with caching the *right* things.

## What to cache

A high hit rate requires caching the *right* data — and knowing what makes data a good caching candidate is fundamental:

- **Cache the frequently-accessed (hot) data.** Cache data that's *accessed often* — the hot, popular, frequently-requested items — because those are the accesses that will *hit* (be reused). Caching hot data gives a high hit rate (the skewed-access insight: cache the popular minority to serve most requests). Caching rarely-accessed data wastes cache space on things that won't be reused (low hit contribution). Prioritize the hot data.
- **Cache the expensive-to-obtain data.** Cache data that's *expensive* to fetch or compute (slow queries, heavy computations, network calls) — because caching it saves the most cost per hit. Caching cheap-to-obtain data saves little (the miss wasn't costly anyway). So the best candidates are *both* frequently-accessed *and* expensive to obtain — maximum benefit per cache slot. Reuse × cost is the value of caching an item.
- **Cache the staleness-tolerant data.** Cache data that can tolerate being *slightly stale* — because cached data can lag the source (the invalidation problem). Data that *must* be perfectly current is a poor caching candidate (you'd have to invalidate constantly). Data that's fine slightly stale (most content, computed aggregates, popular records) caches well. Staleness tolerance is a key criterion. Perfectly-consistent-required data resists caching.

What to cache: data that's frequently accessed (hot — for hit rate), expensive to obtain (for benefit per hit), and staleness-tolerant (for feasibility) — the best candidates are all three (reused, costly, tolerant). Caching the right data (not everything) is how you achieve a high hit rate and real benefit. Equally important is knowing what *not* to cache.

## What not to cache, and cache sizing

The complement — what *not* to cache, and how cache *size* matters — completes the fundamentals:

- **Don't cache rarely-accessed data.** Data accessed *infrequently* rarely hits (little reuse), so caching it wastes cache space and adds overhead for negligible benefit. Caching cold data lowers the effective hit rate (it displaces hot data or just sits unused). Don't cache what won't be reused. Cold data doesn't belong in the cache.
- **Don't cache constantly-changing or must-be-fresh data.** Data that changes *constantly* or must be *perfectly current* is a bad caching candidate — it's always stale (or requires constant invalidation), so the consistency cost dominates any benefit. Caching rapidly-changing or freshness-critical data causes staleness bugs for little gain. Don't cache what you can't keep consistent enough. (The invalidation post covers this hard problem.)
- **Cache size and the eviction consequence.** Caches are *bounded* (finite, faster-but-smaller storage — that's the point). So you *can't cache everything* — the cache holds only a subset, and when full, adding new data requires *evicting* something (the eviction post). Cache *size* affects hit rate (bigger cache holds more hot data → higher hit rate, with diminishing returns) and cost (bigger cache costs more). Sizing the cache (big enough for a good hit rate, not wastefully large) is a fundamental tradeoff. Because caches are bounded, *what to keep and what to evict* becomes central — the next post's topic.
- **The fundamental tradeoffs.** Caching balances *hit rate* (benefit) against *cost* (cache size, complexity) and *consistency* (staleness risk). The fundamentals — hits/misses, hit rate, what to cache, sizing — all serve navigating these tradeoffs: cache the right (hot, expensive, tolerant) data in an appropriately-sized cache to get a high hit rate, accepting bounded size (hence eviction) and staleness risk (hence invalidation). These tradeoffs recur throughout the series.

Caching fundamentals — hits (fast, the benefit) and misses (slow, the cost), the hit rate (the key metric determining caching's value, maximized by caching hot/expensive/tolerant data in an adequately-sized cache), and the bounded-cache reality (can't cache everything, hence eviction) — are the foundation of all caching. Cache the right data for a high hit rate, and know what not to cache. Next: eviction policies — deciding what to keep when the cache is full.

## Key takeaways

- The fundamental cache events are hits (requested data is in the cache — served fast, the benefit) and misses (not in the cache — fetched slowly from the source and stored for next time — the cost, slower than no cache due to overhead); the basic flow is check-cache → hit (return cached) or miss (fetch, store, return).
- Hit rate (hits / total accesses) is the single most important cache metric — it determines whether caching helps (high hit rate = effective; low = ineffective or net-harmful from miss overhead) — so maximizing hit rate is the central goal of cache design, driven by locality, cache size, and eviction policy.
- Cache the right data for a high hit rate: frequently-accessed (hot — the accesses that hit), expensive-to-obtain (max benefit per hit), and staleness-tolerant (feasible to cache) — the best candidates are all three (reuse × cost, tolerant).
- Don't cache rarely-accessed data (little reuse — wastes space, lowers effective hit rate) or constantly-changing/must-be-fresh data (always stale or requires constant invalidation — consistency cost dominates).
- Caches are bounded (finite fast-but-small storage — the point), so you can't cache everything: cache size affects hit rate (bigger → higher, with diminishing returns) and cost, and a full cache must evict to add new data (the next topic) — the fundamental tradeoffs balance hit rate (benefit) against cost (size/complexity) and consistency (staleness).

## Further reading

- [Hit rate (Wikipedia)](https://en.wikipedia.org/wiki/Hit_rate)
- [Cache (computing) (Wikipedia)](https://en.wikipedia.org/wiki/Cache_(computing))
- [Why caching exists (previous post)](/blog/posts/cache-01-why-caching-exists.html)
