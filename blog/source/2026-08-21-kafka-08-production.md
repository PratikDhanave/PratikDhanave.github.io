# Kafka in Production

*Kafka's defaults will run; whether they'll survive a broker failure, a traffic spike, or a year of growth depends on a handful of decisions — replication, durability, partitioning, and what you monitor — that are far cheaper to make now than to retrofit later.*

The concepts are in place; this final post is about running Kafka for real. Production Kafka is mostly about a few decisions that determine durability and scale, plus knowing the pitfalls that bite teams and the honest cases where Kafka is the wrong tool. This eighth post closes the Event-Driven Architecture with Kafka series.

## Replication and in-sync replicas

The foundation of Kafka's durability is **replication**: each partition has a leader and a configurable number of replicas on other brokers. Producers write to the leader; followers copy the data. The set of replicas that are caught up is the **in-sync replica set (ISR)**. Two settings work together to decide how durable a write really is:

- **Replication factor** — how many copies of each partition exist. Three is the common production choice: it tolerates one broker failure with room to spare.
- **`min.insync.replicas`** — the minimum ISR members that must acknowledge a write (with `acks=all`) for it to succeed. With replication factor 3 and `min.insync.replicas=2`, a write must reach at least two replicas, so it survives losing one broker *and* the cluster refuses writes rather than accepting ones it can't safely replicate.

The combination that matters: **`acks=all` + replication factor 3 + `min.insync.replicas=2`** is the standard durable configuration. `acks=all` alone is not enough — without `min.insync.replicas`, a partition down to one in-sync replica would still accept writes that a single failure then loses. Durability is this trio, not any one setting.

## Partitioning strategy: decide early

Partition count is the decision teams most regret getting wrong, because it's awkward to change later. It sets two ceilings from earlier in the series: consumer parallelism (a group can't have more active consumers than partitions) and throughput. More partitions mean more parallelism and headroom — but also more overhead (open files, more rebalancing work, more end-to-end latency at extremes), so more is not free.

The guidance: estimate your target throughput and peak consumer parallelism, and provision partitions to cover peak *with growth headroom*, because increasing partitions later is disruptive (it changes key-to-partition mapping, breaking per-key ordering for existing keys). Under-provisioning caps your scale; wild over-provisioning adds overhead. Pick a considered number up front, and remember the key-distribution lesson: a good key spreads load across those partitions rather than creating a hot one.

## What to monitor

Kafka is a system you must watch, and a few signals matter most:

- **Consumer lag** — the gap between the latest offset and a consumer group's committed offset. This is *the* health metric of an event system: rising lag means consumers are falling behind producers, and events are getting staler. Alert on it.
- **Under-replicated partitions** — partitions whose ISR is below the replication factor. A sign a broker is struggling or down; it's a direct durability risk.
- **Broker health** — disk (Kafka is disk-bound and retention fills disks), CPU, network, and request latencies.
- **Rebalance frequency** — frequent consumer-group rebalances (from slow consumers or flapping instances) tank throughput, as the consumers post covered.

Lag and under-replicated partitions are the two you cannot run blind on: the first tells you consumers are keeping up, the second tells you your data is as durable as you think.

## Common pitfalls

The failures that recur, so you can avoid them:

- **Hot partitions** from a poorly-chosen key — one partition does most of the work and caps throughput despite a high partition count. Fix the key's distribution.
- **Blocking the poll loop** with slow processing — triggers endless rebalances. Move slow work off the poll thread.
- **Assuming global ordering** — ordering is per-partition only; designs that need total order across a topic are fighting Kafka.
- **`acks=all` without `min.insync.replicas`** — a false sense of durability, as above.
- **Non-idempotent consumers** on at-least-once delivery — duplicates cause double effects; make processing idempotent.
- **Unbounded retention on a full disk** — Kafka keeps data by policy; if retention outpaces disk, brokers fail. Size retention to disk deliberately.

Most Kafka incidents trace back to one of these six, and every one is preventable at design time.

## When not to use Kafka

An honest close, matching the series' first post. Kafka is heavy infrastructure — a distributed, stateful cluster to run, monitor, and reason about. It is overkill for:

- **Simple request/response** between two services — use a direct call; an event bus adds latency and operational weight for no decoupling benefit.
- **Low-volume task queues** — a simple queue (or a database-backed job table) is far less to operate when you don't need replay, retention, or high throughput.
- **Small systems** where the operational cost of Kafka dwarfs the benefit — you don't stand up a cluster for a handful of events a minute.

Kafka earns its considerable operational cost when you genuinely need durable, replayable, high-throughput event streams shared across many independently-evolving consumers — the exact case event-driven architecture is for. Reach for it there, and reach for something simpler everywhere else.

## The series, in one line

Event-driven architecture decouples services by sharing durable, replayable *facts* instead of synchronous calls, and Kafka is the log that makes those facts durable, ordered, and replayable at scale. Master the log and its consequences — producers keying for order and durability, consumer groups sharing and committing work, delivery semantics made correct with idempotency, schemas as an evolving contract, and the patterns and production settings above — and you can design event systems that scale and survive failure. Use it where independent evolution, fan-out, and replayable history are real; keep it simple everywhere else.

## Key takeaways

- Durability is a trio, not one setting: `acks=all` + replication factor 3 + `min.insync.replicas=2` ensures a write reaches multiple replicas and the cluster refuses writes it can't safely replicate.
- Partition count sets your consumer-parallelism and throughput ceilings and is disruptive to change later (it breaks per-key ordering) — provision for peak plus growth up front, with a well-distributed key.
- Monitor consumer lag (the health metric of an event system) and under-replicated partitions (a durability risk) above all, plus broker disk/health and rebalance frequency.
- Avoid the recurring pitfalls: hot partitions, blocking the poll loop, assuming global ordering, `acks=all` without `min.insync.replicas`, non-idempotent consumers, and unbounded retention on a full disk.
- Kafka is heavy infrastructure — use it for durable, replayable, high-throughput streams shared across many independent consumers; for simple request/response or low-volume queues, something simpler is better.

## Further reading

- [Apache Kafka — official documentation](https://kafka.apache.org/documentation/)
- [Kafka operations & configuration — Apache Kafka docs](https://kafka.apache.org/documentation/#operations)
- [Event-Driven Architecture with Kafka — start of the series](/blog/posts/kafka-01-why-event-driven.html)
