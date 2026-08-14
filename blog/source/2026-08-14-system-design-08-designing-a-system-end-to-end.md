# Designing a System End to End

*The capstone — one problem, a home-timeline feed, designed the whole way through with the method from post one: clarify, estimate, contract, then high-level to deep-dive to bottleneck, naming the trade-off at every step and drawing on all seven earlier posts.*

---

Seven posts of this series built a toolbox: a method for approaching any design, then scaling, caching, data, consistency, async processing, and reliability. This finale spends the toolbox on a single problem, end to end, so you can see how the pieces compose under one set of requirements. The point is not the finished diagram — it is the *sequence of decisions* that produces it. If you memorize the diagram, you learn one system. If you internalize the sequence, you can design the next one, unseen.

The problem: **design the home timeline** — the ranked-or-chronological feed of posts from the accounts a user follows, the core of any social product. It is a good capstone precisely because it is deceptively simple to state and brutally opinionated to build: the read path, the write path, and the social graph all pull in different directions, and where they collide is exactly where the earlier posts earn their keep.

We will run the method from **post 1** in order: requirements, estimation, API and data model, then high-level design, deep-dives, and bottlenecks.

---

## 1. Requirements: refuse to design first

Before any boxes, ask what the system does and the properties it must hold — the two buckets from post 1.

**Functional requirements** (the verbs):

- Publish a post (text, optional media reference).
- Follow and unfollow another account.
- Read *my* home timeline — recent posts from everyone I follow, newest-first.
- See my own new post in my own timeline immediately.

Everything else — ranking by an ML model, notifications, search, direct messages — is explicitly **out of scope**. Naming what you defer is part of the method, not a cop-out.

**Non-functional requirements** — the six from post 1, with the numbers extracted:

- **Scale:** ~100M daily active users, average ~200 accounts followed each, heavily read (a user reads their feed far more often than they post). This is a **read-heavy** system with one nasty twist we will find in estimation.
- **Latency:** feed read must feel instant — target p99 under ~200 ms. Publishing can be slower; a post appearing in followers' feeds a few seconds late is fine.
- **Availability:** high — four nines on the read path. People tolerate a delayed post far less than a feed that won't load.
- **Consistency:** **eventual** is acceptable for other people's posts (a few seconds of lag is invisible), but **read-your-own-writes** is required for your own.
- **Durability:** a published post must never be silently lost. The *materialized feed* can be lost and rebuilt — it is derived data.
- **Cost:** commodity hardware, horizontal scale-out; no exotic infrastructure.

**The gotcha:** that split — eventual for others, read-your-own-writes for yourself, and a feed that is *derived, disposable data* while posts are *durable source-of-truth data* — is the single most load-bearing set of requirements in the whole design. Miss it and you either over-build (strong consistency on a feed nobody notices lagging) or under-build (losing posts to save a feed you could have recomputed). The requirements decide the architecture; extracting them *is* the design.

---

## 2. Back-of-the-envelope estimation

Now turn scale into numbers, the way post 1 did — rounding a day to ~10^5 seconds and working to one significant figure.

```text
Assumptions (stated, not precise):
  Daily active users        100M   = 10^8
  Avg accounts followed      200
  Feed reads per user/day     20   (opens app, refreshes)
  Posts per user/day         0.5   (most users lurk)

Feed reads/sec:
  10^8 users x 20 reads = 2 x 10^9 reads/day
  2 x 10^9 / 10^5 s     ≈ 20,000 reads/sec   (peak ~2x ≈ 40,000/sec)

Posts/sec (writes to source of truth):
  10^8 x 0.5 = 5 x 10^7 posts/day
  5 x 10^7 / 10^5 s     ≈ 500 posts/sec       (peak ~2x ≈ 1,000/sec)

Fan-out amplification (the twist):
  each post must reach ~200 followers' feeds
  500 posts/sec x 200 ≈ 100,000 feed-writes/sec  (peak ~200,000/sec)

Storage:
  post ≈ 300 B (text + metadata; media lives elsewhere as a URL)
  5 x 10^7 posts/day x 300 B = 1.5 x 10^10 B ≈ 15 GB/day
  per year ≈ 5.5 TB ; over 5 years ≈ 27 TB

Materialized feed cache (store latest ~500 post-ids per user):
  500 ids x 8 B = 4 KB/user
  10^8 users x 4 KB = 4 x 10^11 B ≈ 400 GB   (fits across a few RAM nodes)

Read bandwidth (a feed page hydrates ~20 posts x 300 B ≈ 6 KB):
  20,000 reads/sec x 6 KB ≈ 120 MB/sec outbound
```

