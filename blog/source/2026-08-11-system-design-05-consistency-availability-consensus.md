# Consistency, Availability, and Consensus

*The theory that governs distributed data, made practical — CAP stated correctly, PACELC, the full consistency spectrum with "what the user sees" examples, quorums, and Raft-style consensus without the proofs.*

---

The previous posts in the System Design Fundamentals series left you with a loose thread. Post 2 added read replicas to scale reads and warned that a follower lags the primary, so a read right after a write can return stale data. Post 4 made replication a first-class decision and named the same problem — replication lag — then said the honest answer to "is stale OK?" is a business decision we would take up here. This is that post.

Once your data lives on more than one machine, you cannot have everything. You cannot have every read see the latest write, and always get an answer, and survive the network breaking, all at once. The theorems below are not academic trivia — they are the rules that decide, for every single operation your system serves, what a user is allowed to observe. The goal here is to state those rules correctly (the popular versions are wrong in ways that lead to bad designs) and turn them into choices you make on purpose.

---

## CAP, stated correctly

The CAP theorem is the most cited and most misquoted result in distributed systems. The folklore version — "pick two of three: Consistency, Availability, Partition tolerance" — is misleading enough to cause real design mistakes. Here is what Brewer's result actually says.

The three letters are:

- **C (consistency)** — here it means *linearizability*: every read sees the most recent write, as if there were a single copy of the data. (Note this is a different "C" from the ACID one in transactions.)
- **A (availability)** — every request to a non-failed node gets a non-error response.
- **P (partition tolerance)** — the system keeps working when the network drops or delays messages between nodes.

The correct reading is conditional, not a menu. A **network partition** — some nodes cannot talk to others — is not a design option you can decline. Packets get lost, switches fail, a data center link flaps. Partitions *will* happen. So P is not really on the table to trade away. The real theorem is:

> **When a partition occurs, you must choose between C and A. You cannot have both.**

Picture two replicas that can no longer reach each other, and a write arrives at one of them:

```text
   write "x = 2"
        |
        v
   [ replica A ]   X---network partition---X   [ replica B ]
   (has x = 2)                                  (still has x = 1)
        |                                            |
   a reader hits B and asks for x. Now what?
        |
   +----+---------------------------------------+
   |                                            |
  choose C:                                  choose A:
  B refuses / blocks — it can't confirm      B answers x = 1 —
  it has the latest value. No stale reads,   stays up, but returns
  but B is now unavailable.                  a STALE value.
```

B has two options and only two. It can refuse to answer until it reconnects and confirms it has the newest value (**CP** — consistent, but unavailable during the partition). Or it can answer with the value it has, which might be stale (**AP** — available, but not consistent). There is no third door.

