# Building a Search System in Practice — Putting It All Together

*Knowing how inverted indexes, BM25, and vector search work is one thing; assembling them into a search system that's fast, relevant, and maintainable is another. This closing post is the practical synthesis — the architecture of a real search system, the choices that matter, and the hard-won operational lessons that no algorithm paper mentions. It turns the series into something you can actually build, whether it's a product search box or the retrieval layer of a RAG application.*

Posts 1–7 built the components; this post assembles them. The goal is the engineer's working picture: what a search system looks like end to end, what decisions you'll face, and how to run it well. And because the retrieval layer of a RAG system *is* a search system, everything here applies directly to building AI applications.

## The anatomy of a search system

A production search system is a pipeline with the offline/online split from post 1, now fully populated with the series' components:

**Indexing (offline):**
- **Ingest** documents from the source(s), handle updates and deletions.
- **Analyze** text into terms (post 3) — the tokenization/normalization choices that quietly set quality.
- **Build the index** — an inverted index for keyword search (post 2), and/or a vector index for semantic search (post 7), computing embeddings if hybrid.

**Querying (online):**
- **Understand the query** — analyze it the same way as documents (post 3), and optionally expand/rewrite it (spelling correction, synonyms, intent detection).
- **Retrieve candidates** — fetch matches from the inverted index (BM25) and/or the vector index, typically a few hundred to a few thousand.
- **Rank / rerank** — score with BM25, a learned ranker, or a neural reranker (posts 4, 6); fuse lexical and semantic results if hybrid (post 7).
- **Present** — return the top results, often with snippets, highlighting, and facets.

This retrieve-then-rank, offline-index/online-serve shape is universal — the same architecture whether you use Elasticsearch/OpenSearch for a product catalog, a vector database for a RAG app, or a hybrid of both. Internalizing this anatomy lets you reason about any search system by asking which component is doing what.

## The decisions that actually matter

Building search is a series of choices, and a few dominate the outcome:

- **Buy vs build.** Almost always, use an existing engine — **Elasticsearch/OpenSearch** or **Lucene/Solr** for keyword and increasingly hybrid, a **vector database** for semantic, or managed search services. Writing your own inverted index or ANN implementation is rarely justified; the value is in using these tools *well*, not reinventing them. This is the single most important practical decision, and the answer is usually "buy/adopt."
- **Keyword, semantic, or hybrid?** Match it to the queries (post 7): keyword for exact/structured/known-item search (catalogs, codes, logs), semantic for natural-language/conceptual search, **hybrid** when you have both — which, for most natural-language products and all RAG, you do. Default to hybrid unless you have a clear reason not to.
- **Analysis configuration** (post 3) — the tokenization, stemming, stop-word, and synonym choices, tuned to your language and domain. High-leverage and easy to under-invest in.
- **Relevance tuning** — field weights (title vs body), BM25 parameters, boosts for freshness/popularity, and whether to add learning-to-rank (post 6). This is ongoing, data-driven work, not a one-time setup.

The meta-point: most of the engineering is *configuration and tuning of existing components*, guided by evaluation — not algorithm implementation. Knowing the internals (this series) is what lets you configure and tune them intelligently.

## Operating search: the lessons papers don't mention

Finally, the operational realities that determine whether a search system stays good:

