# Eviction Policies

*A cache is a small space pretending to be a big one, and the pretense only works if it's clever about what to keep. When a bounded cache fills up, every new item forces out an old one — and which one you evict determines your hit rate, which determines whether the cache is worth having at all. Eviction policies are the algorithms that make this choice, and understanding them (especially the workhorse, LRU) is essential to building caches that actually stay effective.*

Because caches are *bounded* (from the fundamentals post), a full cache must **evict** something to make room for new data — and the **eviction policy** deciding *what* to evict directly determines the hit rate. This post covers why eviction is necessary, the main policies (**LRU**, **LFU**, **FIFO**, and others), **TTL**-based expiration, and how to choose. Eviction is where a bounded cache decides what's worth keeping, making it central to cache effectiveness.

## Why eviction is necessary

**Eviction** — removing items from the cache to make room — is necessary because caches are *bounded*, and the policy for *what* to evict matters enormously:

- **Bounded caches must evict.** A cache is *finite* (faster-but-smaller storage — the whole point, from the fundamentals post), so it *can't hold everything*. When the cache is *full* and new data needs to be added, something must be *removed (evicted)* to make room. Eviction is the inevitable consequence of bounded cache size — every cache that fills up must decide what to drop. There's no avoiding it.
- **The choice determines hit rate.** *Which* item you evict determines *future hit rate*: if you evict data that *will be needed soon*, you cause a future miss; if you evict data that *won't be needed*, you lose nothing. So a good eviction policy *keeps the data most likely to be reused* and evicts the data least likely to be reused — maximizing future hits. The eviction policy directly drives hit rate (the key metric), making it central to cache effectiveness. Evict wrong, and hit rate drops.
- **The ideal is impossible, so we approximate.** The *optimal* policy would evict the item that won't be needed for the longest time — but that requires knowing the *future*, which is impossible. So real policies *approximate* this using the *past* (recency, frequency) as a predictor of the future (relying on locality — recently/frequently used data is likely to be used again). Eviction policies are heuristics that guess what to keep based on past access patterns. They're educated guesses, not perfect.

