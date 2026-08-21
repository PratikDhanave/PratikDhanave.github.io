# Vector Quantization: Compressing the Vectors

*Vectors are big, and storing millions of them in full precision is where vector search gets expensive. Quantization compresses each vector into a fraction of its size — trading a little recall for large memory savings — and it's the technique that lets both IVF and HNSW scale from millions of vectors to billions without a memory budget that breaks the bank.*

The last two posts covered algorithms for *searching* fast; both share a weakness — **memory**. Vectors are large (hundreds to thousands of dimensions in full-precision floats), and at scale the vectors themselves dominate cost, especially for memory-hungry HNSW. **Vector quantization** compresses them, and it's the third leg of scalable vector search alongside the search algorithms. This post covers scalar quantization, product quantization, and how they combine with IVF and HNSW. (This is quantizing the *vectors in the index*, distinct from quantizing model weights in the LLM serving series — same idea, different target.)

## Why compress vectors

Do the memory math. A single vector of dimension 1,000 in 32-bit floats is 4,000 bytes. Ten million such vectors are 40 GB — just for the raw vectors, before any index overhead (and HNSW adds its graph on top). That's expensive RAM, and it's the binding constraint on how much you can hold and search in memory.

Quantization attacks this directly by storing each vector in far fewer bits, with three payoffs:

- **Less memory** — the dominant benefit; compression of 4×, 8×, or far more lets you fit vastly more vectors in the same RAM (or fit the same data on cheaper hardware).
- **Faster search** — smaller vectors mean less data to move and, with the right method, cheaper distance computation, so search can actually speed up.
- **Enables scale** — quantization is often what makes billion-scale vector search feasible at all, by shrinking the footprint to something a machine can hold.

The cost, as always, is a little **recall** — compressed vectors are approximations, so distances computed from them are slightly off, occasionally reordering neighbors. The craft is capturing the memory win while keeping recall loss acceptable.

## Scalar quantization: fewer bits per number

The simplest approach, **scalar quantization**, reduces the precision of each number in the vector — for example, mapping 32-bit floats down to 8-bit integers by scaling each dimension's value range onto 256 levels. This gives a straightforward 4× compression (32→8 bits) with typically small recall loss, and it's cheap to compute both ways.

Scalar quantization is the easy, safe first step: modest compression, minimal recall impact, simple to reason about. Many systems use 8-bit scalar quantization as a low-risk default that quarters memory. You can go further (fewer bits) for more compression at more recall cost, but scalar quantization's real limitation is that it treats each dimension independently and can't exploit correlations between dimensions — which is what product quantization does.

## Product quantization: the workhorse

**Product quantization (PQ)** is the technique behind most large-scale vector search, achieving far more compression than scalar quantization. Its idea is clever: instead of quantizing each number, quantize *chunks* of the vector against a learned codebook.

```text
Original vector (dim 1024, 4-byte floats = 4096 bytes):
  [ ─────────────── 1024 numbers ─────────────── ]
Split into m sub-vectors:
  [ sub1 ][ sub2 ][ sub3 ] ... [ sub_m ]
For each sub-vector position, learn a codebook of representative
centroids (e.g. 256 of them). Replace each sub-vector with the
1-byte ID of its nearest centroid:
  [ id1 ][ id2 ][ id3 ] ... [ id_m ]   →  m bytes total
```

By splitting the vector into `m` sub-vectors and replacing each with a small code (an ID into a per-chunk codebook of, say, 256 centroids = 1 byte each), a vector shrinks from thousands of bytes to just `m` bytes — compression of 10×, 20×, or more. Distances are then estimated from the codes using precomputed lookup tables, which is also fast.

PQ's trade-offs:

