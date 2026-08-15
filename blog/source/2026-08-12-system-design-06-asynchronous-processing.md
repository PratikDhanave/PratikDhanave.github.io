# Asynchronous Processing and Messaging

*How queues, pub/sub, and log-based streaming let systems stay responsive under load — the delivery semantics, ordering rules, backpressure, and outbox patterns that decide whether async saves you or sinks you.*

---

Every request-response system eventually hits the same wall: some work is too slow, too spiky, or too failure-prone to do while a user waits. Resizing an uploaded video, charging a card through a flaky third party, fanning out a notification to a million followers — do these on the request path and your latency is hostage to the slowest dependency you have. **Asynchronous processing** is the escape hatch. You accept the request, hand the slow work to a message broker, return immediately, and let a separate pool of workers grind through it on their own schedule.

That single move — decoupling the producer of work from its consumer through a durable intermediary — is one of the highest-leverage decisions in system design. It also opens a box of trade-offs that trip up almost everyone the first time: what happens when a message is delivered twice, when the queue fills faster than workers drain it, or when your service crashes after writing to the database but before publishing the event. This post walks the whole terrain, trade-off first.

---

## Why go asynchronous at all

Four distinct problems push a system toward async, and it helps to keep them separate because different messaging tools solve them differently.

**Smoothing spikes.** Traffic is bursty. A flash sale, a viral post, a batch job kicking off at midnight — the arrival rate briefly exceeds what your workers can process. If everything is synchronous, the excess load falls straight onto your database and your users see timeouts. A queue in front of the workers acts as a buffer: requests pile up in durable storage and drain at whatever steady rate the workers can sustain. The peak is absorbed, not amplified.

**Decoupling producers from consumers.** Synchronous calls bind two services together in time — both must be up, both must be fast, and the caller must know the callee's address. A broker breaks that binding. The producer writes a message and moves on; it does not know or care which service reads it, how many readers there are, or whether they are even running right now. You can add a second consumer of the same events tomorrow without touching the producer.

**Getting slow work off the request path.** A user clicks "export report." Generating the report takes 40 seconds. Nobody should hold an HTTP connection open that long. Instead you enqueue an "export requested" job, return a 202 with a job id, and let the user poll or receive a push when it's done. The request stays fast; the slow work happens elsewhere.

**Resilience.** If the email provider is down, a synchronous send fails and the user's action fails with it. An asynchronous send parks the message in a queue; when the provider recovers, the worker retries and the message goes through. The failure is contained to the background, invisible to the user.

**The gotcha:** async is not free latency reduction — it is latency *relocation*. The work still happens; you have only moved it off the path the user waits on. If a user genuinely needs the result before they can continue, making it async just replaces a slow response with a fast-but-incomplete one plus a polling problem. Reach for async when the work can truly happen later, not when you wish it were faster.

---

## Three shapes of messaging

"Put a message on a queue" hides three genuinely different architectures. Picking the wrong one is a common and expensive mistake.

### Point-to-point queues

A classic **message queue** — RabbitMQ, Amazon SQS, ActiveMQ — is a pipe with many possible readers but *each message goes to exactly one of them*. Producers push; a pool of competing consumers pulls; once a worker takes a message and acknowledges it, it's gone. This is the natural fit for **work distribution**: a hundred image-resize jobs land on the queue and ten workers each grab roughly ten of them. Scale by adding workers. The queue does not remember a message after it's acknowledged.

### Publish/subscribe

**Pub/sub** — SNS, Google Pub/Sub, a RabbitMQ fanout exchange — flips the cardinality. One published message is delivered to *every* subscriber. An "order placed" event goes simultaneously to the billing service, the inventory service, the analytics pipeline, and the email service, each with its own independent copy. This is the natural fit for **broadcasting facts**: the producer announces that something happened and any number of interested parties react, each unaware of the others.

### Log-based streaming

**Log-based** systems — Apache Kafka, Apache Pulsar, AWS Kinesis — look like a hybrid but are architecturally distinct. The broker is an append-only, partitioned **log** on disk. Producers append records to the end; consumers read forward at their own pace, tracking a numeric **offset** that marks how far they've read. Crucially, reading does *not* delete: the record stays until a retention window expires (say, seven days), so multiple independent consumers can read the same stream, and any of them can rewind and **replay** history from an earlier offset. That combination — durable retention plus replayable, per-consumer position — is what makes the log the substrate for event sourcing, stream processing, and rebuilding a downstream store from scratch.

