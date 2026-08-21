# IVF: The Inverted File Index

*The simplest way to beat brute force is to avoid searching most of your data — cluster the vectors into regions, and at query time only look inside the few regions nearest the query. That's IVF, and its one tuning knob, how many regions to probe, is a clean, visible dial on the recall-versus-speed trade at the heart of the whole field.*

Brute force searches everything. The first idea for going faster is intuitive: **don't**. If you group nearby vectors into clusters ahead of time, then a query only needs to search the clusters *near* it, skipping the rest. This is the **Inverted File Index (IVF)**, one of the two dominant ANN approaches. It's easy to understand, easy to tune, and its behavior makes the recall/latency trade-off from the first post concrete and controllable.

## The idea: partition, then search part

IVF works in two phases — a one-time build and a per-query search.

**Build (once):**

1. Run a clustering algorithm (typically k-means) over your vectors to find a set of *centroids* — representative center points that partition the space into regions (cells).
2. Assign every vector to its nearest centroid. Each centroid now owns a list ("inverted list") of the vectors in its cell.

**Search (per query):**

1. Compare the query to the *centroids* (few of them) to find the nearest cells.
2. Search only the vectors in those nearest cells — brute force *within* the selected cells — and return the closest.

```text
Space partitioned into cells by centroids (×):

     × cell A      × cell B      × cell C
       • • •         • • •         • • •
       • •           • • •         • •
                        ▲
                      query → nearest centroid is B
                      → search ONLY cell B's vectors (skip A and C)
```

Instead of scanning all N vectors, you scan the few cells nearest the query — a large fraction of the data is skipped entirely. That's the speedup: you've traded searching everything for searching a slice.

## nprobe: the recall knob

IVF's brilliance is that its accuracy/speed trade is a single, legible parameter: **nprobe** — the number of nearest cells to search. Search only the 1 closest cell and you're very fast but might miss neighbors that happen to sit in an adjacent cell; search more cells and you find more true neighbors but do more work.

```text
nprobe = 1   → search 1 cell   → fastest, lowest recall
nprobe = 8   → search 8 cells  → slower, higher recall
nprobe = all → search every cell → brute force (recall 1.0, no speedup)
```

This is the recall-vs-latency curve from post one, made into a dial you turn. And it exposes IVF's core weakness, the **edge problem**: a true nearest neighbor can fall just across a cell boundary, in a cell you didn't probe, so you miss it. Raising nprobe searches more neighboring cells and recovers those boundary neighbors — at the cost of speed. Tuning IVF is essentially choosing nprobe (and the number of cells) to hit your recall target at acceptable latency, which you do by measuring recall against brute-force ground truth.

## The other knob: number of cells

The build-time choice of **how many centroids/cells** (often written `nlist`) interacts with nprobe and shapes the trade:

- **More cells** — each cell holds fewer vectors, so searching a cell is cheaper, but the space is chopped finer, so more true neighbors fall into non-probed cells (you may need a higher nprobe to compensate). More cells also means comparing the query against more centroids up front.
- **Fewer cells** — each cell holds more vectors (more work per probed cell), but coarser partitioning means fewer boundary misses per cell probed.

A common rule of thumb scales the number of cells with dataset size (e.g. on the order of the square root of N), but the right values are found by tuning for your data and recall target. The two knobs together — `nlist` (cells) and `nprobe` (cells searched) — define IVF's operating point.

## Strengths and weaknesses

IVF's trade-offs make it a strong fit for some situations and not others:

**Strengths:**

- **Simple and intuitive** — clustering plus partial search; easy to reason about and tune (one main knob).
- **Memory-efficient relative to graph methods** — it stores the vectors plus a modest set of centroids and lists, with less structural overhead than HNSW's graph (next post). This matters at large scale.
- **Fast build compared to graph methods** — clustering is cheaper to compute than building a navigable graph.
- **Combines well with quantization** — IVF is frequently paired with product quantization (the quantization post) to compress the vectors in each list, saving large amounts of memory — the well-known IVF-PQ combination.

**Weaknesses:**

- **The edge/boundary problem** — true neighbors near cell borders get missed unless nprobe is raised, so achieving very high recall can require probing many cells.
- **Recall depends on cluster quality** — if the data's structure doesn't cluster cleanly, partitioning is less effective.
- **Updates need care** — adding many vectors over time can unbalance the clusters (new data may not fit the original centroids well), sometimes requiring periodic retraining of the index for best recall.
- **Generally lower recall-at-speed than HNSW** for many workloads — HNSW often achieves higher recall at the same latency, which is why it's frequently preferred when memory allows.

## When to reach for IVF

IVF shines when its particular balance fits:

- **Large datasets where memory matters** — IVF (especially IVF-PQ) is more memory-efficient than HNSW, so at very large scale where the graph's overhead is costly, IVF's compactness wins.
- **Batch or throughput-oriented workloads** — where you can tune nprobe for good throughput and don't need HNSW's absolute best single-query latency.
- **When paired with quantization** — the IVF-PQ combination is a workhorse for compressing huge vector collections into manageable memory while staying fast.

IVF is the "partition the space" answer to beating brute force, with a clean dial (nprobe) on the recall/speed trade and excellent memory behavior when combined with quantization. The next post covers the other dominant approach, which navigates a graph instead of partitioning space — HNSW — and often achieves higher recall at the same speed.

## Key takeaways

- IVF avoids searching most of the data: cluster vectors into cells around centroids (build, via k-means), then at query time search only the cells nearest the query (skipping the rest).
- Its recall/speed trade is one legible knob — nprobe, the number of nearest cells to search: low nprobe is fast but misses boundary neighbors, high nprobe raises recall toward brute force at the cost of speed.
- A second build-time knob, the number of cells (nlist), interacts with nprobe: more cells means cheaper per-cell search but more boundary misses; the two together set the operating point, tuned against brute-force ground truth.
- IVF's core weakness is the edge problem (true neighbors just across an unprobed cell boundary are missed); its strengths are simplicity, memory efficiency, fast build, and excellent pairing with product quantization (IVF-PQ).
- Reach for IVF at large scale where memory matters (especially IVF-PQ to compress huge collections) and for throughput-oriented workloads; HNSW (next) often achieves higher recall at the same latency when memory allows.

## Further reading

- [Brute force and when it's enough (previous post)](/blog/posts/vecsearch-03-brute-force-flat-search.html)
- [FAISS wiki — IVF and IVF-PQ indexes](https://github.com/facebookresearch/faiss/wiki)
- [The nearest neighbor problem — the recall/latency/memory triangle](/blog/posts/vecsearch-01-nearest-neighbor-problem.html)
