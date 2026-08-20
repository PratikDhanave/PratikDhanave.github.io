# Data Foundations: The Substrate Everything Depends On

*Model quality is bounded by data quality, and the defects you tolerate here — poor lineage, silent drift, unmanaged PII, careless retrieval — resurface downstream as hallucinations, bias, privacy incidents, and un-auditable decisions.*

Every model, retrieval system, and evaluation downstream inherits the quality of the data beneath it. This is the phase teams are most tempted to rush, and the one whose shortcuts are most expensive later. "Garbage in, GenAI out" is not a slogan; it is the mechanism by which a powerful model produces confidently wrong output. This post is Phase 2 of the roadmap — establishing the governed, high-quality, well-described data substrate the rest of the system stands on.

## Data quality as an engineered property

Treat data quality the way you treat code quality: as something tested and gated, not hoped for. Define the dimensions that matter — completeness, accuracy, consistency, timeliness, validity, uniqueness — and express them as automated tests and **data contracts** in your pipelines, failing the build on violation. A layered architecture (raw, cleansed, curated, in the medallion idiom) keeps each stage independently testable and makes it obvious where a defect entered. Quality that is not enforced in the pipeline degrades silently until it surfaces as a model failure no one can explain.

## Lineage, cataloging, and PII

You cannot govern or debug what you cannot trace. Track where every dataset came from and where it flows, in a catalog that records ownership, sensitivity labels, and lineage. That catalog is the backbone of both governance (it answers "what data trained this, and may we use it?") and incident response (it answers "what's affected?"). The ability to trace data lineage and inference is also what makes decisions explainable and auditable — a requirement, not a nicety, for anything consequential.

PII deserves special, concrete discipline: strip or tokenize it across *all* stores — not just the training set, but the search indexes, caches, aggregates, and logs. The classic leak is sanitizing the training data and leaving personal data in the vector index or the request logs. Apply data minimization and purpose limitation from the start; this is where privacy-by-design stops being a policy word and becomes an implemented control. And remember that a right-to-erasure request must propagate into the vector index and caches too — a stale retrieved document is both a correctness and a privacy defect.

## Retrieval is a data-engineering problem

For any system that grounds a model in your data, retrieval quality — not model choice — is usually the dominant lever on accuracy. That makes chunking, embedding, and indexing first-class engineering, not defaults to accept. The techniques below are roughly ordered by return on effort.

- **Chunking.** Choose deliberately — fixed-size versus structural versus layout-aware for PDFs and tables. Keep each chunk about one thing, specific enough to match precisely yet complete enough to stand alone. Small-to-big retrieval (embed small chunks, return the larger parent) and prepending document-level context to each chunk both materially improve relevance.
- **Hybrid retrieval.** Combine dense (vector) similarity with sparse (keyword/BM25) matching, fused together. Pure-vector recall misses exact terms, names, and codes that keywords catch; hybrid is the fix.
- **Retrieve-then-rerank.** The single most reliable quality upgrade: retrieve a wide candidate set cheaply, then re-rank with a more precise cross-encoder down to a tight top handful that actually enters the context.
- **Query pre-processing.** Rewrite, expand, and decompose questions, and route them to the right index before retrieving.
- **Embedding and index choices.** Trade dimension, cost, and latency; validate on *your* data rather than trusting a leaderboard, and budget for the fact that changing the embedding model forces re-embedding the entire corpus — a real migration cost. Choose an ANN index (fast high-recall versus compact) to match your recall and memory constraints.
- **Freshness and erasure.** Design incremental re-indexing, change-data-capture from the source of truth, tombstoning of deleted documents, and versioned-index cutover — including the erasure propagation noted above.

Because "lost in the middle" is real — models use the beginning and end of a long context better than the buried middle — retrieving *fewer, better* chunks and placing them well beats retrieving more.

## Feature stores and vector stores are not the same thing

A recurring confusion worth settling: a **feature store** solves point-in-time-correct joins (preventing label leakage) and a shared online/offline store (eliminating training-serving skew) — it matters mainly for predictive and tabular ML. A **vector store** solves nearest-neighbor retrieval for grounded generation. They are different tools for different problems; a GenAI-only application often needs the vector store and not the feature store. Do not adopt one thinking it does the other's job.

## Labeling and synthetic data

Where you need labels, build labeling workflows with quality control and inter-annotator agreement, not ad-hoc tagging. Where you use synthetic data, generate it under governance and track its provenance so it is never silently conflated with real data — an unmarked synthetic record that leaks into evaluation or training quietly corrupts both.

## The gate and anti-patterns

Phase 2 is done when curated, quality-tested datasets exist for the target use case with automated quality gates; lineage and sensitivity classification are queryable for every dataset in scope; PII handling is implemented across *all* stores including indexes and caches; and, for RAG systems, a retrieval design is documented and its retrieval quality is measurable. Avoid the recurring failures: pointing a powerful model at un-curated data and blaming the model; PII leaking via the side door of the vector index or logs; treating chunking and embedding as incidental; and running with no monitoring on input-data distributions — the silent drift the observability phase will need to catch.

## Key takeaways

- Model quality is bounded by data quality; defects here (lineage, drift, PII, retrieval) resurface downstream as hallucinations, bias, privacy incidents, and un-auditable decisions.
- Engineer data quality with defined dimensions expressed as automated tests and data contracts that fail the build, over a layered, independently-testable architecture.
- Maintain a catalog with ownership, sensitivity, and lineage; strip or tokenize PII across *all* stores (indexes, caches, logs), and propagate right-to-erasure into the vector index.
- Retrieval quality usually dominates grounded-generation accuracy: invest in deliberate chunking, hybrid retrieval, and especially retrieve-then-rerank; validate embeddings on your data and design for freshness and erasure.
- Feature stores (point-in-time joins, training-serving skew) and vector stores (nearest-neighbor retrieval) solve different problems — don't conflate them; govern labeling and synthetic-data provenance.

## Further reading

- [Datasheets for Datasets — Gebru et al., 2018](https://arxiv.org/abs/1803.09010)
- [Lost in the Middle: How Language Models Use Long Contexts — Liu et al., 2023](https://arxiv.org/abs/2307.03172)
- [NIST AI Risk Management Framework](https://www.nist.gov/itl/ai-risk-management-framework)