| Property | Point-to-point (SQS, RabbitMQ) | Pub/sub (SNS, Pub/Sub) | Log (Kafka, Pulsar) |
|---|---|---|---|
| Message reaches | one consumer | every subscriber | every consumer group |
| After consumption | deleted on ack | delivered, then gone | retained until window expires |
| Replay past messages | no | no | yes, by resetting offset |
| Ordering | limited / per-group (FIFO) | generally none | strict per-partition |
| Best for | distributing work | broadcasting events | streaming, replay, event sourcing |

**The gotcha:** don't reach for Kafka just because it's the fashionable answer. A partitioned log is powerful but operationally heavy — partitions, consumer groups, offset management, retention tuning. If all you need is "run these jobs on some workers," a managed queue like SQS is a fraction of the operational cost and gives you retries and dead-lettering for free. Match the tool to the cardinality and the replay requirement, not to the résumé.

---

## Delivery semantics, and the exactly-once myth

Once a network sits between producer and consumer, you must confront a hard truth: **you cannot have both no-loss and no-duplication at the transport level.** Brokers offer three semantics.

- **At-most-once.** Fire and forget. The message is delivered zero or one times, never more. If the consumer crashes mid-processing, the message is simply lost. Fine for disposable telemetry where a dropped sample doesn't matter.
- **At-least-once.** The broker keeps redelivering until the consumer acknowledges. Nothing is ever lost — but a consumer that processes a message and then crashes *before* its ack is sent will receive that same message again on restart. Duplicates are guaranteed to happen eventually. This is the default and the right choice for almost everything.
- **Effectively-once (a.k.a. "exactly-once").** Every message affects the system exactly one time — no loss, no duplicate effect.

**The gotcha:** "exactly-once *delivery*" over a network does not really exist, no matter what a product page implies. The reason is fundamental: after the consumer processes a message, its acknowledgement can be lost in flight. The broker, having heard nothing, must choose — redeliver (risking a duplicate) or not (risking a loss). No amount of protocol cleverness escapes that fork. What real systems achieve is exactly-once *effect*, and they get it by combining at-least-once delivery with **idempotent processing**: the consumer is written so that handling the same message twice produces the same result as handling it once (typically by recording a dedup key and skipping repeats). The broker's "exactly-once" features — Kafka's transactional producer, for instance — deliver this only within the broker's own boundary; the moment your handler touches an external database or API, idempotency is *your* job. We'll go deep on how to build idempotent consumers in the next post; for now, internalize the rule: **design for at-least-once, and make duplicate processing harmless.**

---

## Ordering: cheaper per-key, ruinous globally

Message ordering is one of those guarantees that sounds trivial and turns out to cost throughput.

A log gets its parallelism from **partitions**: the stream is split into N independent shards, and N consumers can read them concurrently. Within a single partition, records are strictly ordered — record 5 is always read after record 4. Across partitions there is *no* order at all, because they're being read independently and in parallel. To keep related messages ordered, you route them to the same partition with a **partition key**: use `account_id` as the key and every event for account 42 lands on the same partition, in order, while account 43's events flow through a different partition entirely.

**The gotcha:** insisting on *global* ordering — a single total order across every message in the system — collapses your parallelism to one. The only way to guarantee that message A is processed before message B when they might be on different partitions is to have a single partition and a single consumer, which is a throughput ceiling of one. The escape is to realize you almost never need global order. You need *per-entity* order: events for a given user, account, or document must be ordered relative to each other, but user 1's events have no meaningful ordering relationship with user 2's. Choose a partition key that captures exactly the ordering you need and no more, and you keep both correctness and parallelism.

Consumer groups make this concrete. In Kafka, a **consumer group** is a set of workers that jointly consume a topic; the broker assigns each partition to exactly one member of the group, so adding consumers (up to the partition count) scales throughput while preserving per-partition order. Each group tracks its own offsets independently, which is how the same topic can feed both a real-time service and a nightly batch job without either interfering with the other — and how a consumer can rewind its offset to replay.

---

## Backpressure: the queue is a shock absorber, not a black hole

Here is where a lot of async designs quietly rot. You put a queue between producer and consumer, load goes up, and for a while everything is fine — the queue absorbs the burst exactly as intended. Then the producer's average rate creeps above the consumer's drain rate, and the queue depth begins to climb. And climb. And climb.

