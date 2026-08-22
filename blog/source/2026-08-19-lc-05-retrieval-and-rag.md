# Retrieval and RAG

*Answering questions over your own data is the most common LLM application, and LangChain gives you the whole pipeline as composable, swappable components — loaders, splitters, embeddings, vector stores, retrievers — behind standard interfaces. The retriever, in particular, is just another Runnable, so RAG becomes a chain like any other.*

Retrieval-augmented generation is where LangChain's component model and its integration breadth pay off most, because RAG has *many* moving parts and LangChain provides a standard, swappable component for each. This post covers LangChain's retrieval stack — how documents become searchable and how the **retriever** abstraction plugs into chains. The deep *why* of RAG lives in the [Agentic RAG](/blog/series/agentic-rag/) and [LlamaIndex](/blog/series/llamaindex-concept-by-concept/) series; this post is specifically how LangChain does it.

## The retrieval pipeline as components

RAG requires getting your data into a searchable form and then retrieving relevant pieces at query time. LangChain models each stage as a component with a standard interface, so the pipeline is composable and each piece is swappable:

- **Document loaders** — ingest data from sources (files, PDFs, web pages, databases, APIs) into LangChain **Documents**. LangChain's integration breadth shines here: loaders exist for a huge range of sources, so you rarely write ingestion glue.
- **Text splitters** — split Documents into chunks (the chunking decision the RAG/LlamaIndex series stress as setting the retrieval-quality ceiling). LangChain offers splitters with configurable size/overlap and structure-aware options.
- **Embedding models** — turn chunks into vectors, behind a standard embeddings interface (so the embedding provider is swappable, like the chat model).
- **Vector stores** — store and search the vectors. LangChain integrates with many vector stores (pgvector, and dedicated vector databases) behind one interface, so you swap the store without changing your code — the store-agnostic standardization from the first post.
- **Retrievers** — the query-time component that fetches relevant chunks for a question (below).

The key point is that each stage is a *standard, swappable component with a rich integration catalog*. Building RAG in LangChain is largely selecting and composing these components — pick a loader for your source, a splitter, an embedding model, a vector store — rather than writing each from scratch. And because the choices are behind standard interfaces, you can change any of them (a different vector store, a different embedding model) with minimal code change, which is exactly LangChain's standardization value applied to RAG.

## The retriever: RAG's key abstraction

The **retriever** is LangChain's central retrieval abstraction: given a query, it returns relevant Documents. Crucially, a retriever is **just a Runnable** (the LCEL post), which is what makes RAG compose so cleanly — the retriever plugs into a chain exactly like a prompt or model:

```python
# Illustrative shape — see the LangChain docs for exact API.
retriever = vector_store.as_retriever(search_kwargs={"k": 4})

rag_chain = (
    {"context": retriever, "question": RunnablePassthrough()}
    | prompt | model | output_parser
)
```

Because the retriever is a Runnable, it slots into the RAG chain from the last post as one more composable step — retrieve context in parallel with forwarding the question, then generate. This is the elegance of LangChain's design: retrieval isn't a special subsystem, it's a component that composes like everything else. And retrievers are pluggable in a deeper sense — the retriever abstraction covers *different retrieval strategies*, not just basic vector search:

- **Vector store retriever** — the common case: similarity search over embeddings.
- **Retrievers with different strategies** — hybrid (combining semantic and keyword search — the [vector-search filtering post](/blog/posts/vecsearch-07-filtering-and-hybrid-search.html)), retrievers that rerank, retrievers that do query transformation, multi-query retrievers, and more.
- **Non-vector retrievers** — retrievers backed by search engines, databases, or other sources, all behind the same interface.

So "retriever" is a swappable strategy behind one interface: you can upgrade from basic similarity to hybrid-plus-reranking (the retrieval-quality improvements from the Agentic RAG series) by changing the retriever, while the chain around it stays the same. That's the retrieval-engineering advice from the RAG series, made pluggable.

## Connecting to retrieval quality

LangChain gives you the *components*; the *quality* of your RAG still depends on the retrieval-engineering decisions those other series cover, and LangChain is where you apply them:

- **Chunking** — the splitter's size/overlap/structure choices set the ceiling on retrieval quality (the LlamaIndex documents-and-nodes lesson). LangChain gives you the splitters; choosing them well is on you.
- **Embedding model choice** — affects retrieval quality, cost, and requires re-embedding to change (the embeddings lesson); LangChain makes it swappable, but the choice matters.
- **Retrieval strategy** — basic similarity often underperforms; hybrid search, reranking, and query transformation (the Agentic RAG improvements) materially help, and LangChain exposes them as retriever configurations/components.
- **Metadata filtering** — restricting retrieval by metadata (tenant, date, type — the vector-search filtering post) for correctness and relevance, supported through the retriever/vector-store interface.

The relationship to internalize: **LangChain provides the pluggable RAG machinery; the RAG/LlamaIndex/vector-search series provide the principles for using it well.** LangChain won't automatically give you good retrieval — it gives you the components and makes the good techniques (hybrid, reranking, filtering) available to compose. Applying those techniques is what turns a basic LangChain RAG chain into a good one.

## Building RAG in LangChain

The practical shape, tying it together:

- **Ingest** with the loader for your source and a well-chosen splitter (chunking sets the ceiling).
- **Embed and store** with a standard embedding model and a vector store (both swappable), building your searchable index.
- **Retrieve** with a retriever — start simple (vector similarity), then upgrade the retriever to hybrid/reranking/filtered as quality needs grow, without changing the surrounding chain.
- **Compose** the retriever into a RAG chain (retrieve in parallel with the question → prompt → model → parser), which is a Runnable like any other.
- **Improve on evidence** — measure retrieval quality (the eval discipline) and upgrade the retriever/splitter/embeddings accordingly.

RAG is LangChain's most compelling use case because it's exactly where the component model and integration breadth deliver most: a many-part pipeline built from standard, swappable, composable pieces, with the retriever slotting into chains as one more Runnable. The next post covers giving LangChain applications the ability to *act* — tools and agents.

## Key takeaways

- LangChain models the RAG pipeline as standard, swappable components with a rich integration catalog — document loaders, text splitters, embedding models, vector stores, retrievers — so building RAG is largely selecting and composing pieces rather than writing them, and any piece is swappable behind its interface.
- The retriever is RAG's key abstraction and is just a Runnable, so it composes into chains exactly like a prompt or model — retrieval isn't a special subsystem but a component that plugs into the RAG chain.
- Retrievers are pluggable strategies behind one interface: basic vector similarity, hybrid (semantic + keyword), reranking, query transformation, multi-query, and non-vector retrievers — so you upgrade retrieval quality by changing the retriever while the chain stays the same.
- LangChain provides the machinery; retrieval *quality* still depends on the decisions the RAG/LlamaIndex/vector-search series cover — chunking (sets the ceiling), embedding choice, retrieval strategy (hybrid/rerank/filter), and metadata filtering — which LangChain makes available to compose, not automatic.
- Build RAG by ingesting with a loader + well-chosen splitter, embedding into a swappable vector store, retrieving with a retriever you upgrade over time, composing it into a RAG chain, and improving on measured evidence.

## Further reading

- [Chains and composition (previous post)](/blog/posts/lc-04-chains-and-composition.html)
- [Agentic RAG series — retrieval quality in depth](/blog/series/agentic-rag/)
- [Vector Search Internals — hybrid search and filtering](/blog/posts/vecsearch-07-filtering-and-hybrid-search.html)
