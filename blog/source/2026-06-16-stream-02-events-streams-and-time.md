# Events, Streams, and Time — The Core Model

*Stream processing has a small, elegant core model: everything is an event, events form streams, and time is a first-class concern. Getting these three ideas precise — especially the subtle and crucial distinction between when an event happened and when you process it — is what makes the rest of stream processing (windowing, state, correctness) comprehensible. This post builds the core vocabulary that everything else depends on.*

Post 1 established that stream processing computes on unbounded data in motion. This post makes "data in motion" precise: what an event is, what a stream is, and why *time* is the hardest and most important concept in the whole field. The time distinction introduced here is the single idea that trips up newcomers most and unlocks everything once understood.

## Events and streams

The atom of stream processing is the **event**: a record of something that happened, at a point in time. A transaction, a click, a sensor reading, a log line, an order — each is an event, typically a small immutable record carrying *what happened*, *when*, and relevant data. Events are **immutable** (they record a fact that occurred; you don't change the past) and **timestamped** (they happened at a time, which matters enormously, below).

A **stream** is an unbounded, ordered (or partially-ordered) sequence of events — the continuous flow of post 1. Conceptually it's an append-only log of events arriving over time, with no end. This maps directly onto the [event-driven / Kafka](/blog/series/event-driven-architecture-with-kafka/) world: a Kafka topic *is* a stream of events, and stream processing is computing over such streams.

The programming model built on this is a **dataflow**: a stream-processing job is a graph of operations (transform, filter, aggregate, join) that events flow *through*. Each event enters, passes through the operations, and produces output — continuously, for every event, forever. This dataflow-of-events model is the shape of every stream processor: you define *what to do to each event and how to combine them*, and the engine runs it continuously over the unbounded stream. Simple operations (map, filter) act on one event at a time; the interesting ones (aggregations, joins, windows) combine *many* events, which is where time and state come in.

## The crucial distinction: event time vs processing time

Here is the single most important and most subtle concept in stream processing: an event has *two* different times, and conflating them causes most stream-processing bugs.

- **Event time** — when the event *actually happened* in the real world, recorded in the event itself (the timestamp on the transaction, the moment the sensor read). This is the *true* time of the event.
- **Processing time** — when your stream processor *actually handles* the event, i.e. the wall-clock time at the moment of computation.

These differ, often significantly, because events take time to travel (network delays), can be buffered, batched, or delayed, and arrive **out of order** and **late**. A transaction that *happened* at 12:00:00 (event time) might reach your processor at 12:00:05 (processing time), after a transaction that happened at 12:00:02 — so the order you *receive* events is not the order they *occurred*. A mobile device offline for an hour sends its events when it reconnects, arriving an hour "late" in processing time though their event time is an hour ago.

Why this matters so much: **the correct answer almost always depends on event time, not processing time.** "How many transactions happened between 12:00 and 12:01?" is a question about *event time* (when they happened), and answering it by processing time (when you saw them) gives the wrong answer whenever events are delayed or out of order — which, on a real stream, is always. If you count "transactions I processed between 12:00 and 12:01," you'll miss the late ones and miscount the out-of-order ones. Correct stream processing requires reasoning in *event time*, which is hard precisely because events don't arrive in event-time order. This single distinction is the root of why windowing and watermarks (posts 3–4) exist: they're the machinery for computing correct event-time results from an out-of-order, processing-time-ordered stream.

## Why time makes streaming hard

The event-time/processing-time gap is what makes stream processing fundamentally harder than batch, and it's worth seeing why clearly:

- **In batch, time is easy.** You have all the data at once, so you can sort by event time, group into time buckets, and compute — the data is complete and you can look at any time range fully. Out-of-order-ness doesn't matter because you have everything before you start.
- **In streaming, time is the central problem.** You *don't* have all the data — more events (possibly with past event times) keep arriving — so you can never be sure you've seen *all* the events for a given event-time range. When computing "transactions between 12:00 and 12:01," when are you *done*? A late event with event time 12:00:30 might arrive at processing time 12:05. Do you wait? How long? This is the unboundedness of post 1 made concrete in the time dimension: you must produce results for event-time windows *without ever being certain the window is complete*.

This creates the core tension streaming must resolve: **completeness vs latency.** Wait longer for late events → more complete/correct results but higher latency; emit sooner → lower latency but risk missing late events. There's no free lunch, and the mechanisms of the next posts — **watermarks** (post 3, a way to estimate "event time has probably progressed past here, so late events are unlikely") and **windowing** (post 4, bounding the unbounded stream into finite chunks to compute over) — are precisely how stream processing manages this tension in a principled way. Understanding that time is the hard part, and *why* (event time ≠ processing time, and you never know if you've seen everything), is understanding the heart of stream processing.

The throughline: stream processing's core model is small — an **event** is an immutable, timestamped record of something that happened; a **stream** is an unbounded ordered sequence of events (a Kafka topic *is* a stream); and a job is a **dataflow** graph of operations events flow through continuously. The crucial, most-misunderstood concept is that every event has **two times**: **event time** (when it actually happened, in the event) and **processing time** (when your processor handles it) — and they differ because events travel, buffer, and arrive **late and out of order**. Correct answers almost always depend on **event time**, which is hard precisely because events *don't* arrive in event-time order — the root of why windowing and watermarks exist. This makes **time the central problem** of streaming (trivial in batch, where you have all the data): you must compute event-time results **without ever knowing a time range is complete**, creating the core **completeness-vs-latency** tension that the rest of the field's machinery resolves.

## Key takeaways

- The core model: an **event** is an **immutable, timestamped** record of something that happened; a **stream** is an **unbounded, ordered sequence** of events (append-only log — a Kafka topic *is* a stream); a job is a **dataflow** graph of operations (map/filter/aggregate/join) that events flow through continuously, forever.
- Every event has **two times**, and conflating them causes most stream bugs: **event time** (when it *actually happened*, recorded in the event — the true time) vs **processing time** (when your processor *handles* it — wall clock).
- They differ, often a lot, because events travel (network delay), buffer, and arrive **out of order and late** (an offline phone sends an hour's events at reconnect) — so the order you *receive* events ≠ the order they *occurred*.
- **Correct answers almost always depend on event time, not processing time** ("how many transactions happened 12:00–12:01?" is about *when they happened*), and answering by processing time miscounts whenever events are delayed/reordered — which on a real stream is always; this is the root of windowing and watermarks (posts 3–4).
- **Time is the central problem** of streaming (trivial in batch where you have all the data): you can never be sure you've seen *all* events for an event-time range, so you compute results **without knowing the range is complete**, creating the core **completeness-vs-latency** tension — wait longer (more correct, higher latency) vs emit sooner (lower latency, risk missing late events) — that watermarks and windowing resolve.

## Further reading

- [Event (computing) — the atom of a stream](https://en.wikipedia.org/wiki/Event_(computing))
- [Stream processing — the dataflow model over events](https://en.wikipedia.org/wiki/Stream_processing)
