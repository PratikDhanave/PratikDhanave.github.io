# Caching

*The highest-leverage tool for latency and scale — and the source of its hardest problem, invalidation. Where caches live, the patterns for filling them, how they evict, and why keeping them correct is the part that stays hard.*

---

Caching is the single cheapest way to make a slow system fast. You take a value that was expensive to produce — a database join, a rendered page, a call to a downstream service — and you keep the answer somewhere fast so the next reader doesn't pay the full cost. Done well, a cache turns a 50-millisecond query into a 200-microsecond lookup and lets one database serve ten times the traffic.

But a cache is a *copy*, and the moment you have two copies of a fact you have to decide what happens when one of them changes. That decision — when a cached copy is allowed to be wrong, and how you fix it — is the whole discipline. This post walks through why caching works, where caches physically live, the patterns for reading and writing through them, how they decide what to throw away, and the part everyone underestimates: keeping the copies honest.

---

## Why caching works at all

Two facts about real workloads make caching pay off.

**The latency gap is enormous.** [Post 1 in this series](/blog/) laid out the numbers every engineer should carry around, and caching lives entirely inside that gap. Reading a value already in main memory takes on the order of 100 nanoseconds. Reading it from a local SSD is roughly a thousand times slower — hundreds of microseconds. A round trip to a database over the network, plus the query itself, is easily 1–50 milliseconds, and a cross-region call can be 100 milliseconds or more. When you cache, you are moving a value up that ladder — from "network + disk + compute" down to "memory" — and each rung is one to three orders of magnitude. Nothing else in your toolbox buys speedups that large for so little code.

**Access is not uniform.** Real traffic exhibits *locality*. **Temporal locality** means a value read once is likely to be read again soon — the article on the front page, the logged-in user's own profile, today's exchange rate. **Spatial locality** means related values get accessed together. On top of that, most systems are *read-heavy*: reads outnumber writes by 10:1, 100:1, sometimes 1000:1. A cache exploits all three. A small, fast copy of the "hot" set absorbs the vast majority of requests, and the expensive backend only sees the misses. This is why a cache with room for 1% of your data can still serve 95% of your reads — the 1% is the part everyone actually wants.

If your workload had no locality — every request touched a uniformly random key exactly once — a cache would do nothing but add overhead. Measure your hit rate before you celebrate; a cache that isn't being hit is pure cost.

---

## Where caches live

There is no single "the cache." Caching happens at every layer between the user's eyeball and your database, and each layer has different reach, size, and staleness behavior.

```text
Browser cache      →  per-user, on the device, closest & cheapest
CDN / edge         →  shared, geographically near the user
Reverse proxy      →  in front of your app (nginx, Varnish)
Application memory  →  in-process, per-instance, fastest server-side
Distributed cache   →  Redis / Memcached, shared across instances
DB query / buffer   →  the database caching its own pages & plans
```

- **Client / browser cache.** The `Cache-Control`, `ETag`, and `Expires` headers you send tell the browser it may reuse a response without asking again. This is the cheapest hit of all — zero network — but you control it only indirectly, through headers, and you can't reach in to invalidate a copy already sitting on someone's laptop.
- **CDN / edge cache.** A shared cache in dozens of locations physically near users. Ideal for static assets and cacheable pages; the win is both latency (short round trip) and offload (your origin never sees the request). You *can* invalidate here — via a purge API — but purges are eventually consistent across edges.
- **Reverse proxy cache.** nginx or Varnish sitting in front of your app caching whole responses. Useful for anonymous, cacheable pages before a request ever touches application code.
- **Application in-memory cache.** A map or an LRU structure inside your process. Nanosecond access, no serialization, no network — but it's *per-instance*. Ten app servers means ten independent caches that can disagree, and a deploy wipes them all cold.
- **Distributed cache (Redis, Memcached).** A separate tier every app instance shares. One coherent copy, survives deploys, scales past one machine's memory — at the cost of a network hop (still microseconds on a LAN, far cheaper than the database) and a new thing to operate. This is the workhorse of most backends.
- **Database's own caches.** Your database already caches. Its buffer pool keeps hot pages in RAM, and it caches query plans. Some of "the database is fast enough" is really "the working set fits in the buffer pool." Understanding this stops you from adding a redundant cache in front of data the DB was already serving from memory.

