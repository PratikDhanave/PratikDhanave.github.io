# GraphRAG — Grounding an LLM in a Knowledge Graph

*This is the post the whole series was building toward. Retrieval-augmented generation gives an LLM relevant text to ground its answers, but plain RAG retrieves disconnected chunks and misses the relationships between facts. GraphRAG grounds the model in a knowledge graph instead — so it can follow relationships, reason across multiple hops, and answer questions that no single chunk contains. It's where ontologies stop being theory and become the thing that makes an AI system trustworthy on your domain.*

Posts 1–5 built the ontology and the knowledge graph. This post connects them to the LLM. The motivation is post 1's closing point: language models are fluent but factually shaky and have no stable model of *entities and their relationships*. A knowledge graph is exactly that missing piece. GraphRAG is the technique that feeds the graph's structured truth to the model — and understanding *why* it beats plain RAG on connected questions is understanding why this series matters for AI engineering.

## A quick recap of plain RAG, and where it falls short

**Retrieval-augmented generation (RAG)** improves an LLM by retrieving relevant documents and putting them in the prompt, so the model answers *from provided context* rather than from parametric memory alone — reducing hallucination and adding fresh, private knowledge. Standard RAG works by **vector similarity**: chunk your documents, embed them, and at query time retrieve the chunks whose embeddings are closest to the question. It's powerful and it's the default for a reason.

But vector RAG has a structural blind spot: it retrieves *independent chunks by surface similarity*, and it knows nothing about how facts relate. That breaks down on exactly the questions knowledge graphs are good at:
- **Multi-hop questions** — "Which drugs made by companies headquartered in Switzerland treat the disease that this gene causes?" The answer requires *chaining* relationships (gene → disease → drug → company → country). No single chunk contains that chain, so vector retrieval pulls fragments and the model has to guess the connections — which is to say, hallucinate them.
- **Aggregation / global questions** — "What are the main themes across all these incident reports?" needs a synthesized view of the whole corpus, not the top-k most similar chunks.
- **Relationship-sensitive precision** — vector similarity can retrieve a chunk that *mentions* the right entities but states the *wrong relationship* between them, and the model can't tell.

The root issue is that plain RAG discards structure. The knowledge is connected; the retrieval isn't.

## What GraphRAG adds

**GraphRAG** grounds retrieval in a knowledge graph so that *relationships* become part of what's retrieved. Instead of (or alongside) fetching similar text chunks, it retrieves a relevant *subgraph* — the entities in the question plus the connected entities and relationships around them — and feeds that structured context to the LLM. The model now sees not just facts but *how they connect*:

