# Retrievers and Query Engines

*A retriever finds the relevant Nodes; a query engine turns those Nodes into a grounded answer. Together they are the RAG pipeline — and the seams between them (postprocessing, response synthesis) are where you tune quality.*

You have Nodes in an index. Now you need to answer questions with them. LlamaIndex splits that into two composable pieces: a **retriever** that fetches the relevant Nodes for a query, and a **query engine** that wraps retrieval plus **response synthesis** into an end-to-end "ask, get a grounded answer" flow. Understanding the seam between them is what lets you tune a RAG system rather than treat it as a black box. This fourth post in the LlamaIndex series assembles the query pipeline.

## Retrievers: fetching the relevant Nodes

A **retriever** takes a query and returns the Nodes most relevant to it. The default retriever for a `VectorStoreIndex` does similarity search — embed the query, return the top-k nearest Nodes:

```python
retriever = index.as_retriever(similarity_top_k=5)
nodes = retriever.retrieve("What is our refund policy?")
```

`top_k` is the first knob: too low and you miss relevant context; too high and you flood the LLM with noise and cost. But similarity search isn't the only retrieval mode. Different index types expose different retrievers, and you can go further:

- **Metadata-filtered retrieval** — combine similarity with structured filters (this tenant, this date range, this document type). This is how you enforce access control and freshness, and it's built on the metadata you attached at ingestion.
- **Hybrid retrieval** — combine semantic (vector) search with keyword/sparse search, which catches exact terms, names, and codes that pure embeddings can miss.
- **Query transformation** — rewrite, expand, or decompose the query before retrieving (HyDE, sub-questions), improving recall on hard or multi-part questions.

These are the same retrieval-engineering ideas from the [Agentic RAG](/blog/series/agentic-rag/) series, exposed as LlamaIndex retrievers. The point: retrieval is pluggable and tunable, not a fixed similarity lookup.

## Node postprocessors: refining what was retrieved

Between retrieval and answer generation, LlamaIndex lets you insert **node postprocessors** that transform the retrieved Nodes — the most important being **reranking**. A retriever optimized for recall returns a generous candidate set; a reranker (a cross-encoder or an LLM) then reorders them by true relevance to the query and keeps the best few. This two-stage "retrieve broadly, rerank precisely" pattern is one of the highest-return upgrades to a RAG system, and in LlamaIndex it's just a postprocessor you add to the pipeline. Other postprocessors filter by similarity cutoff, by metadata, or fetch surrounding context — each a small, composable refinement of the Node set before it reaches the model.

## Query engines: retrieval plus synthesis

A **query engine** is the end-to-end object: give it a question, it retrieves, (optionally) postprocesses, and then **synthesizes a response** — assembles the Nodes into a prompt and calls the LLM to produce a grounded answer:

```python
query_engine = index.as_query_engine(similarity_top_k=5)
response = query_engine.query("What is our refund policy?")
print(response)              # the answer
print(response.source_nodes) # the Nodes it used — for citations
```

Notice `source_nodes`: the response carries the Nodes it was built from, so you can show citations and let users verify the answer against its sources — essential for trust and debugging. A query engine is really retriever + postprocessors + response synthesizer composed together, and each part is swappable.

## Response synthesis: how Nodes become an answer

**Response synthesis** is the step that turns retrieved Nodes into text, and it has strategies for different situations. When all the Nodes fit in the context window, they're stuffed into one prompt (`compact`/`refine`). When they don't, LlamaIndex can iterate — refine an answer across Nodes, or build a tree of summaries — so the pattern scales beyond a single context window. The synthesizer is also where the answer's grounding is enforced through prompting: answer *from the provided context*, and say when the context doesn't contain the answer. The concept to hold: getting the right Nodes is retrieval; turning them into a faithful, cited answer is synthesis, and both matter.

## The pipeline, assembled

Put it together and the RAG pipeline is a composition of swappable stages: **retriever** (get candidate Nodes, possibly filtered/hybrid/transformed) → **node postprocessors** (rerank and refine) → **response synthesizer** (build the grounded, cited answer). LlamaIndex gives you a sensible default for all of it in `index.as_query_engine()`, and then lets you open up and tune each stage as your quality needs grow. That layering — one line to start, every seam accessible when you need it — is the framework's core design, and it's why understanding these pieces individually pays off.

## Key takeaways

- A retriever fetches the Nodes most relevant to a query; `top_k` is the first knob, and retrieval can be metadata-filtered (access control, freshness), hybrid (semantic + keyword), or query-transformed (HyDE, sub-questions).
- Node postprocessors refine retrieved Nodes between retrieval and synthesis; reranking ("retrieve broadly, rerank precisely") is one of the highest-return RAG upgrades and is just a composable postprocessor here.
- A query engine composes retriever + postprocessors + response synthesizer into an end-to-end "ask, get a grounded answer" flow.
- Responses carry `source_nodes` — the Nodes the answer was built from — enabling citations, verification, and debugging.
- Response synthesis turns Nodes into a faithful answer with strategies (compact/refine/tree) that scale past a single context window; getting the right Nodes is retrieval, turning them into a grounded answer is synthesis, and both matter.

## Further reading

- [LlamaIndex documentation](https://docs.llamaindex.ai)
- [Agentic RAG series](/blog/series/agentic-rag/)
- [LlamaIndex, Concept by Concept — start of the series](/blog/posts/llamaindex-01-what-is-llamaindex.html)
