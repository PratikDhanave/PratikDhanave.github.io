# Fault Tolerance and Exactly-Once — Not Losing or Double-Counting

*A stream-processing job runs forever, which means it will experience failures — nodes crash, networks partition, processes restart. The question isn't whether failure happens but what happens to your results when it does: do you lose events, double-count them, or get exactly the right answer anyway? Fault tolerance, and the famous "exactly-once" guarantee, are what separate a toy stream processor from one you can trust with money. This post is about surviving failure correctly.*

Post 5 established that stateful streaming's hardest problem is surviving failure, because state is the accumulated result of processing countless past events. This post is how modern stream processors solve it — checkpointing and exactly-once semantics — and what those guarantees really mean. It's the concept that makes stateful streaming trustworthy.

## The delivery guarantees: at-most, at-least, exactly-once

When a stream processor fails and recovers, each event ends up having been processed in one of three ways, and these define the fundamental guarantees:

- **At-most-once** — each event is processed *zero or one* times. On failure, in-flight events may be *lost* (never processed). Simple and fast (no bookkeeping), but you lose data on failure — acceptable only when occasional loss is tolerable (some metrics, some logs). The weakest guarantee.
- **At-least-once** — each event is processed *one or more* times. On failure, the processor replays events to ensure none are lost — but some may be processed *more than once* (the ones in flight during the failure get reprocessed on recovery). No data loss, but **duplicates**. Common and often acceptable *if* your processing is idempotent (reprocessing a duplicate doesn't change the result).
- **Exactly-once** — each event affects the result *exactly one time*, even across failures — no loss, no duplicates. The result is *as if* each event were processed precisely once. This is the gold standard, and it's what you need when duplicates or losses corrupt correctness — counting money, billing, any aggregate where double-counting is wrong.

The crucial subtlety: "exactly-once" doesn't mean each event is *physically* processed exactly once (failures force replays, so physical reprocessing happens) — it means each event's *effect on the state and results* is exactly-once. It's **exactly-once *semantics***: the outcome is correct as if there were no duplicates or losses, achieved *despite* physical replays. Understanding that distinction (effect, not physical execution) is key to understanding how it's possible at all.

Why this matters: for many financial and correctness-critical streams (the kind the [fintech](/blog/series/the-fintech-engineering-handbook/) and AI-financial-engineering work cares about), at-least-once's duplicates would mean double-counting transactions — unacceptable — so exactly-once is the required guarantee, and it's a major reason modern stream processors exist.

## How exactly-once is achieved: checkpointing

The mechanism behind exactly-once (and fault tolerance generally) is **checkpointing**: periodically taking a *consistent snapshot* of the entire job's state (post 5) and the stream positions, durably, so that on failure the job can restore that snapshot and resume *as if the failure hadn't happened*.

The idea, at a high level:

- **Consistent distributed snapshots.** The processor periodically snapshots *all* its distributed state (post 5's keyed state across all nodes) together with *where it was in the input stream* (the offsets/positions), in a way that's **consistent** — the state snapshot corresponds exactly to having processed the stream up to those recorded positions. (Flink's mechanism, based on the Chandy-Lamport distributed-snapshot algorithm, inserts markers into the stream to coordinate a consistent snapshot without stopping processing.) This consistency is the hard part — snapshotting a distributed, continuously-running computation at a coherent point.
- **Durable storage.** Checkpoints are written to durable, reliable storage (distributed file systems/object storage), so they survive the crash of any processing node.
- **Recovery by restore-and-replay.** On failure, the job restores the last checkpoint — the state *and* the stream positions — and resumes reading the input *from those positions*. Because the input stream is replayable (durable logs like Kafka let you re-read from an offset — the [Kafka series](/blog/series/event-driven-architecture-with-kafka/)), the job reprocesses events after the checkpoint, rebuilding to exactly where it was. State is restored, not lost (post 5's catastrophe averted).

This gives *at-least-once* on its own (replayed events after the checkpoint get reprocessed). To reach *exactly-once*, two more things are needed:
- **State updates are tied to checkpoints** so that on restore, the state reflects exactly the checkpointed position — no double-applied updates to state.
- **Outputs/sinks must cooperate.** The genuinely hard part: the *external effects* (writing to a database, sending to another system) must also be exactly-once, which requires **transactional or idempotent sinks** — the sink either participates in a transaction committed with the checkpoint (two-phase commit), or is idempotent so replayed writes don't duplicate. Exactly-once *end-to-end* requires the whole pipeline (source → processing → sink) to cooperate, and the sink is usually the limiting factor.

So exactly-once is: consistent checkpointing of state+positions, replayable sources, and transactional/idempotent sinks — together producing correct results despite failures and physical replays.

## What it costs, and choosing the right guarantee

Exactly-once is powerful but not free, and the engineering judgment is choosing the guarantee that fits:

- **Exactly-once has overhead.** Checkpointing consistent distributed state costs performance and latency (coordinating snapshots, writing to durable storage), and transactional sinks add latency (commit coordination). Stronger guarantees cost more throughput and latency — a real tradeoff.
- **Choose the guarantee by need.** **At-most-once** when loss is tolerable and you want max speed/simplicity (some telemetry). **At-least-once** when you can't lose data and your processing/sink is *idempotent* (so duplicates don't matter) — often the pragmatic sweet spot, cheaper than exactly-once. **Exactly-once** when duplicates or losses corrupt correctness (money, billing, exact counts) and you'll pay the overhead for it. Matching the guarantee to the correctness requirement is the key decision — don't pay for exactly-once where at-least-once-plus-idempotency suffices, and don't risk at-least-once's duplicates where correctness demands exactly-once.
- **Idempotency is the cheap escape.** A powerful pattern: make your processing/sink **idempotent** (reprocessing an event produces the same result — e.g. upserts keyed by event ID), and then cheap at-least-once delivery gives effectively-correct results without the full cost of exactly-once. Designing for idempotency is often the pragmatic path to correctness.

The through-line: a forever-running stream job *will* fail, so fault tolerance is non-negotiable, and the guarantee you provide — at-most-once (may lose), at-least-once (may duplicate), exactly-once (correct as if neither) — determines whether your results survive failure correctly. Exactly-once *semantics* (correct effects despite physical replays) is achieved by **consistent checkpointing** of distributed state and stream positions to durable storage, **replayable sources**, and **transactional/idempotent sinks** — restoring and replaying from the last checkpoint so the job resumes as if nothing failed. It costs performance, so choose the guarantee by the correctness need, using **idempotency** as the pragmatic route to correctness where full exactly-once isn't warranted. This is the machinery that makes stateful streaming trustworthy enough to count money on, and it's a defining capability of serious stream processors.

The throughline: a forever-running stream job **will fail**, so fault tolerance is non-negotiable and the **delivery guarantee** decides whether results survive correctly: **at-most-once** (0-or-1 processing — may *lose* events; fast/simple, weakest), **at-least-once** (1-or-more — no loss but **duplicates**; fine if processing is idempotent), or **exactly-once** (each event affects the result *exactly one time* despite failures — the gold standard for money/billing/exact counts). Crucially, exactly-once means exactly-once **semantics** (correct *effect* on state/results despite physical replays), not physical single execution. It's achieved by **checkpointing** — periodic **consistent snapshots** of all distributed state (post 5) *plus* stream positions, written **durably** — with recovery by **restore-and-replay from the last checkpoint** over **replayable sources** (Kafka offsets), plus **transactional/idempotent sinks** for end-to-end exactly-once (the sink is usually the limiting factor). Stronger guarantees **cost** throughput/latency, so choose by correctness need, using **idempotency** as the cheap route to correctness.

## Key takeaways

- A forever-running stream job **will experience failures**, so fault tolerance is non-negotiable, and the **delivery guarantee** determines what happens to results on failure.
- Three guarantees: **at-most-once** (0-or-1 — may *lose* in-flight events; fast, simple, weakest), **at-least-once** (1-or-more — no loss but **duplicates** on replay; fine if processing is **idempotent**), **exactly-once** (each event affects the result **exactly one time** despite failures — gold standard for money/billing/exact counts where loss or double-counting corrupts correctness).
- Key subtlety: **exactly-once means exactly-once *semantics*** — each event's *effect on state/results* is exactly-once, achieved *despite* physical replays (failures force reprocessing); it does *not* mean each event is physically processed once.
- Achieved by **checkpointing**: periodic **consistent distributed snapshots** of all state (post 5) *and* stream positions/offsets, written to **durable storage**; on failure, **restore the last checkpoint and replay** from those positions over a **replayable source** (durable logs like Kafka — restoring state rather than losing it). Reaching exactly-once *end-to-end* also needs **transactional or idempotent sinks** (two-phase commit or idempotent writes — the sink is usually the limiting factor).
- Stronger guarantees **cost** throughput/latency (snapshot coordination, durable writes, transactional commits), so **choose the guarantee by the correctness requirement** — and use **idempotency** (reprocessing yields the same result, e.g. event-ID-keyed upserts) as the pragmatic, cheaper route to correctness where full exactly-once isn't warranted. This machinery is what makes stateful streaming trustworthy enough to count money on.

## Further reading

- [Stream processing — fault tolerance and processing guarantees](https://en.wikipedia.org/wiki/Stream_processing)
- [Apache Flink — checkpointing and exactly-once semantics](https://en.wikipedia.org/wiki/Apache_Flink)
