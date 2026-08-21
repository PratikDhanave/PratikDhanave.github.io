# Replication

*Replication is keeping copies of the same data on multiple nodes, and it's the answer to two different problems at once — surviving failures and serving reads at scale. The hard part is never the copying; it's what happens when the copies disagree, which they always eventually do.*

If a single machine holds your only copy of the data, that machine's failure is your data's death, and its capacity is your read ceiling. **Replication** — maintaining copies of the data on several nodes — solves both: copies survive individual failures, and reads can be spread across them. But the instant you have more than one copy, you inherit the problem that shaped the whole series — keeping them consistent when writes arrive and nodes fail. This post covers the three replication architectures and the trade-offs baked into each.

## Why replicate

Three distinct motivations, often conflated:

- **Fault tolerance** — if one node holding the data dies, another copy can serve, so the system survives hardware failure without data loss.
- **Read scalability** — read-heavy workloads can be spread across replicas, multiplying read throughput beyond one machine.
- **Latency** — placing replicas near users (geographically) lets reads be served locally instead of across the world.

These pull in different directions — scaling reads wants many replicas everywhere, but more copies make consistency harder and writes slower — which is why there are several architectures rather than one.

## Single-leader replication

The most common design: one replica is the **leader** (primary), and all writes go to it. The leader applies each write locally, then streams the changes to its **followers** (replicas), which apply them in the same order. Reads can be served by the leader or any follower.

```text
        writes
          │
          ▼
      ┌────────┐   replication stream   ┌──────────┐
      │ LEADER │ ─────────────────────▶ │ FOLLOWER │  ◀─ reads
      └────────┘ ─────────────────────▶ ┌──────────┐
                                        │ FOLLOWER │  ◀─ reads
                                        └──────────┘
```

The central choice is **synchronous vs. asynchronous** replication:

- **Synchronous** — the leader waits for follower(s) to confirm the write before acknowledging the client. No data loss if the leader then dies (a follower has it), but the write is as slow as the slowest follower, and a stalled follower blocks writes.
- **Asynchronous** — the leader acknowledges immediately and replicates in the background. Fast and available even if followers lag, but if the leader crashes before a write propagates, that write is **lost**.
- **Semi-synchronous** (the common compromise) — wait for *one* follower synchronously, replicate to the rest asynchronously: guaranteed durability on at least two nodes without waiting for all.

Single-leader is simple and gives a clean consistency story (one place decides write order), but it has two costs: the leader is a write bottleneck and a single point of failure, so you need **failover** (promote a follower when the leader dies — itself a consensus problem, covered next post), and asynchronous followers serve **stale reads**, which is where the session guarantees from the [consistency models](/blog/posts/distsys-02-consistency-models.html) post earn their keep.

## Multi-leader replication

When one leader isn't enough — typically multi-datacenter setups where you want a local leader in each region — you can have **multiple leaders**, each accepting writes and replicating to the others. This improves write availability and latency (write to your nearest leader) and tolerates a datacenter outage.

The price is severe and unavoidable: **write conflicts**. Two leaders can accept conflicting writes to the same key concurrently, and because they're separated, neither sees the other in time. Now you must *detect* the conflict (this is exactly what the vector clocks from the [time and ordering](/blog/posts/distsys-04-time-clocks-ordering.html) post are for) and *resolve* it — via last-write-wins (simple but data-losing), application-defined merge logic, or conflict-free data types (CRDTs) that merge deterministically. Multi-leader buys write locality and availability at the cost of conflict handling, so reach for it only when a single leader genuinely can't meet your latency or availability needs.

## Leaderless replication

The third architecture drops the leader entirely: **any replica accepts writes**, and the client (or a coordinator) writes to *several* replicas and reads from *several*, using **quorums** to stay consistent. This is the Dynamo-style design behind systems like Cassandra.

The mechanism is the **quorum condition**. With N replicas, if you require W replicas to acknowledge a write and R replicas to answer a read, then setting **W + R > N** guarantees the read set and write set overlap in at least one replica — so a read is guaranteed to see the latest write:

```text
N = 3, W = 2, R = 2  →  W + R = 4 > 3  ✓  (read and write sets always overlap)
```

Quorums make the consistency/availability trade *tunable per operation*, connecting directly to CAP:

- **W + R > N** — strong-ish consistency (reads see latest writes), but writes need W nodes up and reads need R nodes up.
- **Lower W** — faster, more available writes, weaker read consistency.
- **Lower R** — faster reads, higher staleness risk.

Because writes may reach only some replicas, leaderless systems repair divergence in the background — **read repair** (fix stale replicas noticed during a read) and **anti-entropy** (a background process that syncs replicas) — and use vector clocks to detect concurrent writes. Leaderless trades the simplicity of a single write-order authority for high availability and per-request tunability, pushing conflict handling into the read path.

## Choosing an architecture

- **Single-leader** — the default for most systems. Simple, strong write ordering, good read scaling; accept the leader bottleneck and plan failover. Use unless you have a specific reason not to.
- **Multi-leader** — multi-region writes where local write latency and per-region availability matter enough to justify building conflict resolution. Don't adopt it for the write throughput alone.
- **Leaderless (quorum)** — maximum write availability and tunable consistency, at the cost of read-path complexity (quorums, read repair, conflict detection). Good for always-writable, high-availability workloads.

Every architecture makes the same fundamental trade in a different place: **how much do writes coordinate, and where do you pay for disagreement** — at write time (synchronous), at failover, at read time (quorums/repair), or in conflict resolution (multi-leader). There is no copy-free lunch. The one thing all three eventually need — agreeing on *who* the leader is, or on a single order of operations despite failures — is consensus, the subject of the next post.

## Key takeaways

- Replication keeps copies of data on multiple nodes for fault tolerance, read scalability, and lower latency — but introduces the core problem of keeping copies consistent when writes and failures happen.
- Single-leader (all writes to one primary, streamed to followers) is the simple default; the key knob is synchronous (durable, slow, blocking) vs. asynchronous (fast, available, can lose writes on leader crash), with semi-sync as the common compromise, plus stale follower reads and failover to manage.
- Multi-leader (a write-accepting leader per region) buys write locality and availability but forces conflict detection (vector clocks) and resolution (LWW, merge, or CRDTs) — adopt only when a single leader can't meet latency/availability needs.
- Leaderless/quorum (any replica writable, W + R > N guarantees read/write overlap) makes consistency tunable per operation and maximizes availability, at the cost of read-path complexity — quorums, read repair, anti-entropy, conflict detection.
- Every architecture makes the same trade — how much writes coordinate and where you pay for disagreement — so pick by where you can best afford that cost; all of them ultimately need consensus for leadership/ordering.

## Further reading

- [Dynamo: Amazon's Highly Available Key-value Store (2007)](https://www.allthingsdistributed.com/files/amazon-dynamo-sosp2007.pdf)
- [Time, Clocks, and Ordering (previous post)](/blog/posts/distsys-04-time-clocks-ordering.html)
- [Event-Driven Architecture with Kafka series](/blog/series/event-driven-architecture-with-kafka/)
