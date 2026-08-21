# Producers: Writing Events

*A producer looks trivial — send a record to a topic — but the three decisions it makes (which partition, how durably, how safely on retry) determine your ordering, your durability, and whether retries create duplicates.*

Writing to Kafka is where a lot of correctness is won or lost. The producer API is small, but behind `send(record)` sit choices about partitioning, acknowledgement, and idempotency that decide whether your events are ordered, durable, and free of duplicates. This third post in the Event-Driven Architecture with Kafka series covers producers and the decisions that matter.

## The record key controls partitioning

Every record can carry a **key**, and the key is how you control which partition it lands in. Kafka's default partitioner hashes the key and maps it to a partition, so **all records with the same key go to the same partition** — and, because ordering is guaranteed within a partition, all records with the same key are strictly ordered relative to each other.

This is the single most important producer decision, and it follows directly from the per-partition ordering rule from the log post. If order matters for a subset of events, key them by that subset:

- Key `orders` events by `order_id` (or `customer_id`) → all events for one order (or customer) are ordered.
- A `null` key → records are distributed across partitions with no ordering guarantee between them, which is fine for events that are genuinely independent.

The trap: choosing a key with poor distribution creates a **hot partition** — if 90% of traffic shares one key, one partition does 90% of the work and your parallelism collapses. Choose a key that both scopes ordering correctly *and* spreads load evenly. This is exactly the fintech "order events per account" requirement, and the key is how you satisfy it.

## acks: how durable is "sent"

The `acks` setting decides when the producer considers a write successful, trading durability against latency:

- **`acks=0`** — fire and forget; the producer doesn't wait for any acknowledgement. Fastest, but a write can be silently lost. Almost never right for events you care about.
- **`acks=1`** — the leader broker acknowledges once it has written the record. Durable against most cases, but if the leader fails before followers replicate, the record can be lost.
- **`acks=all`** — the leader waits until the record is replicated to all in-sync replicas before acknowledging. The strongest guarantee: the write survives a broker failure. This is what you use for events that must not be lost.

For anything financial or otherwise unforgiving, `acks=all` is the baseline, paired with replication (the production post covers the in-sync-replica machinery). The cost is a little latency for a lot of durability — usually the right trade for events.

## The idempotent producer: retries without duplicates

Producers retry on transient failures — a timeout, a leader change. Naively, a retry can create a **duplicate**: the write actually succeeded, the acknowledgement was lost, the producer retries, and the record is written twice. Kafka's **idempotent producer** eliminates this. With it enabled, each record carries a producer id and sequence number, and the broker deduplicates retries so a record is written **exactly once** even across retries, while preserving order.

This is close to free and should essentially always be on for producers you care about — it turns "at-least-once with possible duplicates on retry" into "exactly-once *into the partition*," which is a meaningfully stronger guarantee for no real cost. (Exactly-once across a full read-process-write pipeline needs transactions, the next post's subject; the idempotent producer is the write-side half of it.)

## Ordering, and how retries can break it

Ordering within a partition is guaranteed — but a subtle producer setting can violate it. If the producer allows multiple in-flight batches to a partition *and* retries are enabled *without* idempotency, a retried batch can land after a later batch, reordering records. The idempotent producer fixes this too: it safely allows in-flight batches while preserving order. So the practical guidance is simple — enable the idempotent producer, and you get retry-safe, duplicate-free, order-preserving writes without hand-tuning in-flight-request limits.

## Batching: throughput without sacrificing safety

Producers batch records per partition before sending, which is the main lever for throughput. Two settings govern it: `linger.ms` (wait a few milliseconds to accumulate a fuller batch) and `batch.size` (the max batch bytes). A small `linger.ms` trades a touch of latency for far better throughput and compression, because sending one batch of 100 records is vastly cheaper than 100 individual sends. Compression (`compression.type`, e.g. lz4/zstd) applies per batch and cuts network and storage. None of this changes durability or ordering — batching is a pure efficiency lever, and it's usually worth a small `linger.ms` for the throughput and compression gains.

## A producer, in shape

Pulling it together, a producer for events you care about looks like: `acks=all`, idempotence enabled, a deliberate key that scopes ordering and spreads load, a modest `linger.ms` with compression, and application-level handling of the send result (success/failure) so a genuine failure isn't ignored. The API call is one line; the configuration is where you encode your durability and ordering requirements. Get the key and `acks`/idempotence right, and the producer side of your event system is correct by construction.

## Key takeaways

- The record key controls partitioning: same key → same partition → strict ordering for that key; scope the key to what must stay ordered (order_id, customer_id), and choose it to spread load or you create a hot partition.
- `acks` trades durability for latency: `acks=all` (wait for replication to in-sync replicas) is the baseline for events that must not be lost; `acks=0`/`1` risk silent loss.
- The idempotent producer deduplicates retries so records are written exactly once into the partition, order-preserving — essentially free and should be on for anything you care about.
- Retries with multiple in-flight batches and no idempotency can reorder records; enabling the idempotent producer makes writes retry-safe *and* order-preserving without manual tuning.
- Batching (`linger.ms`, `batch.size`) plus compression is a pure throughput lever that doesn't affect durability or ordering — a small linger is usually worth it.

## Further reading

- [Apache Kafka — producer documentation](https://kafka.apache.org/documentation/#producerapi)
- [Kafka design & the log — Apache Kafka docs](https://kafka.apache.org/documentation/#design)
- [The Fintech Engineering Handbook series](/blog/series/the-fintech-engineering-handbook/)
