# Time, Clocks, and Ordering

*The most dangerous line of code in a distributed system is the one that trusts a timestamp. Physical clocks on different machines disagree, drift, and jump backward — so "which event happened first?" cannot be answered by comparing wall-clock times. Logical clocks answer it instead, by tracking causality rather than time.*

Almost everything in a distributed system eventually needs to order events: which write is newer, which transaction came first, who acquired the lock. On a single machine you'd just check the clock. Across machines, that instinct is a trap, because there is no single clock — each node has its own, and they don't agree. This post explains why physical time fails as an ordering mechanism and how **logical clocks** — Lamport timestamps and vector clocks — give you the ordering you actually need.

## Why you can't trust the wall clock

Every machine has a **time-of-day clock** synchronized (imperfectly) over the network via NTP. Three properties make it unsafe for ordering events across machines:

- **Clocks disagree.** Even well-synchronized clocks differ by milliseconds to tens of milliseconds. Two events on two machines within that window can't be reliably ordered by timestamp — the "earlier" timestamp may belong to the later event.
- **Clocks drift.** Quartz oscillators run slightly fast or slow, so clocks diverge continuously between synchronizations.
- **Clocks jump.** NTP corrections, leap seconds, and VM migrations can make a clock *jump backward*, so a later event gets an *earlier* timestamp than an earlier one. Time is not even guaranteed to move forward.

The practical consequence is brutal: **"last write wins," implemented with wall-clock timestamps, can silently discard the actually-newer write** because the machine that made it had a slightly slow clock. Ordering by physical time is ordering by an unreliable, non-monotonic, per-node approximation — and it produces data-loss bugs that are nearly impossible to reproduce.

A note on the exception: some systems (famously Google's Spanner) use *tightly bounded* clocks (TrueTime) with GPS and atomic sources, treating time as an interval with known uncertainty and waiting out that uncertainty to order events safely. That works, but it requires special hardware and deliberate waiting — it's proof that raw wall-clock ordering is unsafe *unless* you engineer the uncertainty away.

## What we actually need: happens-before

The insight that unlocks distributed ordering is that you rarely need to know the *real time* an event occurred — you need to know whether one event *could have caused* another. Lamport formalized this as the **happens-before** relation (written →):

- If A and B are on the same node and A occurs first, then A → B.
- If A is the sending of a message and B is its receipt, then A → B.
- It's transitive: if A → B and B → C, then A → C.

If A → B, then A could have influenced B, so any correct ordering must put A before B. If *neither* A → B nor B → A, the events are **concurrent** — they have no causal relationship, and no "true" order between them exists or is needed. Happens-before captures causality, which is the thing ordering actually cares about, and it needs no synchronized clock — only the messages the nodes already exchange.

## Lamport clocks: a cheap logical order

A **Lamport clock** is a single integer counter per node that implements happens-before with minimal machinery:

1. Each node increments its counter before every local event.
2. When a node sends a message, it includes its current counter value.
3. When a node receives a message, it sets its counter to `max(local, received) + 1`.

```text
Node A:  a1(1) ── send(msg, ts=2) ─────────────┐
                                                 ▼
Node B:  b1(1) ────────────────── recv → max(1,2)+1 = 3
```

The guarantee: **if A → B, then timestamp(A) < timestamp(B).** This gives you a consistent total order (break ties by node ID) that never contradicts causality — a slow node can't make a caused event look earlier than its cause. Lamport clocks are cheap (one integer, piggybacked on messages) and enough whenever you need *an* order consistent with causality — dedup, log merging, tie-breaking.

Their limitation: the implication only goes one way. `timestamp(A) < timestamp(B)` does **not** tell you whether A → B or the two are concurrent. A Lamport clock can order events, but it can't detect *conflicts* (concurrent updates), and detecting conflicts is exactly what many replicated systems need.

## Vector clocks: detecting concurrency

A **vector clock** carries more information: each node keeps a *vector* of counters, one entry per node, representing its latest knowledge of every node's progress.

1. Each node increments *its own* entry before a local event.
2. Messages carry the whole vector.
3. On receipt, a node takes the element-wise `max` of its vector and the received one, then increments its own entry.

Now comparison is richer. For two vectors V(A) and V(B):

- If every entry of V(A) ≤ V(B) (and they differ), then **A → B** (A happened before B).
- If neither is ≤ the other, the events are **concurrent** — a genuine conflict.

This is the piece Lamport clocks can't provide: vector clocks *detect concurrent updates*. When two clients update the same key on different replicas during a partition, vector clocks reveal that the versions are concurrent rather than one superseding the other — so the system can preserve both and resolve the conflict (merge, or hand it to the application) instead of silently dropping one. The cost is size: the vector grows with the number of nodes, so systems prune or bound it. The trade is information for space — pay it when you need to *detect* conflicts, not just order events.

## Choosing a clock

The decision follows directly from what you need to know:

- **Wall-clock time** — fine for *displaying* timestamps, logging, and coarse TTLs, and safe for ordering *only* with engineered uncertainty bounds (Spanner-style). Never use raw wall-clock timestamps to decide which of two concurrent writes wins.
- **Lamport clocks** — when you need a single total order consistent with causality and don't need to detect conflicts (event logs, sequencing, tie-breaking).
- **Vector clocks** — when you must *detect concurrent updates* to resolve conflicts correctly (leaderless/multi-leader replication, collaborative editing, anti-entropy).

The unifying idea: distributed ordering is about *causality, tracked through messages*, not about time read from a clock. Get that straight and a whole category of "impossible" timestamp bugs disappears. Next we apply this to replication, where concurrent writes — and the clocks that detect them — become concrete.

## Key takeaways

- Physical clocks disagree, drift, and can jump backward, so wall-clock timestamps cannot reliably order events across machines — "last write wins" by timestamp silently discards the genuinely newer write.
- What you actually need is the happens-before relation: A → B means A could have caused B; events with no happens-before relation either way are concurrent, and need no order.
- Lamport clocks (one integer per node, `max+1` on receive) guarantee A → B implies timestamp(A) < timestamp(B) — a cheap total order consistent with causality — but can't tell ordering from concurrency.
- Vector clocks (a counter per node) can compare versions to detect concurrent updates, which is what lets replicated systems preserve conflicting writes instead of dropping one — at the cost of size growing with node count.
- Choose by need: wall-clock for display/TTLs (or Spanner-style bounded time for safe ordering), Lamport for causal total order, vector clocks for conflict detection.

## Further reading

- [Lamport, "Time, Clocks, and the Ordering of Events in a Distributed System" (1978)](https://lamport.azurewebsites.net/pubs/time-clocks.pdf)
- [CAP and PACELC (previous post)](/blog/posts/distsys-03-cap-and-pacelc.html)
- [Distributed Systems from First Principles — start of the series](/blog/posts/distsys-01-why-distributed-is-hard.html)
