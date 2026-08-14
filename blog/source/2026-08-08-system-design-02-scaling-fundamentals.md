# Scaling Fundamentals

*How systems grow under load — vertical vs horizontal scaling, why statelessness is the real enabler, load balancing from L4 to L7, consistent hashing, read/write scaling, the scale cube, and when the honest answer is "don't scale yet."*

---

Scaling is the art of serving more work without the system falling over. That "more" can be requests per second, concurrent users, data volume, or geographic spread — and each pulls in a slightly different direction. The instinct is to reach for a bigger machine or more machines, but the interesting decisions happen *before* that: what has to be true about your service so that adding capacity actually helps. This post walks the fundamentals — the two axes of scaling, the property that makes one of them possible, and the routing layer that ties it together — while being honest about the failure modes each choice drags in.

Every technique here is a trade. There is no free capacity; you are always exchanging simplicity for headroom, or consistency for throughput. The goal is to know *which* trade you are making, on purpose.

---

## Two axes: scaling up vs scaling out

There are exactly two ways to add capacity, and everything else is a refinement of one of them.

**Vertical scaling (scale up)** means making one machine more powerful — more CPU cores, more RAM, faster disks. Your code and topology don't change; the box just gets bigger. It is the least disruptive option and, for a huge range of workloads, the correct first move.

**Horizontal scaling (scale out)** means adding more machines and spreading the work across them. Instead of one 64-core box, you run eight 8-core boxes behind a load balancer.

```text
   Vertical (scale up)              Horizontal (scale out)

      +-----------+              +------+  +------+  +------+
      |           |              | node |  | node |  | node |
      |  bigger   |              +------+  +------+  +------+
      |    box    |                  \        |        /
      |           |                   \       |       /
      +-----------+                    +--------------+
                                       | load balancer|
                                       +--------------+
```

Vertical scaling is limited by physics and economics. There is a largest machine you can buy, and the price curve bends sharply upward near the top — the last increment of capacity on a single box costs far more than the first. You also inherit a single point of failure: one box, one fate. When it reboots, everyone waits.

Horizontal scaling has no such ceiling in principle — you keep adding commodity nodes — and it lets you tolerate the loss of any single node. That is why, past a certain point, horizontal wins: it is the only path to both very high capacity and high availability at a sane cost.

**The gotcha:** horizontal scaling is not free capacity you flip on. It introduces coordination, network partitions, partial failures, and the need for a routing layer — a whole class of problems a single box never has. Vertical scaling stays *simple*; horizontal scaling buys *headroom and resilience* at the cost of distributed-systems complexity. Reach for out only when up runs out.

---

## Statelessness: the property that makes scale-out work

Here is the fact that surprises people: adding more nodes only helps if **any node can serve any request**. The moment a request *must* land on one specific node — because that node is holding data the request needs — your fleet stops being interchangeable and horizontal scaling quietly breaks.

A **stateless** service keeps no client-specific state in the node's own memory between requests. Everything the request needs is either carried in the request itself or fetched from a shared backing store. The node is a pure function: request in, response out, nothing remembered.

```text
   Stateful node (bad for scale-out)     Stateless node (good)

   request --> [ node holds your        request --> [ node ] --+
                 session in RAM ]                    [ node ] --+--> shared
                 you're stuck here                   [ node ] --+    store
                                                                    (session/
                                                                     cache/DB)
```

The move is to **externalize state**: push sessions, carts, and progress into a shared store — a cache like Redis, a database, or a signed token the client carries (a JWT-style cookie). Now every node sees the same truth, so the load balancer can send request N+1 to a different node than request N without anyone noticing.

The classic anti-pattern is the **sticky session** (session affinity): the load balancer pins each client to the node that first served them, because that node holds their session in local memory. It works — until it doesn't. When that node dies, everyone pinned to it loses their session. When you add nodes, the new ones sit idle while old ones stay hot, because existing users are glued elsewhere. During a deploy, draining a node logs its users out.

**The gotcha:** horizontal scaling only works if the service is stateless, or its state is externalized to a shared store. Sticky sessions *look* like they solve the problem, but they re-couple a client to a specific node — reintroducing the single-point-of-failure and uneven-load problems you scaled out to escape. Use affinity as a stopgap, not an architecture; the real fix is to get the state out of the node.