- **Measure relevance continuously** (post 5). Stand up offline evaluation (a test set with judgments) *and* online metrics (click-through, reformulation, A/B tests) from the start, because every tuning change needs a verdict and "it looks better" is not one. A search system without relevance measurement is flying blind, and this is the most common gap in real systems.
- **Relevance tuning never ends.** Queries, content, and user expectations shift, so relevance is a continuous process — monitor failing queries (zero results, high reformulation), and feed them back into analysis, synonyms, and ranking. The best search teams treat relevance as a product, not a project.
- **Performance and scale.** Watch query latency (the inverted index and ANN are fast, but reranking and large result sets add up), cache hot queries, and shard the index as it grows (post 2). Freshness vs cost is a real trade-off — how fast must new documents become searchable?
- **The data pipeline is where it breaks.** As in all ML (ML series, post 8), most production incidents are *data* problems — an analysis change that silently altered matching, an embedding model swap that shifted the vector space, a broken ingestion that staled the index. Monitor the pipeline, not just the query path.
- **For RAG specifically:** the retriever caps the system. An LLM can't answer from context it never received, so retrieval quality (measured with post 5's metrics) is the ceiling on RAG quality — which is why investing in hybrid retrieval and reranking usually helps a RAG app more than a bigger model. Chunking strategy (how documents are split before indexing) is the RAG-specific analysis decision that most affects quality.

The series' closing synthesis: a search system is the components of this series — analysis, inverted index, ranking, evaluation, learned and semantic retrieval — assembled into an offline-index/online-retrieve-then-rank pipeline, almost always built on existing engines, and kept good by *continuous relevance measurement and tuning*. The algorithms are 50 years old and brand new at once (BM25 beside embeddings), and the craft is combining them well for your queries and operating the result with discipline. Whether you're building a search box or the retrieval layer of an AI application, it's the same system and the same lessons — and the retrieval layer is, increasingly, where AI applications quietly succeed or fail.

The throughline: a production search system is an **offline-index / online-retrieve-then-rank pipeline** assembling the series' parts — **analyze** (post 3) → **index** (inverted + vector, posts 2,7) offline; **understand query → retrieve candidates → rank/rerank/fuse** (posts 4,6,7) → present, online — the same shape for a product catalog or a RAG retriever. The decisions that matter: **buy/adopt vs build** (almost always adopt Elasticsearch/OpenSearch/vector DBs — the value is using them well), **keyword vs semantic vs hybrid** (default hybrid for natural-language/RAG), analysis configuration, and ongoing relevance tuning — mostly *configuration guided by evaluation*, not algorithm implementation. Operate with **continuous relevance measurement** (offline + online/A-B, post 5), never-ending tuning, performance/scale care, and data-pipeline monitoring (most incidents are data problems). For **RAG**, the retriever **caps** system quality — so hybrid retrieval, reranking, and chunking strategy often help more than a bigger model.

## Key takeaways

- A search system is an **offline-index / online-retrieve-then-rank pipeline**: offline **analyze** (post 3) and **index** (inverted index post 2, and/or vector index post 7); online **understand the query → retrieve candidates → rank/rerank/fuse** (posts 4, 6, 7) **→ present** — the same architecture for a product catalog, a vector-DB RAG app, or a hybrid.
- The dominant decision is **buy/adopt vs build**: almost always adopt existing engines (**Elasticsearch/OpenSearch, Lucene/Solr, vector databases**) — the value is using them *well*, not reinventing inverted indexes or ANN.
- Choose **keyword vs semantic vs hybrid** by query type (keyword for exact/known-item, semantic for conceptual, **hybrid** for both — the default for natural-language products and all RAG); most engineering is **configuration + relevance tuning guided by evaluation**, not algorithm implementation.
- Operate with discipline: **continuous relevance measurement** (offline test sets + online CTR/reformulation/A-B, post 5 — "it looks better" is not a verdict), **never-ending tuning** (monitor failing/zero-result queries, feed back), **performance/scale** (latency, caching, sharding, freshness-vs-cost), and **data-pipeline monitoring** (most incidents are data problems, as in all ML).
- For **RAG**, the **retriever caps the system** (the LLM can't use context it never got), so retrieval quality is the ceiling — invest in **hybrid retrieval, reranking, and chunking strategy** (the RAG-specific analysis choice), often a bigger win than a larger model.

## Further reading

- [Information retrieval — the field this series builds](https://en.wikipedia.org/wiki/Information_retrieval)
- [Search engine indexing — the offline half of a search system](https://en.wikipedia.org/wiki/Search_engine_indexing)