Two minutes of arithmetic and the design has already declared itself. Reads outnumber posts 40:1, so we lean on caching and replicas (posts 2 and 3). Source-of-truth storage is tens of terabytes over five years, so it must shard (post 4). And the killer: **fan-out amplifies 500 posts/sec into 100,000 feed-writes/sec** — a 200x write multiplier that is invisible until you do the multiplication. That single number is why a naive "just write to a table and query it" design collapses, and why the write path, not the read path, is where the interesting engineering lives.

**The gotcha:** the amplification is the whole ballgame, and it is easy to miss because "post a tweet" *sounds* like one write. Never invent a precise QPS to sound authoritative — round hard, say your assumptions aloud, and let the multiplication surface the real load. The estimate is a decision tool, not a prediction.

---

## 3. API and data model

Write the contract before the boxes — it forces precision and surfaces hidden decisions.

```text
POST   /posts        { text, media_url? }        -> { post_id, created_at }
GET    /feed?cursor= &limit=20                    -> { posts[], next_cursor }
POST   /follow       { target_id }               -> 204
DELETE /follow/{target_id}                        -> 204
```

Pagination uses an **opaque cursor**, not an offset. Offsets shift as new posts arrive and reads become inconsistent; a cursor (encode the last seen post-id) gives stable, forward-only paging.

The data model splits along the durability line the requirements drew:

```text
posts            (source of truth, durable)
  post_id     snowflake id   (PK; time-sortable — id order == time order)
  author_id   string
  text        string
  media_url   string?
  created_at  timestamp

follows          (the social graph, durable)
  follower_id  string
  followee_id  string
  (indexed BOTH ways: by follower_id and by followee_id)

feed             (materialized per reader; derived, disposable)
  user_id     string
  post_ids    ordered list (newest-first, capped ~500)
```

Two modeling choices matter. First, **`post_id` is a Snowflake-style id** — a 64-bit value with a timestamp in the high bits — so ids sort in creation order. That makes "newest 20" a range scan and lets cursors be plain ids, no separate sort. Second, the **follow graph is double-indexed**: by `follower_id` to answer "who do I follow?" (the read path) and by `followee_id` to answer "who follows this author?" (the fan-out path). One index cannot serve both cheaply — you pay for two, a concrete instance of the read/write bargain from post 4.

---

## 4. High-level design

Now the boxes — low resolution, proving the whole thing hangs together.

```text
                         +------------------+
  client ── LB ─────────>|   API service    |  (stateless, scales out — post 2)
                         +---+----------+---+
                             |          |
                 write path  |          |  read path
                             v          v
                    +----------------+  +-------------------------+
                    |  post store    |  |  feed cache (RAM)       |
                    |  (sharded DB)  |  |  user_id -> post_ids    |
                    +-------+--------+  +------------+------------+
                            |                        | miss / celebrity merge
                 post-created event                  v
                            v                +----------------+
                    +----------------+       |  post store    |
                    |  fan-out queue |       |  (read replica)|
                    +-------+--------+       +----------------+
                            v
                    +----------------+
                    | fan-out workers|── expand followers, write feed cache
                    +----------------+
```

The write path is deliberately asynchronous: publishing durably persists the post, emits an event, and returns — the expensive fan-out happens behind a queue. The read path is a cache lookup that almost always hits. The rest of the design is deep-diving these two paths where the numbers said the pressure is.

---

## 5. Deep-dives: applying the series

### Scaling the stateless tier (post 2)

The API service holds no session state — the token carries identity, the feed lives in the cache, posts live in the store. That statelessness is exactly what post 2 called the real enabler of scale-out: any request can hit any instance, so we put them behind an L7 load balancer with health checks and add instances until 40,000 peak reads/sec are comfortable. No vertical heroics; horizontal all the way.

### Caching the feed (post 3)

The materialized `feed` is itself a cache — a **cache-as-primary read path**, not a lazy read-through. We keep the newest ~500 post-ids per user in RAM (~400 GB total, per estimation), so a feed read is one memory lookup for the ids plus a batched hydrate of ~20 posts. This is the latency-for-freshness trade from post 3 made literal: the feed is allowed to be a few seconds stale so the read can be a memory hit instead of a graph traversal plus 200-way query.

The eviction policy is size- and recency-based: cap the list, drop cold users' materialized feeds entirely and rebuild on demand (the pull path below is the miss handler). We size the hot set from the estimate rather than guessing.

**The gotcha:** the highest-leverage move here is not adding a cache in front of a query — it is **precomputing the answer** so the read never runs a query at all. But precomputation moves all the cost to write time, which is why the fan-out amplification from estimation dominates the design. You are not caching a computation; you are choosing to pay it 200x on the write side to make reads free.

