# CAP and PACELC

*The CAP theorem is the most cited and most misunderstood result in distributed systems. It does not say "pick two of three." It says something narrower and more useful: when the network partitions, you must choose between consistency and availability — and PACELC completes the picture by asking what you trade even when it doesn't.*

Every distributed data system eventually confronts one unavoidable question: when nodes can't talk to each other, do you keep serving requests (and risk returning stale or conflicting data), or do you refuse to serve (to protect correctness)? The **CAP theorem** formalizes that this is a genuine dichotomy, not an engineering failure you can design away. Understanding it precisely — and its extension, **PACELC** — is what lets you read a database's guarantees honestly instead of by its marketing.

## What CAP actually says

CAP concerns three properties of a distributed data store:

- **Consistency (C)** — every read receives the most recent write or an error. (This is linearizability, *not* the "C" in ACID — a common and costly confusion.)
- **Availability (A)** — every request receives a non-error response, without the guarantee that it contains the most recent write.
- **Partition tolerance (P)** — the system continues to operate despite messages being dropped or delayed between nodes (a network partition).

The theorem: **when a partition occurs, a system cannot be both consistent and available.** If two nodes can't communicate and a write lands on one, the other must either return possibly-stale data (choosing A, sacrificing C) or refuse to answer (choosing C, sacrificing A). There is no third option, because the two nodes physically cannot coordinate.

## The "pick two" framing is wrong

The popular "pick two of C, A, P" phrasing is misleading, because **P is not optional**. Network partitions are a fact of the physical world — cables cut, switches fail, packets drop — so any real distributed system *must* tolerate them. You don't choose whether partitions happen; you only choose how to *respond* when they do.

So the honest statement is: **a distributed system must be partition-tolerant, and therefore, during a partition, it must choose between C and A.** That reduces the taxonomy to two meaningful kinds of system:

- **CP (consistency over availability)** — during a partition, refuse requests that can't be served consistently. The system may become unavailable, but it never returns wrong data. Choose this when incorrectness is unacceptable: financial ledgers, locks, uniqueness, coordination.
- **AP (availability over consistency)** — during a partition, keep serving from whatever replica you can reach, accepting stale or divergent data that gets reconciled later. Choose this when being down is worse than being briefly wrong: shopping carts, social feeds, presence, caches.

Note that "CA" — consistent and available but not partition-tolerant — describes a single-node system or one that simply hasn't partitioned *yet*; it isn't a real option for a distributed system.

## The trade-off is not all-or-nothing

CAP is stated in absolutes, but production systems make the choice at finer granularity. A single system can be **CP for some operations and AP for others** — refuse a "deduct from balance" during a partition but keep serving "show product page." Many databases expose the trade-off as a *tunable* per request: quorum settings (the subject of the replication post) let you dial toward consistency or availability read-by-read and write-by-write. And the choice interacts directly with the [consistency models](/blog/posts/distsys-02-consistency-models.html) from the last post: an AP system doesn't abandon consistency entirely, it drops from linearizability to eventual/causal and leans on session guarantees. CAP tells you the extremes you're forced between during a partition; real systems live on a dial between them.

## PACELC: the half of the story CAP omits

CAP only describes behavior *during a partition* — which is rare. It says nothing about the normal case, when the network is healthy, yet that case dominates your system's life. **PACELC** completes the picture:

> **If** there is a **P**artition, trade between **A**vailability and **C**onsistency (the CAP choice); **E**lse (normal operation), trade between **L**atency and **C**onsistency.

The second clause is the one you feel every day. Even with no partition, a system that guarantees strong consistency must coordinate replicas on each operation, and that coordination costs **latency**. A system willing to relax consistency can answer from the nearest replica immediately, buying **lower latency**. So the real, always-present trade-off is latency vs. consistency; the partition case is the rare, dramatic version of the same tension.

PACELC gives a sharper vocabulary for classifying systems:

- **PC/EC** — consistent under partition *and* in normal operation, paying availability and latency for it (systems built around strong consistency and consensus).
- **PA/EL** — available under partition and low-latency normally, relaxing consistency in both cases (systems built for availability and speed).
- Mixed profiles (e.g. PC/EL) exist too, and tunable systems let you pick per operation.

The lesson: don't evaluate a datastore only by "what happens during a partition." Ask what it costs you in latency *the other 99.9% of the time*, because that's the trade you pay continuously.

## Using this in practice

CAP and PACELC aren't trivia — they're a lens for design decisions:

- **Classify each operation, not the whole system.** Decide per operation whether a stale answer is tolerable; make the coordinate-heavy CP choice only where it's required, and take the AP/low-latency path everywhere else.
- **Read a database's real guarantees.** "Highly available" usually means AP/EL — expect staleness. "Strongly consistent" usually means PC/EC — expect higher latency and reduced availability under partition. The label tells you the trade you're signing up for.
- **Design partition behavior deliberately.** Decide *now* what each part of your system does when nodes can't talk — serve stale, degrade gracefully, or reject — rather than discovering the default during an outage.

The next posts give you the machinery behind these choices: how ordering is established without a shared clock, how replication actually distributes data, and how consensus lets nodes agree despite all of the above.

## Key takeaways

- CAP: during a network partition, a distributed data store must choose between consistency (every read sees the latest write) and availability (every request gets a non-error response) — it cannot have both.
- "Pick two of three" is wrong: partition tolerance is mandatory in any real distributed system, so the actual choice is C-vs-A *during a partition* — giving CP (correct but may be unavailable) and AP (available but may be stale) systems.
- The trade-off is tunable and per-operation: one system can be CP for critical writes and AP for cheap reads, often via quorum settings, dropping from linearizability to eventual/causal consistency rather than abandoning it.
- PACELC completes CAP: if Partition, trade A vs C; Else, trade Latency vs C — the latency-vs-consistency tension is present in *normal* operation, which dominates the system's life.
- In practice, classify each operation, read a datastore's guarantees as the trade they imply (AP/EL = expect staleness; PC/EC = expect latency), and design partition behavior deliberately rather than by default.

## Further reading

- [Consistency models (previous post)](/blog/posts/distsys-02-consistency-models.html)
- [Jepsen — consistency and CAP in real systems](https://jepsen.io/consistency)
- [Distributed Systems from First Principles — start of the series](/blog/posts/distsys-01-why-distributed-is-hard.html)
