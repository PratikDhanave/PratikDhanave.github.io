# Consensus and Raft

*Consensus is the problem of getting a group of unreliable machines to agree on a single value despite crashes, delays, and lost messages. It sounds narrow, but it's the hidden foundation under leader election, distributed locks, configuration, and every "exactly one node is in charge" guarantee. Raft is the algorithm that finally made it understandable.*

Almost every hard problem in the earlier posts reduced to the same underlying need: the nodes must **agree**. Who is the leader? In what order do operations apply? Is this partition still allowed to serve writes? **Consensus** is that problem stated precisely — getting multiple nodes to agree on a value such that they all decide the same thing and never un-decide it — and it must work despite the partial failure that defines the whole field. This post explains what consensus guarantees and how **Raft** achieves it.

## What consensus must guarantee

A consensus algorithm lets a set of nodes agree on a value (or a sequence of values) with these properties, even when some nodes crash and messages are lost or delayed:

- **Agreement** — no two nodes decide different values. This is the whole point: one truth, not several.
- **Validity** — the agreed value was actually proposed by some node (no inventing values).
- **Termination** — non-failed nodes eventually decide (the algorithm makes progress).

The reason consensus is hard is the reason the whole series is hard: a node can't tell a crashed peer from a slow one, so it can never simply "wait for everyone." Consensus algorithms get around this with **majorities** — decisions require agreement from more than half the nodes — which is the single idea that makes everything else work.

## The majority (quorum) principle

The foundational trick of modern consensus is that any decision requires a **majority** (a quorum) of the nodes. With a cluster of N nodes, a majority is ⌊N/2⌋ + 1 — 3 of 5, 2 of 3. This one rule delivers two critical properties:

- **Any two majorities overlap.** Two different majorities of the same cluster must share at least one node. That shared node prevents two conflicting decisions from both succeeding — it's the mechanism behind Agreement, and the same overlap idea as the read/write quorums from the [replication](/blog/posts/distsys-05-replication.html) post.
- **The system tolerates a minority failing.** A 5-node cluster keeps working with 2 nodes down (3 remain, a majority); a 3-node cluster tolerates 1 failure. To tolerate F failures you need **2F + 1** nodes.

The majority rule is also why consensus clusters use *odd* numbers of nodes: 5 nodes tolerate 2 failures, and so do 6 — the extra node adds cost without adding fault tolerance, because a majority of 6 is 4 (tolerating 2) just like 5.

Crucially, majorities are what make consensus **safe under partition**. If the network splits the cluster, at most *one* side can hold a majority, so at most one side can make decisions — the minority side stops rather than diverging. That is consensus enforcing the CP side of CAP: it sacrifices availability on the minority partition to never violate agreement.

## Raft: consensus you can understand

Consensus algorithms were long dominated by Paxos, which is famously hard to understand and implement correctly. **Raft** was designed explicitly for *understandability* and decomposes consensus into three digestible pieces: **leader election**, **log replication**, and **safety**. Every node is in one of three states — **follower**, **candidate**, or **leader** — and time is divided into numbered **terms**, each with at most one leader.

### Leader election

Raft has exactly one leader at a time, and all client requests go through it. Followers expect regular **heartbeats** from the leader. If a follower hears nothing for an *election timeout*, it assumes the leader is dead, becomes a **candidate**, increments the term, votes for itself, and asks the others for their votes.

- A node grants its vote to at most one candidate per term (and only if the candidate's log is at least as up-to-date as its own).
- A candidate that collects votes from a **majority** becomes leader and starts sending heartbeats.
- If no one wins (split vote), the term ends with no leader and a new election starts. Raft uses *randomized* election timeouts so nodes rarely time out simultaneously, making split votes resolve quickly.

The majority requirement guarantees at most one leader per term (two leaders would need two overlapping majorities, impossible), and it means a partitioned minority can never elect a leader — so it can't accept writes.

### Log replication

Once elected, the leader serves client operations by appending them to its **log** and replicating entries to followers:

```text
Client → Leader: append entry
Leader: append to own log, send to followers
Followers: append, acknowledge
Leader: once a MAJORITY have the entry → "committed" → apply it, reply to client
```

An entry is **committed** only once a majority of nodes have stored it. Committed entries are then applied to each node's state machine *in the same order*, which is what gives every node an identical, consistent view — this is the "single order of operations everyone agrees on" that consistency models needed. Because commitment requires a majority, a committed entry survives the failure of any minority of nodes.

### Safety

Raft's safety rules ensure agreement is never violated even across leader changes: a candidate can only win if its log is at least as current as the majority that elects it, which guarantees a new leader already has every committed entry — so committed operations are never lost or reordered when leadership changes. This is the property that makes Raft *correct*, not just live.

## Where consensus actually lives

You rarely implement Raft yourself; you use it through the systems built on it. Consensus is the engine inside:

- **Coordination services** — etcd and ZooKeeper provide consensus-backed storage for configuration, service discovery, and **distributed locks**; Kubernetes stores all its cluster state in etcd.
- **Leader election / failover** — the "promote a follower when the leader dies" step from the replication post is a consensus decision, so the cluster never ends up with two leaders (split brain).
- **Strongly consistent databases** — systems needing linearizability use consensus (Raft/Paxos/variants) to agree on the commit order of transactions.

The practical guidance: **don't build consensus from scratch** — it's subtle, and the safety edge cases are exactly where hand-rolled implementations fail. Delegate agreement to a proven system (etcd/ZooKeeper) or a database that embeds a proven algorithm. Understand consensus deeply so you know *what it costs* (a majority must be reachable, so it's a CP building block that trades availability for correctness) and *when you need it* (anywhere "exactly one" or "single agreed order" must hold) — then reach for a battle-tested implementation.

## Key takeaways

- Consensus is getting unreliable nodes to agree on a value with Agreement (no two decide differently), Validity (agreed value was proposed), and Termination (progress) — despite crashes and lost messages.
- The core mechanism is majority (quorum) decisions: any two majorities overlap (preventing conflicting decisions) and a cluster of 2F+1 nodes tolerates F failures — which is why consensus clusters use odd node counts.
- Majorities make consensus safe under partition: at most one side of a split holds a majority, so the minority stops rather than diverging — consensus is a CP building block trading availability for correctness.
- Raft decomposes consensus for understandability: leader election (randomized timeouts, one leader per term via majority vote), log replication (an entry commits once a majority store it, then applies in order), and safety rules that preserve committed entries across leader changes.
- Don't implement consensus yourself — use it through etcd/ZooKeeper (config, locks, leader election) or consensus-backed databases; understand its cost and when "exactly one" or a single agreed order is required.

## Further reading

- [Raft — "In Search of an Understandable Consensus Algorithm" (Ongaro & Ousterhout)](https://raft.github.io/raft.pdf)
- [The Raft site — visualization and implementations](https://raft.github.io/)
- [Replication (previous post)](/blog/posts/distsys-05-replication.html)
