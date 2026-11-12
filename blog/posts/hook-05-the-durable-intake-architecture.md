<!-- Markdown version for AI agents and readers. Canonical: https://pratikdhanave.com/blog/posts/hook-05-the-durable-intake-architecture.html -->

# The Durable Intake Architecture — Queues Behind Endpoints, DLQs, and Poison Events

*The naive webhook handler does everything inline: receive, verify, run business logic, call three services, return 200. It works in the demo and fails in every interesting way in production — timeouts under load, lost events on deploy, one bad payload blocking the stream. The production architecture is almost boringly uniform across serious teams: a thin endpoint that durably enqueues and immediately acks, workers that process from the queue, and explicit machinery for the events that refuse to process. This post builds that architecture piece by piece.*

Posts [2](/blog/posts/hook-02-delivery-semantics.html)–[4](/blog/posts/hook-04-webhook-security.html) defined the semantics, consumption discipline, and verification; this post is where they get a home. The queueing theory underneath is [Kafka-series](/blog/series/event-driven-architecture-with-kafka/) territory; here it's applied to the integration edge.

## The core separation: accept fast, process safely

The architecture's one big idea is splitting the receiver into two halves with a durable buffer between:

- **The endpoint** does the minimum that must happen synchronously: verify the signature (post 4 — before anything touches a queue), optionally claim the event ID (post 3's atomic insert, which also dedups at the door), persist the raw event durably, return 2xx. Milliseconds of work, no business logic, no downstream calls — which satisfies post 2's ack-on-durable-acceptance rule and keeps you inside provider timeouts no matter what processing costs.
- **The queue** is the durability boundary: once enqueued, the event survives deploys, worker crashes, and downstream outages. The provider's retry machinery (post 2) covers you *up to* the ack; the queue covers you after. Between them, no gap — that's the whole reliability story in one sentence.
- **Workers** consume at their own pace, apply post 3's idempotent processing, and absorb downstream slowness by letting depth grow rather than dropping work. Partitioning by resource ID gives the per-aggregate serialization post 3 wanted; concurrency scales across resources while staying serial within one.

The payoff shows up operationally: deploys stop losing events (the endpoint and workers roll independently; the queue holds the difference), load spikes become queue depth instead of 5xx storms, and a downstream dependency's outage becomes *lag you can watch* instead of data loss you discover.

## Failure routing: retries, DLQs, and poison events

Within the worker, failures need routing, not heroics. **Transient failures** (downstream timeout, lock contention) retry with backoff-and-jitter — your own internal copy of post 2's machinery, with a bounded attempt budget. **Persistent failures** exhaust the budget and move to the **dead-letter queue**: a durable parking lot for events that couldn't process, carrying the original payload, the error history, and attempt metadata. The DLQ's three operational rules decide whether it's a safety net or a landfill: it is **monitored** (depth > 0 pages someone — every entry is a failed state change), **diagnosable** (enough context attached to debug without archaeology), and **replayable** (after the fix ships, dead-lettered events re-enter processing — which is why post 3's idempotency isn't optional: replay is a planned operation, not an emergency).

**Poison events** are the special case the DLQ exists for: a payload that *deterministically* crashes the handler — the malformed edge case, the unexpected null, the schema surprise. Without a DLQ, a poison event and at-least-once redelivery combine into a processing loop that blocks its partition forever (the retry budget is the circuit breaker that routes it out). Two refinements: distinguish *can't-parse* (quarantine immediately, don't burn retries) from *can't-process* (retry, then dead-letter), and record the handler version with each failure — half of poison diagnosis is "which deploy stopped understanding this shape."

## The operational dashboard this architecture implies

The architecture names its own health metrics: **ingress rate vs processing rate** (sustained divergence = falling behind), **queue depth and oldest-message age** (lag made visible — age matters more than depth), **retry rate by error class** (rising transients = a downstream degrading), **DLQ depth and age** (should hover at zero), and **end-to-end latency** from provider event-time to effect-applied (the number your users actually experience as "sync delay"). Alert on age and DLQ entries; graph the rest. A webhook pipeline without these is reliable only in the sense that nobody knows otherwise.

The takeaway: the production receiver is a **thin verifying endpoint + durable queue + idempotent workers** — accept in milliseconds, process at leisure, partition by resource for ordering, and let provider retries and queue durability meet with no gap between them. Failures route rather than block: bounded internal retries for transients, a **monitored, diagnosable, replayable DLQ** for the persistent, immediate quarantine for the unparseable — so one poison payload never dams the stream. The dashboard falls out of the design: rates, depth, age, retry classes, DLQ, end-to-end lag. Boring architecture, precisely because it has absorbed every exciting failure already.

## Key takeaways

- Split receive from process: endpoint does **verify → claim → persist → 2xx** in milliseconds; queue is the durability boundary; workers apply idempotent logic, partitioned by resource ID.
- Provider retries protect up to the ack; the queue protects after — **designed correctly, there is no gap**, and deploys/spikes/outages become lag, not loss.
- Route failures: bounded backoff for transients → **DLQ** (monitored, diagnosable, replayable) for the persistent → immediate quarantine for can't-parse; the retry budget is the circuit breaker that stops **poison events** from blocking partitions.
- Replay is a planned operation — which is why post 3's idempotency is architectural, not optional.
- The health model is implied by the design: ingress vs processing rate, depth, **oldest-message age**, retry classes, DLQ depth/age, end-to-end sync latency.

## Further reading

- [Message queue — the durability boundary at the center](https://en.wikipedia.org/wiki/Message_queue)
- [Dead letter queue — the parking lot that keeps failure from blocking flow](https://en.wikipedia.org/wiki/Dead_letter_queue)

---

Author: Pratik Dhanave (https://pratikdhanave.com) | Published: 2026-11-01
Canonical: https://pratikdhanave.com/blog/posts/hook-05-the-durable-intake-architecture.html
Attribution: please link the canonical URL when citing or quoting this post.