- **Multi-hop by traversal, not by luck.** For the Swiss-drug question, GraphRAG starts at the gene node and *walks the edges* (post 4's path queries) — gene → disease → drug → company → country — assembling the exact chain of facts the answer needs, then hands the model that chain. The connections are retrieved, not invented. This is the headline win: questions that require reasoning across relationships become reliable because the reasoning path is grounded in the graph.
- **Precise, verifiable context.** Because the retrieved facts are typed relationships from the graph (with provenance, post 5), the model's answer can be grounded in and cited back to specific, authoritative triples — far more verifiable than "a chunk that seemed relevant."
- **Global structure for summarization.** Graph community detection (clustering related entities) lets GraphRAG build hierarchical summaries of a whole corpus, so "what are the themes?" is answered from the graph's structure rather than a sample of chunks — the approach that made GraphRAG prominent for whole-corpus questions.
- **The ontology constrains and enriches.** Because the graph is typed (post 1) and reasoned (post 2), retrieval can exploit the ontology — follow only relevant relationship types, include inferred facts, and respect the domain's logic. The ontology makes retrieval *smart about meaning*, not just connectivity.

In short, GraphRAG retrieves *connected, typed, verifiable* context where plain RAG retrieves *isolated, untyped, similarity-ranked* text. On relationship-heavy domains that difference is the difference between an assistant that reliably reasons over your data and one that plausibly guesses.

## How it fits together — and when to use it

GraphRAG is the payoff that ties the series into a working system:
- The **ontology** (posts 1–2) defines the types and rules, so retrieved context is meaningful and the LLM's grounding respects the domain's logic.
- The **knowledge graph** (post 3), built through careful **construction and entity resolution** (post 5), is the authoritative, connected source of truth — and its quality directly bounds answer quality (a wrong edge becomes a confidently wrong answer, so post 5's rigor is what makes GraphRAG safe).
- **Graph queries** (post 4) are the retrieval mechanism — traversing from the question's entities to the relevant subgraph.
- The **LLM** supplies the fluency: it turns the retrieved subgraph into a natural-language answer, and often also helps *build* the graph by extracting entities and relations from text (post 5). The relationship is symbiotic — the graph grounds the model, and the model helps populate the graph.

The honest engineering judgment: GraphRAG is not a free upgrade. It requires building and maintaining a knowledge graph (the hard work of post 5), so it's worth it when your questions are genuinely *relationship-heavy, multi-hop, or global*, and when *verifiability* matters — regulated domains, complex internal knowledge, anything where "plausible" isn't good enough. For simple lookup-style Q&A over a document pile, plain vector RAG is cheaper and sufficient. Many mature systems are **hybrid**: vector retrieval for broad semantic recall *plus* graph retrieval for precise multi-hop grounding, getting both the coverage of embeddings and the precision of the graph. The skill is knowing that when an AI system keeps failing on "how are these connected?" questions, the fix usually isn't a bigger model or better embeddings — it's giving the model a graph to stand on.

The takeaway: plain **RAG** grounds an LLM in text chunks retrieved by **vector similarity**, but it retrieves *isolated, untyped* fragments and is blind to how facts relate — so it fails on **multi-hop** questions (whose answer is a *chain* of relationships no single chunk holds), **global/aggregation** questions, and relationship-precision. **GraphRAG** grounds the model in a **knowledge graph**: it retrieves a relevant **subgraph** by *traversing* relationships (post 4), so multi-hop answers come from walked edges rather than guessed connections, context is **typed, verifiable, and citable** (with provenance), community structure enables whole-corpus summarization, and the **ontology** makes retrieval smart about meaning. It ties the series together — ontology (types/rules) + knowledge graph (construction/resolution quality bounds answer quality) + graph queries (retrieval) + LLM (fluency, and graph-builder) — and it's worth its construction cost when questions are relationship-heavy/multi-hop/global and verifiability matters; otherwise plain vector RAG suffices, and many systems go **hybrid**.

## Key takeaways

- **RAG** grounds an LLM in retrieved documents (reducing hallucination, adding fresh/private knowledge), standardly via **vector similarity** over text chunks — but it retrieves *isolated, untyped* fragments and knows nothing about relationships.
- Vector RAG fails on **multi-hop** questions (answer is a *chain* of relationships — gene→disease→drug→company→country — no chunk contains it, so the model guesses/hallucinates the links), **global/aggregation** questions, and cases where a chunk mentions the right entities but the wrong relationship.
- **GraphRAG** retrieves a relevant **subgraph** by **traversing** the knowledge graph, so multi-hop chains are *walked, not invented*; context is **typed, verifiable, and citable** (provenance from post 5); **community detection** enables whole-corpus summarization; and the **ontology** lets retrieval follow relevant relationship types and include inferred facts.
- It ties the series together: **ontology** (meaning/rules) + **knowledge graph** (whose **construction/entity-resolution quality directly bounds answer quality** — a wrong edge → confidently wrong answer) + **graph queries** (the retrieval) + **LLM** (fluency, and often the graph's builder via extraction) — a symbiotic loop.
- GraphRAG isn't free (you must build/maintain the graph): use it for **relationship-heavy, multi-hop, global, or verifiability-critical** domains; use plain vector RAG for simple lookup Q&A; and consider **hybrid** (vector recall + graph precision). When an AI keeps failing "how are these connected?" questions, the fix is usually a graph to stand on, not a bigger model.

## Further reading

- [Retrieval-augmented generation — grounding LLMs in retrieved context](https://en.wikipedia.org/wiki/Retrieval-augmented_generation)
- [Knowledge graph — the structured grounding GraphRAG retrieves from](https://en.wikipedia.org/wiki/Knowledge_graph)