---

## Load balancing: the front door to a fleet

Once you have many interchangeable nodes, something has to decide which node each request goes to. That is the **load balancer** (LB). It presents a single address to the world and fans traffic across the pool behind it, removing dead nodes and rebalancing as the fleet changes.

### L4 vs L7

Load balancers operate at one of two layers, and the difference is how much they understand about the traffic.

An **L4 (transport-layer)** balancer routes on IP addresses and TCP/UDP ports. It doesn't parse the payload — it just forwards connections. This makes it extremely fast and protocol-agnostic, but it can't make decisions based on request content.

An **L7 (application-layer)** balancer terminates the connection and reads the actual request — HTTP method, path, headers, cookies. That lets it route `/api/` to one pool and `/images/` to another, retry failed requests, terminate TLS, and rewrite headers. It does more work per request, so it costs more CPU, but it enables far richer routing.

```text
   L4: routes on IP:port           L7: routes on request content

   conn --> [ pick a node ]        GET /api/users --> [ api pool ]
            no idea what's         GET /img/logo  --> [ static pool ]
            inside the bytes       reads method/path/headers/cookies
```

A common pattern is both: a fast L4 layer at the edge for raw throughput and DDoS absorption, feeding L7 balancers that do the smart routing.

### Balancing algorithms

The LB needs a rule for picking a node:

- **Round-robin** — hand requests to nodes in rotation. Simple and fair when every request costs about the same and every node is identical.
- **Least-connections** — send the next request to the node with the fewest active connections. Better when request durations vary wildly, because it naturally avoids piling long requests onto a busy node.
- **Consistent hashing** — hash a key (client IP, user ID, cache key) to a point on a ring and route to the next node clockwise. This makes routing *stable*: the same key keeps landing on the same node even as the pool changes.

### Health checks

None of this matters if the LB keeps sending traffic to a dead node. **Health checks** are periodic probes — a TCP connect, or an L7 `GET /healthz` — that mark a node in or out of rotation. A good health endpoint checks the node's real dependencies (can it reach the database?), not just "is the process alive," so a node that can't actually serve requests gets pulled before users hit it.

