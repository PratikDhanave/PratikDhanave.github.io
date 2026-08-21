# The Log: Kafka's Core Abstraction

*Almost everything Kafka does follows from one deceptively simple idea — an append-only, ordered, durable log — and once that clicks, topics, partitions, and offsets stop being jargon and become obvious.*

Kafka can look like a pile of concepts: brokers, topics, partitions, offsets, consumer groups, replication. But they all sit on top of one primitive, and if you understand that primitive the rest follows. The primitive is the **log** — an append-only, totally-ordered sequence of records. This second post in the Event-Driven Architecture with Kafka series is about the log and its structure, because everything else in Kafka is a consequence of it.

## What "the log" means

Forget message queues for a moment. A log here is the same thing a database's write-ahead log is: an ordered, append-only file. You can only add records to the end, each record gets a sequential position, and records are never modified once written. Readers read from a position forward. That is it — and its power is precisely its simplicity. Because the log is append-only and ordered, it gives you a durable, replayable, totally-ordered record of what happened, which is exactly the "share facts" substrate event-driven architecture needs.

The crucial break from a queue: in a queue, reading a message removes it. In a log, reading does *not* consume — the record stays, and each reader independently tracks how far it has read. Many consumers can read the same log at their own pace, and any of them can go back and re-read. This one property is why Kafka enables things a queue cannot.

## Topics: named streams of events

A **topic** is a named log — a category of events, like `orders` or `payments`. Producers append events to a topic; consumers read from it. Topics are the unit of organization: you publish "OrderPlaced" events to the `orders` topic, and anything interested in orders subscribes to it. Conceptually a topic is one logical log, but for scale it is split into partitions.

## Partitions: the log, scaled

A single append-only log has a ceiling: one machine's throughput, one writer at the tail. Kafka breaks that ceiling by splitting a topic into **partitions** — each partition is an independent log, and the topic is the set of them. This is the single most important structural idea in Kafka, so it's worth being precise about what it buys and what it costs:

- **Parallelism.** Partitions can live on different brokers and be written and read in parallel. A topic's throughput scales with its partition count. Consumers, too, parallelize across partitions (the next post's subject).
- **Ordering is per-partition, not per-topic.** This is the trade-off people miss. Records within a *partition* are strictly ordered; records across *different* partitions have no guaranteed order. So Kafka gives you ordering exactly where you scope it to — within a partition — and not globally across a topic.

That ordering rule shapes design: if two events must be processed in order (say, all events for one account), they must go to the *same* partition. How you control that is the producer's job (via the record key), covered in the next post — but the reason it matters is rooted here, in the per-partition ordering guarantee.

## Offsets: a reader's position

Every record in a partition has an **offset** — its sequential position, 0, 1, 2, and so on. The offset is how everything is addressed. A consumer's entire state is, essentially, "which offset am I at in each partition." Reading is "give me records from offset N forward"; committing progress is "I've processed up to offset N."

Two consequences make offsets powerful. First, because the consumer owns its offset (rather than the broker deleting on read), consumers are independent — a slow one doesn't affect a fast one, and each can be at a different place in the same partition. Second, because records persist, a consumer can *reset* its offset — jump back to reprocess history, or forward to skip. Replay, the capability that distinguishes Kafka, is just "set the offset backward and read again." A new service can start at offset 0 and consume the entire history to build its state; a fixed-and-redeployed consumer can rewind past the bug and reprocess.

## Retention: how long facts live

Because a log is not emptied by reading, Kafka has to decide how long to keep records. **Retention** is that policy — by time (keep 7 days), by size (keep 100 GB per partition), or, with **log compaction**, keep at least the latest record for each key indefinitely. Retention is what makes the log a durable source of truth rather than a transient buffer: set it long (or compact by key), and the log becomes a replayable history of your events; set it short, and Kafka behaves more like a fast buffer. Compaction in particular is powerful for event-carried state — a `customers` topic compacted by customer id keeps the latest state of every customer forever in the log itself.

## Why this abstraction is so general

Step back and notice what the log unifies. A message queue, a database's replication stream, an event bus, an audit trail, a stream-processing input — all of them are, underneath, "an ordered sequence of records that consumers read forward." Kafka picks that one abstraction and makes it distributed, durable, and replayable, and in doing so becomes usable as all of those things at once. That generality is why Kafka ended up at the center of so many architectures: it is not a queue with extra features, it is the log abstraction done well, and the log turns out to be the right shape for event-driven systems. Every remaining post in this series is a consequence of what you now know: producers append to partitioned logs, consumers read forward by offset, and ordering, replay, and durability all flow from the log.

## Key takeaways

- Kafka's one primitive is the log: an append-only, ordered, durable sequence of records that readers read forward — and reading does *not* consume, so many consumers read the same log independently and can re-read.
- A topic is a named log (a category of events); it is split into partitions, each an independent log, which is how a topic scales throughput across brokers.
- Ordering is guaranteed *within* a partition, not across a topic — so events that must stay ordered (e.g. per account) must share a partition.
- An offset is a record's position in a partition; a consumer's state is its offsets, which makes consumers independent and makes replay simply "reset the offset and read again."
- Retention (by time/size, or key-based compaction) decides how long facts live, turning the log into a durable, replayable source of truth rather than a transient buffer.

## Further reading

- [Apache Kafka — official documentation](https://kafka.apache.org/documentation/)
- [Kafka design & the log — Apache Kafka docs](https://kafka.apache.org/documentation/#design)
- [Event-Driven Architecture with Kafka — start of the series](/blog/posts/kafka-01-why-event-driven.html)