An unbounded queue does not fail loudly. It fails by growing: latency stretches because messages sit longer and longer before being processed (a message enqueued when depth is 2 million won't be touched for hours), and memory or disk fills until the broker or the process falls over. By the time you notice, the backlog is enormous and draining it takes as long as it took to build.

**The gotcha:** an unbounded queue is a capacity problem wearing a disguise. It converts "we can't keep up" — which should be an immediate, visible signal — into a slow-motion latency and memory leak that only detonates hours later. The fix is **backpressure**: bound the queue, and when it's full, push the pressure back onto the producer. A bounded queue that rejects or blocks new work forces the mismatch to surface at the source, where someone can act on it — shed load, return a 429, scale consumers, or slow the producer down. A queue should be a shock absorber that smooths *transient* bursts, not a hidden infinite buffer papering over a permanent throughput deficit. If your average arrival rate exceeds your average service rate, no queue size saves you; you need more consumers or less work.

Flow control is the same idea generalized: the consumer signals how much it can handle (a prefetch limit in RabbitMQ, `max.poll.records` in Kafka, an in-flight cap in SQS) so the broker never floods it faster than it drains.

---

## A minimal worker in Go

The consumer side of async is usually a loop: pull, process, acknowledge, repeat — with bounded concurrency so a burst can't spawn unlimited goroutines. The sketch below shows the shape, with the two invariants that matter most: **acknowledge only after successful processing** (so a crash mid-work redelivers rather than loses), and **process idempotently** (so redelivery is harmless).

```go
// A bounded worker pool draining a queue. `sem` caps concurrency so a
// backlog can't spawn unbounded goroutines — that's backpressure applied
// to ourselves.
func runWorkers(ctx context.Context, q Queue, n int) {
    sem := make(chan struct{}, n) // at most n messages in flight
    for {
        msg, err := q.Receive(ctx) // blocks; respects flow-control limits
        if err != nil {
            return // context cancelled or queue closed
        }
        sem <- struct{}{} // acquire a slot (blocks when n are busy)
        go func(m Message) {
            defer func() { <-sem }() // release the slot
            if alreadyProcessed(m.DedupKey) {
                q.Ack(m) // duplicate from at-least-once redelivery — skip, but ack
                return
            }
            if err := handle(m); err != nil {
                q.Nack(m) // return to queue for retry; DLQ after max attempts
                return
            }
            markProcessed(m.DedupKey)
            q.Ack(m) // ack ONLY after success, so a crash redelivers
        }(msg)
    }
}
```

The `sem` channel is the backpressure knob: when `n` messages are being handled, `q.Receive` stops being called until a slot frees, so the worker never pulls more than it can process. The `alreadyProcessed`/`markProcessed` pair is idempotency in miniature — the real version needs those two steps to be atomic, which is exactly the subject of the next post.

---

## Poison messages and dead-letter queues

Retries are essential, but retrying *forever* is a trap. Some messages can never succeed — malformed payload, a referenced record that was deleted, a bug in the handler. This is a **poison message**: it fails, gets redelivered, fails again, and if the broker keeps retrying it can block the partition behind it or spin a worker uselessly, starving healthy messages.

The standard defense is a **dead-letter queue (DLQ)**: after a message fails some maximum number of attempts, the broker moves it to a separate queue instead of redelivering it. This does two good things at once — it unblocks the main flow so healthy messages keep moving, and it *preserves* the failed message for a human to inspect, fix, and replay rather than silently dropping it.

**The gotcha:** a DLQ is only useful if someone watches it. An unmonitored dead-letter queue is just a slow data-loss bucket — messages accumulate there unseen until someone wonders months later why a batch of orders never shipped. Alert on DLQ depth the same way you'd alert on error rate, and treat a nonzero DLQ as an incident, not a curiosity.

---

## The dual-write problem and the outbox

Here is the subtlest failure in the whole area, and it bites nearly every event-driven system that hasn't been designed for it.

Your service needs to do two things when an order is placed: write the order row to its database, and publish an "order placed" event to the broker. The naive code does them one after the other:

```text
1. db.Save(order)          // succeeds
2. broker.Publish(event)   // ...crash here
```

If the process dies between step 1 and step 2, the database has the order but the event was never published. Downstream services — billing, shipping, analytics — never hear about it. The order silently falls into a hole. Swap the order of the two writes and you get the opposite failure: an event published for an order that was never persisted. There is no ordering of two independent writes to two independent systems that is crash-safe, because they cannot share a transaction. This is the **dual-write problem**.

**The gotcha:** writing to your database and then publishing to a broker are two separate operations with no shared transaction — a crash in between loses the event (or invents one), and it happens rarely enough that you'll ship it to production before you notice. The fix is the **transactional outbox**: instead of publishing directly, write the event into an `outbox` table *in the same database transaction* as the business data. Now the order row and the event row commit atomically — either both land or neither does. A separate process (polling the outbox table, or tailing the database's change log via change-data-capture) reads unpublished rows and forwards them to the broker, marking them sent.

