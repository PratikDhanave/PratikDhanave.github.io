# What Stream Processing Is — Computing on Data in Motion

*Most software processes data at rest: you store it, then query it. Stream processing flips that — it computes on data in motion, as each event arrives, continuously and forever. This shift from "store then process" to "process as it flows" underpins fraud detection, real-time analytics, monitoring, and the event-driven systems that react to the world as it happens. This series builds stream processing from first principles, starting with why computing on data in motion is a fundamentally different model.*

This series complements the blog's [Event-Driven Architecture with Kafka](/blog/series/event-driven-architecture-with-kafka/) and data-engineering coverage with the *processing* side: not how events move, but how you compute over them continuously. Post 1 establishes the core mental shift — from bounded, stored data to unbounded, flowing data — and why it changes everything about how you compute.

## Batch vs stream: the fundamental divide

The classic way to process data is **batch processing**: collect a finite, bounded dataset (a day's transactions, a table), run a computation over all of it, produce a result, done. The data is *at rest* — complete and unchanging while you process it — and the job has a clear start and end.

**Stream processing** is the opposite: compute over an *unbounded, continuous* flow of data (**events**) as they arrive, with no end. The data is *in motion* — events keep coming, forever — so the computation is *continuous and long-running* rather than start-to-finish. You don't wait for "all the data" because there is no "all"; you process each event (or small groups) as it flows past and continuously update results.

This distinction drives everything:
- **Batch** answers "what happened?" over a complete past dataset, with high latency (you wait for the batch) but simplicity (the data is bounded and stable).
- **Stream** answers "what is happening *now*?" as events occur, with low latency (react immediately) but at the cost of grappling with unbounded, never-complete, out-of-order data.

The defining challenge of stream processing flows directly from *unboundedness*: because the data never ends and is never complete, you can't just "wait for all of it" — you must produce results *incrementally* and *continuously* over a flow that has no natural stopping point, while handling the messiness (late, out-of-order events) that real-time data brings. Everything hard about stream processing — windowing, time semantics, state, exactly-once — comes from this one fact: the data is infinite and in motion.

## Why process data in motion

Computing on data as it flows, rather than storing it and querying later, matters for a growing class of problems where *latency is the point*:

- **React in real time.** Fraud detection must flag a suspicious transaction *as it happens*, not in tomorrow's batch report — by then the money is gone. Any problem where the value of a response decays with time (fraud, security alerts, trading signals, operational incidents) needs stream processing, because batch's "process it later" is too late.
- **Continuous, up-to-date results.** Real-time dashboards, live metrics, and monitoring need results that reflect *now*, continuously updated as events arrive — not a snapshot from the last batch run.
- **React to events as they occur.** Event-driven systems (the [Kafka series](/blog/series/event-driven-architecture-with-kafka/)) trigger actions in response to events — update inventory when an order arrives, notify when a threshold is crossed — which is inherently stream processing: computing and acting per event.
- **Handle data that's naturally a stream.** Sensor readings, logs, clicks, transactions, and telemetry are *born* as continuous streams, so processing them as a stream (rather than artificially batching) is the natural fit, especially at high volume where waiting to batch adds unacceptable delay.

The driving force is that the world produces events continuously and increasingly demands *immediate* response, so the "store everything, query later" model — great for analyzing the past — can't serve the growing need to *act on the present*. Stream processing is how software keeps up with a world that happens in real time.

## The spectrum and where streaming fits

It's worth placing stream processing in context rather than as a rival to batch:

- **Batch and stream are a spectrum, not enemies.** Many systems use both — batch for heavy historical analysis and model training, streaming for real-time reaction — and the line blurs (micro-batching processes tiny batches frequently to approximate streaming; some engines unify both). The question isn't "batch or stream?" but "what latency does this problem need?"
- **Streaming is harder, so use it when latency justifies it.** Stream processing's unboundedness makes it genuinely harder than batch (the rest of this series is largely about that difficulty — time, windowing, state, fault tolerance), so it's not a free upgrade. When a problem tolerates latency (daily reports, periodic analytics), batch is simpler and fine; when a problem *needs* low latency (react now), streaming earns its complexity.
- **The modern reality: more things need real time.** As businesses demand real-time insight and reaction — live personalization, instant fraud blocking, operational monitoring, event-driven microservices — stream processing has moved from a specialized niche to core infrastructure, which is why understanding it matters even if your current work is batch.

The through-line to carry: stream processing is computing on **unbounded data in motion**, continuously, as events arrive — a fundamentally different model from batch's bounded, store-then-process approach, driven by the need to *act on the present* rather than analyze the past. Its difficulty all stems from unboundedness (no "all the data," never complete, out of order), and its value is low-latency reaction to a world that happens in real time. The rest of the series builds the concepts that tame the unbounded flow — events and time, windowing, state, and fault tolerance — and the systems that implement them.

The throughline: **batch processing** computes over a **bounded, at-rest** dataset start-to-finish (answers "what happened?", high latency, simple), while **stream processing** computes over an **unbounded, in-motion** flow of **events** continuously as they arrive (answers "what is happening now?", low latency). The divide drives everything, and stream processing's defining difficulty flows from **unboundedness** — no "all the data," never complete, events arrive late and out of order — so you must produce results **incrementally and continuously** over a flow with no stopping point. You process data in motion when **latency is the point** (fraud/security/trading/ops where a late response is worthless), for **continuous up-to-date results**, to **react to events** (event-driven systems), and for **naturally-streaming data** (sensors, logs, clicks). Batch and stream are a **spectrum** (use the latency a problem needs — streaming is harder, so reserve it for when low latency justifies the complexity), and streaming has become core infrastructure as the world increasingly demands real-time reaction.

## Key takeaways

- **Batch processing** computes over a **bounded, at-rest** (complete, unchanging) dataset start-to-finish — "what happened?", high latency, simple; **stream processing** computes over an **unbounded, in-motion** flow of **events** continuously as they arrive — "what is happening *now*?", low latency.
- Stream processing's defining difficulty comes from **unboundedness**: there's no "all the data," it's never complete, and events arrive late/out-of-order — so you must produce results **incrementally and continuously** over a flow with no natural stopping point (the source of windowing, time semantics, state, and exactly-once).
- Process data **in motion** when **latency is the point** — fraud, security, trading, operational alerts, where a response that comes "in tomorrow's batch" is worthless — plus **continuous up-to-date results** (live dashboards/metrics), **reacting to events** (event-driven systems, the Kafka series), and **naturally-streaming data** (sensors, logs, clicks, telemetry).
- The driver is a world that **produces events continuously and demands immediate response**, which the "store everything, query later" model can't serve — streaming is how software **acts on the present** rather than only analyzing the past.
- Batch and stream are a **spectrum, not rivals** (many systems use both; the question is "what latency does this need?"); streaming is **genuinely harder** (unboundedness), so reserve it for when low latency justifies the complexity — but it has become **core infrastructure** as real-time reaction becomes the norm.

## Further reading

- [Stream processing — computing on data in motion](https://en.wikipedia.org/wiki/Stream_processing)
- [Batch processing — the bounded, store-then-process model](https://en.wikipedia.org/wiki/Batch_processing)
