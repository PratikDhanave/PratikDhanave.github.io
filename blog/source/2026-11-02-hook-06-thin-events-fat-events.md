# Thin Events, Fat Events — Payload Design and the Fetch-on-Event Pattern

*Every webhook program eventually argues about payload shape: send the whole resource ("fat"), or just an ID and a hint ("thin")? The argument feels stylistic and is actually architectural — it decides your staleness semantics, your security exposure, your versioning burden, and whether consumers converge on truth or drift from it. This post makes the trade explicit, explains why providers have been drifting thin, and locates the pattern most receivers should default to: the event as doorbell, the API as truth.*

Posts [1](/blog/posts/hook-01-why-webhooks-are-hard.html)–[3](/blog/posts/hook-03-idempotent-consumption.html) kept bumping into this choice — point-in-time payloads, fetch-on-event as an ordering cure. This post gives it the full treatment, including the adjacent choice everyone revisits annually: events versus polling.

## The trade, stated honestly

**Fat events** carry the resource state at event time. Their virtue is self-containment: one delivery, zero follow-up calls, consumers can be simple and even offline-processable. Their costs compound with scale: the payload is **stale by construction** (post 1 — the resource may have changed before processing, badly so for day-late retries); every delivery **broadcasts full state** to every endpoint, logs, and queues along the way (a data-exposure surface post 4 cares about — payment and PII fields living in third-party request logs); and the payload schema becomes a **second public API** that must be versioned in lockstep with the real one, doubling the compatibility surface ([API Versioning and Evolution](/blog/series/api-versioning-and-evolution/) territory).

**Thin events** carry identity and occurrence: resource type, ID, what happened, when, a version number. The consumer fetches current state if it cares. Costs: a read API call per interesting event (amplified across consumers), and consumers must be online to the API. Virtues: the fetch returns **current truth, with proper authorization**, through the one API whose versioning you already manage; the event itself exposes almost nothing; and — the quiet structural win — duplicates and disorder *both* collapse, because any sequence of "something changed" doorbells followed by fetches converges on the same state (post 3's analysis). Providers at scale drift thin for exactly these reasons, with read-amplification managed by consumer-side debouncing: coalesce a burst of doorbells for one resource into one fetch.

## The receiver's default: doorbell + fetch + upsert

For state synchronization — the most common webhook job — the pattern that resists the most failure modes is: treat events as **notifications that a resource deserves attention**; on receipt (through post 5's queue), fetch the resource; **upsert by version** (post 3's gate). Events may lie about details, arrive twice, or arrive backwards; the fetch cannot, because it asks the source of truth *now*. The fat payload, when present, demotes to an optimization hint: process from it only when its version stamp proves it's not stale, fetch otherwise — fast path when safe, truthful path when not. When *not* to pay the fetch: genuinely immutable event-shaped facts (a log entry, a completed one-shot) where the payload can't go stale because the fact can't change — fat is fine there, and that's precisely the boundary: **fat for facts, thin for state**.

## Events versus polling: the honest comparison

The adjacent decision deserves its honest framing, because "webhooks replaced polling" is marketing, not architecture. **Polling** gives you consumer-controlled pacing, trivially testable flows, no public endpoint (post 4's whole surface gone), and bounded staleness equal to the interval — at the cost of latency floor and wasted reads. **Events** give you low latency and proportional work — at the cost of the entire discipline this series exists to teach. The mature answer is usually **both**: events for latency, a slow reconciliation poll for truth (post 8 builds this out), because the poll catches exactly what events structurally can't — the deliveries that never came. And modern providers increasingly offer a third shape worth preferring when available: **pull-based event feeds** (cursor-paged event lists you consume at your pace) — polling's control with events' granularity, and no inbound endpoint at all.

The takeaway: payload shape is architecture — **fat events** are self-contained but stale-by-construction, data-exposing, and a second API to version; **thin events** are doorbells whose follow-up fetch returns authorized, current truth and structurally dissolves duplicate/ordering problems at the price of read amplification (debounce it). Default to **doorbell → queued fetch → version-gated upsert** for state sync, accept fat payloads only as version-proven fast paths, keep fat for immutable facts — and pair events with reconciliation polling (or prefer cursor-paged event feeds outright), because latency and truth are different requirements and no single channel serves both.

## Key takeaways

- The trade is architectural: fat = self-contained but **stale, exposing, doubly-versioned**; thin = **fetch-for-truth** with read amplification (coalesce bursts per resource).
- Default pattern for state sync: **event as doorbell → fetch current state → upsert by version** — converges under duplication and disorder because the API, not the payload, is truth.
- Fat payloads demote to **optimization hints**: use only when a version stamp proves freshness; fetch otherwise. Rule of thumb: **fat for immutable facts, thin for mutable state**.
- Events vs polling isn't a rivalry: events buy latency, polling buys control and bounded staleness — mature systems run **events + reconciliation polling**, and cursor-paged **event feeds** are often the best of both with no inbound endpoint.

## Further reading

- [Publish–subscribe pattern — the decoupling model payload design lives inside](https://en.wikipedia.org/wiki/Publish%E2%80%93subscribe_pattern)
- [Polling (computer science) — the alternative that never actually went away](https://en.wikipedia.org/wiki/Polling_(computer_science))
