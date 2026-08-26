# Batch vs Streaming

*How fresh does the data need to be? That one question splits data engineering into two paradigms. Batch processing handles data in large chunks on a schedule — simpler, cheaper, and fine when yesterday's data is good enough. Stream processing handles data continuously as it arrives — more complex and costly, but necessary when you need to know now. Choosing between them (and knowing when each fits) is one of the most consequential architectural decisions in a data platform, and it's driven by real requirements, not by which sounds more impressive.*

Data can be processed in two fundamental paradigms: **batch** (in scheduled chunks) and **streaming** (continuously as it arrives). This post covers both, the key tradeoffs (latency vs complexity/cost), when to use each, and representative tools (Spark for batch, Kafka/streaming for streams). It builds on pipelines (batch and streaming are two pipeline styles) and is a core architectural distinction in data engineering. The choice hinges on how fresh the data needs to be.

## Batch processing

**Batch processing** processes data in large *chunks* on a *schedule* — accumulating data and processing it periodically. It's the traditional, simpler paradigm:

- **Process accumulated data periodically.** Batch collects data over a period, then processes it *all at once* on a schedule (e.g. every night, every hour). Data accumulates, then a batch job runs — extracting, transforming, loading a chunk of data — then waits until the next scheduled run. It processes bounded chunks at intervals, not continuously.
- **Simpler and cheaper.** Batch is *simpler* to build and reason about (process a fixed chunk, on a schedule, with clear start/end) and often *cheaper* (run periodically, use resources in bursts, no continuous infrastructure). Its simplicity and cost-efficiency make it the default for much data engineering — most data work doesn't need continuous processing, so batch suffices. Batch is the workhorse.
- **The cost: latency.** Batch's downside is *latency/freshness* — data is only as fresh as the last batch run. If you process nightly, the data is up to a day old; the results reflect data as of the last batch, not the current moment. For many uses (daily reports, periodic analytics) this is fine; for uses needing *current* data, batch's latency is a problem. Batch trades freshness for simplicity. The data lags by the batch interval.
- **Spark: a batch workhorse.** *Apache Spark* is a widely-used engine for large-scale batch (and more) processing — distributing computation across a cluster to process big data efficiently. It exemplifies batch tooling: process large volumes of accumulated data with distributed compute. (Spark also does streaming, but it's rooted in large-scale batch/distributed processing.) Spark handles the "process lots of data in a batch job" need at scale.

Batch processing handles data in scheduled chunks — simpler, cheaper, and the default for most data work — at the cost of latency (data is only as fresh as the last batch run). It fits uses where periodic freshness suffices (most analytics/reporting), with tools like Spark for large-scale batch. When you need fresher data, you turn to streaming.

## Stream processing

**Stream processing** processes data *continuously as it arrives* — handling each event/record in near real-time rather than accumulating chunks. It's the paradigm for low latency:

- **Process data continuously, event by event.** Streaming processes data *as it arrives* — a continuous flow of events/records processed in near real-time (or as they come), rather than accumulated and processed in scheduled batches. Data flows in and is processed immediately/continuously, keeping results *current*. It's continuous, unbounded processing.
- **Low latency / fresh data.** Streaming's key benefit is *low latency* — data is processed and available *nearly as soon as it's produced*, so results reflect the *current* state, not a stale batch. When you need *fresh, up-to-the-moment* data (real-time dashboards, immediate reactions to events, fraud detection, live monitoring), streaming provides it. Freshness is streaming's reason for being. It answers "what's happening *now*?"
- **The cost: complexity.** Streaming is *more complex* than batch — handling a continuous flow (unbounded data), managing state over time, dealing with out-of-order or late data, ensuring correctness in a never-ending process, and running continuous infrastructure. This complexity (and often higher cost of always-on processing) is streaming's downside. Streaming trades simplicity for freshness — the inverse of batch. Continuous processing is genuinely harder.
- **Kafka and streaming systems.** *Apache Kafka* is a widely-used system for *streaming data* — a distributed platform for publishing, storing, and consuming continuous streams of events (a durable, scalable "log" of events that producers write and consumers read). Kafka (and stream-processing engines built around such event streams) is foundational to streaming architectures — the backbone for moving and processing continuous event data. It exemplifies the streaming infrastructure that handles continuous flows.

Stream processing handles data continuously as it arrives, giving low latency / fresh data (results reflect the current moment) — necessary for real-time needs — at the cost of greater complexity (continuous unbounded processing, state, out-of-order data) and often cost, with systems like Kafka underpinning streaming. Batch and streaming are opposite tradeoffs, and choosing between them is the key decision.

## Choosing: latency vs complexity

The choice between batch and streaming is fundamentally a tradeoff of **latency (freshness) vs complexity (and cost)** — driven by real requirements:

- **The core tradeoff.** Batch = simpler and cheaper, but higher latency (staler data); streaming = fresher data (low latency), but more complex and often costlier. It's freshness vs simplicity/cost. Neither is universally better — they're different points on the tradeoff, suited to different needs. The right choice depends on *how fresh the data must be* versus *how much complexity/cost you'll accept*.
- **Let the freshness requirement decide.** The key question: *how fresh does the data need to be for its use?* If periodic freshness suffices (daily/hourly reports, most analytics), *batch* is the right, simpler, cheaper choice. If the use genuinely needs *current, real-time* data (live dashboards, immediate event reactions, fraud detection, monitoring), *streaming* is warranted despite its complexity. Match the paradigm to the actual freshness requirement — don't over-engineer with streaming when batch suffices, nor under-serve a real-time need with batch.
- **Don't reach for streaming by default.** A common mistake is choosing streaming because it sounds more advanced/impressive, when batch would suffice — adding needless complexity and cost. Most data needs *don't* require real-time; batch is the right default unless there's a genuine freshness requirement. Use streaming when the real-time need is real, not by default. (This echoes the "use the simplest thing that works" theme across the blog's engineering series.) Simpler batch is often the right call.
- **Hybrid and convergence.** Real platforms often use *both* — batch for most processing, streaming for the parts needing freshness. And modern tools increasingly *unify* batch and streaming (handling both in one framework), blurring the line. But the *decision* — what needs real-time vs periodic — remains, and it's driven by requirements. You often mix paradigms per use case.

