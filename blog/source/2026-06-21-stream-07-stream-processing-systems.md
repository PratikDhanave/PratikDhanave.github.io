# Stream Processing Systems — The Engines That Run It

*The concepts of stream processing — events, time, windows, state, fault tolerance — are realized by a handful of systems, and choosing among them is one of the main practical decisions in building a streaming pipeline. This post maps the landscape: the engines, the models they embody, and how to think about which fits a problem. It's the bridge from understanding stream processing to actually running it.*

Posts 2–6 built the concepts; this post covers the systems that implement them. You rarely build a stream processor from scratch (post 5's lesson — the state and fault-tolerance machinery is why frameworks exist), so the real engineering is choosing and using the right engine. Understanding the landscape and its tradeoffs is what lets you pick well.

## The landscape of stream processing systems

The systems cluster into a few categories, each embodying a different model:

- **Stream-processing frameworks (the heavyweights).** **Apache Flink** is the archetype: a true stream processor with first-class event-time, watermarks, windowing, sophisticated managed state, and exactly-once fault tolerance (posts 2–6). It's built for stateful, correctness-critical, large-scale streaming and embodies the full concept set of this series. **Apache Spark Structured Streaming** approaches streaming via *micro-batching* (processing tiny batches very frequently to approximate a stream) and, more recently, continuous processing — strong if you're already in the Spark ecosystem for batch. These are the engines for serious, stateful stream processing.
- **Kafka-native stream processing.** **Kafka Streams** is a *library* (not a separate cluster) for building stream processing directly on Kafka — you embed it in your application, and it does stateful stream processing (windows, joins, aggregations, exactly-once) over Kafka topics. **ksqlDB** puts a SQL interface on top. These shine when Kafka ([Kafka series](/blog/series/event-driven-architecture-with-kafka/)) is already your event backbone and you want processing without a separate heavyweight cluster — lightweight, tightly integrated, operationally simpler.
- **Cloud-managed streaming services.** The cloud providers offer managed streaming (Google Dataflow — which implements the influential *Apache Beam* model; AWS Kinesis Data Analytics; Azure Stream Analytics) that run streaming jobs without you managing the infrastructure. Attractive for avoiding operational burden, at the cost of some lock-in and less control.
- **The unifying model: Apache Beam.** Beam is a *programming model* (not an engine) that abstracts over event time, windowing, watermarks, and triggers — essentially the concept set of this series as an API — and runs on multiple engines (Flink, Dataflow, Spark). It codified the modern streaming model (the "Dataflow model" from Google's influential paper), so understanding Beam's concepts is understanding modern streaming regardless of engine.

The practical reality: for *serious stateful streaming*, Flink is the leading open-source engine; if *Kafka is your backbone* and you want lightweight processing, Kafka Streams fits; if you want *managed/no-ops*, a cloud service; and the *concepts* (Beam/Dataflow model) are common across all of them, so learning the concepts transfers between engines.

## How to choose

Choosing a stream processing system comes down to a few decisive questions, not a "best engine" ranking:

- **How much state and what correctness guarantee?** Heavy stateful processing with exactly-once (posts 5–6) points to Flink (or a managed service with strong guarantees). Simpler or stateless processing has more options, including lightweight Kafka Streams.
- **What's your existing ecosystem?** If Kafka is already your event backbone, **Kafka Streams/ksqlDB** integrate most naturally and avoid a separate system. If you're heavily invested in Spark for batch, **Spark Structured Streaming** reuses that. If you're on a cloud platform, its **managed service** may be simplest. The existing stack often dominates the decision, because operational and integration cost matters more than marginal engine features.
- **Build-vs-operate tradeoff.** Self-managed engines (Flink) give maximum control and capability but real operational burden (running a stateful distributed cluster is hard); managed services trade control for less ops. Match this to your team's capacity — a small team may prefer managed or Kafka-Streams-embedded-in-the-app over operating a Flink cluster.
- **Latency requirements.** True streaming (Flink, Kafka Streams) gives the lowest latency; micro-batching (Spark) has slightly higher latency but may be fine, and simpler if you're already batch-oriented. Match the engine's latency model to the problem's need (post 1's "what latency does this need?").

The meta-point: there's no universally best stream processor — the right choice depends on state/correctness needs, existing ecosystem, operational capacity, and latency requirements. The good news is that because the *concepts* (this series) are shared across engines, you can reason about any of them with the same mental model, and switching engines is more about operations than relearning streaming.

## Stream processing SQL and the trend toward accessibility

A significant trend worth knowing: **streaming SQL**. Tools like ksqlDB, Flink SQL, and Spark Structured Streaming let you express stream processing in *SQL* — "SELECT count(*) FROM transactions GROUP BY TUMBLE(...)" — rather than low-level code. This matters because:
- It makes stream processing *accessible* to analysts and engineers who know SQL but not stream-processing APIs, broadening who can build streaming pipelines.
- It expresses the concepts of this series (windows, aggregations, joins over streams) in a familiar declarative form — windowing becomes a `GROUP BY` over a window, etc.
- It's part of a broader convergence of batch and streaming (post 1): the same SQL increasingly runs over both bounded and unbounded data, blurring the line.

The direction of the field is toward *more accessible, more unified* stream processing — SQL interfaces, the common Beam/Dataflow model, managed services — lowering the barrier that once made streaming a specialist skill. For an engineer, this means the concepts (events, time, windows, state, fault tolerance) are the durable knowledge, while the *interface* (code vs SQL, this engine vs that) is increasingly a choice rather than a steep separate learning curve. Learn the concepts, and the systems become approachable.

The throughline: you rarely build a stream processor (the state/fault-tolerance machinery is why frameworks exist), so the real decision is **choosing an engine**. The landscape: **heavyweight frameworks** (**Flink** — the leading open-source true stream processor with full event-time/state/exactly-once; **Spark Structured Streaming** — micro-batch, good in the Spark ecosystem), **Kafka-native** (**Kafka Streams** — a library embedded in your app, lightweight, ideal when Kafka is your backbone; **ksqlDB** for SQL), **cloud-managed** services (Dataflow/Kinesis/Azure — no-ops, some lock-in), and the unifying **Apache Beam/Dataflow model** (the concept set as a portable API). Choose by **state/correctness needs** (heavy stateful + exactly-once → Flink), **existing ecosystem** (Kafka → Kafka Streams; Spark → Structured Streaming; cloud → managed — often the dominant factor), **build-vs-operate capacity**, and **latency**. **Streaming SQL** (ksqlDB, Flink SQL) and the common Beam model are making streaming **more accessible and unified** — so the **concepts** are the durable knowledge, and the interface/engine is increasingly a choice.

## Key takeaways

- You rarely build a stream processor from scratch (post 5 — the state/fault-tolerance machinery is why frameworks exist), so the practical engineering is **choosing and using an engine**.
- The landscape: **heavyweight frameworks** — **Apache Flink** (the leading open-source *true* stream processor: first-class event-time, watermarks, windowing, managed state, exactly-once — the full concept set) and **Spark Structured Streaming** (**micro-batch** approximating streaming, strong in the Spark ecosystem); **Kafka-native** — **Kafka Streams** (a *library* embedded in your app, lightweight, ideal when Kafka is your backbone) and **ksqlDB** (SQL on top); **cloud-managed** services (Google Dataflow, AWS Kinesis, Azure Stream Analytics — no-ops, some lock-in); and the unifying **Apache Beam / Dataflow model** (the concepts as a portable API across engines).
- Choose by decisive questions, not a "best engine": **state + correctness needs** (heavy stateful with exactly-once → Flink or strong managed service), **existing ecosystem** (Kafka → Kafka Streams; Spark → Structured Streaming; cloud → its managed service — often the dominant factor), **build-vs-operate capacity** (Flink = max control + real ops burden; managed = less control, less ops), and **latency** (true streaming lowest; micro-batch slightly higher but simpler if already batch).
- There's **no universally best** stream processor — but the **concepts are shared across engines** (Beam/Dataflow model), so the same mental model reasons about any of them and switching is mostly operational, not relearning.
- **Streaming SQL** (ksqlDB, Flink SQL, Spark) expresses windows/aggregations/joins declaratively, making streaming **accessible** to SQL users and advancing the **batch-streaming convergence** — so the **concepts** (events, time, windows, state, fault tolerance) are the durable knowledge while the interface/engine is increasingly a choice, not a steep separate skill.

## Further reading

- [Apache Flink — the leading open-source stream processor](https://en.wikipedia.org/wiki/Apache_Flink)
- [Apache Kafka — the event backbone and Kafka Streams](https://en.wikipedia.org/wiki/Apache_Kafka)
