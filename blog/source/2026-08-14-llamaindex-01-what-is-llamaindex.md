# What Is LlamaIndex?

*LlamaIndex began as the fastest way to build RAG and has grown into a full data framework for LLM applications — connect your data, index it, retrieve it, and reason over it, with agents and workflows on top.*

If your LLM application needs to answer questions over *your* data — documents, databases, APIs — LlamaIndex is one of the most direct ways to build it. It started as a RAG library and has become a broader data framework: readers that ingest your data, a chunk model, indexes, retrievers, query engines, and, increasingly, agents and event-driven workflows on top. This series builds LlamaIndex up concept by concept; this first post covers what it is, its pipeline, and when to reach for it.

## The problem LlamaIndex solves

A base LLM knows nothing about your private data, and it goes stale. The fix is *context augmentation* — bringing your data to the model at query time — and the canonical form is retrieval-augmented generation (RAG). Building RAG yourself means wiring together document loading, chunking, embedding, a vector store, retrieval, reranking, and prompt assembly. LlamaIndex packages that whole pipeline into a coherent framework with sensible defaults, so you can go from "a folder of documents" to "ask questions over them" in a few lines, and then customize each stage as your needs grow.

That is its core value proposition: the shortest path from *your data* to *an LLM that can reason over it*, without hand-building the retrieval plumbing.

## The pipeline: connect → index → retrieve → respond

LlamaIndex's mental model is a data pipeline, and the primitives map onto its stages:

- **Readers** (data loaders, many from LlamaHub) ingest your sources — files, PDFs, databases, APIs — into **Documents**.
- **Documents** are split into **Nodes** — the chunks that get retrieved.
- **Indexes** (most commonly a `VectorStoreIndex`) organize Nodes for efficient retrieval, using **embeddings** and a vector store.
- **Retrievers** fetch the Nodes most relevant to a query.
- **Query engines** wrap retrieval plus response synthesis into an end-to-end "ask a question, get a grounded answer" flow.

The smallest complete example shows how much the framework does for you:

```python
from llama_index.core import VectorStoreIndex, SimpleDirectoryReader

documents = SimpleDirectoryReader("data").load_data()   # read a folder
index = VectorStoreIndex.from_documents(documents)        # chunk, embed, index
query_engine = index.as_query_engine()                    # retriever + synthesis
print(query_engine.query("What is our refund policy?"))
```

Four lines take you from a folder to grounded question-answering. Under those four lines is the whole RAG pipeline — and each stage (reader, chunking, embedding, index, retriever, synthesizer) is customizable when the defaults aren't enough. That "simple by default, deep when needed" layering is central to LlamaIndex.

## More than RAG: agents and workflows

LlamaIndex in its current form is no longer just a RAG indexing library. It has grown into an **event-driven workflow framework** with agents, a production runtime, and built-in observability and evaluation. Two additions matter:

- **Agents** — an LLM that decides which action or tool to use given the conversation and the latest message. Crucially, a LlamaIndex *query engine can be exposed as a tool*, so an agent can decide *when* to retrieve — the agentic-RAG pattern, built in.
- **Workflows** — an event-driven abstraction for orchestrating steps and LLM calls, the modern core for building complex agentic applications in LlamaIndex.

So the framework spans from "four-line RAG" to "orchestrated multi-step agentic system," with the same primitives underneath. Later posts cover the agent and workflow layers; know now that LlamaIndex is a data *and* agent framework, not only a retrieval library.

## How it relates to what you already know

If you've read the [Agentic RAG](/blog/series/agentic-rag/) series, LlamaIndex is largely an *implementation* of those ideas — retrieval, reranking (via node postprocessors), query transformation, and agentic retrieval are all first-class here. This series focuses on the framework's concepts and how to use them; the *why* behind good retrieval lives in that RAG series, and the two complement each other: read Agentic RAG for the principles, this series for the LlamaIndex realization.

## When to use LlamaIndex — and when not

LlamaIndex fits when your application is fundamentally about *reasoning over your data*: RAG systems, document Q&A, knowledge assistants, and agentic apps that need retrieval. Its readers, index abstractions, and query engines save real work, and it scales from a prototype to a customized production pipeline.

It's less compelling when your app isn't data-centric — a pure orchestration or tool-using agent with no retrieval need doesn't benefit much from LlamaIndex's data-framework strengths, and a general agent framework may fit better (the [agent-framework comparison](/blog/posts/ai-decisions-02-agent-frameworks.html) covers that choice). And for a trivial one-off retrieval you might not need a framework at all. As always, match the tool to the shape of the problem: LlamaIndex is the strong choice when data and retrieval are at the center.

## Where the series goes

From here we go primitive by primitive: documents and nodes (ingesting and chunking data), indexes and embeddings (organizing it for retrieval), retrievers and query engines (the RAG pipeline assembled), chat engines and memory (conversational retrieval), agents and tools (agentic RAG, RAG-as-a-tool), workflows (event-driven orchestration), and production (ingestion, evaluation, observability). By the end you'll be able to build data-centric LLM applications in LlamaIndex from a four-line prototype to a customized production system.

## Key takeaways

- LlamaIndex is a data framework for LLM apps: the shortest path from your data to an LLM that can reason over it, packaging the whole RAG pipeline with customizable stages.
- Its pipeline is connect → index → retrieve → respond: readers ingest Documents, Documents split into Nodes, indexes (VectorStoreIndex) organize them via embeddings, retrievers fetch relevant Nodes, and query engines add synthesis.
- Four lines take you from a folder to grounded Q&A, with every stage customizable when defaults aren't enough — "simple by default, deep when needed."
- It's now more than RAG: agents (with query engines exposed as tools for agentic RAG) and event-driven workflows make it a data *and* agent framework with production runtime and eval/observability.
- Use LlamaIndex when your app is fundamentally about reasoning over your data; a general agent framework may fit better for non-data-centric orchestration.

## Further reading

- [LlamaIndex documentation](https://docs.llamaindex.ai)
- [run-llama/llama_index on GitHub](https://github.com/run-llama/llama_index)
- [Agentic RAG series](/blog/series/agentic-rag/)
