# Schemas and Event Design

*In an event-driven system your events are a public API that outlives every service that reads them, so how you shape them and how you evolve them without breaking consumers is not a detail — it is the contract the whole architecture rests on.*

Once events decouple your services, the events themselves become the most important contract in the system — more durable than any single service, read by consumers you haven't written yet. Getting their schema, their evolution, and their design right is what keeps a decoupled system from quietly re-coupling through broken payloads. This sixth post in the Event-Driven Architecture with Kafka series covers schemas, compatibility, and event design.

## Events are a contract, and contracts need schemas

To Kafka, a record's value is just bytes — it does not care what's inside. That freedom is a trap: without an agreed structure, every consumer guesses at the payload, and a producer changing a field silently breaks consumers it has never heard of. The fix is an explicit **schema** for each event type, enforced so producers and consumers share a definition. Because events in a durable log are read by many independent consumers over a long time, the schema is effectively a **published API** — and you evolve it with the same care you'd give a public API, not the casualness of an internal function signature.

## The schema registry

The common way to enforce and manage schemas is a **schema registry** — a service that stores the schema for each topic and assigns versions. Producers register (or validate against) the schema and write a small schema id alongside each record; consumers look up the schema by id to deserialize. This does three things: it *enforces* that produced records conform, it *versions* schemas so you can evolve them, and it keeps the payload compact (a schema id, not the whole schema, travels with each record). The registry is what turns "events are a contract" from an aspiration into something enforced at write time.

## Serialization formats

Three formats dominate, and the choice is a real trade-off:

- **Avro** — compact binary with a schema, designed for exactly this use; strong, well-defined schema evolution rules and tight registry integration. The traditional Kafka default.
- **Protobuf** — compact binary, schema-first, widely used, great cross-language tooling; also well-supported by registries.
- **JSON (with a schema)** — human-readable and universally easy, at the cost of size and weaker typing; workable with a JSON-Schema in the registry.

The rule of thumb: binary formats (Avro/Protobuf) for high-throughput, strongly-typed pipelines where size and evolution rigor matter; JSON when human-readability and simplicity outweigh efficiency. What matters more than the format is that there *is* a registered schema with enforced evolution — a schemaless topic is a future outage.

## Schema evolution and compatibility

The hard part isn't defining a schema once; it's changing it without breaking the consumers and producers that don't upgrade at the same time. In a decoupled system you cannot deploy everyone atomically, so schema changes must be **compatible**. Registries enforce compatibility modes:

- **Backward compatible** — new schema can read data written with the old schema. Lets you upgrade *consumers* first. (Typical safe changes: adding an optional field with a default, removing a field.)
- **Forward compatible** — old schema can read data written with the new schema. Lets you upgrade *producers* first. (Typical: adding a field, removing an optional one.)
- **Full compatible** — both directions.

The practical discipline: make only compatible changes, and let the registry *reject* an incompatible one at deploy time rather than discovering it when a consumer crashes in production. The changes that break compatibility — renaming a field, changing a type, adding a required field with no default — are exactly the ones to avoid or stage carefully (add-new-then-migrate-then-remove). Treating the schema as an evolvable contract, guarded by the registry, is what lets independent teams ship without a coordinated big-bang.

## Event design: what goes in an event

Beyond serialization, *what* you put in an event shapes how well the architecture works. A key design axis:

- **Event notification** — a thin event that says something happened with minimal data ("OrderPlaced: order_id=123"). Consumers that need details call back to the source. Small events, but re-introduces coupling (consumers must query the producer) and load.
- **Event-carried state transfer** — the event carries the state consumers need ("OrderPlaced" with the full order details). Consumers act without calling back, staying decoupled — at the cost of larger events and some duplicated data.

Event-carried state transfer is often preferred in EDA precisely because it preserves decoupling — a consumer doesn't need to call the producer, so the producer can be down and the consumer still works. The trade is event size and the discipline of including the right state. Choose deliberately: notification when payloads are heavy and consumers rarely need full detail; state transfer when decoupling and consumer autonomy matter (usually).

## Events versus commands, again

The events-are-facts distinction from the first post shows up in design here too. Model events as *things that happened* ("PaymentCaptured"), immutable and past tense, owned by the producer — not as *instructions* ("CapturePayment") aimed at a consumer. Fact-shaped events keep the producer ignorant of consumers (decoupled); command-shaped ones re-couple. And design each event to be **self-describing and self-contained** enough that a consumer can act on it without hidden context — which, combined with a registered, compatibly-evolving schema, is what makes your events a durable, trustworthy contract the whole system can build on.

## Key takeaways

- In EDA, events are a published API — durable, read by many future consumers — so they need explicit, enforced schemas, evolved with API-level care.
- A schema registry stores and versions each topic's schema, enforces conformance at write time, and keeps payloads compact (a schema id travels with the record).
- Choose serialization by trade-off — Avro/Protobuf (compact, strong evolution) for high-throughput typed pipelines, JSON for readability — but the non-negotiable is having a registered schema at all.
- Evolve schemas only in compatible ways (backward lets you upgrade consumers first, forward lets you upgrade producers first) and let the registry reject incompatible changes at deploy, not in production.
- Design events as self-contained past-tense facts; prefer event-carried state transfer (carry the state consumers need) over thin notifications to preserve decoupling and consumer autonomy.

## Further reading

- [Apache Kafka — official documentation](https://kafka.apache.org/documentation/)
- [The Fintech Engineering Handbook series](/blog/series/the-fintech-engineering-handbook/)
- [API Design series](/blog/series/api-design/)
