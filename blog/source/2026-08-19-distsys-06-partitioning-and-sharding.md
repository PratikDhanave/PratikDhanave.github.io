# Partitioning and Sharding

*Replication makes copies of the whole dataset; partitioning splits the dataset into pieces so each node holds only some of it. Every large-scale system does both — and the way you choose which piece goes where quietly determines whether your load spreads evenly or one unlucky node melts down under a celebrity's traffic.*

Replication solves availability and read scaling, but it doesn't solve *size*: every replica still holds the entire dataset, so when the data outgrows a single machine, copies don't help. **Partitioning** (also called **sharding**) is the answer — split the data into partitions and place each on a different node, so the total dataset and write load scale beyond one machine. This post covers how to split data, how partitioning combines with replication, and the failure mode that dominates in practice: the hot partition.

## Why partition

Partitioning exists to break through single-node limits that replication can't:

- **Storage** — a dataset too large for one machine's disk must be divided across many.
- **Write throughput** — a single leader can only absorb so many writes; partitioning spreads writes across independent nodes, each the leader for its own slice.
- **Parallelism** — queries and processing can run across partitions concurrently.

The goal is **balance**: spread data and load evenly so no single node becomes the bottleneck. A partitioning scheme that puts too much data or too much traffic on one node — a *skew* — defeats the entire purpose, because the system is only as fast as its busiest partition.

## Partition by key range

The first scheme assigns a *contiguous range* of keys to each partition — like volumes of an encyclopedia (A–C, D–F, …).

- **Strength:** range queries are efficient — keys that are near each other live on the same partition, so "give me all orders from last Tuesday" hits one partition, not all of them.
- **Weakness:** ranges cause **hot spots** when access isn't uniform across the key space. The classic example is a timestamp key: if you partition by time, *all* current writes land on the single partition holding "now," while the historical partitions sit idle. The scheme concentrates load exactly where activity concentrates.

Range partitioning is the right choice when you need range scans *and* your access is reasonably spread across the key space — but you must choose the partition key to avoid the monotonically-increasing-key trap.

## Partition by hash of key

The second scheme runs each key through a hash function and assigns partitions by hash value. Because a good hash scatters even similar keys uniformly, this **spreads load evenly** and eliminates the monotonic-key hot spot — sequential timestamps hash to entirely different partitions.

The trade is the mirror image of range partitioning: **range queries become inefficient**, because adjacent keys are deliberately scattered across all partitions, so a range scan must query every partition and merge. Hash partitioning is the default for point-access workloads (look up by ID) where even load matters more than range scans — which is most key-value and many document workloads.

A subtlety: naively using `hash(key) mod N` breaks badly when N changes, because adding or removing a node remaps *almost every* key, triggering a massive reshuffle. **Consistent hashing** (and range-based rebalancing schemes) solve this by moving only a small fraction of keys when the node count changes — essential for a system that must grow and shrink without a full reshard.

## Partitioning meets replication

Partitioning and replication are **orthogonal and used together**, not alternatives. Each partition is *itself* replicated across several nodes for fault tolerance. So a node typically holds *some* partitions as leader and *other* partitions as follower — leadership is spread across the cluster rather than concentrated:

```text
              Partition P1        Partition P2        Partition P3
Node A     leader(P1)          follower(P2)        follower(P3)
Node B     follower(P1)        leader(P2)          follower(P3)
Node C     follower(P1)        follower(P2)        leader(P3)
```

This combination is what production systems actually run: partitioning gives you scale (each node handles a slice), replication gives each slice fault tolerance, and spreading leadership balances the write load. The consistency and consensus concerns from earlier posts apply *per partition* — each partition is its own little single-leader (or quorum) group.

## The hot partition problem

The failure mode that dominates real systems is the **hot partition** (hot spot): one partition receives disproportionate load while others idle, so the system is bottlenecked on a single node despite all your sharding. Even perfect hash partitioning by *key* can't fix it, because the skew is often in a *single key's* traffic:

- A **celebrity user** whose posts are read by millions — all that read traffic hits the one partition holding that user's data.
- A **viral item** — one product, one video, one hashtag — concentrating writes/reads on its partition.

The lesson is that partitioning balances *keys*, but load can concentrate on *one key*, and no key-level scheme divides a single key across partitions. Mitigations exist but cost something: **add a random suffix** to a hot key to split it across partitions (at the cost of having to read/merge all the splits), **cache** hot keys in front of storage, or **replicate** hot partitions more widely for reads. The key engineering habit is to *anticipate* skew — assume some keys will be far hotter than others — and design the partition key and mitigations accordingly, rather than assuming uniform load and discovering the hot spot during an incident.

## Choosing a scheme

- **Range partitioning** — when range scans matter and access is spread across the key space; avoid monotonically increasing partition keys (timestamps, auto-increment IDs) that create a single write hot spot.
- **Hash partitioning** — the default for point-access workloads needing even load; pair it with consistent hashing so rebalancing moves few keys. Accept that range scans now fan out to all partitions.
- **Always combine with replication** — partition for scale, replicate each partition for fault tolerance, spread leadership for balance.
- **Design for skew from day one** — expect hot keys; choose partition keys, caching, and key-splitting to keep a single popular entity from melting one node.

Partitioning gives you scale; replication gives you survival; and both, per partition, rely on nodes agreeing on who leads and in what order operations apply. That agreement — consensus — is the next and central post.

## Key takeaways

- Partitioning (sharding) splits the dataset into pieces across nodes so total size and write throughput scale past a single machine — solving the size problem replication can't.
- Range partitioning (contiguous key ranges) makes range scans efficient but creates hot spots on monotonic keys like timestamps; hash partitioning spreads load evenly but scatters ranges, so scans fan out to all partitions.
- Use consistent hashing (not `hash mod N`) so growing or shrinking the cluster moves only a small fraction of keys instead of triggering a full reshuffle.
- Partitioning and replication are orthogonal and combined: each partition is replicated, and a node is leader for some partitions and follower for others, spreading write load across the cluster.
- The dominant real-world failure is the hot partition — a single celebrity/viral key concentrating load on one node; anticipate skew and mitigate with key-splitting, caching, or wider read replication, because no key-level scheme splits a single key.

## Further reading

- [Consistent hashing (overview)](https://en.wikipedia.org/wiki/Consistent_hashing)
- [Replication (previous post)](/blog/posts/distsys-05-replication.html)
- [System Design Fundamentals series](/blog/series/system-design-fundamentals/)
