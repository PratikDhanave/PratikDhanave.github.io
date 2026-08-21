# Consumers and Consumer Groups

*A single consumer reading a topic is easy; the elegant part is how Kafka lets a group of consumers share the work automatically, rebalance when members come and go, and each remember exactly where it left off.*

Producers append; consumers read. But the interesting engineering is in how consumers *scale* and *track progress*. Kafka's answer — consumer groups, partition assignment, and offset commits — is what lets you add consumers to handle more load and recover exactly where you stopped after a crash. This fourth post in the Event-Driven Architecture with Kafka series covers consumers and the group mechanics that make them robust.

## Consumer groups: sharing the work

A **consumer group** is a set of consumers that cooperate to read a topic, identified by a shared `group.id`. The rule that governs everything: **each partition is consumed by exactly one consumer in the group at a time.** Kafka distributes the topic's partitions across the group's members, so the work is shared and no two members process the same partition simultaneously.

This gives you horizontal scaling almost for free: to process a topic faster, add consumers to the group, and Kafka reassigns partitions to spread the load. But it also sets the ceiling — **parallelism within a group is capped at the partition count.** A topic with 6 partitions supports at most 6 useful consumers in a group; a 7th sits idle with no partition to own. This is why partition count (from the log post) is a capacity decision made up front: it bounds how much you can parallelize consumption later.

Different groups are independent. Two groups subscribed to the same topic each get *all* the events — this is how EDA fan-out works: the `payments` group and the `email` group both consume every `orders` event, each at its own pace, each tracking its own offsets. One topic, many independent groups, is the shape of event-driven consumption.

## Rebalancing: adapting to change

Membership changes — a consumer crashes, a new one joins, a deploy rolls instances. When it does, Kafka **rebalances**: it redistributes partitions across the current members so the group keeps covering all partitions. This is what makes a group self-healing — a crashed consumer's partitions are reassigned to survivors automatically, and a new consumer picks up a share.

Rebalancing is powerful but not free, and understanding its cost avoids two classic problems. During a rebalance, consumption pauses briefly while partitions move (a "stop-the-world" moment in older protocols; incremental/cooperative rebalancing reduces this). And frequent rebalances — from consumers that process slowly and miss heartbeats, or from flapping instances — cause repeated pauses that tank throughput. The practical guidance: keep processing fast enough to stay within the session timeout (or move slow work off the poll thread), and prefer cooperative rebalancing so a membership change doesn't stall the whole group. A group that rebalances constantly spends its time reassigning instead of consuming.

## The poll loop

A consumer's life is a loop: `poll()` for a batch of records, process them, repeat. `poll()` does double duty — it fetches records *and* sends the heartbeats that tell the group coordinator the consumer is alive. This is why the golden rule of consumers is **don't block the poll loop**: if processing a batch takes longer than the timeout, the coordinator thinks the consumer died and triggers a rebalance, and you get the repeated-pause problem above. For slow processing, either raise the timeout deliberately or hand work to a separate thread/pool, keeping the poll loop responsive. The poll loop's rhythm — fetch, process, commit, repeat — is the heartbeat of a Kafka consumer in both senses.

## Offsets: remembering where you are

A consumer's progress is its **committed offset** per partition — "I have processed up to here." On restart or rebalance, a consumer resumes from the last committed offset, which is how Kafka delivers *at-least-once* by default and how a crashed consumer recovers exactly where it stopped. How and when you commit is a correctness decision:

- **Auto-commit** periodically commits offsets in the background. Convenient, but it can commit an offset for records you fetched but haven't finished processing — so a crash can *skip* unprocessed records (at-most-once, data loss) or, depending on timing, reprocess.
- **Manual commit after processing** is the safe pattern: process the batch, *then* commit. If you crash before committing, you reprocess the batch on restart — at-least-once, no loss. This is what most correct consumers do.

The timing rule that flows from this: **commit after you've done the work, not before.** Commit-before-process risks losing records; commit-after-process risks reprocessing them. For events, reprocessing (a duplicate) is almost always a better failure than losing (a gap) — which is why at-least-once is the default posture, and why consumers must be built to tolerate duplicates.

## Which leads to delivery semantics

That last point — commit timing determines whether you lose or duplicate records — is the doorway to the next post. At-least-once (commit after processing, tolerate duplicates) is the workhorse, at-most-once (commit before) is rarely what you want, and exactly-once needs more machinery. The key consumer-side takeaway is that *your commit strategy is your delivery guarantee*, and that at-least-once demands idempotent processing so a reprocessed record doesn't cause a double effect.

## Key takeaways

- A consumer group shares a topic's partitions with the rule "one partition → one consumer in the group," giving horizontal scaling capped at the partition count; separate groups each get all events (EDA fan-out).
- Rebalancing reassigns partitions when membership changes, making a group self-healing — but it pauses consumption, so avoid frequent rebalances (fast processing, cooperative rebalancing).
- The poll loop fetches *and* heartbeats, so never block it; move slow processing off the poll thread or it triggers spurious rebalances.
- A consumer resumes from its committed offset; commit *after* processing (manual commit) for at-least-once with no loss — auto-commit or commit-before-process risks skipping records.
- Your commit strategy *is* your delivery guarantee; at-least-once is the default and requires idempotent processing to tolerate the duplicates that reprocessing produces.

## Further reading

- [Apache Kafka — consumer documentation](https://kafka.apache.org/documentation/#consumerapi)
- [Apache Kafka — official documentation](https://kafka.apache.org/documentation/)
- [Event-Driven Architecture with Kafka — start of the series](/blog/posts/kafka-01-why-event-driven.html)