The layers compose: a request can be answered by the browser, then the CDN, then the app cache, then Redis, and only a true miss reaches the database. Each layer you add cuts load on everything behind it — and adds one more copy you must reason about.

---

## Cache patterns: how the cache gets filled

The pattern is the contract between your application, the cache, and the source of truth. Pick it deliberately.

**Cache-aside (lazy loading).** The application owns the logic. On a read, check the cache; on a miss, load from the database, put it in the cache, and return it. Writes go straight to the database and (usually) invalidate or update the cache entry. This is the most common pattern because it's simple and the cache only ever holds data someone actually asked for. The downsides: every miss pays the full latency (cache lookup *plus* DB read), and the read-load-store sequence has a subtle race with concurrent writes that can leave stale data behind.

**Read-through.** Same shape as cache-aside, but the cache library — not your code — fetches from the backing store on a miss. Your application only ever talks to the cache. This centralizes the loading logic and keeps call sites clean, at the cost of a cache that has to know how to load your data.

**Write-through.** On a write, update the cache *and* the database synchronously, as one operation. The cache is always consistent with the DB for data that's cached, so reads never see a write they missed. The price is write latency — every write pays for two stores — and you cache data that may never be read.

**Write-behind (write-back).** On a write, update the cache immediately and return; flush to the database asynchronously, often batched. Writes feel instant and the database sees far fewer, larger writes. This is the fastest write path and the most dangerous: between the cache write and the flush, the durable copy is *behind*, and a crash in that window loses data.

**Refresh-ahead.** The cache predicts which soon-to-expire entries are hot and refreshes them *before* they expire, so popular keys are never served cold. It hides refresh latency for predictable access patterns but wastes work refreshing things nobody asks for again, and it's only as good as its prediction.

| Pattern | Read cost | Write cost | Consistency | Main risk |
|---|---|---|---|---|
| Cache-aside | Miss pays full load | Cheap (DB only) | Can go stale on write | Read/write race |
| Read-through | Miss pays full load | — | Same as aside | Cache must know the store |
| Write-through | Always warm | 2 writes | Strong for cached keys | Slow writes |
| Write-behind | Always warm | Cheapest | Eventual | **Data loss on crash** |
| Refresh-ahead | Rarely cold | Background | Good for hot keys | Wasted refreshes |

**The gotcha:** write-behind loses data on a crash before the flush completes. If you cache a user's just-submitted order in write-back mode and the node dies before the batch reaches the database, that order is simply gone, and nothing upstream knows. Know your durability trade-off before you pick the fastest write path — write-behind is right for metrics counters and view tallies, wrong for anything a user would be furious to lose.

---

## Eviction and sizing

A cache is finite. When it's full and a new entry arrives, something has to go, and the eviction policy decides what.

- **LRU (least recently used)** throws out whatever hasn't been touched for the longest time. It's the default in most systems because it approximates temporal locality well and is cheap to maintain. Its blind spot is a large scan — reading a million rows once evicts your genuinely hot set to make room for data you'll never read again.
- **LFU (least frequently used)** evicts the least-often-accessed entry, keeping items that are popular over time rather than merely recent. It resists scan pollution but needs frequency counters and can cling to items that *were* hot last week and aren't anymore, unless it ages the counts.
- **TTL (time to live)** is orthogonal to both: every entry carries an expiry, and stale entries are dropped regardless of use. TTL is your first line of defense against staleness and often runs *together* with LRU/LFU — LRU manages the size, TTL manages the age.

Sizing is the other half. Too small and your hit rate collapses; too large and you're paying for memory to cache the cold tail. The number that matters is the hit rate as a function of size — it usually rises steeply then flattens, and the knee of that curve is where your money is best spent. Redis's `maxmemory` plus a `maxmemory-policy` (for example `allkeys-lru`) enforces the ceiling and the eviction rule together; set both explicitly rather than discovering the default under load.