- **Massive compression** — the main draw; it's how billion-scale indexes fit in memory.
- **Approximate distances** — distances are computed from the codes, not the true vectors, so there's more recall loss than scalar quantization. The compression/recall trade is tunable via `m` (more sub-vectors = less compression, higher fidelity) and codebook size.
- **A training/build step** — the codebooks must be learned from the data (like IVF's clustering), so PQ has build cost and can need retraining if the data distribution shifts.

PQ is more aggressive than scalar quantization: bigger memory savings, more recall cost, more complexity. It's the tool for when memory is the binding constraint at large scale.

## Combining quantization with the search algorithms

Quantization isn't an alternative to IVF and HNSW — it *combines* with them, and the combinations are what production systems actually run:

- **IVF-PQ** — the classic large-scale combination from the IVF post: partition into cells (IVF) *and* compress the vectors within each cell (PQ). You get both the search-space reduction of IVF and the memory reduction of PQ — the workhorse for huge, memory-constrained vector collections.
- **HNSW + quantization** — pair HNSW's fast graph navigation with scalar or product quantization to tame its memory weakness (from the HNSW post). Common in vector databases to keep HNSW's recall/latency while cutting its footprint.
- **Rerank with full precision** — a widely-used refinement: use quantized vectors for the fast *approximate* search to get candidates, then recompute exact distances on the *full-precision* vectors for just those candidates to fix the ordering. This recovers most of the recall lost to quantization at small extra cost — a two-stage "search compressed, rerank exact" pattern that's very effective.

The last point is worth internalizing: quantization's recall loss can be largely *recovered* by reranking a small candidate set with the original vectors, so you often get PQ's memory savings with near-full recall. This mirrors the retrieve-broadly-then-rerank pattern from the RAG series.

## Choosing a quantization strategy

- **Start with no quantization or scalar (8-bit)** — if memory isn't tight, don't compress (perfect fidelity) or use 8-bit scalar for an easy 4× with minimal recall loss.
- **Use product quantization when memory is the binding constraint** — at large scale (many millions to billions), PQ (usually as IVF-PQ) is what makes the footprint feasible; tune `m` for your recall target.
- **Add full-precision reranking** — whenever you quantize aggressively, rerank the top candidates on original vectors to recover recall cheaply; keep the full vectors available (on disk if not in RAM) for this.
- **Measure recall after quantizing** — always validate recall against brute-force ground truth on your data, since the recall cost is data-dependent.

Quantization is the memory lever that lets vector search scale, completing the toolkit: IVF and HNSW for search speed, quantization for memory, and reranking to recover recall. The next post moves from raw similarity to *real* queries — filtering by metadata and combining with keyword search — and the final one to choosing and operating an index in production.

## Key takeaways

- Vectors dominate memory at scale (10M × 1024-dim floats ≈ 40 GB before index overhead), so quantization compresses them — trading a little recall for large memory savings and often faster search, enabling billion-scale search.
- Scalar quantization reduces precision per number (e.g. float32→int8 for 4× compression) with small recall loss — the easy, safe first step, but can't exploit correlations between dimensions.
- Product quantization (PQ) splits vectors into sub-vectors and replaces each with a small codebook ID, achieving 10–20×+ compression (the large-scale workhorse) at more recall cost and requiring a learned/trained codebook.
- Quantization combines with the search algorithms: IVF-PQ (partition + compress) for huge memory-constrained collections, HNSW+quantization to tame HNSW's memory, and full-precision reranking of top candidates to recover most lost recall cheaply.
- Choose by memory pressure: none/8-bit scalar when memory is comfortable, PQ (usually IVF-PQ) when memory is the binding constraint, always add reranking when quantizing aggressively, and validate recall against brute-force ground truth.

## Further reading

- [HNSW: navigable small world graphs (previous post)](/blog/posts/vecsearch-05-hnsw-graphs.html)
- [FAISS wiki — product quantization and IVF-PQ](https://github.com/facebookresearch/faiss/wiki)
- [LLM Inference and Serving: quantization (weights, the sibling technique)](/blog/posts/llmserve-04-quantization.html)