```text
── one atomic DB transaction ──
   INSERT INTO orders     (...);
   INSERT INTO outbox     (event='order_placed', payload=...);
   COMMIT;                        // both or neither

── separate relay process ──
   SELECT * FROM outbox WHERE published = false;
   broker.Publish(row); mark published = true;   // at-least-once to the broker
```

Note the relay publishes *at-least-once* — it may crash after publishing but before marking the row sent, re-sending on restart. Which is fine, because by now you know the answer: the consumer is idempotent, so a duplicate event is harmless. The outbox closes the atomicity gap; idempotent consumers absorb the duplicates the outbox's own retries create. The two patterns are partners.

---

## Event-driven architecture: choreography vs orchestration

Zoom out and these mechanics compose into a style: **event-driven architecture**, where services communicate primarily by emitting and reacting to events rather than calling each other directly. A multi-step business process — place order, charge card, reserve inventory, ship — can be coordinated two ways.

**Choreography** is decentralized. Each service listens for events and emits its own; there is no conductor. "Order placed" triggers the payment service, whose "payment captured" event triggers the inventory service, and so on. It's beautifully decoupled — adding a step means adding a listener, touching nothing else — but the overall flow exists nowhere explicit. Understanding "what happens when an order is placed" means tracing events across a dozen services, and cyclic or emergent behavior is easy to create by accident.

**Orchestration** is centralized. A coordinator (often a workflow engine) explicitly drives the sequence: it calls payment, waits, calls inventory, waits, calls shipping, and handles compensation if a step fails. The flow lives in one readable place and failure handling is explicit, at the cost of a central component every step depends on.

The rule of thumb: choreography when steps are genuinely independent reactions to a fact; orchestration when a process has a definite sequence, needs a clear owner, or requires coordinated rollback across steps. Most mature systems use both — choreography for loose fan-out, orchestration for the critical transactional flows.

---

## Key takeaways

- **Async relocates work, it doesn't delete it.** Use it when work can truly happen off the request path — to smooth spikes, decouple services, and contain failures — not as a wish for lower latency.
- **Three messaging shapes, three jobs.** Point-to-point queues distribute work, pub/sub broadcasts facts, log-based streaming adds retention and replay. Don't reach for Kafka when SQS will do.
- **Design for at-least-once.** Exactly-once *delivery* over a network is a myth; you get exactly-once *effect* by making processing idempotent. (Next post.)
- **Order per key, never globally.** Partition by the entity that needs ordering; a single global order collapses parallelism to one.
- **Bound your queues.** An unbounded queue hides a capacity problem until it detonates as latency and OOM. Apply backpressure so the mismatch surfaces at the source.
- **Close the atomicity gaps.** The transactional outbox fixes the dual-write problem; dead-letter queues quarantine poison messages — but only if someone is watching the DLQ.

---

## Further reading

- [Apache Kafka — Documentation & Design](https://kafka.apache.org/documentation/#design) — the partitioned-log model, consumer groups, offsets, and delivery-semantics discussion straight from the source.
- [Apache Kafka — design](https://kafka.apache.org/documentation/#design) — the log-centric architecture popularized by Jay Kreps's essay "The Log," which reframed the log as a first-class primitive.
- [Amazon SQS Developer Guide](https://docs.aws.amazon.com/AWSSimpleQueueService/latest/SQSDeveloperGuide/welcome.html) — standard vs FIFO queues, at-least-once delivery, visibility timeouts, and dead-letter queues.
- [Transactional Outbox pattern — microservices.io](https://microservices.io/patterns/data/transactional-outbox.html) — the canonical write-up of the dual-write problem and its fix.
- [Saga pattern — microservices.io](https://microservices.io/patterns/data/saga.html) — choreography vs orchestration for multi-step, cross-service transactions.