**The gotcha:** "CA" — consistent *and* available while giving up partition tolerance — is not a real runtime choice. You do not get to opt out of partitions; the network decides that for you. A single-node database is trivially "CA" only because it has no network between replicas to partition — the moment you replicate for availability (post 2's whole premise), P is forced on you and the C-vs-A choice is real. So when someone says "we picked CA," what they actually have is a system that is neither C nor A when the network breaks — it just has no defined behavior for the case that will eventually happen.

And crucially: CAP only constrains you **during a partition**. When the network is healthy, you can have both strong consistency and availability. Which is exactly the gap the next theorem fills.

---

## PACELC: the trade-off that never goes away

CAP is silent about normal operation, and normal operation is where your system spends ~99.9% of its life. PACELC (Abadi) extends it to say something about both regimes:

> **If there is a Partition, choose between Availability and Consistency; Else (normal operation), choose between Latency and Consistency.**

The "else" clause is the important addition. Even with a perfectly healthy network, keeping replicas strongly consistent means a write must be acknowledged by other nodes before it counts, and a read must confirm it is not stale. That coordination costs **round trips** — latency. To make a read guaranteed-fresh, you either send it to the one authoritative node or you contact a majority of nodes and wait for the slowest to reply.

So the tension is not a rare failure-mode problem; it is a tax you pay on every request. Systems get classified on both axes:

| System | On Partition | Else (normal) | Character |
|---|---|---|---|
| Default single-leader SQL (sync replica) | PC | EC | Consistency-first, pays latency |
| Dynamo-style (Cassandra, defaults) | PA | EL | Availability + low latency, eventual |
| A strongly-consistent store (e.g. etcd, Spanner) | PC | EC | Consistency at a latency cost, always |

**The gotcha:** teams obsess over the partition case (rare) and forget the "else" case (constant). If your product needs single-digit-millisecond reads at the edge, strong consistency may be off the table *even though the network is fine* — not because of CAP, but because of PACELC's latency term. The cost of "every read is fresh" is paid mostly in latency during the 99.9% when nothing is broken.

---

## The consistency spectrum: what the user actually sees

"Consistent vs eventual" is a false binary. There is a graded spectrum of guarantees, from strongest (and most expensive) to weakest (and cheapest). The only way to reason about them is to ask: *what is a user allowed to observe?* Here they are, strong to weak.

**Strong / linearizable.** There appears to be a single copy of the data, and every operation takes effect at some instant between its call and its return. Once a write completes, *every* reader, everywhere, sees it or something newer. What the user sees: you change your display name and hit save; from that instant, every device and every other user sees the new name. Nobody ever sees the old one again. This is the most intuitive model and the most expensive.

**Sequential consistency.** All nodes agree on a single global *order* of operations, and each process's own operations appear in the order it issued them — but that global order need not match real (wall-clock) time. What the user sees: everyone watching a comment thread sees comments in the same order, and it is a plausible order, but it might not be the exact real-time order in which they were posted.

**Causal consistency.** Operations that are causally related (a reply depends on the message it answers) are seen in that order by everyone; unrelated operations may be seen in different orders on different nodes. What the user sees: nobody ever sees a *reply* before the *message* it replies to. But two unrelated posts from strangers might appear in different orders for you and me. This is often the sweet spot — it forbids the nonsensical orderings while staying cheap.

**Read-your-writes.** A weaker, per-user guarantee: after *you* write something, *your* subsequent reads see it. Other users may still see the old value for a while. What the user sees: you post a comment, refresh, and your comment is there — even if your friend does not see it for another second. This is exactly the fix for post 2's "I changed my name, why does it still show the old one?" complaint.

**Monotonic reads.** Once you have seen a value, you will never see an *older* one on a later read. Time only moves forward for a given reader. What the user sees: you refresh and see 42 likes; a later refresh shows 42 or more, never back down to 41.

**Eventual consistency.** The only promise is that *if writes stop, all replicas eventually converge* to the same value. Until then, anything goes. What the user sees: a like count that reads 41 on one refresh, 43 on the next, 42 on the next — bouncing around before settling.

```text
STRONGER / costlier                                   WEAKER / cheaper
  linearizable → sequential → causal → read-your-writes
                                     → monotonic-reads → eventual
  "everyone sees                                   "everyone agrees
   the latest, now"                                 EVENTUALLY, maybe"
```

**The gotcha:** eventual consistency does not just mean "a bit stale." Without a **monotonic-reads** guarantee layered on top, a reader can go *backwards in time* — see the new value, then the old one again on the next request — because two consecutive reads can land on two different replicas that lag by different amounts. That "likes count went 43 → 42 → 43" flicker is not a UI bug; it is the storage layer showing through. If that is unacceptable, you must ask for monotonic reads explicitly (e.g. by pinning a user's session to one replica).

The practical punchline: **you rarely pick one model for the whole system.** You pick per operation. A bank ledger's balance is linearizable; the "people also viewed" widget is eventual; your own profile edits are read-your-writes. Post 4's advice — decide on purpose, not by accident of your connection pool — is exactly this, applied one query at a time.

---

## Quorums: tuning the dial with R + W > N

Post 4 introduced leaderless (Dynamo-style) replication and mentioned the quorum rule. Here is the mechanism, because it is the clearest example of *tuning* the consistency/availability trade-off with a knob rather than an all-or-nothing switch.

With `N` replicas holding each key, you require every write to be acknowledged by `W` of them and every read to consult `R` of them. If you choose values so that

```text
   R + W > N

   example: N = 3, W = 2, R = 2

   write "x=2" ── ack ──> [R1: x=2]  [R2: x=2]  [R3: x=1 (missed it)]
                                \___________/
                                 W = 2 acks → write succeeds

   read x ── query ──> pick any 2 of 3:
        if the 2 include R1 or R2, you SEE x=2 (with a version/timestamp
        you use to discard the stale x=1). R + W > N guarantees the read
        set and the write set OVERLAP by at least one replica.
```

Because the read set and the write set must share at least one node (that is what `R + W > N` forces), every read is guaranteed to touch at least one replica that saw the latest write, and versioning lets it pick the newest value. That gives you strong-ish reads without a leader.

The knob is which values you pick:

- `W = N, R = 1` — fast reads, slow/fragile writes (a write needs *every* replica up).
- `W = 1, R = N` — fast writes, slow reads.
- `W = R = quorum` (majority) — balanced; survives one node down out of three.

**The gotcha:** `R + W > N` buys you overlap, but it is not free and it is not full linearizability. Every read and every write now needs a *majority* to respond, so a single slow or down replica raises tail latency (you wait for the quorum) and, if enough nodes are unreachable, requests *fail* — you have traded away some availability for the freshness guarantee. Turning the dial toward consistency always turns it away from latency and availability; there is no setting that gives you all three. (And subtle races — a write seen by the read quorum but not yet by a majority — mean quorums approximate strong consistency rather than perfectly guaranteeing it.)

---

## Consensus: agreeing on one value despite failures

Quorums handle "what is the current value of this key." A harder problem sits underneath much of distributed systems: getting a set of machines to **agree on a single value** — a decision, a leader, an ordering — even when some of them crash or messages are lost. That is **consensus**.

You need it whenever the answer has to be *one thing* that everybody honors:

- **Who is the leader?** (single-leader replication must elect one, and exactly one, after the old one dies — otherwise you get split-brain, two primaries accepting conflicting writes).
- **What is the order of these operations?** (a replicated log where every node must apply the same commands in the same sequence).
- **Did this distributed transaction commit or abort?** (everyone must reach the same verdict).
- **What is the current config / who owns this lock?**

The foundational algorithm is **Paxos** (Lamport), which proved consensus is achievable with a majority of nodes even amid failures — but it is famously hard to understand and to implement correctly. **Raft** (Ongaro & Ousterhout) was designed later with the explicit goal of being *understandable*, and it is what most modern systems actually use. Here is Raft at an intuition level.

**Leader election.** Nodes are in one of three roles: follower, candidate, leader. Time is divided into numbered *terms*. A follower that hears nothing from a leader for a randomized timeout becomes a candidate, bumps the term, and asks everyone to vote for it. If it collects votes from a **majority**, it becomes leader. Randomized timeouts make it unlikely two candidates tie repeatedly, so an election converges fast.

**Log replication.** All writes go to the leader. The leader appends each command to its log and ships it to followers.

```text
   client write ──> [ LEADER ]  term 4
                        | append to own log, then replicate
          +-------------+--------------+
          v             v              v
    [follower]     [follower]     [follower(down)]
     ack ✓          ack ✓            (no ack)
          \_____________/
        leader has a MAJORITY (2 of 3 followers + itself)
                → entry is COMMITTED → applied to state machine
                → leader tells client "done" and followers to commit
```

**Commit.** Once a log entry is stored on a majority of nodes, the leader marks it **committed**, applies it to its state machine, and returns success to the client. A crashed follower catches up later by replaying the leader's log. Because a new leader can only be elected by a majority, and any majority overlaps the majority that committed an entry, a committed entry can never be lost — the new leader is guaranteed to have it. That overlap is the same `majority ∩ majority ≠ ∅` idea as quorums, which is not a coincidence.

Note the cost: every committed write waits for a majority round trip. That is PACELC's "else, latency" term showing up at the very bottom of the stack.

**The gotcha:** do not roll your own consensus. It is one of the classic footguns in this field — the edge cases (split votes, network partitions healing, stale leaders that do not yet know they were deposed, log divergence) are exactly where naive implementations silently corrupt data. Use a library or a service that implements Raft/Paxos correctly and has been tested against them. Which is what everyone does — see below.

---

## Where consensus shows up in practice

You will rarely write a consensus algorithm, but you will constantly *use* one, often without noticing:

- **etcd** (Raft) is the consistent key-value store behind Kubernetes — it holds cluster state and config, and is the reference example of "small amount of critical data, must be strongly consistent."
- **ZooKeeper** (Zab, a Paxos-like protocol) plays the same role for the Hadoop/Kafka ecosystem: coordination, config, and naming.
- **Distributed locks and leader election.** "Only one worker should run this cron job" or "only one node is the primary" is a consensus problem. You express it as a lease/lock in etcd or ZooKeeper rather than inventing a locking scheme.
- **Configuration and service discovery.** The single source of truth for "what is the current config" needs every node to agree — a natural fit for a consensus-backed store.
- **Databases with strong guarantees.** Spanner, CockroachDB, and YugabyteDB use Paxos/Raft groups under the hood to keep their replicas linearizable.

The pattern is always the same: keep the *amount* of strongly-consistent, consensus-managed data small (leader identity, config, locks, critical metadata) and layer cheaper consistency models over the bulk of your data. Consensus is expensive, so you concentrate it — the same "push the hard problem into a few purpose-built systems" instinct from post 2.

---

## Key takeaways

- **CAP is about partitions.** "Pick 2 of 3" is wrong. Partitions are not optional, so the real choice is C-vs-A *during* a partition; "CA" is not a runtime option, just undefined behavior for the case that will happen.
- **PACELC completes the picture.** Even with no partition, strong consistency costs latency on every request — the trade-off you pay 99.9% of the time.
- **Consistency is a spectrum, chosen per operation.** Linearizable → causal → read-your-writes → monotonic reads → eventual. Match each to what the user is allowed to see; do not pick one model for the whole system.
- **Eventual consistency can go backwards.** Without monotonic reads, a reader sees new-then-old — a storage artifact, not a UI bug.
- **Quorums (`R + W > N`) are a dial, not a switch** — they force read/write overlap for fresh reads, but every operation now needs a majority, costing latency and availability.
- **Consensus agrees on one value despite failures.** Raft (understandable descendant of Paxos) does it via leader election, log replication, and majority commit. Never roll your own — use etcd, ZooKeeper, or a Raft library.

Strong consistency is not "better." It is a specific, expensive guarantee you buy with latency and availability, one operation at a time. The skill is knowing which operations truly need it — and letting everything else be cheap.

---

## Further reading

- [Brewer, "CAP Twelve Years Later: How the 'Rules' Have Changed" (IEEE, 2012)](https://www.infoq.com/articles/cap-twelve-years-later-how-the-rules-have-changed/) — the author's own correction of the folklore reading.
- [Gilbert & Lynch, "Brewer's Conjecture and the Feasibility of Consistent, Available, Partition-Tolerant Web Services" (2002)](https://groups.csail.mit.edu/tds/papers/Gilbert/Brewer2.pdf) — the formal proof of CAP.
- [Abadi, "Consistency Tradeoffs in Modern Distributed Database System Design" (PACELC, IEEE, 2012)](https://www.cs.umd.edu/~abadi/papers/abadi-pacelc.pdf) — the paper that adds the latency term.
- [Ongaro & Ousterhout, "In Search of an Understandable Consensus Algorithm" (Raft, USENIX ATC 2014)](https://raft.github.io/raft.pdf) — the Raft paper; also see [raft.github.io](https://raft.github.io/) for the visualization.
- [Lamport, "Paxos Made Simple" (2001)](https://lamport.azurewebsites.net/pubs/paxos-simple.pdf) — the accessible statement of the ancestor algorithm.
- [etcd documentation](https://etcd.io/docs/) — a production Raft key-value store; read how it is used for coordination and config.
- [Jepsen analyses](https://jepsen.io/analyses) — empirical testing of real databases' consistency claims under partitions; the best cure for hand-wavy guarantees.
