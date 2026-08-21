# Choosing and Operating a Vector Index

*The final decision isn't "which algorithm is best" — it's "which point on the recall-latency-memory triangle does my workload need, and what's the simplest thing that hits it." For a huge number of systems the honest answer is far less exotic than the vector-database marketing suggests, and knowing when you've genuinely outgrown Postgres is worth more than knowing HNSW's internals.*

This series opened with a triangle — recall, latency, memory — and every algorithm since is a different point in it. This closing post is about *choosing*: matching an index (and a system to run it) to your actual requirements, then operating it in production. It ties the internals back to the practical decision the [AI Architecture Decisions](/blog/posts/ai-decisions-07-vector-storage.html) series framed, now with the mechanics to reason about it properly.

## Start from requirements, not algorithms

The mistake is picking an algorithm (or a trendy vector database) first. Start instead from the numbers your workload demands:

- **Scale** — how many vectors? Thousands, millions, or billions? This is the biggest driver.
- **Recall target** — how bad is missing a true neighbor? RAG that must find the answer needs high recall; a "similar items" widget tolerates less.
- **Latency budget** — how fast must queries return? Interactive search needs low latency; batch jobs don't.
- **Memory/cost budget** — how much RAM can you afford? This decides whether you need quantization and which algorithm fits.
- **Update pattern** — static corpus, incremental inserts, or high churn (including deletes)?
- **Filtering and hybrid needs** — do queries filter by metadata (multi-tenant?) and need exact-match/keyword search?

These map directly onto the series: scale and memory decide brute-force vs. IVF vs. HNSW and whether to quantize; recall and latency set the tuning knobs (nprobe, efSearch); update pattern favors HNSW (inserts) or flat (churn); filtering/hybrid needs shape the system choice. Answer these first, and the index mostly picks itself.

## The decision, walked through

Following the series' logic, the choice cascades by scale:

- **Small (up to ~tens of thousands, or per-user corpora): brute force.** Perfect recall, no tuning, trivial updates (the brute-force post). Don't build an ANN index you don't need — this covers far more systems than people expect, including per-tenant and on-device cases.
- **Medium (hundreds of thousands to millions): HNSW, memory permitting.** Best recall-at-latency, good incremental inserts, the default in vector databases. Tune efSearch for your recall target. Add scalar quantization if memory is tight.
- **Large and memory-constrained (many millions to billions): IVF-PQ.** When HNSW's memory overhead is too costly, IVF plus product quantization compresses the footprint to feasible while staying fast. Tune nprobe and PQ parameters, and rerank on full-precision vectors to recover recall.
- **Any scale needing exact matches: add hybrid search**, and **any multi-tenant system: get filtering right** (pre-filter for correctness) — regardless of the base algorithm.

The through-line: **escalate on evidence.** Begin with the simplest thing that could work (often brute force or pgvector), measure recall and latency at your real scale, and move to a more complex index or system only when a measurement says you must.

## Where to run it: library vs. database vs. Postgres

The index is one decision; the *system* hosting it is another, and it follows the same escalate-on-evidence logic (the [pgvector-vs-dedicated](/blog/posts/ai-decisions-07-vector-storage.html) decision, now with mechanics):

- **A library (FAISS, hnswlib)** — you embed the ANN algorithm directly in your application and manage storage/persistence yourself. Maximum control and efficiency, but you build the operational scaffolding (persistence, updates, scaling). Good when vector search is a component you want to control tightly.
- **Postgres + pgvector** — add vector search to the database you already run. For most systems (up to millions of vectors), this is the pragmatic default: one system to operate, transactional consistency with your other data, metadata filtering via SQL joins, and no new infrastructure. The recurring lesson — *the database you already have, with a vector extension, beats adding a specialized system until scale or specific features force the upgrade.*
- **A dedicated vector database** — purpose-built systems that handle ANN indexing, filtering, hybrid search, sharding, and scaling out of the box. Justified when you genuinely outgrow pgvector: billions of vectors, very high query throughput, or you need advanced features (sophisticated filtering, hybrid, distributed scale) you'd otherwise build yourself.

