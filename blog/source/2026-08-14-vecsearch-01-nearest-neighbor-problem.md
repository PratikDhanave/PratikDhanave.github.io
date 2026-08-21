# The Nearest Neighbor Problem

*Every RAG system, recommendation engine, and semantic search box rests on one deceptively simple operation: given a query vector, find the closest vectors among millions. Doing it exactly is easy and doesn't scale; doing it fast enough to be useful means giving up exactness on purpose — and understanding that trade is the foundation of vector search.*

Semantic search, RAG retrieval, recommendations, deduplication, and image search all reduce to the same problem: you have a huge collection of **vectors** (embeddings), a query vector, and you need the ones *nearest* to the query. This series opens up how that's actually done — IVF, HNSW, quantization, filtering — but it starts with the problem itself, because the central insight of the whole field is that the *exact* answer is too slow, and the entire discipline is about approximating it well.

## From meaning to vectors

The premise, familiar from the RAG and LLM serving series: an **embedding model** turns a piece of content — text, an image, audio — into a **vector**, a list of numbers (often hundreds to thousands of dimensions), positioned so that *semantically similar content has nearby vectors*. "How do I reset my password?" and "I forgot my login credentials" land close together even though they share no words, because the embedding captures meaning, not spelling.

This is powerful because it turns "find relevant content" into "find nearby vectors" — a pure geometry problem. Semantic search becomes: embed the query, find the nearest stored vectors, return their content. Everything in this series is about doing that last step — **nearest-neighbor search** — quickly over millions or billions of vectors.

## The exact problem, and why it doesn't scale

The exact version is trivial to state and to implement: to find the nearest vectors to a query, compute the distance from the query to *every* stored vector, sort, and take the closest K. This is **exact k-nearest-neighbor (kNN)** search, and it's completely correct.

It's also completely unscalable. The cost is O(N × d): for N vectors of dimension d, every query compares against all N vectors, each comparison touching all d dimensions. With a few thousand vectors that's instant. With ten million 1,000-dimensional vectors, every single query does ten billion multiply-adds — far too slow for interactive search, and it grows linearly with your data. Worse, the vectors are large, so they may not fit in fast memory, adding I/O cost. Exact search is a straight line on a graph of latency-vs-data-size, and that line goes to unacceptable fast.

You can't index your way out of this the way a B-tree indexes a database, either, because — as the next post explains — high-dimensional space breaks the geometric assumptions that low-dimensional indexes (like the ones in the Database Internals series) rely on. Nearest-neighbor search in high dimensions is genuinely hard.

## The key move: approximate on purpose

Here is the insight that defines the entire field: **you give up on the exact answer.** Instead of *the* nearest neighbors, you accept *probably most of* the nearest neighbors — **Approximate Nearest Neighbor (ANN)** search. This sounds like a compromise, but it's the enabling trade, and it's justified because:

- **The embeddings are already approximate.** The vectors are a lossy, learned approximation of meaning; the "true" nearest vector isn't ground truth about relevance anyway, just the closest point in an imperfect space. Missing the 3rd-closest vector and returning the 4th usually makes no difference to a user.
- **The speedup is enormous.** Accepting a small chance of missing some true neighbors buys orders-of-magnitude faster search — from linear scans to near-constant or logarithmic-ish query time. This is the difference between vector search being possible and impossible at scale.

So the discipline of vector search is: **trade a little accuracy for a lot of speed**, and control that trade deliberately. Every algorithm in this series (IVF, HNSW, quantization) is a different strategy for making that trade well — being fast while missing as few true neighbors as possible.

## Recall: measuring the trade

Because ANN gives up exactness, you need a way to measure *how much* — and that metric is **recall**. Recall@K is the fraction of the true top-K nearest neighbors that the approximate search actually returned:

```text
recall@10 = (# of true top-10 neighbors found in your returned top-10) / 10

recall@10 = 1.0  → perfect: you found all the true neighbors
recall@10 = 0.9  → you found 9 of the 10 true nearest; missed one
```

Recall is *the* quality metric of vector search, and it trades directly against speed and memory:

- **Higher recall** — closer to exact results — costs more (search more of the data, use more memory), so it's slower or bigger.
- **Lower recall** — faster and smaller — but you miss more true neighbors, which can hurt downstream quality (e.g. RAG missing the relevant chunk).

Every ANN algorithm exposes knobs that move you along this **recall-vs-latency (and recall-vs-memory)** curve. There's no universally right setting — a RAG system might need high recall so it doesn't miss the answer, while a "similar items" feature tolerates lower recall for speed. The engineering is choosing the operating point for your use case, which is exactly what the final post is about.

## The three-way trade-off

Zoom out and vector search is governed by a three-way tension you'll see in every algorithm ahead:

- **Recall (accuracy)** — how many true neighbors you find.
- **Latency (speed)** — how fast each query returns.
- **Memory (cost)** — how much RAM the index needs (vectors are large, and indexes add overhead).

You cannot maximize all three — the whole field is picking two to favor and paying in the third. IVF and HNSW trade memory and build-time for query speed at high recall; quantization trades a little recall for large memory savings; brute force gives perfect recall but poor latency at scale. Keeping this triangle in mind makes every subsequent algorithm legible: each is a different point in the recall-latency-memory space, chosen for a different workload.

## Where the series goes

From here: distance metrics and why high dimensions are strange (the geometry underneath), brute-force/flat search (the exact baseline and when it's enough), IVF (partition the space and search part of it), HNSW (navigate a graph to the neighborhood fast), vector quantization (compress vectors to save memory), filtering and hybrid search (combining similarity with metadata and keywords), and choosing/operating an index in production. Throughout, the lens is this post's triangle — recall, latency, memory — and the founding trade: approximate on purpose, and control the approximation.

## Key takeaways

- Semantic search, RAG, and recommendations all reduce to nearest-neighbor search: embed content into vectors where similar meaning is nearby, then find the vectors closest to a query.
- Exact kNN (compare the query to every vector) is correct but O(N×d) — unscalable at millions of vectors — and high-dimensional geometry prevents low-dimensional indexing tricks from saving it.
- The field's defining move is Approximate Nearest Neighbor (ANN): give up exactness on purpose, accepting *probably most* of the true neighbors in exchange for orders-of-magnitude speedup — justified because embeddings are already approximate.
- Recall@K (fraction of true top-K neighbors actually returned) is the quality metric; it trades directly against latency and memory, and every ANN algorithm exposes knobs to set that operating point.
- Vector search is a three-way trade-off — recall vs. latency vs. memory — that you can't maximize all of; every algorithm (IVF, HNSW, quantization, brute force) is a different point in that space chosen for a different workload.

## Further reading

- [FAISS — a library for efficient similarity search (Meta)](https://github.com/facebookresearch/faiss)
- [ANN-Benchmarks — comparing approximate nearest-neighbor algorithms](https://ann-benchmarks.com/)
- [Agentic RAG series — retrieval in depth](/blog/series/agentic-rag/)
