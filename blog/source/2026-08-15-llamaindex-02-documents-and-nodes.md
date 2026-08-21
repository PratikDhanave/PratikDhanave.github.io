# Documents and Nodes

*Everything LlamaIndex retrieves is a Node, and the quality of your Nodes — how you load your data and how you chunk it — sets the ceiling on everything downstream, no matter how good your model or retriever is.*

Before LlamaIndex can index or retrieve anything, your data has to become its two foundational objects: **Documents** and **Nodes**. This is the least glamorous part of a RAG system and the most decisive — retrieval quality is bounded by chunk quality, so getting ingestion and chunking right matters more than almost anything you tune later. This second post in the LlamaIndex series covers loading data and turning it into good Nodes.

## Readers: getting data in

Data enters LlamaIndex through **readers** (data loaders). The built-in `SimpleDirectoryReader` handles a folder of common file types, and **LlamaHub** provides a large ecosystem of readers for other sources — databases, Notion, Slack, web pages, APIs, and many more. A reader's job is to turn a source into **Documents**.

```python
from llama_index.core import SimpleDirectoryReader

documents = SimpleDirectoryReader("data").load_data()
```

The reader you choose matters because it determines what raw text and metadata you start from. For messy real-world sources — complex PDFs with tables, scanned documents, layout-heavy files — naive text extraction loses structure, and LlamaIndex offers stronger parsing (LlamaParse) for exactly those hard documents. The principle: garbage extraction in, garbage retrieval out, so invest in getting clean, well-structured Documents from your real sources rather than accepting whatever the simplest loader produces.

## Documents: your data with metadata

A **Document** is LlamaIndex's container for a piece of source data — its text plus **metadata** (source, title, dates, tags, whatever you attach). Metadata is not an afterthought: it travels with the data through chunking and becomes filterable at retrieval time. Attaching good metadata — the source document, a section, an access-control tag, a date — is what later lets you retrieve *only* the right subset (this tenant's docs, recent content, a specific manual) rather than searching everything. Set metadata thoughtfully at the Document stage; it pays off throughout the pipeline.

## Nodes: the unit of retrieval

Documents are usually too large to retrieve or embed whole, so LlamaIndex splits them into **Nodes** — chunks of a Document, each with its own text, metadata (inherited and added), and relationships back to its source and neighbors. **Nodes are the atomic unit of retrieval**: when you query, LlamaIndex returns the most relevant Nodes, not whole Documents. Everything downstream — embedding, indexing, retrieval, the context handed to the LLM — operates on Nodes.

This is why chunking is the highest-leverage decision in the pipeline. A Node that splits a concept in half retrieves poorly; one that crams several topics together matches loosely and pollutes the context. Good Nodes are each about *one* thing, sized to be specific enough to match precisely yet complete enough to stand alone.

## Chunking: the decision that sets the ceiling

LlamaIndex controls chunking through **node parsers / text splitters**, and the choices mirror the retrieval-engineering principles from the [Agentic RAG](/blog/series/agentic-rag/) series:

- **Chunk size and overlap.** Smaller chunks are more precise but risk losing context; larger ones carry more context but retrieve less precisely. A modest overlap keeps ideas from being severed at boundaries. There's no universal number — it depends on your content, and it's worth tuning against your evals.
- **Structure-aware splitting.** Splitting on natural boundaries (sentences, paragraphs, sections, or document structure) beats blindly cutting every N characters, because it keeps coherent ideas together. Layout-aware parsing matters especially for PDFs and tables.
- **Small-to-big / parent retrieval.** Embed small, precise chunks for matching but return the larger parent Node for context — a pattern LlamaIndex supports that materially improves relevance.

The takeaway: don't accept default chunking blindly. It sets the ceiling on retrieval quality, and no reranker, bigger model, or clever prompt recovers information that bad chunking scattered or severed.

## Metadata and relationships pay off later

Two properties of Nodes become powerful downstream. **Metadata filtering** lets retrieval combine similarity search with structured predicates — "find chunks similar to this query *and* from this product's manual *and* updated this year" — which is essential for access control, multi-tenancy, and freshness. And **relationships** (a Node knowing its source Document and neighboring Nodes) enable patterns like fetching surrounding context or tracing an answer back to its origin. Both are set up here, at the Document/Node stage, and both are why thoughtful ingestion is an investment, not overhead.

## Key takeaways

- Data enters LlamaIndex via readers (SimpleDirectoryReader, plus a large LlamaHub ecosystem) that turn sources into Documents; use stronger parsing (LlamaParse) for messy PDFs/tables/scans.
- A Document is text plus metadata; metadata travels through the pipeline and becomes filterable at retrieval, so attach source/section/tags/dates deliberately.
- Nodes are chunks of Documents and the atomic unit of retrieval — everything downstream operates on Nodes, which is why chunk quality bounds retrieval quality.
- Chunking is the highest-leverage decision: tune size/overlap, split on natural structure (not blind N-character cuts), and consider small-to-big/parent retrieval; defaults are a starting point, not an answer.
- Node metadata (for filtering — access control, multi-tenancy, freshness) and relationships (for context/traceability) are set at ingestion and pay off throughout, making thoughtful ingestion an investment.

## Further reading

- [LlamaIndex documentation](https://docs.llamaindex.ai)
- [Agentic RAG series](/blog/series/agentic-rag/)
- [LlamaIndex, Concept by Concept — start of the series](/blog/posts/llamaindex-01-what-is-llamaindex.html)
