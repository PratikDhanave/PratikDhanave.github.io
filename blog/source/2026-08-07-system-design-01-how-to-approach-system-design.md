# How to Approach System Design

*A repeatable method for designing systems and acing the design interview — clarify requirements, estimate on the back of an envelope, pin down the API and data model, then work high-level to deep-dive to bottleneck, always naming the trade-off.*

---

Most people treat system design as a memory test: enumerate a load balancer, a cache, a message queue, a sharded database, and hope the interviewer nods. That approach falls apart the moment the problem is unfamiliar, because you have no way to decide *which* components belong and *why*. The engineers who design well — and who breeze through the interview — are not recalling a parts list. They are running a **method**: a small set of questions asked in a fixed order that turns a vague prompt into a defensible design.

This post opens a series on that method. It is deliberately component-free. We will not talk about how a specific database replicates or how a cache evicts until later posts. Here the goal is the *procedure* you apply to every problem, and the one idea that sits underneath all of it: **there is no free lunch.** Every choice you make buys one property by spending another — latency for consistency, cost for durability, simplicity for scale. Design is the discipline of choosing which bill to pay.

---

## Start by refusing to design

The single most common failure in a design interview is drawing boxes before understanding the problem. A prompt like "design a URL shortener" or "design a news feed" is intentionally underspecified. Your first move is not to reach for a whiteboard — it is to ask questions until the problem has edges.

Split the questions into two buckets.

**Functional requirements** are what the system *does* — the observable behaviors. For a URL shortener: create a short link from a long URL, redirect a short link to its target, optionally let users pick a custom alias, optionally show click analytics. Write these as a short list of verbs. If you can't state them in one breath, you don't understand the problem yet.

**Non-functional requirements** are the properties the system must hold *while* doing those things. These are what actually shape the architecture, and there are six you should ask about every single time:

- **Scale** — how many users, how many requests, how much data, and the read-to-write ratio. A 100:1 read-heavy system and a write-heavy system are different machines.
- **Latency** — how fast a response must feel. "Under 100 ms at the p99" is a design constraint; "fast" is not.
- **Availability** — what fraction of the time it must work. Three nines (99.9%) allows ~8.8 hours of downtime a year; four nines (99.99%) allows ~53 minutes. Each extra nine roughly multiplies your cost and complexity.
- **Consistency** — must every reader see the latest write immediately (strong), or is a short lag acceptable (eventual)? A bank balance and a "likes" counter sit at opposite ends.
- **Durability** — once you acknowledge a write, can you ever lose it? A photo upload demands durability; an ephemeral typing indicator does not.
- **Cost** — the budget, human and financial. Infinite scale at infinite cost is not an achievement.

**The gotcha:** the interviewer will rarely volunteer these numbers — extracting them *is* the test. And the answers are not academic. "Read-heavy, eventual consistency is fine, four nines" points you straight at replicas and caching; "write-heavy, strongly consistent, durable" points at a very different, harder design. If you skip this step, every later decision is a guess.

---

## Back-of-the-envelope estimation

Once you know the scale, translate it into numbers *before* you design, because the numbers decide whether one machine suffices or you need a hundred. This is arithmetic, not engineering, and the interviewer wants to see the arithmetic, not a precise answer.

Two tables make this fast. First, the powers of two — because bytes come in these sizes:

```text
2^10  ≈ 1 thousand   1 KB
2^20  ≈ 1 million     1 MB
2^30  ≈ 1 billion     1 GB
2^40  ≈ 1 trillion    1 TB
2^50  ≈ 1 quadrillion 1 PB
```

Second, the order-of-magnitude latencies every engineer should carry in their head. These are well-known ballpark figures — not benchmarks from any specific machine — and their *ratios* are what matter:

```text
L1 cache reference                    ~1 ns
Main memory (RAM) reference           ~100 ns
Read 1 MB sequentially from RAM       ~10 µs
Read 1 MB sequentially from SSD       ~200 µs
Round trip within the same datacenter ~500 µs
Read 1 MB sequentially from SSD       ~1 ms
Disk seek (spinning disk)             ~10 ms
Round trip across continents          ~150 ms
```

The lesson lives in the gaps: memory is roughly a hundred times faster than SSD, SSD is far faster than a spinning-disk seek, and a cross-continent round trip is glacial next to all of them. This is *why* caching in RAM beats hitting disk, and why chatty cross-region calls kill latency — you can reason about it from the ratios alone.

Now a worked estimate. Suppose our URL shortener must support **100 million new links per day** and is heavily read — say **100 reads per write**.

