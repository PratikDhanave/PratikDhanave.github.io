# Why Caching Exists

*There's an old joke that there are only two hard things in computer science: cache invalidation and naming things. It's a joke because caching is everywhere and sounds simple — just keep a copy of stuff you'll need again — and it's true because getting caching right is genuinely, surprisingly hard. Caching is one of the most universal and powerful ideas in computing, appearing at every layer from CPU to CDN, and understanding why it exists and when it helps is foundational to building fast systems.*

This series is a practical guide to **caching systems** — the idea of storing reused data in a faster place to make systems faster and cheaper, and how to do it well. It's aimed at engineers who use caching (which is nearly everyone) and want to understand it deeply. This first post covers the fundamental idea of caching, why it works (locality), its connection to the memory hierarchy, and when caching helps (and when it doesn't) — setting up the series on fundamentals, eviction, invalidation, patterns, distributed caching, web/CDN caching, and pitfalls.

## What caching is

**Caching** is storing a copy of data (or a computed result) in a *faster-to-access* place, so that future requests for it can be served *quickly* from the cache instead of *slowly* from the original source. The fundamental idea:

- **Keep reused data in a faster tier.** A cache is a *faster, smaller* store that holds *frequently- or recently-used* data, so repeated accesses get it *fast* (from the cache) instead of *slow* (recomputing or refetching from the original, slower source). It trades a little fast storage for a lot of saved time on repeated access. That's the whole core idea: store what you'll reuse somewhere fast.
- **It avoids repeating expensive work.** The point is to *avoid redoing* expensive operations — an expensive computation, a slow database query, a network fetch — by *remembering the result* and reusing it. The first time you pay the full cost (and cache the result); subsequent times you get it cheaply from the cache. Caching turns repeated expensive work into one expensive operation plus many cheap lookups. It's memoization at a system level.
- **It's a universal pattern.** Caching appears *everywhere* in computing — CPU caches, memory, disk caches, database buffer pools, application caches, web caches, CDNs, DNS — at every layer. The same idea ("keep reused data in a faster tier") recurs at every scale. This universality makes caching one of the most important patterns to understand: it's a fundamental technique applied throughout computing. Once you see it, you see it everywhere.

Caching is storing reused data/results in a faster tier to serve repeated accesses quickly instead of redoing expensive work — a universal pattern appearing at every layer of computing. It's a fundamental performance technique. The reason it works comes down to a property of how data is actually accessed: locality.

## Why caching works: locality

Caching works because of **locality of reference** — the empirical fact that data access is *not* uniformly random but tends to *reuse* the same and nearby data. Without locality, caching wouldn't help:

