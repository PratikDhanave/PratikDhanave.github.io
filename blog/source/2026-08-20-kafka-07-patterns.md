# Event-Driven Patterns

*Kafka gives you a durable log; these patterns are what you build on it — event sourcing, CQRS, the outbox, sagas, and the choice between choreography and orchestration — the vocabulary of real event-driven systems.*

The mechanics — log, producers, consumers, delivery, schemas — are the foundation. This post is about what you *build* on them: the recurring patterns that turn a Kafka cluster into an event-driven architecture. This seventh post in the Event-Driven Architecture with Kafka series is a tour of the patterns you'll actually design with, several of which connect directly to the fintech systems covered elsewhere on this blog.

## Event sourcing

**Event sourcing** stores state as the full sequence of events that produced it, rather than just the current snapshot. Instead of a `balance` column you overwrite, you append `Deposited`, `Withdrawn`, `Deposited` — and the balance is *derived* by folding those events. Kafka's durable, ordered, replayable log is a natural fit: the events *are* the source of truth, and current state is a projection you can rebuild by replaying from offset 0.

The payoff is enormous for systems that need auditability and time-travel — you have a complete, immutable history of everything that happened, you can reconstruct state at any past point, and you can build entirely new views by replaying history through new logic. The cost is complexity: you think in events and projections rather than rows, and querying "current state" means maintaining a materialized view. It shines where the history itself is valuable (ledgers, audit-critical domains) — which is exactly why the [Fintech Engineering Handbook](/blog/series/the-fintech-engineering-handbook/) treats it as a pillar.

## CQRS

**Command Query Responsibility Segregation** separates the write model from the read model. Commands change state (often producing events); queries read from separate, purpose-built read models optimized for how they're queried. It pairs naturally with event sourcing and Kafka: writes append events to the log, and consumers project those events into one or more read models (a search index, a cache, a denormalized table) each shaped for its queries.

The value is that reads and writes can scale and be modeled independently — a write model tuned for correctness and a read model tuned for fast queries, kept in sync by the event stream. The cost is eventual consistency (the read model lags the write by the projection delay) and more moving parts. Use CQRS when read and write needs genuinely diverge; don't impose it on simple CRUD where one model serves both.

## The outbox pattern

A recurring correctness problem: a service must *both* update its database *and* publish an event, and doing them as two separate operations means one can succeed while the other fails — a lost event or a phantom one. The **outbox pattern** solves it. The service writes the event to an `outbox` table *in the same database transaction* as the business change, so they commit atomically. A separate relay (often via change-data-capture) then reads the outbox and publishes to Kafka.

This guarantees the event is durable the moment the business change commits — you can no longer lose it. The relay may publish a row twice if it crashes after publishing but before marking it sent, so the outbox is **at-least-once**, which is why consumers must be idempotent (the delivery post's theme). The outbox is the standard bridge between a database transaction and the event log, and it's covered hands-on in the fintech handbook.

## Sagas: distributed workflows without distributed transactions

A business process often spans services — place order → reserve inventory → charge payment → arrange shipping — and you cannot wrap that in one ACID transaction across services. A **saga** models it as a sequence of local transactions, each publishing an event that triggers the next, with **compensating actions** to undo prior steps if a later one fails (if payment fails, *release* the reserved inventory). Kafka carries the events that drive the saga forward and the compensation events that unwind it.

Sagas trade the simplicity of a single transaction for the reality that distributed transactions don't scale — you get eventual consistency and must design explicit compensations for every step, but you get a workflow that survives partial failure across services. They come in two flavors, which is the next distinction.

## Choreography versus orchestration

How do the steps of a multi-service workflow coordinate? Two styles:

- **Choreography** — no central coordinator; each service reacts to events and emits its own, and the workflow *emerges* from those reactions. Maximally decoupled and Kafka-native, but the overall flow is implicit — no single place shows the whole process, which makes it harder to understand and debug as it grows.
- **Orchestration** — a central orchestrator explicitly directs the steps ("now reserve inventory, now charge"), usually still communicating via events. The flow is explicit and easy to reason about and monitor, at the cost of a coordinator that knows about the participants (a little re-coupling).

Neither is universally right. Choreography suits simple, stable flows where decoupling is paramount; orchestration suits complex, evolving workflows where visibility and control matter more than maximal decoupling. Many mature systems use both — choreography for loose fan-out reactions, orchestration for the critical multi-step business processes that need to be understood and audited.

## Stream processing, briefly

Beyond point consumers, Kafka is a substrate for **stream processing** — continuously transforming, aggregating, joining, and windowing event streams (via Kafka Streams or a processor like Flink). This is where events become real-time analytics, enrichment, and derived streams: counting events per minute, joining orders with customers, detecting patterns as they happen. It's a large topic of its own, but the connection to know is that the same log that decouples your services is also a live dataset you can compute over continuously — the patterns above plus stream processing are what a full event-driven platform is made of.

## Key takeaways

- Event sourcing stores state as the replayable sequence of events (deriving current state by folding them) — a natural fit for Kafka's log, ideal where auditable history matters (ledgers, fintech).
- CQRS separates the write model from purpose-built read models kept in sync by the event stream — independent scaling/modeling at the cost of eventual consistency; use it when reads and writes genuinely diverge.
- The outbox pattern writes the event to an outbox table in the same DB transaction as the business change, then relays it to Kafka — guaranteeing durability (at-least-once, so consumers must be idempotent).
- Sagas model cross-service workflows as local transactions plus compensating actions, trading single-transaction simplicity for failure-survivable eventual consistency.
- Choreography (emergent, maximally decoupled, implicit flow) vs orchestration (central coordinator, explicit and auditable flow) — choose per workflow, often both; and the log doubles as a live dataset for stream processing.

## Further reading

- [The Fintech Engineering Handbook series](/blog/series/the-fintech-engineering-handbook/)
- [System Design Fundamentals series](/blog/series/system-design-fundamentals/)
- [Apache Kafka — official documentation](https://kafka.apache.org/documentation/)