```text
Writes per second (QPS):
  100,000,000 writes/day ÷ 86,400 s/day ≈ 1,160 writes/sec
  (round the day to ~10^5 s to do this in your head: 10^8 / 10^5 = 10^3)

Reads per second:
  1,160 × 100 ≈ 116,000 reads/sec

Peak (assume ~2× average):
  writes ≈ 2,300/sec, reads ≈ 232,000/sec

Storage per link (URL + alias + metadata) ≈ 500 bytes:
  per day:  10^8 × 500 B = 5 × 10^10 B  = 50 GB/day
  per year: 50 GB × 365  ≈ 18 TB/year
  over 5 years          ≈ 90 TB

Read bandwidth (a redirect returns a tiny response, say ~500 B):
  232,000 reads/sec × 500 B ≈ 116 MB/sec outbound

Cache sizing (Pareto: ~20% of links drive ~80% of reads):
  hot set ≈ 20% of one day's links = 2 × 10^7 links × 500 B ≈ 10 GB
  → a hot working set that fits comfortably in the RAM of a single cache node
```

Nothing here is exact, and that is the point. In under two minutes you learn that reads dominate by two orders of magnitude (so you will lean on caching and read replicas), that five years of data is tens of terabytes (so a single node won't hold it — you'll shard), and that the hot set fits in memory (so a cache will absorb most traffic cheaply). The design has *already* started to take shape, driven entirely by numbers.

**The gotcha:** never invent precise figures to sound authoritative — "we'll do 47,000 QPS at 12 ms p99" from thin air is a red flag. Round aggressively (a day is ~10^5 seconds, a year is ~3×10^7), state your assumptions out loud, and let the interviewer correct them. The estimate is a *tool for making decisions*, not a prediction; being right to one significant figure is exactly enough.

---

## Pin down the API and the data model

With requirements and rough scale in hand, define the contract before the boxes. This forces precision and exposes hidden requirements early.

The **API** is the set of operations clients can invoke. Keep it small and explicit:

```text
POST /shorten        { long_url, custom_alias? }  -> { short_url }
GET  /{short_code}                                -> 302 redirect to long_url
GET  /{short_code}/stats                          -> { clicks, created_at }
```

Even this tiny sketch surfaces decisions: is `custom_alias` allowed, and how do you handle collisions? Does the redirect return 301 (permanent, aggressively cached by browsers — great for load, terrible for analytics) or 302 (temporary, so every click reaches your server and can be counted)? That one status code is a genuine trade-off between offloading traffic and capturing data — and you only notice it by writing the API down.

The **data model** is the shape of what you store. For our shortener, the core entity is small:

```text
Link
  short_code   string   (primary key)
  long_url     string
  user_id      string   (nullable)
  created_at   timestamp
  click_count  integer
```

Modeling it raises the next round of questions. How do you generate `short_code` — a hash of the URL (deterministic, but collisions need handling), or a counter encoded in base-62 (unique by construction, but reveals volume and needs a distributed ID scheme)? Should `click_count` live on this row (simple, but a hot row under heavy writes) or in a separate append-only analytics store (scales writes, adds complexity)? You do not have to resolve all of these now — but naming them here means your high-level design can address them deliberately instead of by accident.

---

## High-level design, then deep-dive, then bottlenecks

Now, and only now, draw the architecture. Do it in three passes, widening focus each time.

**Pass 1 — high-level design.** Sketch the major components and the data flow between them, end to end, at low resolution: clients hit an API layer through a load balancer; writes go to a datastore; reads are served from a cache that falls back to the datastore; analytics events flow to a separate pipeline. Boxes and arrows. The goal is a design that plausibly satisfies the functional requirements — no more. Resist the urge to detail any single box; you are proving the whole thing hangs together.

