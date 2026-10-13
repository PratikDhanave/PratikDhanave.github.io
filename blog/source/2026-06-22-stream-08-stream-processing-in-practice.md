# Stream Processing in Practice — Building Real Pipelines

*Knowing the concepts and the engines is one thing; building a stream-processing pipeline that's correct, reliable, and operable in production is another. This closing post assembles the series into practical judgment: how to design a streaming pipeline, the operational realities that trip teams up, and when to reach for streaming at all. It turns the theory of data-in-motion into something you can actually run.*

Posts 1–7 built the concepts (events, time, windows, state, fault tolerance) and the systems. This post is how to use them in anger. The recurring theme, as with the blog's other "in practice" posts, is that the model is the easy part — the operational discipline around a forever-running stateful distributed system is the real work.

## Designing a streaming pipeline

A stream-processing pipeline has a recognizable shape, assembling the series:

- **Source** — where events come from, ideally a durable, replayable log (Kafka — the [Kafka series](/blog/series/event-driven-architecture-with-kafka/)) so fault-tolerant replay (post 6) is possible. The source's durability and replayability directly enable the processing guarantees downstream.
- **Processing** — the dataflow of operations (post 2): stateless transforms/filters, then the stateful heart — windowed aggregations (post 4), joins, pattern detection — reasoning in **event time** with **watermarks** (posts 2–3) and managing **state** (post 5).
- **Sink** — where results go (a database, another stream, a dashboard, an alerting system), which must cooperate with the fault-tolerance guarantee (post 6 — transactional/idempotent sinks for exactly-once).

Designing it well means answering the series' questions for your problem: *What's the event-time vs processing-time story* (how late/out-of-order is the data, what watermark policy)? *What windows* (tumbling/sliding/session, post 4)? *What state* and how is it bounded (post 5)? *What guarantee* (at-least-once + idempotency, or exactly-once, post 6)? *What latency* does the problem actually need (post 1)? These decisions, made deliberately, are the design — and getting the time/window/state/guarantee choices right for the problem is most of building a correct pipeline.

## The operational realities

Running a streaming pipeline in production surfaces hard realities beyond a working design:

