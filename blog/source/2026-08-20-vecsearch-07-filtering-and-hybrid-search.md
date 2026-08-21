# Filtering, Hybrid Search, and Recall

*Real search is never pure vector similarity. Users want "similar documents from this project, updated this year" and they expect an exact product code to match exactly. Combining similarity with metadata filters and keyword search — without wrecking recall — is where academic ANN meets production requirements, and it's harder than it looks.*

The previous posts built fast, memory-efficient similarity search. But production search has constraints similarity alone can't express: access control ("only this user's documents"), freshness ("last 30 days"), and exact matches (a part number, a name) that embeddings handle poorly. This post covers **metadata filtering**, **hybrid search** (dense + sparse), and how both interact with the recall you worked to achieve. This is where the vector-search internals meet the retrieval-quality lessons of the [Agentic RAG](/blog/series/agentic-rag/) series.

## Metadata filtering: similarity with conditions

Almost every real query combines "similar to X" with structured predicates: *find chunks similar to this query **and** from this tenant **and** of type 'manual' **and** updated this year.* The vectors carry the semantic part; **metadata** attached to each vector (tenant, type, date, tags) carries the structured part. Filtering is essential for:

- **Access control / multi-tenancy** — restrict results to the querying user's or tenant's data. This is a *correctness and security* requirement, not an optimization — returning another tenant's data is a breach.
- **Freshness** — limit to recent content.
- **Categorization** — restrict to a document type, source, language, or status.

The subtlety is *when* the filter is applied relative to the ANN search, and it creates a genuine dilemma:

- **Post-filtering** — do the ANN search first, then discard results that fail the filter. Simple, but dangerous for recall: if you retrieve the top 100 by similarity and *then* filter, you might be left with very few (or zero) that match the filter — the true matching neighbors may have ranked below your retrieval cutoff and never been fetched. A selective filter (matches few vectors) makes post-filtering fail badly.
- **Pre-filtering** — restrict to vectors passing the filter *first*, then do similarity search only among those. Gives correct, complete results, but is harder to do efficiently: the ANN index (IVF cells, HNSW graph) is built over *all* vectors, and restricting to a subset can break the index's structure — a graph walk may need to traverse through filtered-out nodes, and cells may be mostly filtered away.

This **filtering problem** is a real engineering challenge in vector databases, and different systems solve it differently — filtered HNSW traversal, partitioned indexes per filter value, or hybrid strategies that switch between pre- and post-filtering based on filter selectivity. The practical points: understand which strategy your vector database uses, be aware that *highly selective filters* are the hard case (where naive post-filtering silently returns too few results), and test recall *with your filters applied*, not just on unfiltered search.

## Hybrid search: dense meets sparse

Vector (dense) search is superb at *semantic* similarity but has a well-known blind spot: it can miss **exact matches** — specific keywords, names, product codes, error codes, rare terms — because embeddings capture meaning, not exact tokens. A query for error code "E-4021" or a specific person's name may not retrieve the document that contains it verbatim, because that exact string isn't semantically distinctive to the embedding.

**Hybrid search** fixes this by combining **dense** (vector) search with **sparse** (keyword/lexical) search — classic term-based retrieval like BM25:

```text
query → ┌─ dense (vector) search  → semantically similar results
        └─ sparse (keyword) search → exact-term matches (BM25)
              │
              ▼  fuse the two ranked lists
        combined ranking (e.g. Reciprocal Rank Fusion)
```

Each covers the other's weakness:

- **Dense** finds conceptually related content that shares no keywords ("password reset" ≈ "forgot login").
- **Sparse** finds exact terms, codes, names, and rare words that embeddings gloss over.

The two result lists are **fused** into one ranking — a common method is **Reciprocal Rank Fusion (RRF)**, which combines rankings by how highly each result appears in each list, without needing the scores to be on the same scale. Hybrid search reliably outperforms either method alone for real-world queries, which is why it's now standard in serious retrieval systems and a key recommendation from the RAG series. If your search must handle both natural-language questions *and* exact identifiers (most do), hybrid is the answer.

## Reranking: the recall recovery step

Both filtering and quantization (previous post) can cost recall, and the ANN trade itself means the first-pass results are approximate. **Reranking** is the standard way to recover quality: retrieve a *generous* candidate set with fast approximate search, then reorder it with a slower, more accurate model that scores true relevance to the query.

This "retrieve broadly, rerank precisely" pattern (from the Agentic RAG series) is especially valuable in vector search because:

- It **recovers recall lost to approximation** — casting a wide net in the fast ANN pass, then letting a precise reranker (a cross-encoder, or exact distance on full-precision vectors) fix the ordering, means the true best results surface even if the ANN ranking was rough.
- It **combines cleanly with hybrid search** — fuse dense and sparse candidates, then rerank the merged set for a final high-quality ordering.
- It **lets you tune fast search for recall, not precision** — the ANN pass just needs to *include* the true neighbors in its candidate set (high recall); the reranker handles precise ordering, so you can run the ANN pass looser/faster.

The design principle: don't ask one stage to be both fast and perfectly accurate. Retrieve broadly and approximately, then rerank narrowly and precisely — the two-stage pipeline hits both speed and quality.

## Putting real queries together

A production retrieval query typically layers all of these:

1. **Apply metadata filters** (pre-filter for correctness, especially for access control — never leak across tenants).
2. **Run hybrid retrieval** (dense + sparse) over the filtered set to catch both semantic and exact matches.
3. **Fuse** the dense and sparse results (e.g. RRF) into one candidate list.
4. **Rerank** the fused candidates with a precise model to recover recall and order by true relevance.
5. **Return** the top few to the LLM (in RAG) or the user.

Each stage addresses a specific gap: filters for correctness/scope, hybrid for exact-match blind spots, reranking for approximation loss. Skipping stages is where retrieval quietly underperforms — pure vector search with post-filtering and no reranking is a common, fixable cause of "RAG that misses the obvious answer."

## Key takeaways

- Real queries combine similarity with metadata filters (tenant/access-control, freshness, type) — and filter timing matters: post-filtering (search then discard) can silently return too few results for selective filters, while pre-filtering (restrict then search) is correct but harder to do efficiently over an ANN index.
- The filtering problem is a genuine vector-DB engineering challenge (highly selective filters are the hard case); know your system's strategy and always test recall *with filters applied*, and never leak across tenants (a security requirement).
- Dense (vector) search misses exact matches — codes, names, rare terms — so hybrid search combines it with sparse/keyword search (BM25), fusing the two rankings (e.g. Reciprocal Rank Fusion) to cover both semantic and exact-match needs; it reliably beats either alone.
- Reranking recovers recall lost to ANN approximation, quantization, and filtering: retrieve a broad candidate set fast, then reorder with a precise model (cross-encoder or exact distance) — letting you tune the fast pass for recall and the reranker for precision.
- Production retrieval layers all of it: filter (correctness/scope) → hybrid retrieve (semantic + exact) → fuse → rerank (recover recall/order) → return; skipping stages is a common, fixable cause of retrieval that misses obvious answers.

## Further reading

- [Vector quantization (previous post)](/blog/posts/vecsearch-06-vector-quantization.html)
- [Agentic RAG series — query transformation, reranking, evaluation](/blog/series/agentic-rag/)
- [The nearest neighbor problem — recall as the quality metric](/blog/posts/vecsearch-01-nearest-neighbor-problem.html)
