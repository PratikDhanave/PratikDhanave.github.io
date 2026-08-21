# Distance Metrics and the Curse of Dimensionality

*"Nearest" is meaningless until you define "distance," and the metric you choose — cosine, dot product, or Euclidean — must match how your embedding model was trained or your search is quietly wrong. And in high dimensions, distance itself behaves so strangely that the naive intuitions you'd bring from 2D geometry actively mislead you.*

The last post reduced search to "find the nearest vectors." This one asks two questions that underlie every algorithm to come: *what does "near" mean* (distance metrics), and *why is high-dimensional space so hard* (the curse of dimensionality). Getting the metric wrong silently corrupts results; misunderstanding high-dimensional geometry leads to indexes that don't work. Both are foundational.

## Distance metrics: defining "near"

A **distance metric** (or similarity measure) is the function that scores how close two vectors are. Three dominate vector search, and they are *not* interchangeable:

- **Cosine similarity** — measures the *angle* between two vectors, ignoring their magnitude. Two vectors pointing the same direction are maximally similar regardless of length. This is the most common metric for text embeddings, because it captures "same meaning/direction" while ignoring magnitude differences that often reflect length or frequency rather than meaning.
- **Dot product (inner product)** — multiplies and sums element-wise; it's affected by *both* angle and magnitude. Larger-magnitude vectors score higher. Some models are trained so that dot product is the right measure (magnitude carries signal, e.g. importance).
- **Euclidean distance (L2)** — the straight-line distance between the two points. Intuitive (it's ordinary geometric distance) and used by some models and for non-text vectors.

The critical, often-missed rule: **use the metric your embedding model was trained with.** An embedding model is optimized so that a *specific* distance measure reflects similarity; using a different one at search time gives subtly wrong rankings. If the model was trained for cosine similarity, searching with Euclidean distance will return plausible-but-suboptimal neighbors, and you may never notice because the results look reasonable. Always check the model's documentation for its intended metric and configure your index to match.

A useful relationship simplifies this: if you **normalize** vectors to unit length (divide by their magnitude), then cosine similarity, dot product, and Euclidean distance all produce the *same ranking*. This is why many systems normalize embeddings on ingestion — it makes the metric choice moot and lets the index use whichever is fastest to compute. Normalizing up front is a common, safe default for text embeddings.

## Why the metric choice matters downstream

The metric isn't just a config flag — it shapes every algorithm in the series, because IVF's clustering, HNSW's graph construction, and quantization's error all depend on the distance function. An index built assuming one metric doesn't correctly serve another. So the metric is a decision you make *once, up front*, matched to your model, and then everything else is built on it. Change the metric later and you rebuild the index. This is why "which metric?" belongs at the very start of designing vector search, not as an afterthought.

## The curse of dimensionality

Now the strange part. Embeddings live in *high-dimensional* space — hundreds to thousands of dimensions — and high-dimensional space does not behave like the 2D or 3D space our intuitions come from. This collection of counterintuitive behaviors is the **curse of dimensionality**, and it's *why* nearest-neighbor search is hard enough to need a whole field.

Two phenomena matter most for vector search:

- **Distances concentrate.** As dimensionality grows, the distances between random points become increasingly *similar to each other* — the nearest and farthest points end up almost the same distance away. In very high dimensions, the very notion of a clear "nearest" neighbor weakens, because everything is roughly equidistant. This is unsettling but real, and it means nearest-neighbor results in high dimensions are inherently less sharply separated than low-dimensional intuition suggests.
- **Space is mostly empty, and volume explodes.** The volume of high-dimensional space grows so fast that any realistic number of points is sparse within it — your millions of vectors are scattered thinly across an unimaginably vast space. Most of the space contains no data at all.

## Why the curse breaks classic indexes

The practical consequence — and the reason vector search needs IVF and HNSW rather than the tree indexes from the Database Internals series — is that **space-partitioning indexes that work beautifully in low dimensions fail in high dimensions.** A structure like a k-d tree, which recursively splits space to prune the search, works great in 2D or 3D: you can rule out most of the space quickly. But in high dimensions, because of distance concentration and volume explosion, these trees can't prune effectively — a query ends up needing to check almost all the partitions anyway, degrading to no better than brute force.

This is a deep point: **you cannot solve high-dimensional nearest-neighbor search by exact partitioning.** The geometry that makes B-trees and k-d trees efficient (a clear notion of "this region is far, skip it") doesn't hold. That's precisely why the field turned to *approximate* methods (from the last post) built on different ideas — probabilistic partitioning into clusters (IVF) and greedy graph navigation (HNSW) — that sidestep the curse rather than fighting it. The curse of dimensionality isn't a footnote; it's the reason the rest of the series exists.

## Living with high dimensions

A few practical implications flow from all this:

- **Match the metric to the model, and consider normalizing.** Use the model's intended distance measure; normalizing vectors to unit length makes cosine/dot/Euclidean equivalent and is a safe default for text.
- **Expect approximate, not crisp, neighbors.** Because distances concentrate, don't expect the geometry to hand you an obviously-best single neighbor; retrieval returns a *set* of plausibly-relevant vectors, which is why RAG returns several chunks and often reranks them.
- **Dimensionality has a cost.** Higher-dimensional embeddings capture more nuance but cost more memory and compute per comparison, and suffer the curse more. Some models offer smaller embedding dimensions (or techniques to shorten them) as a deliberate trade of a little quality for less memory and faster search — worth considering at scale.
- **Don't reach for classic tree indexes.** They don't work here; the approximate methods in the coming posts exist specifically because of the curse.

With "near" defined and the strangeness of high dimensions understood, we can look at the algorithms. The next post starts with the honest baseline everything else is measured against: brute-force search.

## Key takeaways

- A distance metric defines "near": cosine (angle only, the common text default), dot product (angle and magnitude), and Euclidean/L2 (straight-line) — and they are not interchangeable.
- Use the metric your embedding model was trained for, or rankings are subtly wrong; normalizing vectors to unit length makes cosine, dot, and Euclidean give the same ranking — a safe default worth doing on ingestion.
- The metric is a foundational, up-front decision because IVF clustering, HNSW graphs, and quantization all depend on it — changing it later means rebuilding the index.
- The curse of dimensionality makes high-dimensional space behave strangely: distances concentrate (nearest and farthest become similar) and volume explodes (data is sparse), so "nearest neighbor" is inherently less crisp than low-dimensional intuition suggests.
- The curse breaks classic space-partitioning indexes (k-d trees) — they can't prune in high dimensions and degrade to brute force — which is exactly why vector search uses approximate methods (IVF, HNSW) built on clustering and graph navigation instead.

## Further reading

- [The nearest neighbor problem (previous post)](/blog/posts/vecsearch-01-nearest-neighbor-problem.html)
- [FAISS documentation and wiki](https://github.com/facebookresearch/faiss/wiki)
- [Postgres/pgvector vs a Dedicated Vector Database](/blog/posts/ai-decisions-07-vector-storage.html)