### The datastore and shard key (post 4)

Two stores, two different shard keys — and post 4 warned the shard key is the highest-stakes decision you make.

- **Post store**, sharded by `post_id`. Writes spread evenly (Snowflake ids embed a timestamp *and* a machine bit, avoiding a monotonic hotspot), and hydrating a feed is a batched multi-get across shards by id. Over five years this holds ~27 TB, well past one machine — sharding is mandatory, not optional.
- **Feed cache**, sharded by `user_id` (the *reader*). A feed read touches exactly one shard: the reader's. Fan-out writes scatter across reader shards, which is what we want — no single shard owns a popular author's blast.

The follow graph is the subtle one. Sharded by `follower_id`, "who do I follow" is one-shard; but fan-out needs "who follows this author," which is scattered — hence the second index by `followee_id`. We accept the write-side cost of the double index because both access patterns are hot.

### The consistency model (post 5)

We chose **eventual consistency** for other people's posts and it is the right call: a follower seeing a post two seconds after publish is imperceptible, and demanding strong consistency here would force synchronous fan-out to 200 feeds before the post could ack — trading the fast publish the requirements allow for a latency nobody asked for. This is post 5's lesson in the specific: pick the *weakest* consistency the requirement tolerates and buy availability and latency with the slack.

The one exception is **read-your-own-writes**. Because fan-out is async, your own post may not be in your materialized feed for a second or two — unacceptable when *you* just posted. Fix: on a feed read, merge the reader's own most-recent posts (a tiny, single-author query on the reader's own id) on top of the cached feed. Your posts appear instantly; everyone else's arrive via fan-out. Cheap, and it satisfies the exact consistency guarantee the requirements named.

**The gotcha:** the shard key and the consistency choice are where the real design lives — everything else is plumbing. Get "shard the feed by reader, shard posts by id, eventual-with-read-your-own-writes" right and the system works; get it wrong and no amount of caching saves you. Interviewers and readers reward this reasoning, not the box count.

### Async fan-out (post 6)

Publishing enqueues a `post-created` event and returns; **fan-out workers** consume it, look up the author's followers, and append the `post_id` to each follower's feed cache. This is post 6's decoupling exactly: the producer (publish) is fast and the expensive, spiky consumer (200-way fan-out) runs behind a queue that absorbs bursts. When a spike pushes fan-out past 200,000 writes/sec, the queue depth grows and workers drain it — the publish latency never moves. Throughput smooths; the buffer eats the spike.

### Reliability and rate-limiting (post 7)

The failure that *will* happen, planned for per post 7:

- **Idempotent feed writes.** A retried fan-out must not duplicate a post in a feed. Because the feed is a set/ordered-list keyed by `post_id`, re-appending the same id is a no-op — retries are safe by construction.
- **Dead-letter queue + retries with backoff.** A follower shard that is briefly down doesn't drop the fan-out; the event retries, and a poison event lands in a DLQ for inspection instead of blocking the worker.
- **Rate-limit publishing** with a per-user token bucket (from post 7) — caps spam and abuse, and protects the fan-out pipeline from a single account flooding it.
- **Graceful degradation.** If a reader's feed-cache shard is unavailable, fall back to the **pull path**: query the reader's followees for their recent posts and merge at read time. Slower, but the feed still loads — availability preserved by trading latency, exactly the reliability/latency trade post 7 framed.

---

## 6. Bottlenecks and trade-offs

Now attack the design, pass three of the method.

**The celebrity problem (the real bottleneck).** Pure fan-out-on-write assumes ~200 followers. An account with 10M followers turns *one* post into 10M feed writes — a fan-out storm that stalls the queue and hot-spots reader shards. The fix is a **hybrid** model: fan out on write for ordinary authors, but for high-follower accounts **do not** fan out — instead, at read time, pull the celebrity's recent posts and merge them into the reader's materialized feed. Normal authors stay push (cheap reads); celebrities go pull (cheap writes). The read path merges the two. This directly reuses post 3's hot-key insight — a handful of keys drive disproportionate load and need their own path.

| Approach | Write cost | Read cost | Best for |
|---|---|---|---|
| Fan-out on write (push) | High (200x amplification) | Very low (one lookup) | Ordinary accounts |
| Fan-out on read (pull) | None | High (query N followees) | Celebrities, inactive users |
| Hybrid (push + pull merge) | Bounded | Low + small merge | The real system |

