# Why Event-Driven Architecture?

*Synchronous request/response quietly welds your services together until a change in one breaks three others; event-driven architecture breaks that weld by making the event — a fact that happened — the thing services share.*

Most systems start synchronous: service A calls service B, waits, gets an answer. It is simple and it works — until you have a dozen services, and A must know about B, C, and D, and a slow D drags down A, and adding E means changing everyone who should notify it. The coupling that felt free at the start becomes the thing that slows every change. Event-driven architecture (EDA) is the alternative, and Apache Kafka is the platform most teams reach for to build it. This series builds Kafka and EDA up concept by concept; this first post is about the *why* — the problem EDA solves and when it is worth the shift.

## The cost of synchronous coupling

Direct, synchronous calls create three kinds of coupling that compound as a system grows:

- **Temporal coupling.** The caller and callee must both be up *at the same time*. If B is down or slow, A's request fails or hangs. Failures and latency propagate along the call graph.
- **Address coupling.** A must know B exists and where to reach it. Every producer of information must know every consumer of it, so adding a new consumer means changing every producer that should feed it.
- **Logic coupling.** A ends up knowing *what B does with the data* — it calls "chargeCard" and "sendEmail" and "updateInventory" in sequence, orchestrating everyone else's job.

The result is a distributed monolith: services that are separate processes but cannot change independently. The classic symptom is that a single business action ("place an order") requires touching five services in lockstep, and no team can ship without coordinating with four others.

## The shift: share events, not calls

Event-driven architecture inverts the flow. Instead of A *telling* B what to do, A *announces what happened* — "OrderPlaced" — and any service that cares reacts. The event is a **fact**: an immutable statement that something occurred, in the past tense, owned by the service that produced it. A publishes the fact to a shared log; the payments service, the email service, and the inventory service each consume it and do their part, independently.

This single change dissolves the three couplings:

- **Temporal:** the event is durably stored, so a consumer that is down simply reads it when it comes back. The producer does not wait and does not fail because a consumer is slow.
- **Address:** the producer publishes to a topic and knows nothing about who consumes it. Adding a new consumer means subscribing to the topic — zero changes to the producer.
- **Logic:** the producer states a fact and stops. What each consumer does with it is the consumer's business, not the producer's.

"OrderPlaced" is published once; payments, email, and inventory each react. Tomorrow you add a fraud-check service — it subscribes, and nothing else changes. That is the promise of EDA: services that evolve independently because they share facts, not commands.

## Events are facts, not commands

A distinction worth fixing early, because it shapes good event design. A **command** tells a specific service to do something ("ChargeCard") — it is directed, it expects an outcome, and it re-introduces coupling. An **event** states that something happened ("OrderPlaced," "PaymentCaptured") — it is a broadcast fact, past tense, with no expectation about who listens or what they do. EDA is built on events. A producer that publishes "ChargeCard" as if it were an event is really just doing a disguised synchronous call and keeps the logic coupling. Name and think of events as facts — things that are *true*, that happened — and the decoupling follows.

## Why a log, not just a message queue

You could publish events to a traditional message queue, and many systems do. Kafka is different in a way that matters for EDA, and it is worth previewing: Kafka is a **distributed, durable, replayable log**, not a transient queue. In a classic queue, a message is consumed and gone. In Kafka, events are *retained* — appended to a log that multiple independent consumers read at their own pace, and can *re-read*. That unlocks capabilities a queue cannot: a new service can process the entire history of events to build its state, a buggy consumer can be fixed and replay from the past, and the log itself becomes a source of truth. The next post is entirely about this log abstraction; for now, know that "why Kafka" and "why the log" are the same answer.

## When EDA is worth it — and when it isn't

EDA is not free, and it is not always right. It adds real complexity: eventual consistency (consumers lag behind producers), harder debugging (flow is implicit across many reactors rather than an explicit call chain), and the operational weight of running a platform like Kafka. Reach for it when the benefits are real — many services that must evolve independently, workflows where one action fans out to many reactions, high-throughput data pipelines, or systems where an auditable log of everything that happened is itself valuable (fintech, especially).

Skip it when a simple synchronous call would do: two services with a tight, stable, request/response relationship do not need an event bus between them, and forcing one in adds latency and complexity for no decoupling benefit. The honest rule: EDA earns its cost when independent evolution, fan-out, or replayable history genuinely matter; otherwise a direct call is simpler and better.

## Where the series goes

From here we build the whole picture: the log abstraction (topics, partitions, offsets), producers (how events get written, with ordering and durability), consumers and consumer groups (how they read and scale), delivery semantics and exactly-once, schemas and event design, the core event-driven patterns (event sourcing, CQRS, outbox, saga), and running Kafka in production. By the end you will understand not just how Kafka works, but how to design systems around events.

## Key takeaways

- Synchronous request/response creates temporal, address, and logic coupling that compounds into a distributed monolith where services can't change independently.
- Event-driven architecture shares *events* (immutable past-tense facts) instead of *calls*: a producer announces what happened, and any consumer that cares reacts independently.
- This dissolves the three couplings — durable events remove temporal coupling, topic-based publish removes address coupling, and stating-a-fact removes logic coupling.
- Design events as facts ("OrderPlaced"), not disguised commands ("ChargeCard"); commands re-introduce the coupling EDA removes.
- Kafka is a durable, replayable *log* (not a transient queue), which lets new consumers process history and buggy ones replay; adopt EDA when independent evolution, fan-out, or replayable history matter — otherwise a direct call is simpler.

## Further reading

- [Apache Kafka — official documentation](https://kafka.apache.org/documentation/)
- [The Fintech Engineering Handbook series](/blog/series/the-fintech-engineering-handbook/)
- [System Design Fundamentals series](/blog/series/system-design-fundamentals/)