Choosing between batch and streaming is a latency-vs-complexity/cost tradeoff driven by *how fresh the data needs to be*: batch (simpler, cheaper, higher latency) for periodic-freshness needs (most cases — the right default), streaming (fresher, more complex/costly) for genuine real-time needs — matched to requirements, not chosen by which sounds more impressive. Next: the modern data stack — the tools and architecture tying it all together.

## Key takeaways

- Batch processing handles data in scheduled chunks (accumulate, then process periodically — nightly/hourly) — simpler to build and reason about, often cheaper (bursty resource use), and the default for most data work — at the cost of latency (data is only as fresh as the last batch run); Apache Spark is a workhorse for large-scale distributed batch.
- Stream processing handles data continuously as it arrives (each event in near real-time) — giving low latency / fresh data reflecting the current moment (for real-time dashboards, fraud detection, live monitoring) — at the cost of greater complexity (continuous unbounded processing, managing state, out-of-order/late data) and often cost; Apache Kafka underpins streaming as a distributed event-stream platform.
- The choice is fundamentally latency (freshness) vs complexity (and cost): batch is simpler/cheaper but staler, streaming is fresher but more complex/costly — neither universally better, just different points on the tradeoff.
- Let the *freshness requirement* decide: if periodic freshness suffices (most analytics/reporting), use batch (simpler, cheaper); if the use genuinely needs current real-time data, use streaming despite its complexity — match the paradigm to the actual need.
- Don't reach for streaming by default because it sounds advanced — most needs don't require real-time, so batch is the right default unless there's a genuine freshness requirement (the "simplest thing that works" theme) — and real platforms often use both (batch for most, streaming where fresh), with modern tools increasingly unifying the two.

## Further reading

- [Apache Spark (Wikipedia)](https://en.wikipedia.org/wiki/Apache_Spark)
- [Apache Kafka (Wikipedia)](https://en.wikipedia.org/wiki/Apache_Kafka)
- [Data modeling for analytics (previous post)](/blog/posts/de-04-data-modeling.html)