**At 10x scale** (1B DAU): the fan-out queue and worker fleet become the constraint long before storage does. You would push the push/pull threshold lower (more accounts served by pull), partition the fan-out queue by author-shard to parallelize, and consider regional feed caches to keep reads local (post 1's cross-continent latency tax). Storage grows linearly and is boring; the write amplification grows and is not.

**What we deliberately deferred:** ML ranking (we ship chronological — ranking is a scoring layer over the same materialized feed, added later without touching the write path); media storage and CDN (posts carry a `media_url`; the blob layer is a separate design); full-text search; notifications; and multi-region active-active with its consistency headaches. Each is a real feature and each is *out of scope by choice*, so the core design stays legible.

**The gotcha:** always name what you deferred and why — deferral is a design decision, not an omission. And resist over-engineering for scale you don't have: at a few thousand users this entire architecture is malpractice, and a single Postgres with a well-indexed `posts` table and a query-time join over the follow graph handles far more load than people expect. Build the fan-out machine only when the estimation numbers demand it. The discipline cuts both ways — scale up when the arithmetic says so, and *not before*.

---

## The series arc

Step back and the whole series is one method applied seven times:

```text
1 method      -> ask requirements, estimate, contract, spiral to bottleneck
2 scaling     -> stateless tier, scale out, load-balance the read fleet
3 caching     -> precompute the feed; latency bought with a little staleness
4 data        -> shard posts by id, feed by reader; the shard key decides everything
5 consistency -> eventual for others, read-your-own-writes for you
6 async       -> queue the fan-out; decouple fast publish from expensive spread
7 reliability -> idempotent retries, rate limits, degrade to pull on failure
8 this design -> compose all of the above under one set of requirements
```

Every arrow is a trade-off chosen on purpose, and every choice traces back to a requirement extracted in step one. That is the throughline of the entire series: **system design is disciplined trade-off analysis, not a memorized parts list.** The engineer who recites "load balancer, cache, queue, sharded DB" has a vocabulary; the engineer who can say *why the feed shards by reader, why fan-out is async, and why celebrities get a different path — and what each choice costs* — has a method. The vocabulary fails on the next unfamiliar problem. The method does not.

---

## Key takeaways

- **Run the method, don't recall a diagram.** Requirements, estimation, contract, then high-level → deep-dive → bottleneck. The finished picture is a by-product of the sequence.
- **Estimation surfaces the hidden constraint.** The 200x fan-out amplification is invisible until you multiply — and it, not the read rate, dictates the architecture.
- **The shard key and consistency model are the design.** Feed sharded by reader, posts by id, eventual-with-read-your-own-writes — get these right and the rest is plumbing.
- **Precompute to make reads free, then pay for it asynchronously.** Fan-out-on-write is caching the *answer*; the queue absorbs the write cost so publish stays fast.
- **Plan for the failure and the outlier.** Idempotent retries, rate limits, degrade-to-pull, and a hybrid push/pull path for celebrities — the edge cases are where real designs are decided.
- **Name what you defer, and don't over-build.** Chronological before ML ranking, one Postgres before a fan-out machine. Scale when the arithmetic demands it, not before.

---

## Further reading

- [Google SRE Book](https://sre.google/sre-book/table-of-contents/) — Site Reliability Engineering; the chapters on SLOs, load balancing, addressing cascading failures, and handling overload underpin the reliability deep-dive.
- [The Site Reliability Workbook](https://sre.google/workbook/table-of-contents/) — the practical companion, with concrete patterns for load shedding, retries, and graceful degradation.
- [Amazon Builders' Library: Timeouts, retries, and backoff with jitter](https://aws.amazon.com/builders-library/timeouts-retries-and-backoff-with-jitter/) — primary-source guidance on making the fan-out and read paths resilient.
- [Amazon Builders' Library: Caching challenges and strategies](https://aws.amazon.com/builders-library/caching-challenges-and-strategies/) — the materialized-feed-as-cache decisions, invalidation, and hot keys.
- [Amazon Dynamo paper](https://www.allthingsdistributed.com/files/amazon-dynamo-sosp2007.pdf) — the canonical treatment of partitioning, eventual consistency, and the availability/consistency trade-off.
- [Redis documentation: Sorted sets](https://redis.io/docs/latest/develop/data-types/sorted-sets/) — the data structure that maps directly onto a per-user materialized feed of time-ordered post ids.
- [Brewer's CAP theorem, formalized](https://users.ece.cmu.edu/~adrian/731-sp04/readings/GL-cap.pdf) — Gilbert and Lynch, the formal basis for the consistency choices made throughout the series.
- [AWS Well-Architected Framework](https://docs.aws.amazon.com/wellarchitected/latest/framework/welcome.html) — the reliability, performance, and cost pillars, and the trade-offs between them, as a checklist against any finished design.