**The gotcha:** the load balancer you added to remove the single point of failure *is itself* a single point of failure until you make it redundant. Run at least two LBs with automatic failover (a floating/virtual IP, DNS failover, or a managed LB that's replicated across zones for you). A single LB in front of a hundred healthy nodes still means one bad box takes the whole site down.

---

## Why consistent hashing matters

Suppose you have a cache spread across N nodes and you pick the node for a key with `hash(key) % N`. It works perfectly — until N changes. Add or remove a single node and `% N` becomes `% (N+1)`, which remaps *almost every key* to a different node. For a cache, that means a near-total miss storm: every lookup misses, everything stampedes the database at once, and the "small" act of adding one node can knock the system over.

**Consistent hashing** fixes this. Instead of mapping keys directly to node indices, you map both keys and nodes onto the same abstract ring (say, 0 to 2³²−1). A key is served by the first node found walking clockwise from the key's position. When a node joins or leaves, only the keys between it and its neighbor move — roughly `1/N` of the keys — instead of all of them.

```text
   modulo hashing, N: 4 -> 5        consistent hashing, node added
   ~100% of keys remap             only ~1/N of keys move

   key -> hash % 4  ==> node 2     ring:  A ....... B ..X.. C ..... A
   key -> hash % 5  ==> node 0            adding X steals only the
   (moved for almost every key)           slice just before it
```

Real implementations add **virtual nodes**: each physical node is placed at many points on the ring, which smooths out the otherwise lumpy distribution and lets you weight bigger nodes with more points. This is the backbone of distributed caches and of **sharding** — deciding which partition owns which data — precisely because it keeps data movement proportional to the change, not catastrophic.

**The gotcha:** consistent hashing minimizes reshuffling when nodes change; naive `hash % N` remaps almost everything and triggers a cache stampede on the very node event (a scale-up or a node failure) you were trying to survive. Any time routing decisions must stay stable across a changing pool — caches, shards, session stores — consistent hashing (with virtual nodes) is the default, not an optimization.

---

## Read scaling vs write scaling

Not all load is symmetric. Most systems read far more than they write, and the two scale very differently.

**Reads** scale out gracefully. Add **read replicas** — copies of the database that receive a stream of changes from the primary — and fan read queries across them. Ten replicas, roughly ten times the read throughput. Because reads don't mutate anything, spreading them is safe.

```text
                 writes
   client ----------------> [ PRIMARY ] --replication--> [ replica 1 ]
   client --reads-->  <----                          --> [ replica 2 ]
                      any replica                     --> [ replica 3 ]
```

**Writes** are the hard part. Every write must ultimately be reconciled into a single authoritative copy so the data stays correct — you can't have two nodes independently deciding the balance of the same account. That funnels writes through a bottleneck (a primary), and adding read replicas does *nothing* to relieve it. Getting past the write ceiling means partitioning the data so different keys live on different primaries (sharding), which we foreshadow here and take up properly in the databases post.

**The gotcha:** scaling reads with replicas introduces **replication lag** — a replica is always a little behind the primary, so a read right after a write can return stale data ("I just changed my name, why does it still show the old one?"). This is a consistency problem, not a free win: you've traded read throughput for the guarantee that every read reflects the latest write. Route reads that must be current back to the primary (read-your-writes), and accept eventual consistency only where the app can tolerate it. We dig into consistency models in a later post.

---

## Stateless vs stateful services

It's worth naming the distinction directly, because real systems are a mix.

**Stateless services** — API servers, web front-ends, workers that pull from a queue — are the easy case. Scale them out freely, replace nodes at will, deploy by rolling nodes in and out. They hold no truth that would be lost when a node dies.

**Stateful services** — databases, caches, message brokers, anything that *owns* data — can't be treated as interchangeable, because each node holds a distinct slice of reality. Scaling them means replication (for availability) and partitioning (for capacity), plus a story for leader election and failover. This is genuinely harder, which is exactly why the dominant architectural pattern is to **push all the state down into a small number of purpose-built stateful systems** and keep everything in front of them stateless. You concentrate the hard problem so the rest of the fleet stays trivially scalable.

---

## The scale cube: three independent axes

A useful mental model (popularized in *The Art of Scalability*) is that you can scale along three independent directions, often visualized as a cube:

```text
        data partitioning (Z)
              ^
              |
              |
              +--------> horizontal duplication (X)
             /
            /
           v
    functional decomposition (Y)
```

- **X-axis — horizontal duplication.** Run N identical copies behind a load balancer. This is plain scale-out, and it's what everything above has been about. Cheap and effective until a single instance can no longer hold the whole dataset or the whole workload.
- **Y-axis — functional decomposition.** Split the system by *what it does* — separate the payments service from the search service from the notification service. Each can scale, deploy, and fail independently. This is the intuition behind service-oriented and microservice architectures.
- **Z-axis — data partitioning (sharding).** Split by *which data* — users A–M on one shard, N–Z on another, or partition by region. Each shard handles a slice of the data and traffic, which is how you finally get past the write bottleneck.

You rarely pick just one. A mature system duplicates stateless services (X), splits along team and domain boundaries (Y), and shards the data that outgrew a single primary (Z) — usually in that order of adoption, because each step adds operational cost.

---

## Knowing when *not* to scale

The most valuable scaling skill is restraint. Every step toward distribution adds failure modes: network calls that time out, caches that go stale, replicas that lag, coordination that deadlocks, and the operational burden of running it all. A single big box has *none* of these — when it's up, it's simply correct.

Modern hardware is enormous. A single server with tens of cores and hundreds of gigabytes of RAM can serve a very large amount of traffic and hold a surprisingly big dataset entirely in memory. Many teams distribute prematurely, chasing a scale they don't have, and end up with a system that is both slower (network hops everywhere) and less reliable (more moving parts) than the monolith it replaced — while spending their engineering time debugging distributed failures instead of shipping features.

The disciplined path:

- **Measure before you scale.** Find the actual bottleneck with profiling and load tests. It's often a missing index or an N+1 query, not a lack of machines — and no amount of horizontal scaling fixes a slow query, it just multiplies it.
- **Scale up first.** A bigger box buys time with near-zero added complexity. Use that time to fix the real bottleneck.
- **Make it stateless early.** This is the one piece of "scaling" work worth doing *before* you need it, because it's cheap to design in and painful to retrofit. Externalizing state keeps the door to horizontal scaling open without forcing you through it.
- **Scale out when up runs out** — when you've hit the machine ceiling, or when availability (surviving a node loss) demands more than one node regardless of load.

**The gotcha:** premature distribution adds failure modes without adding value. A single well-provisioned box is fine far longer than architecture-astronaut instinct suggests, and it's dramatically easier to reason about, debug, and operate. Scale out because the numbers force you to, not because distributed systems feel more serious.

---

## Choosing your scaling move

| Situation | First move | Why |
|---|---|---|
| Traffic rising, one box coping | Scale up (bigger box) | Simplest, no new failure modes |
| Need to survive a node failure | Scale out (≥2 nodes + LB) | Availability, not just capacity |
| Sessions pinned to nodes | Externalize state, drop stickiness | Makes nodes interchangeable |
| Read-heavy, primary strained on reads | Add read replicas | Reads fan out cheaply |
| Write throughput maxed out | Shard (Z-axis) | Only way past the write bottleneck |
| Cache/shard pool changing | Consistent hashing + vnodes | Minimizes key reshuffling |
| Growing team, tangled monolith | Functional split (Y-axis) | Independent scaling and deploys |
| Not sure where the limit is | Measure first | The bottleneck is rarely "more boxes" |

---

## Key takeaways

- **Two axes, one preference.** Scale *up* for simplicity, scale *out* for headroom and resilience. Up is the right first move; out is the only path past the single-box ceiling.
- **Statelessness is the enabler.** Horizontal scaling works only when any node can serve any request — externalize state, and treat sticky sessions as a stopgap that quietly re-couples clients to nodes.
- **The load balancer is critical infrastructure.** Choose L4 for raw speed, L7 for content-aware routing; pick an algorithm that fits your traffic; health-check real dependencies; and never run just one LB.
- **Consistent hashing keeps routing stable.** Naive modulo hashing remaps almost everything when the pool changes; consistent hashing (with virtual nodes) moves only ~1/N of the keys — essential for caches and shards.
- **Reads and writes scale differently.** Replicas fan reads out but introduce replication lag (stale reads); writes bottleneck on the primary until you shard.
- **Scale deliberately.** The scale cube (duplicate, decompose, partition) shows your options, but a single big box is fine longer than you think — measure, scale up, stay stateless, and only then scale out.

The through-line: adding capacity is easy; keeping the system *correct* while you add it is the real work. Statelessness, stable routing, and honest measurement are what make growth boring — which is exactly what you want. The next posts take up the pieces this one foreshadowed: databases and sharding, then the consistency models that decide how stale a read is allowed to be.

---

## Further reading

- [Consistent Hashing and Random Trees (Karger et al., 1997)](https://www.cs.princeton.edu/courses/archive/fall09/cos518/papers/chash.pdf) — the original paper that introduced consistent hashing for distributed caching.
- [Google SRE Book — Load Balancing at the Frontend](https://sre.google/sre-book/load-balancing-frontend/) and [Handling Overload](https://sre.google/sre-book/handling-overload/) — how Google reasons about distributing traffic and shedding load.
- [NGINX — HTTP Load Balancing guide](https://docs.nginx.com/nginx/admin-guide/load-balancer/http-load-balancer/) — round-robin, least-connections, and hash-based methods explained with real config.
- [Envoy — Load Balancing architecture overview](https://www.envoyproxy.io/docs/envoy/latest/intro/arch_overview/upstream/load_balancing/overview) — L7 balancing, health checking, and the algorithms in a modern proxy.
- [AWS — Elastic Load Balancing product comparison](https://aws.amazon.com/elasticloadbalancing/features/) — the practical distinction between L4 (Network Load Balancer) and L7 (Application Load Balancer).
- [Amazon DynamoDB paper (Dynamo, 2007)](https://www.allthingsdistributed.com/files/amazon-dynamo-sosp2007.pdf) — consistent hashing with virtual nodes and replication applied at production scale.