- **It runs forever, so it must be operable forever.** Unlike a batch job that starts and ends, a streaming job is a *long-lived service* — it needs monitoring, alerting, and the ability to be upgraded, restarted, and scaled *while running*. Operating a perpetual stateful service is fundamentally harder than scheduling a batch job.
- **State is the operational crux.** The large, distributed, fault-tolerant state (post 5) is the hardest thing to operate: checkpoints must succeed and be restorable (test your recovery!), state size must be monitored and bounded (unbounded state growth is the classic production failure), and upgrading a stateful job (changing the code while preserving state — *savepoints*) is a real operational skill. Most serious streaming incidents trace to state.
- **Backpressure and lag.** If the pipeline can't keep up with the input rate, events queue up and *lag* grows — the stream falls behind real time, defeating the point. Monitoring **consumer lag** and handling **backpressure** (the system slowing intake when overwhelmed) are central operational concerns; a streaming pipeline that silently falls behind is a common, damaging failure.
- **Watermark and late-data tuning in reality.** The event-time/watermark/lateness decisions (posts 2–3) must be tuned against *real* data lateness, and real data is messier than the design assumed — so monitoring actual lateness and adjusting watermark policy is ongoing work.
- **Reprocessing and evolution.** Sometimes you must *reprocess* history (a bug fix, a new computation) by replaying the stream from the past (post 6's replayable source enables this), and schemas/logic evolve over a forever-running job — so designing for reprocessing and schema evolution matters.
- **Testing is hard.** Testing stream processing (out-of-order events, late data, failures, state recovery) is harder than testing batch, and under-testing the failure and late-data paths is how pipelines break in production — so deliberately test the messy cases (reordering, lateness, crashes), not just the happy path.

The reality: a production streaming pipeline is a *forever-running, stateful, distributed service*, and the operational burden (state management, lag/backpressure, recovery, evolution) is substantial — much of why streaming is harder than batch is operational, not conceptual.

## When to use streaming — and the honest judgment

Closing the series with the decision that should precede all of it: *should this be a stream at all?*

- **Use streaming when latency genuinely matters** (post 1) — the problem needs to react to or reflect events in near-real-time (fraud, monitoring, real-time analytics, event-driven reaction), and the value decays with delay. This is where streaming's complexity is justified.
- **Prefer batch when you can tolerate latency.** If a problem is fine with periodic results (daily/hourly reports, historical analysis, model training), **batch is simpler, cheaper, and more robust** — don't take on streaming's operational burden (forever-running stateful service, exactly-once machinery) for a problem that doesn't need real-time. Reaching for streaming reflexively is a common over-engineering mistake; the simpler batch job is often the right answer.
- **Consider the spectrum** (post 1) — micro-batching (frequent small batches) or scheduled batch may give "fast enough" results at much lower complexity than true streaming, and is worth considering before committing to a full streaming pipeline.
- **Respect the cost.** Streaming adds real cost — operational complexity, the subtleties of time and state, the always-on infrastructure, the harder testing and debugging — so the latency benefit must genuinely justify it. The honest question is always "does this problem actually need real-time, or am I adding streaming because it's interesting?"

The series' synthesis: stream processing is computing on **unbounded data in motion**, which forces a distinct model — reasoning in **event time** with **watermarks**, bounding the infinite with **windows**, remembering across events with **state**, and surviving failure with **checkpointing and exactly-once** — implemented by engines like Flink and Kafka Streams and operated as a forever-running stateful distributed service. Build a pipeline by deliberately choosing its time/window/state/guarantee/latency story for the problem, operate it with real attention to state, lag, and recovery, and — most importantly — reach for streaming only when latency genuinely justifies its substantial complexity over simpler batch. Done with that judgment, stream processing lets software keep up with a world that happens in real time; done reflexively, it's complexity in search of a problem. Knowing the difference is the point of the series.

The throughline: a production streaming pipeline is **source → processing → sink** — a durable replayable **source** (Kafka) enabling fault tolerance, **processing** (stateless transforms + the stateful heart of windowed aggregations/joins reasoning in event time with watermarks and managed state), and a **sink** cooperating with the guarantee (transactional/idempotent for exactly-once). Design it by deliberately choosing its **event-time/watermark, window, state-bounding, guarantee, and latency** story for the problem. Operate it knowing it's a **forever-running stateful distributed service**: **state is the operational crux** (checkpoints restorable, state bounded, savepoint upgrades — most incidents trace to state), **backpressure/lag** must be monitored (a pipeline silently falling behind defeats the point), watermark/late-data policy needs real-data tuning, and **reprocessing/evolution/testing** (the messy out-of-order/late/failure paths) are hard. Above all, **use streaming only when latency genuinely justifies its complexity** — prefer simpler batch or micro-batch when you can tolerate latency, since reflexive streaming is a classic over-engineering mistake.

## Key takeaways

- A streaming pipeline is **source → processing → sink**: a durable, **replayable source** (Kafka — enables fault-tolerant replay, post 6), **processing** (stateless transforms + the stateful heart — windowed aggregations/joins/pattern detection in **event time** with **watermarks** and managed **state**, posts 2–5), and a **sink** that cooperates with the guarantee (transactional/idempotent for exactly-once, post 6).
- Design by deliberately answering the series' questions for your problem: **event-time vs processing-time** (data lateness, watermark policy), **windows** (tumbling/sliding/session), **state** (and how it's bounded), **guarantee** (at-least-once+idempotency vs exactly-once), and **latency** needed — getting these right is most of building a correct pipeline.
- Operate it as a **forever-running stateful distributed service**: **state is the crux** (restorable checkpoints — *test recovery*; bounded, monitored state — unbounded growth is the classic failure; **savepoint** upgrades), **backpressure/lag** monitoring (a pipeline silently falling behind real time is a common damaging failure), real-data **watermark/lateness tuning**, and **reprocessing/schema evolution**; and **test the messy paths** (reordering, late data, crashes, state recovery), which is harder than batch testing.
- Much of why streaming is **harder than batch is operational**, not conceptual — the perpetual stateful distributed service carries substantial operational burden.
- **Use streaming only when latency genuinely justifies it** (fraud, monitoring, real-time analytics/reaction where value decays with delay); **prefer batch** (simpler, cheaper, more robust) when you can tolerate latency, and consider **micro-batch** for "fast enough" at lower complexity — reaching for streaming reflexively is a classic over-engineering mistake, so always ask "does this *need* real-time, or is it just interesting?" Done with that judgment, streaming lets software keep up with a real-time world.

## Further reading

- [Stream processing — building and operating real pipelines](https://en.wikipedia.org/wiki/Stream_processing)
- [Apache Kafka — the durable, replayable source for streaming pipelines](https://en.wikipedia.org/wiki/Apache_Kafka)
