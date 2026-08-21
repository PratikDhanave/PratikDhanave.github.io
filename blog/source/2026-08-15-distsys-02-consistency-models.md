# Consistency Models

*A consistency model is a contract between a distributed system and its users about what a read is allowed to return. It sounds abstract until you realize that every replication bug, every "why did my write disappear?" incident, and every heated architecture debate is really an argument about which model you're entitled to.*

Once data lives on more than one node, "what value will a read return?" stops having an obvious answer. If you just wrote `x = 2`, can another client — or even you, from a different connection — still read `x = 1`? A **consistency model** answers exactly that: it's the formal contract for what reads may return given the writes that have happened. Choosing one is choosing how much reality your system guarantees versus how fast and available it can be. This post builds the ladder of models from strongest to weakest.

## Why we need a contract at all

With one copy of the data, consistency is free: reads see the latest write because there's only one place the data lives. With replicas, a write must propagate, and propagation takes time. During that window, different replicas hold different values, and a read's answer depends on *which replica it hits*. Without a stated model, "correct" is undefined and every developer assumes the strongest guarantee (that reads see the latest write) — which the system may not actually provide. The consistency model makes the guarantee explicit so you can reason about it instead of being surprised by it.

## Linearizability: behave like one copy

**Linearizability** (strong consistency) is the gold standard: the system behaves *as if there were a single copy of the data*, and every operation appears to take effect atomically at some instant between its start and its completion. The consequence that matters: once a write completes, **every** subsequent read (from any client) returns that write or a later one — stale reads are impossible. There is a single, real-time-respecting order everyone agrees on.

This is the model humans intuitively expect, and it's what you want for things like a unique-username check, a lock, or a leader election. But it's expensive: to guarantee no read ever sees a stale value, replicas must coordinate on every operation, which costs latency and — critically — availability when the network partitions (the subject of the next post). Linearizability is correctness at its strongest and cheapest to reason about, but the hardest to provide.

## Sequential and causal consistency: relaxing real time

Below linearizability sit weaker-but-useful models that drop the *real-time* requirement while keeping *some* order:

- **Sequential consistency** — all clients see operations in the *same single order*, and each client's own operations appear in the order it issued them — but that global order need not match real time. Two clients agree on the sequence of events; they just might collectively "agree" on a version of history that lags reality.
- **Causal consistency** — the system preserves *cause-and-effect* order: if operation B could have been influenced by operation A (you read a post, then reply to it), everyone sees A before B. Operations with no causal relationship may be seen in different orders on different nodes. Causal consistency is a sweet spot: it rules out the maddening anomalies (seeing a reply before the message it answers) while remaining achievable with high availability, because unrelated operations don't need coordination.

The pattern: as you weaken the model, you give up agreement on *when* and on *unrelated* events, buying performance and availability, while trying to keep the guarantees that actually prevent user-visible nonsense.

## Eventual consistency: the weakest useful promise

**Eventual consistency** promises only this: if writes stop, all replicas will *eventually* converge to the same value. It says nothing about *when*, and nothing about what you read in the meantime — a read can return stale data, and two reads can even go backward. That sounds barely like a guarantee, and used carelessly it produces exactly the "my write vanished, then came back" bugs users hate.

Yet eventual consistency underpins many of the largest, most available systems in the world, because it never has to block: any replica can accept a read or write immediately and reconcile later. The trick to using it well is to layer *session guarantees* on top so a single user's experience stays sane even while the global system is loosely coupled:

- **Read-your-writes** — you always see your own latest write (even if others don't yet).
- **Monotonic reads** — you never see time go backward: once you've read a value, you won't later read an older one.
- **Monotonic writes / writes-follow-reads** — your own writes apply in order, and a write you make after reading something lands after what you read.

These per-client guarantees are what make an eventually-consistent system *feel* consistent to each user, and they're far cheaper than global linearizability.

## Choosing a model

The model isn't a global setting you pick once — it's a per-operation decision driven by what breaks if a read is stale:

- **Needs linearizability:** anything where a stale read causes incorrectness you can't undo — locks, leader election, uniqueness constraints, "is this seat/inventory still available?", account balances that must not go negative.
- **Causal or session guarantees suffice:** collaborative and social features — comments, messaging, feeds — where cause-and-effect must hold but global real-time order doesn't.
- **Eventual is fine:** high-volume, low-stakes state where availability and speed dominate and brief staleness is harmless — view counts, likes, caches, presence, recommendations.

The engineering skill is matching the model to the operation: pay for strong consistency exactly where correctness demands it, and take the availability and performance of weaker models everywhere else. The next post shows *why* you're forced to make this trade at all — the CAP theorem.

## Key takeaways

- A consistency model is the contract for what a read may return given prior writes; with replicas, "correct" is undefined until you state it, so the model makes the guarantee explicit.
- Linearizability (strong) makes the system behave like one copy with real-time ordering — no stale reads ever — which is the easiest to reason about but the most expensive in latency and availability.
- Sequential and causal consistency relax real-time ordering: sequential keeps one global order, causal preserves cause-and-effect while allowing unrelated operations to be reordered — a high-availability sweet spot.
- Eventual consistency promises only that replicas converge when writes stop; session guarantees (read-your-writes, monotonic reads/writes) layered on top make it feel sane per user at low cost.
- Choose the model per operation: linearizability where stale reads cause unrecoverable incorrectness (locks, uniqueness, balances); causal/session for collaborative features; eventual for high-volume low-stakes state.

## Further reading

- [Jepsen — consistency models map](https://jepsen.io/consistency)
- [Distributed Systems from First Principles — start of the series](/blog/posts/distsys-01-why-distributed-is-hard.html)
- [System Design Fundamentals series](/blog/series/system-design-fundamentals/)