The honest guidance: most teams reaching for a dedicated vector database would be well served by pgvector, and should adopt the specialized system only when scale or a specific feature requirement — measured, not assumed — makes it necessary.

## Operating a vector index

Once chosen, a vector index needs operational care the internals imply:

- **Measure recall continuously against ground truth.** Build a ground-truth set with brute force on a sample, and monitor that your ANN recall stays at target — because recall degrades silently (a bad tuning change or data drift lowers it with no error). Recall is the metric no dashboard shows unless you measure it yourself.
- **Tune the runtime knob to your SLO.** nprobe (IVF) or efSearch (HNSW) is your recall/latency dial; set it from measured recall at acceptable latency, and revisit as data grows.
- **Plan for updates and drift.** IVF's clusters and PQ's codebooks can drift as data changes — schedule retraining/rebuilds. HNSW handles inserts well but deletions poorly — plan for periodic rebuilds if churn is high. Propagate deletes (a privacy and correctness requirement).
- **Watch memory.** The index (especially HNSW) plus vectors dominate RAM; monitor it, and use quantization before you run out. Memory exhaustion is a common production failure.
- **Test filtered and hybrid recall, not just raw.** Your real queries filter and fuse; measure recall under those conditions (the filtering post), since selective filters can quietly gut results.

## The series in one picture

Vector search is the recall-latency-memory triangle, navigated with a small toolkit:

```text
  brute force   → perfect recall, no build/tuning; small or per-user scale
  IVF           → partition space; nprobe dials recall/speed; memory-efficient
  HNSW          → navigate a graph; efSearch dials recall/speed; best recall-at-latency, memory-hungry
  quantization  → compress vectors (scalar/PQ); trades recall for memory; enables scale
  filtering     → similarity + metadata (pre-filter for correctness/tenancy)
  hybrid        → dense + sparse (BM25) fused; catches exact matches
  reranking     → retrieve broad + approximate, reorder precise; recovers recall
```

Combine these to hit your point on the triangle: brute force or pgvector until measurements say otherwise, HNSW for the common quality-latency sweet spot, IVF-PQ when memory binds at huge scale, quantization to fit, and filtering + hybrid + reranking to make raw similarity into production-quality retrieval. Match the tool to the requirement, escalate on evidence, and measure recall — and vector search stops being a mysterious black box and becomes a set of controllable trade-offs.

## Key takeaways

- Choose from requirements, not algorithms: scale, recall target, latency budget, memory budget, update pattern, and filtering/hybrid needs determine the index — answer these and it mostly picks itself.
- The choice cascades by scale: brute force for small/per-user corpora (perfect recall, no tuning), HNSW for medium scale when memory allows (best recall-at-latency), IVF-PQ for large memory-constrained scale — always escalating on measured evidence, not assumption.
- The hosting system follows the same logic: a library (FAISS/hnswlib) for tight control, Postgres+pgvector as the pragmatic default for most systems (up to millions), a dedicated vector database only when scale/throughput/features genuinely force it.
- Operate deliberately: measure recall against brute-force ground truth continuously (it degrades silently), tune nprobe/efSearch to your SLO, plan for drift/retraining and deletions, watch memory (quantize before exhaustion), and test filtered/hybrid recall — not just raw.
- The whole toolkit — brute force, IVF, HNSW, quantization, filtering, hybrid, reranking — is points and refinements on the recall-latency-memory triangle; combine them to hit your workload's point, and vector search becomes controllable trade-offs, not a black box.

## Further reading

- [Filtering and hybrid search (previous post)](/blog/posts/vecsearch-07-filtering-and-hybrid-search.html)
- [Postgres/pgvector vs a Dedicated Vector Database](/blog/posts/ai-decisions-07-vector-storage.html)
- [The nearest neighbor problem — start of the series](/blog/posts/vecsearch-01-nearest-neighbor-problem.html)