**Pass 2 — deep-dive.** Pick the components where the non-functional requirements actually bite and zoom in. Given our estimate — read-heavy, tens of terabytes, a small hot set — the interesting boxes are the cache (what do we cache, how do we invalidate, what happens on a miss) and the datastore (how do we shard 90 TB, what's the partition key, how do reads find the right shard). Spend your time where the numbers said the pressure is, not on the parts that are obviously fine.

**Pass 3 — bottlenecks and trade-offs.** Now attack your own design. Where does it fall over? If the cache node dies, does a thundering herd of 232,000 reads/sec stampede the database? If one shard holds a viral link, is it a hotspot? What's the single point of failure? For each weakness, name the fix *and its cost*: adding cache replicas improves availability but risks serving stale data; adding a write-ahead queue smooths write spikes but adds latency and a component to operate. Stating the cost is what separates a designer from a box-drawer.

**The gotcha:** the flow is a spiral, not a straight line. Discovering a bottleneck in pass 3 often sends you back to revise the data model or even re-ask a requirement ("do we actually need real-time click counts, or is a one-minute delay fine?"). Interviewers reward that loop — it shows you're reasoning, not reciting. What they penalize is diving into the deepest detail of one component before the high-level design exists.

---

## The one idea underneath all of it: no free lunch

Every decision in this series will come back to a single principle: **you cannot maximize everything at once.** The famous constraints make this concrete. The CAP theorem (Gilbert and Lynch's formalization of Brewer's conjecture) says that when the network partitions — and it will — a distributed system must choose between remaining consistent and remaining available; it cannot have both during the partition. That is not a law about databases specifically; it is a law about the universe the system lives in.

The same tension appears everywhere, wearing different clothes:

| You want more… | You usually pay with… | Example |
|---|---|---|
| Lower latency | Freshness / consistency | Serve from cache, risk staleness |
| Stronger consistency | Higher latency / lower availability | Synchronous cross-region writes |
| Higher availability | More cost / more staleness | Extra replicas across zones |
| Higher durability | Higher write latency | Wait for N replicas to acknowledge |
| More scale | More complexity | Sharding, coordination, operations |
| Less complexity | Less scale / less flexibility | One big database, until it isn't enough |

Good design is not the absence of trade-offs — it is choosing the *right* trade-off for the requirements you extracted in step one. That is why the method starts with requirements and ends with trade-offs: the first step tells you which properties you're allowed to spend, and the last step is where you spend them on purpose.

---

## What the rest of this series covers

This opener is the method. The posts that follow apply it to each major dimension of system design, and every one of them is a study in the trade-off above:

1. **How to approach system design** (this post) — the method and the core tension.
2. **Scaling** — vertical vs. horizontal, load balancing, statelessness, and why "just add servers" hides real coordination costs.
3. **Caching** — where to cache, invalidation strategies, and the trade of latency for freshness.
4. **Databases and storage** — SQL vs. NoSQL, indexing, partitioning, and sharding a dataset that outgrows one machine.
5. **Consistency and consensus** — replication, quorums, and the algorithms (Paxos, Raft) that let machines agree despite failures.
6. **Asynchronous processing** — queues, event streams, and decoupling producers from consumers to absorb spikes.
7. **Reliability and resilience** — redundancy, failover, timeouts, retries, and designing for the failure that *will* happen.
8. **A full worked design** — one problem, end to end, running the entire method from clarifying questions to bottleneck analysis.

Each post assumes the method from this one. When you read "we'll cache the hot set," the questions in your head should already be: *what's the read-to-write ratio, what does an in-memory read save us over a disk read, and what does stale data cost the user?* If those questions come automatically, the method has done its job.

---

## Key takeaways

- **Design is a method, not a parts list.** Ask requirements, estimate, define the contract, then design in three passes. The procedure survives unfamiliar problems; memorized components do not.
- **Requirements come in two buckets.** Functional (what it does) and non-functional (scale, latency, availability, consistency, durability, cost). The non-functional ones shape the architecture — always extract the numbers.
- **Estimate before you design.** Round aggressively, carry the powers-of-two and latency ratios in your head, and let the arithmetic tell you where the pressure is. Never invent precise benchmarks.
- **Write the API and data model early.** They force precision and surface hidden trade-offs (301 vs. 302, hash vs. counter) before they become mistakes.
- **Work high-level → deep-dive → bottleneck, and loop back.** Prove the whole system hangs together first; zoom in where the numbers say it matters; then attack your own design.
- **There is no free lunch.** Every property you gain is paid for by another. Good design is choosing the right bill to pay for the requirements you were given.

---

## Further reading

- [Latency Numbers Every Programmer Should Know](https://static.googleusercontent.com/media/sre.google/en//static/pdf/rule-of-thumb-latency-numbers-letter.pdf) — Jeff Dean's widely cited order-of-magnitude latency figures (Google SRE).
- [Google SRE Book](https://sre.google/sre-book/table-of-contents/) — Site Reliability Engineering, especially the chapters on service level objectives, availability, and embracing risk.
- [Brewer's CAP theorem, formalized](https://users.ece.cmu.edu/~adrian/731-sp04/readings/GL-cap.pdf) — Gilbert and Lynch, "Brewer's Conjecture and the Feasibility of Consistent, Available, Partition-Tolerant Web Services."
- [CAP Twelve Years Later: How the "Rules" Have Changed](https://www.infoq.com/articles/cap-twelve-years-later-how-the-rules-have-changed/) — Eric Brewer's own reflection on what CAP does and doesn't say.
- [AWS Well-Architected Framework](https://docs.aws.amazon.com/wellarchitected/latest/framework/welcome.html) — official pillars (reliability, performance efficiency, cost optimization) and the trade-offs between them.
- [Google Cloud Architecture Framework](https://cloud.google.com/architecture/framework) — Google's counterpart, with concrete guidance on reliability, scalability, and cost.
- [Amazon Dynamo paper](https://www.allthingsdistributed.com/files/amazon-dynamo-sosp2007.pdf) — a primary source on eventual consistency, partitioning, and the availability/consistency trade-off in practice.
