# Delivery Semantics and Exactly-Once

*"Exactly-once" is the most misunderstood phrase in streaming — it is real in Kafka, but only within a specific boundary, and outside that boundary the honest and usually-correct answer is at-least-once plus idempotent consumers.*

Every distributed messaging system has to answer: if things fail and retry, is a message delivered at most once, at least once, or exactly once? Kafka supports all three, and knowing which you have — and where Kafka's exactly-once guarantee actually holds — is the difference between a correct event system and one that silently drops or double-processes events. This fifth post in the Event-Driven Architecture with Kafka series covers delivery semantics and exactly-once done right.

## The three semantics

- **At-most-once** — each event is delivered zero or one times. No duplicates, but events can be *lost*. You get this by committing offsets *before* processing (or `acks=0` producing): if you crash mid-process, the record is already marked done and never reprocessed. Rarely what you want, because losing events is usually worse than repeating them.
- **At-least-once** — each event is delivered one or more times. No loss, but *duplicates* are possible. You get this by committing *after* processing: a crash before commit means reprocessing on restart. This is the workhorse default, and it demands that processing tolerate duplicates.
- **Exactly-once** — each event affects the outcome once and only once: no loss, no duplicates. The strongest and the hardest, and the one most often claimed loosely.

The framing that keeps you honest: the real choice for most systems is between losing data and duplicating it, and duplicating is almost always the better failure — *if* your consumers can tolerate duplicates. Which is why the most practical path to correctness is usually at-least-once plus idempotency, not chasing exactly-once everywhere.

## At-least-once plus idempotent consumers

Because at-least-once can deliver a record twice, a correct consumer must make reprocessing *safe* — processing the same event twice must have the same effect as processing it once. That is **idempotent processing**, and it is the most important consumer discipline in event systems. Techniques:

- **Idempotency keys / dedup.** Track processed event ids (from the record key or an id in the payload) and skip ones you've already handled — the same idempotency-key pattern that protects payment APIs, applied to event consumption.
- **Naturally idempotent operations.** "Set balance to X" is idempotent; "add X to balance" is not. Where you can, express effects as idempotent upserts rather than increments.
- **Conditional writes.** Use the event's offset or a version to make the write a no-op if already applied.

Get idempotency right and at-least-once *becomes* effectively exactly-once from the outside — the event may be delivered twice, but it only takes effect once. For a great many systems, this is the pragmatic exactly-once, and it's simpler and more robust than the transactional machinery below.

## Kafka's exactly-once: what it actually covers

Kafka does provide genuine **exactly-once semantics (EOS)**, but for a specific shape: the **read-process-write** pipeline, where a Kafka consumer reads from a topic, processes, and produces results back to Kafka. Two mechanisms combine:

- **The idempotent producer** (from the producers post) — ensures a record is written exactly once into a partition even across retries.
- **Transactions** — let a producer write to multiple partitions/topics *and* commit the consumer's offsets **atomically**, as one unit. Either the output records and the consumed-offset commit all succeed, or none do.

Together these make read-process-write atomic: the input is marked consumed *and* the outputs are produced as a single transaction, so a failure can't leave you having produced outputs without recording the input as done (duplicate) or recording it done without producing (loss). Consumers reading the output use `read_committed` isolation so they never see records from an aborted transaction. This is real exactly-once — within Kafka.

## The boundary that everyone forgets

Here is the caveat that separates people who understand EOS from people who quote it: **Kafka's exactly-once holds for Kafka-to-Kafka processing, not for effects on the outside world.** The moment your consumer's "process" step does something external — charges a card, sends an email, writes to a non-Kafka database — Kafka's transaction cannot cover that external effect. A transaction can atomically commit offsets and Kafka outputs, but it cannot un-send an email or roll back a third-party charge.

So for any consumer with external side effects, you are back to at-least-once plus idempotency: make the external effect idempotent (idempotency key on the charge, dedup on the email), because Kafka's EOS stops at Kafka's boundary. Claiming "exactly-once" for a pipeline that touches external systems is the classic mistake. The honest statement: exactly-once *within* Kafka via transactions; effectively-once *across* external systems via idempotent effects.

## Choosing your semantics

The practical decision tree: if losing an event is acceptable and you want max speed, at-most-once (rare). If you need no loss and your effects are external, at-least-once with idempotent consumers — the common, correct choice. If your pipeline is Kafka-to-Kafka stream processing and you need no duplicates in the output, turn on transactions for true exactly-once. And in all cases, build consumers to tolerate duplicates anyway, because it costs little and is your safety net when a guarantee's boundary turns out to be narrower than you thought. Delivery semantics are not a setting you flip once; they're a property you design for, mostly by making processing idempotent.

## Key takeaways

- Three semantics: at-most-once (no duplicates, can lose — commit before processing), at-least-once (no loss, can duplicate — commit after), and exactly-once (neither); duplicating usually beats losing, so at-least-once is the default.
- At-least-once requires *idempotent processing* — dedup by event id, prefer idempotent upserts over increments, use conditional writes — which makes at-least-once effectively exactly-once from the outside.
- Kafka's true exactly-once (EOS) covers read-process-write *within Kafka*, via the idempotent producer plus transactions that atomically commit outputs and consumed offsets (readers use `read_committed`).
- The forgotten boundary: EOS does not extend to external side effects (charges, emails, non-Kafka DBs) — for those, use at-least-once plus idempotent effects, because the transaction stops at Kafka's edge.
- Design semantics deliberately (at-most/at-least/exactly-once by case), and build consumers to tolerate duplicates regardless — it's cheap insurance against a guarantee's narrower-than-expected boundary.

## Further reading

- [Apache Kafka — official documentation](https://kafka.apache.org/documentation/)
- [Kafka design (delivery semantics) — Apache Kafka docs](https://kafka.apache.org/documentation/#semantics)
- [The Fintech Engineering Handbook series](/blog/series/the-fintech-engineering-handbook/)
