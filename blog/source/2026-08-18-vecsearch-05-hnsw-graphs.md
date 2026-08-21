# HNSW: Navigable Small World Graphs

*HNSW is the algorithm behind most modern vector databases, and its idea is borrowed from the "six degrees of separation" that connects any two people through a short chain of acquaintances. Build the right graph of vectors, and you can walk from a random entry point to a query's nearest neighbors in a handful of hops — searching millions of vectors while touching only a few hundred.*

IVF beats brute force by partitioning space. **HNSW** — Hierarchical Navigable Small World graphs — beats it a different way: by building a graph you can *navigate* greedily toward any query's neighborhood. It typically achieves higher recall at the same latency than IVF, which is why it's the default index in most vector databases. This post explains the small-world idea, the hierarchy that makes it fast, and the parameters that control its trade-offs.

## The small-world idea

Imagine a graph where each vector is a node connected to some of its nearest neighbors. To find the neighbors of a query, you could start at any node and *greedily walk*: repeatedly move to whichever neighbor is closest to the query, until you can't get closer. On a purely local graph (only short-range links), this walk is slow — you shuffle step by tiny step across the space, like traveling the world one town at a time.

The **small-world** insight fixes this. Real social networks connect any two people in a short chain ("six degrees of separation") because, alongside many *local* connections, there are a few *long-range* ones. A graph with both short- and long-range links is a **navigable small world**: the long-range links let a greedy walk take big jumps across the space to get near the target fast, then the short-range links refine to the exact neighborhood. That combination — long hops to approach, short hops to home in — lets you reach any query's vicinity in a small number of steps even in a huge graph.

## The hierarchy: the "H" in HNSW

HNSW adds a **hierarchy** of layers to make the "big jump, then refine" structure explicit and efficient — the idea that gives it the edge over a flat navigable graph. Think of it like a transport network with express and local layers:

```text
Layer 2 (sparse):   A ─────────────── D          few nodes, long links
                     │                 │
Layer 1 (medium):   A ──── B ───── C ─ D          more nodes, medium links
                     │      │       │   │
Layer 0 (all nodes): A-B-C-D-E-F-G-...           every vector, short links
```

- **Higher layers are sparse** — few nodes, long-range links. Searching starts here and covers huge distances in few hops (the express lanes).
- **Lower layers are dense** — more nodes, shorter links, with layer 0 containing *every* vector.
- A search **descends the hierarchy**: start at the top, greedily walk toward the query to get roughly close, drop to the next layer to refine, and repeat down to layer 0 where the actual nearest neighbors are found.

This is analogous to how a skip list (or a coarse-to-fine map) works: the top layers get you to the right region in a few big moves, and the bottom layer pins down the precise neighbors. The result is search that scales roughly logarithmically — searching millions of vectors touches only hundreds of nodes, not millions.

## The parameters

HNSW's trade-offs are controlled by three parameters, split between build time and query time:

- **M (build)** — the number of connections (neighbors) each node keeps. Higher M means a denser, better-connected graph with higher recall and faster search — but more memory (every link is stored) and slower build. M is the main memory/quality lever.
- **efConstruction (build)** — how thoroughly the graph is explored *while inserting* each node to find its best neighbors. Higher efConstruction builds a higher-quality graph (better recall later) at the cost of slower, more expensive index construction. You pay this once, at build time.
- **efSearch (query)** — how many candidates the search keeps in play *while querying* (the size of the dynamic candidate list). This is the runtime recall/latency knob, analogous to IVF's nprobe: higher efSearch explores more of the graph, finding more true neighbors (higher recall) at higher latency; lower efSearch is faster but misses more.

The practical mental model: **M and efConstruction set the graph's quality (and memory) at build time; efSearch dials recall vs. speed at query time.** You tune efSearch per workload to hit your recall target — measured, as always, against brute-force ground truth.

## Strengths and weaknesses

HNSW's profile explains its popularity and its costs:

**Strengths:**

- **High recall at low latency** — for many workloads HNSW achieves better recall at the same speed than IVF, which is why it's the default in most vector databases.
- **Excellent query performance** — roughly logarithmic search; touches few nodes even in huge datasets.
- **Good incremental inserts** — new vectors can be added to the graph without rebuilding it, unlike IVF's clusters that can drift and need retraining. (Deletion is trickier — see below.)
- **No training step** — unlike IVF's k-means, there's no separate clustering to train; you build the graph directly.

**Weaknesses:**

- **High memory usage** — this is the big one. HNSW stores the vectors *plus* the graph's connections (M links per node across layers), which is substantial overhead on top of the vectors themselves. At very large scale this memory cost is HNSW's main drawback and the reason IVF (especially IVF-PQ) is sometimes preferred.
- **Slower, more expensive build** — constructing a good graph (high efConstruction) takes time and compute.
- **Deletion is awkward** — removing nodes from the graph is harder than adding them; implementations often mark deleted and periodically rebuild, so heavy churn is a weak spot.
- **Many parameters to tune** — three interacting knobs versus IVF's simpler dial.

## HNSW plus quantization

HNSW's memory appetite is often addressed by combining it with quantization (the next post): store compressed vectors to cut the memory cost while keeping the graph's fast navigation. Variants that pair HNSW with product quantization or scalar quantization are common in production vector databases precisely to tame the memory weakness. So the two dominant algorithms both lean on quantization to scale — IVF-PQ for partition-based, HNSW+quantization for graph-based.

## Choosing HNSW

HNSW is the right default for most vector search when memory allows:

- **You want the best recall-at-latency** and can afford the memory — the common case, and why vector databases default to it.
- **You have incremental inserts** — a growing corpus where you add vectors continuously without wanting to rebuild.
- **Query latency is critical** — interactive semantic search and RAG where fast, high-recall retrieval matters.

Reach for IVF instead when memory is the binding constraint at very large scale (IVF-PQ compresses better), or when HNSW's build cost and deletion awkwardness don't fit your workload. With both dominant algorithms covered, the next post tackles the memory problem they both face — quantization — which is how either scales to billions of vectors.

## Key takeaways

- HNSW builds a graph of vectors you navigate greedily toward a query; the "navigable small world" property (many short links plus a few long-range ones) lets a greedy walk reach any query's neighborhood in few hops, like six-degrees-of-separation.
- The hierarchy (sparse long-link top layers down to a dense all-nodes layer 0) makes search descend coarse-to-fine — big jumps to the right region, then refinement — giving roughly logarithmic search that touches hundreds of nodes, not millions.
- Three parameters: M (connections per node — memory/quality, build), efConstruction (build thoroughness — graph quality, build), and efSearch (candidates explored — the runtime recall/latency knob, like IVF's nprobe).
- Strengths: high recall at low latency (the default in most vector DBs), logarithmic query speed, good incremental inserts, no training step; weaknesses: high memory (vectors + graph links), expensive build, awkward deletion, more knobs.
- HNSW is the right default when memory allows and latency/recall matter; pair it with quantization to tame its memory cost, or choose IVF-PQ when memory is the binding constraint at very large scale.

## Further reading

- [Efficient and robust approximate nearest neighbor search using HNSW graphs (Malkov & Yashunin)](https://arxiv.org/abs/1603.09320)
- [IVF: the inverted file index (previous post)](/blog/posts/vecsearch-04-ivf-inverted-file-index.html)
- [FAISS wiki — HNSW indexes](https://github.com/facebookresearch/faiss/wiki)