- **Temporal locality: reuse over time.** Data accessed *recently* is likely to be accessed *again soon* — the same items get requested repeatedly (a popular product, a hot database row, a frequently-called function's result). Because of this, *caching recently-used data* pays off: you're likely to need it again, and the cache has it ready. Temporal locality is why caching recent data works.
- **Spatial locality: nearby data.** Data *near* recently-accessed data is likely to be accessed soon (the next array element, related records). This is why caches sometimes fetch *neighboring* data too (like CPU cache lines). Spatial locality is a secondary reason caching helps (prefetching neighbors).
- **The 80/20 reality: skewed access.** In practice, access is *highly skewed* — a small fraction of the data gets the vast majority of the accesses (a few popular items dominate). This means a *small* cache holding the *popular* items can serve *most* requests — you don't need to cache everything, just the hot minority. This skew (Pareto-like) is *why a small cache is so effective*: caching the hot 20% serves 80%+ of requests. Skewed access is the practical foundation of caching's effectiveness.

Caching works because of locality — data access reuses the same (temporal) and nearby (spatial) data, and is highly *skewed* (a small hot subset dominates access) — so a small, fast cache holding the popular data serves most requests. Without this locality, caching wouldn't help; with it (as real access patterns have), caching is enormously effective. This is fundamentally the memory-hierarchy idea, generalized.

## The memory hierarchy connection

Caching is the *general form* of the **memory hierarchy** idea (from computer architecture / the operating-systems series) — recognizing this connects caching to a deep, universal principle:

- **The memory hierarchy is caching in hardware.** Computer memory is a *hierarchy* — fast-tiny (CPU registers, cache) to slow-huge (RAM, disk) — where each faster level *caches* the most-likely-used data from the slower level below (CPU cache holds hot RAM data; RAM holds hot disk data). The memory hierarchy *is* caching, built into hardware: keep likely-used data in faster tiers. It's the hardware instance of the caching pattern.
- **The same principle, everywhere.** The principle — "keep what you'll reuse in a faster, smaller tier" — that makes the memory hierarchy work is *exactly* the caching principle, and it recurs at every level: CPU caches (cache RAM), database buffer pools (cache disk pages in RAM), application caches like Redis (cache database results), CDNs (cache origin content near users), browser caches (cache web resources locally). All are the *same idea* at different scales. Caching is this one universal principle applied throughout the stack.
- **Understanding one illuminates all.** Because it's the same principle, understanding caching illuminates the memory hierarchy, and vice versa — and understanding it at one level (say, Redis caching a database) transfers to others (CPU caching RAM, a CDN caching an origin). This universality is why caching is such a valuable concept: learn it once, recognize it everywhere. It's a foundational pattern of computing. (The OS series' memory-hierarchy post covers the hardware end; this series covers caching broadly.)

Caching is the general form of the memory-hierarchy principle — "keep what you'll reuse in a faster, smaller tier" — which recurs at every level of computing (CPU caches, buffer pools, Redis, CDNs, browsers). Recognizing caching as this one universal principle applied throughout the stack is a powerful unifying insight. But caching isn't always the right tool.

## When caching helps (and when it doesn't)

Caching is powerful but not always appropriate — knowing *when* it helps is essential, because inappropriate caching adds complexity and problems for little gain:

- **Caching helps when data is reused and expensive to get.** Caching pays off when (1) the same data is *accessed repeatedly* (locality/reuse — so the cache gets used), and (2) getting it is *expensive* (slow computation, slow query, network fetch — so caching saves real cost). Repeated access to expensive-to-obtain data is the sweet spot. If data is reused and costly to fetch/compute, caching gives big wins (faster responses, less load on the source, lower cost). This is when to cache.
- **Caching helps read-heavy, tolerant workloads.** Caching suits *read-heavy* workloads (lots of reads of the same data) and data that can tolerate being *slightly stale* (the staleness problem — the invalidation post). Read-heavy access to cacheable, staleness-tolerant data is ideal. Most web content, computed results, and popular records fit this.
- **Caching hurts when data changes constantly or isn't reused.** Caching is *counterproductive* when data is *rarely reused* (the cache rarely hits — no benefit, just overhead) or *changes constantly* (the cache is always stale or must be invalidated constantly — the consistency problem dominates). Caching frequently-changing or rarely-reused data adds complexity and staleness risk for little gain. Don't cache what isn't reused or is always changing. It's the wrong tool there.
- **Caching always adds complexity and consistency risk.** Crucially, caching is *not free*: it adds a *copy* of data that can become *stale* (inconsistent with the source — the hard problem this series returns to), plus complexity (managing the cache, invalidation, eviction). So caching trades *performance* for *complexity and consistency risk*. It's worth it when the performance gain is large (reused, expensive data); it's not worth it when the gain is small (and the added staleness/complexity dominates). Cache deliberately, weighing the tradeoff. (The famous "cache invalidation is hard" is exactly this consistency cost.)

Caching helps when data is reused and expensive to obtain (read-heavy, staleness-tolerant workloads) and hurts when data is rarely reused or constantly changing — and it always adds complexity and consistency risk (stale copies), so cache deliberately where the performance gain justifies the cost. Caching is a fundamental performance technique built on locality and the memory-hierarchy principle, applied throughout computing. The series goes deep: fundamentals, eviction, invalidation, patterns, distributed caching, web/CDN caching, and pitfalls.

## Key takeaways

- Caching is storing a copy of reused data/results in a faster-to-access tier, so repeated requests are served quickly from the cache instead of redoing expensive work (recomputation, slow queries, network fetches) — turning repeated expensive work into one expensive operation plus many cheap lookups (memoization at a system level).
- It's a universal pattern appearing at every layer of computing (CPU caches, buffer pools, Redis, CDNs, browsers, DNS) — the same idea recurring at every scale.
- Caching works because of locality of reference: data access reuses the same data (temporal locality) and nearby data (spatial locality), and is highly *skewed* (a small hot subset dominates access — 80/20), so a small, fast cache holding the popular data serves most requests — without this locality, caching wouldn't help.
- Caching is the general form of the memory-hierarchy principle ("keep what you'll reuse in a faster, smaller tier"), which recurs at every level (CPU→RAM, buffer pool→disk, Redis→database, CDN→origin) — a unifying insight where understanding it at one level transfers to all.
- Caching helps when data is reused *and* expensive to obtain (read-heavy, staleness-tolerant workloads) but hurts when data is rarely reused or constantly changing — and it always adds complexity and consistency risk (stale copies — the famous "cache invalidation is hard"), so cache deliberately only where the performance gain justifies the cost.

## Further reading

- [Cache (computing) (Wikipedia)](https://en.wikipedia.org/wiki/Cache_(computing))
- [Locality of reference (Wikipedia)](https://en.wikipedia.org/wiki/Locality_of_reference)
- [Operating Systems for Engineers — the memory hierarchy in hardware](/blog/series/operating-systems-for-engineers/)