Eviction is necessary because bounded caches must remove items to make room, and the eviction policy (what to evict) directly determines hit rate — so a good policy keeps likely-to-be-reused data and evicts unlikely-to-be-reused data, approximating the impossible ideal (evict what won't be needed longest) using past access as a predictor. The main policies embody different heuristics.

## The main eviction policies

Several standard eviction policies use different heuristics for what to evict — the main ones every engineer should know:

- **LRU (Least Recently Used).** Evict the item that was *accessed least recently* (longest ago). LRU's logic: by *temporal locality* (recently-used data is likely reused soon — from post one), the *least recently used* item is the *least likely* to be needed soon, so it's the best to evict. LRU is the *most common and generally effective* policy — it exploits temporal locality well and matches most real access patterns. It's the default workhorse of caching. When in doubt, LRU.
- **LFU (Least Frequently Used).** Evict the item *accessed least frequently* (fewest times). LFU's logic: *frequently-accessed* items are the hot, popular data (the skewed-access insight) worth keeping, so evict the *least frequently used*. LFU keeps popular items well but can be slow to adapt (an item popular long ago but not recently stays cached; a newly-hot item takes time to build frequency). LFU suits stable popularity; LRU adapts faster to changing access.
- **FIFO (First In, First Out).** Evict the *oldest-inserted* item (regardless of access) — simple queue order. FIFO is *simple* but often *worse* than LRU (it ignores access — evicting old items even if they're still frequently used). FIFO's simplicity is its only advantage; it's usually inferior to LRU because it doesn't consider reuse. Simple but naive.
- **Random.** Evict a *random* item — trivially simple, no bookkeeping. Surprisingly, random eviction isn't terrible (it rarely evicts the hottest data by chance, and avoids LRU's bookkeeping cost) and is used where simplicity/speed matters. It's a low-overhead baseline. Not great, not terrible.

LRU (evict least-recently-used — the common, effective default exploiting temporal locality), LFU (evict least-frequently-used — keeps popular data, slower to adapt), FIFO (evict oldest — simple but ignores access, usually worse), and Random (simple, low-overhead) are the main eviction policies. LRU is the general-purpose workhorse. Alongside these access-based policies, time-based expiration (TTL) is also common.

## TTL: time-based expiration

Separate from (and often combined with) eviction policies is **TTL** (Time To Live) — expiring cached items after a set *time*, regardless of access:

- **Expire after a set time.** A TTL sets how long a cached item stays valid — after the TTL elapses, the item is considered *expired* and removed/refreshed (a miss on next access, refetching fresh data). TTL is *time-based expiration*: items live for a fixed duration, then expire. It's simple and widely used. Every cached item can have a "best before" time.
- **TTL serves freshness (not just space).** Unlike access-based eviction (which manages *space* by removing least-useful items), TTL manages *freshness* — ensuring cached data isn't *too stale* by expiring it after a while. TTL is a key tool for the *consistency/staleness* problem (the invalidation post): even without explicit invalidation, TTL bounds how stale data can get (at most TTL-old). So TTL addresses staleness, while eviction policies address space. They serve different purposes and are often used together.
- **The TTL tradeoff.** TTL trades *freshness* against *hit rate*: a *short* TTL means fresher data but more misses (items expire and must be refetched often — lower hit rate); a *long* TTL means higher hit rate but staler data (items live longer before refresh). Choosing the TTL balances freshness against hit rate for the data's staleness tolerance. It's a key, simple knob for the freshness/performance tradeoff. Short TTL = fresh but more misses; long TTL = stale but fewer misses.

TTL (time-based expiration — items expire after a set duration) manages *freshness* (bounding staleness), complementing access-based eviction policies (which manage *space*) — with the TTL length trading freshness against hit rate. TTL is a simple, widely-used tool, often combined with eviction policies. Choosing among all these depends on the workload.

## Choosing an eviction policy

Selecting the right eviction (and expiration) approach depends on the workload — some practical guidance:

- **LRU is the sensible default.** For most caches, *LRU* is the right default — it exploits temporal locality (which most workloads have), adapts to changing access patterns, and is generally effective. Unless you have a specific reason, LRU (or an LRU approximation, which many systems use for efficiency) is the go-to. Start with LRU.
- **Match the policy to the access pattern.** Choose based on how the data is accessed: *LRU* for recency-dominated access (recently-used likely reused — most workloads); *LFU* for stable-popularity access (some items consistently popular regardless of recency — LFU keeps them); *FIFO/Random* where simplicity/low-overhead matters more than optimal hit rate. Matching the policy to the workload's locality pattern optimizes hit rate. Different access patterns favor different policies.
- **Combine eviction with TTL.** Real caches often use *both*: an eviction policy (LRU) to manage *space* (what to drop when full) *and* TTL to manage *freshness* (expire stale data). Combining them handles both concerns — keep the useful data (eviction) but not too stale (TTL). This combination is common and sensible. Space and freshness are separate concerns, handled together.
- **Consider the overhead.** Policies have *overhead*: LRU/LFU require *bookkeeping* (tracking recency/frequency) that costs memory and time; FIFO/Random are cheaper. For very high-performance caches, the bookkeeping cost matters, which is why systems often use *approximations* of LRU (nearly-LRU with less overhead) rather than exact LRU. The policy's cost is a real consideration at scale. Exact tracking isn't free.

Eviction policies — LRU (the effective default, exploiting temporal locality), LFU (keeps popular data), FIFO/Random (simple), plus TTL (time-based freshness expiration) — decide what a bounded cache keeps, directly determining hit rate. Choose LRU by default, match to the access pattern, combine eviction (space) with TTL (freshness), and mind the overhead. Next: cache invalidation — the genuinely hard problem of keeping cached data consistent.

## Key takeaways

- Eviction (removing items to make room) is necessary because caches are bounded and can't hold everything — a full cache must evict to add new data — and *which* item is evicted directly determines future hit rate (evict data needed soon → future miss; evict unneeded data → no loss), so eviction is central to cache effectiveness.
- The optimal policy (evict what won't be needed longest) requires knowing the future, so real policies approximate it using past access (recency/frequency) as a predictor, relying on locality — the main ones are LRU (evict least-recently-used — the common, effective default exploiting temporal locality, adapts well), LFU (evict least-frequently-used — keeps popular data but slow to adapt), FIFO (evict oldest — simple but ignores access, usually worse), and Random (simple, low-overhead).
- TTL (Time To Live) expires cached items after a set duration regardless of access — managing *freshness* (bounding how stale data can get — a key tool for the consistency problem) rather than space, complementing access-based eviction policies (which manage space); the two are often combined.
- The TTL length trades freshness against hit rate: short TTL = fresher data but more misses (frequent expiry/refetch), long TTL = higher hit rate but staler data — chosen for the data's staleness tolerance.
- Choose LRU as the sensible default (most workloads have temporal locality), match the policy to the access pattern (LFU for stable popularity, FIFO/Random for simplicity), combine eviction (space) with TTL (freshness), and mind bookkeeping overhead (LRU/LFU cost tracking — high-performance systems often use LRU approximations).

## Further reading

- [Cache replacement policies (Wikipedia)](https://en.wikipedia.org/wiki/Cache_replacement_policies)
- [Caching fundamentals (previous post)](/blog/posts/cache-02-caching-fundamentals.html)
- [Cache invalidation (Wikipedia)](https://en.wikipedia.org/wiki/Cache_invalidation)