---

## The hard part: invalidation and coherence

Everything above is mechanical. This is where caching gets genuinely difficult.

**The gotcha:** "there are only two hard things in computer science: cache invalidation and naming things" (attributed to Phil Karlton) is a joke precisely because it's true. The moment the source of truth changes, every cached copy is a potential lie, and you have to decide — explicitly — how long a lie you can tolerate. That tolerance is a *product* decision disguised as an engineering one. A stock ticker tolerates zero staleness; a "number of likes" counter tolerates minutes. Write the number down before you write the code.

You have two fundamental tools, and they trade off against each other:

- **TTL-based expiry** lets entries go stale for a bounded window and then die on their own. It's dead simple and needs no coordination — but it guarantees a window during which readers see old data, and it does nothing on the write side.
- **Explicit invalidation** deletes or updates the entry the instant the underlying data changes. It's precise and can be near-immediate — but it requires you to *know* every cache key affected by a write, which is exactly the part that's hard. Miss one key on one write path and you have a stale entry that TTL might not catch for hours.

Most real systems combine them: explicit invalidation on writes for correctness, plus a modest TTL as a backstop for the invalidations you inevitably miss.

### Cache stampede (the thundering herd)

Here's the scenario that takes down services. A very hot key expires — or the cache restarts cold — and in the same instant a thousand concurrent requests all miss, all decide to recompute the same value, and all hammer the database at once. The backend, which was comfortable serving one recompute, now gets a thousand identical expensive queries and falls over. The cache was *protecting* the database, and the moment of expiry removed the protection all at once.

**The gotcha:** a cold cache plus a traffic spike equals a stampede — many misses recomputing the same key simultaneously. The fix is to make sure only *one* caller recomputes while the rest wait. Three mitigations, often combined:

- **Request coalescing (single-flight).** When N callers miss the same key at once, let exactly one do the work and have the other N−1 wait for and share its result.
- **Jittered TTL.** Don't expire a whole class of keys at the same second. Add randomness to each TTL so expirations spread out instead of firing in a synchronized wave.
- **Early / probabilistic recomputation.** Refresh a hot entry slightly *before* it expires (one lucky request, chosen probabilistically as expiry approaches, does the refresh in the background) so the key is never actually cold at read time.

Here's cache-aside with a TTL and single-flight coalescing in Go, using the real [`golang.org/x/sync/singleflight`](https://pkg.go.dev/golang.org/x/sync/singleflight) package:

```go
package cache

import (
	"context"
	"sync"
	"time"

	"golang.org/x/sync/singleflight"
)

type entry struct {
	val       string
	expiresAt time.Time
}

type Cache struct {
	mu    sync.RWMutex
	data  map[string]entry
	ttl   time.Duration
	group singleflight.Group // coalesces concurrent misses on the same key
	load  func(ctx context.Context, key string) (string, error)
}

func New(ttl time.Duration, load func(context.Context, string) (string, error)) *Cache {
	return &Cache{data: make(map[string]entry), ttl: ttl, load: load}
}

func (c *Cache) Get(ctx context.Context, key string) (string, error) {
	c.mu.RLock()
	e, ok := c.data[key]
	c.mu.RUnlock()
	if ok && time.Now().Before(e.expiresAt) {
		return e.val, nil // hit
	}

	// Miss. singleflight guarantees exactly one load runs per key at a time;
	// concurrent callers for the same key block and share this one result.
	v, err, _ := c.group.Do(key, func() (interface{}, error) {
		val, err := c.load(ctx, key)
		if err != nil {
			return "", err
		}
		c.mu.Lock()
		c.data[key] = entry{val: val, expiresAt: time.Now().Add(c.ttl)}
		c.mu.Unlock()
		return val, nil
	})
	if err != nil {
		return "", err
	}
	return v.(string), nil
}
```

