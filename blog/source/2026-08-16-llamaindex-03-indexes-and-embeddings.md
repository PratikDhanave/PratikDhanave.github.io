# Indexes and Embeddings

*An index is the data structure that makes your Nodes findable, and for RAG that almost always means embeddings in a vector store — but LlamaIndex offers more than one index type, and knowing which organizes your data for which query pattern is the point.*

Once your data is a set of Nodes, you need a way to *find* the relevant ones at query time. That's what an **index** is — a data structure over your Nodes optimized for retrieval. For RAG the workhorse is the `VectorStoreIndex`, built on **embeddings**, but LlamaIndex offers other index types for other access patterns. This third post in the LlamaIndex series covers indexes, embeddings, and where your vectors actually live.

## Embeddings: turning meaning into vectors

An **embedding** is a numeric vector that captures the meaning of a piece of text, such that semantically similar text has nearby vectors. LlamaIndex uses an embedding model to convert each Node into a vector, and retrieval then becomes "find the Nodes whose vectors are nearest the query's vector" — semantic search. The embedding model is a real choice: it affects retrieval quality, cost, latency, and dimension, and it's swappable in LlamaIndex.

Two practical points carry over from retrieval engineering. First, validate the embedding model on *your* data rather than trusting a leaderboard — the best model for your domain isn't always the top of a benchmark. Second, budget for the fact that **changing the embedding model means re-embedding your entire corpus** — every Node's vector must be recomputed — so it's a migration, not a config flip. Choose deliberately, and keep it swappable behind the framework.

## The VectorStoreIndex

The `VectorStoreIndex` is the default and most common index for RAG. It embeds every Node and stores the vectors so they can be searched by similarity:

```python
from llama_index.core import VectorStoreIndex

index = VectorStoreIndex.from_documents(documents)
```

That one call chunks the documents into Nodes, embeds each Node, and builds the searchable index. At query time it embeds the query and returns the nearest Nodes. It's the foundation of nearly every LlamaIndex RAG system, and for many applications it's all you need.

## Where the vectors live: storage and vector stores

By default the index keeps vectors in memory, which is fine for prototyping but not for production. LlamaIndex separates the *index* abstraction from the **vector store** that actually persists and searches the vectors, and it integrates with many — from `pgvector` on Postgres to dedicated vector databases (Qdrant, Milvus, Weaviate, and others). You point the index at a vector store and your embeddings persist and scale there.

Which vector store to use is its own decision — the [pgvector-vs-dedicated-vector-DB comparison](/blog/posts/ai-decisions-07-vector-storage.html) on this blog works it through — but the LlamaIndex point is that the choice is *pluggable*: you build against the index abstraction and swap the underlying store as your scale demands, from in-memory for a demo to Postgres for most systems to a dedicated vector DB at large scale. Also persist the index (via a storage context) so you don't re-embed on every restart — re-embedding a large corpus is slow and costly.

## Other index types

Vector search is the default, but it's not the only way to organize Nodes, and LlamaIndex offers alternatives for different query patterns:

- **Summary index** — keeps all Nodes and is suited to queries that need to consider the whole corpus (summarization over everything), not just the most similar chunks.
- **Document summary index** — stores a summary per document to route queries to the right documents first, then retrieve within them.
- **Knowledge-graph index** — extracts entities and relationships into a graph, for questions that hinge on relationships between things (the GraphRAG idea).
- **Composable / multi-index setups** — combine indexes and route a query to the right one.

The lesson is that "index" isn't synonymous with "vector search." Match the index to the query pattern: vector index for similarity-based Q&A (the common case), summary index for whole-corpus questions, knowledge-graph index for relationship-heavy questions. Most systems use a vector index; reach for the others when your queries don't fit similarity search.

## The ingestion pipeline

For production, the sequence of "load → chunk → embed → store" is worth formalizing as an **ingestion pipeline** — a repeatable process that transforms new or changed source data into indexed Nodes, ideally incrementally rather than re-processing everything. LlamaIndex provides an ingestion pipeline abstraction with transformations and caching, which matters because real data changes: new documents arrive, old ones update, some are deleted. A production RAG system needs to keep its index fresh (add new content, update changed content, remove deleted content — including propagating deletions for correctness and privacy), and doing that incrementally rather than rebuilding the whole index each time is the difference between a demo and a maintainable system. The production post returns to this; the concept to hold now is that indexing is an ongoing pipeline, not a one-time build.

## Key takeaways

- An index is a data structure over Nodes optimized for retrieval; for RAG it's usually a `VectorStoreIndex` built on embeddings (vectors capturing meaning, searched by similarity).
- The embedding model affects quality, cost, latency, and dimension — validate it on your data, and remember changing it forces re-embedding the whole corpus (a migration, not a flip).
- LlamaIndex separates the index from the pluggable vector store that persists/searches vectors (in-memory → pgvector → dedicated vector DB); persist the index so you don't re-embed on restart.
- Vector search isn't the only index: summary indexes suit whole-corpus questions, document-summary indexes route to the right docs, and knowledge-graph indexes handle relationship-heavy queries — match the index to the query pattern.
- Formalize load→chunk→embed→store as an incremental ingestion pipeline that keeps the index fresh (adds/updates/deletes, propagating deletions) rather than rebuilding each time.

## Further reading

- [LlamaIndex documentation](https://docs.llamaindex.ai)
- [Postgres/pgvector vs a Dedicated Vector Database](/blog/posts/ai-decisions-07-vector-storage.html)
- [Agentic RAG series](/blog/series/agentic-rag/)