The `singleflight.Group` is the whole point: a thousand goroutines calling `Get` on the same missing key produce exactly one call to `load`. The database sees one query, not a thousand. Add jitter by randomizing `c.ttl` slightly per entry, and you've covered the two most common stampede causes in a few dozen lines.

### Cache penetration

Stampede is about a *popular* key going missing. **Penetration** is the opposite: requests for keys that *don't exist anywhere*. If someone queries user ID 999999999 that was never created, the cache misses (nothing to cache), the database returns "not found," and nothing gets stored — so the *next* request for that same non-existent key misses again. An attacker (or a buggy client) can fire millions of requests for random non-existent keys and route every single one straight through to your database, bypassing the cache entirely.

Two standard defenses: **cache the negative result** — store a "not found" marker with a short TTL so repeat lookups for a missing key are absorbed by the cache — and put a **Bloom filter** in front of definitely-absent keys, cheaply rejecting lookups for IDs that provably don't exist before they ever reach the store.

### The hot-key problem

Sometimes a single key is so popular it becomes the bottleneck by itself — a celebrity's profile, a flash-sale product, the homepage feed. In a distributed cache, one key lives on one node (its shard), and that node now absorbs a disproportionate share of all traffic while its peers idle. Consistent hashing spreads *keys* evenly across nodes, but it can't spread a *single* key's load. Mitigations: replicate the hot key across several nodes and read from a random replica; add a small local in-process cache in front of the distributed one for the hottest keys (a two-tier cache); or split a hot aggregate into shards (`likes:post42:0..9`) and sum them. First, though, you have to *detect* the hot key — instrument per-key access counts, because you can't fix a hotspot you can't see.

**The gotcha:** caching per-user or otherwise non-idempotent data under the wrong key leaks it across users. If your cache key for "the current user's dashboard" is just `dashboard` instead of `dashboard:{userID}`, the first user's private data gets served to everyone who follows. Cache keys must include *every* input that changes the output — user, tenant, locale, permissions, feature flags. A too-broad key isn't a performance bug; it's a data-leak vulnerability.

---

## Key takeaways

- **Caching wins because of the latency gap and locality.** You're moving hot values up the memory hierarchy — memory vs. disk vs. network is orders of magnitude — and read-heavy, skewed traffic means a tiny cache serves most requests. Measure your hit rate; a cache nobody hits is pure cost.
- **Caches live at every layer** from the browser through the CDN, reverse proxy, in-process memory, a distributed tier like Redis, down to the database's own buffer pool. Each layer offloads everything behind it and adds one more copy to reason about.
- **The pattern is a contract.** Cache-aside is the default; write-through trades write latency for consistency; write-behind is fastest but loses data on a crash. Match the pattern to how much staleness and data loss you can tolerate.
- **Eviction and TTL are different jobs.** LRU/LFU manage *size*, TTL manages *age* — most caches run both.
- **Invalidation is the hard part.** Decide your staleness tolerance explicitly, combine TTL backstops with explicit invalidation, and defend against stampede (coalesce with single-flight, jitter TTLs, recompute early), penetration (cache negatives, Bloom filters), and hot keys (replicate, two-tier, shard). And always key on every input that changes the output.

---

## Further reading

- [Redis documentation — key eviction and `maxmemory` policies](https://redis.io/docs/latest/develop/reference/eviction/)
- [Memcached wiki — overview and design](https://github.com/memcached/memcached/wiki/Overview)
- [MDN — HTTP caching (`Cache-Control`, `ETag`, and validation)](https://developer.mozilla.org/en-US/docs/Web/HTTP/Caching)
- [Cloudflare — what is a CDN and how CDN caching works](https://developer.cloudflare.com/cache/concepts/default-cache-behavior/)
- [`golang.org/x/sync/singleflight` — request coalescing in Go](https://pkg.go.dev/golang.org/x/sync/singleflight)
- [Consistent hashing — Karger et al., "Consistent Hashing and Random Trees" (original paper, PDF)](https://www.cs.princeton.edu/courses/archive/fall09/cos518/papers/chash.pdf)
