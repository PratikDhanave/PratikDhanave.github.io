# Grounding AI in the Customer's Data

*A frontier model knows the public internet and nothing about the customer. All the value of an AI deployment comes from the opposite: making the model reason over the customer's own documents, records, and knowledge. Grounding is the technical heart of the AI forward deployed engineer's job — connecting a general model to a specific company's messy, permissioned, incomplete data so its answers are about their reality, not the model's imagination.*

Every previous post pointed here. Scoping (post 2) required the knowledge to be retrievable; the demo-to-pilot chasm (post 3) was mostly grounding work. This post is the reference architecture: how you connect a model to a customer's data so it produces trustworthy, specific answers. It's where an AI FDE spends much of their time, and where the deployment either becomes real or stays a toy.

## Why grounding is the whole game

An ungrounded LLM answering questions about a customer's business is guessing. It will produce fluent, confident text that draws on general knowledge and pattern-matching — and for anything specific to the company, it will confabulate, because it has no access to the facts. That's unusable in an enterprise, where answers must be about *this* company's actual contracts, tickets, policies, and records.

**Grounding** fixes this by giving the model the relevant real information at answer time, so it reasons over facts instead of inventing them. The dominant technique is **retrieval-augmented generation (RAG)**: retrieve the pieces of the customer's data relevant to a query, put them in the model's context, and instruct the model to answer *from that provided information*. Grounding is what converts the model from an impressive generalist into a system that answers correctly about the customer's world — and it's why the customer's data, not the model, is where the value lives.

## The reference architecture

Here's the shape of a grounded AI system an FDE deploys at a customer. Two flows: an offline **ingestion** path that indexes the customer's data, and an online **query** path that answers using it.

```
  CUSTOMER DATA                INGESTION (offline)              INDEX
  ┌──────────────┐   connect   ┌──────────────────┐  chunks    ┌──────────────┐
  │ Docs, tickets│────────────▶│ Ingest + clean +  │──────────▶│ Vector store │
  │ DBs, wikis   │  (permissioned│ chunk + embed    │  vectors  │ + metadata   │
  └──────────────┘   sync)      └──────────────────┘           └──────┬───────┘
                                                                       │ retrieve
                                                                       │ (top-k, filtered
   QUERY (online)                                                      │  by permissions)
  ┌──────────┐   query   ┌──────────────┐   context   ┌───────────┐   │
  │  User /   │─────────▶│  Retrieval    │◀────────────┤           │◀──┘
  │  workflow │          │  + rerank     │─────────────▶│   LLM     │
  └────┬─────┘           └──────────────┘   grounded   │ (via      │
       │                                     prompt     │  gateway) │
       │                 ┌──────────────┐              └─────┬─────┘
       │◀────────────────┤  Guardrails   │◀───────────────────┘
        answer +         │  + citations  │   answer
        sources          └──────────────┘
```

> **▸ [Open the interactive diagram](/blog/handbook-diagrams/ai-fde-grounded-architecture.html)** — pan, zoom, focus each component, and trace the ingestion and query flows; light/dark, self-contained.

The components, and what makes each hard at a real customer:

- **Data sources.** The customer's documents, tickets, databases, wikis, emails — scattered across systems you don't control, in inconsistent formats, with varying quality. Just *getting access* is often the first real obstacle (post 3's "real data" made concrete).
- **Ingestion pipeline.** Connect to each source, extract text, **clean** it (the data is messy — duplicates, boilerplate, outdated versions), **chunk** it into retrievable pieces, and **embed** each chunk into a vector. Chunking and cleaning quality directly determine retrieval quality — this unglamorous work is where a lot of the outcome is decided.
- **Vector store + metadata.** A [vector database](https://en.wikipedia.org/wiki/Vector_database) holds the embeddings for similarity search, alongside metadata (source, date, and crucially **permissions**). Metadata is not optional: it's how you filter retrieval by who's allowed to see what.
- **Retrieval + rerank.** At query time, embed the query, find the most similar chunks, optionally rerank for precision, and filter by the user's permissions. This is the same retrieve-then-rank pattern that structures search and recommendation — retrieve broadly and cheaply, then rank precisely.
- **The LLM, via a gateway.** The retrieved context plus the query go to the model in a grounded prompt ("answer using only this information; if it's not here, say so"). Routing the call through an [AI gateway](/blog/series/ai-gateways-and-llm-infrastructure/) gives you provider-independence, caching, rate limits, cost control, and logging — infrastructure you'll want from day one.
- **Guardrails + citations.** Check the output, and — critically for trust — return the **sources** the answer was grounded in, so users can verify. Citations turn "trust the AI" into "check the AI," which is often what makes an enterprise willing to adopt it.

## The data reality (what the demo skipped)

Grounding is where the demo's clean sample data collides with reality, and handling that collision is the job:
- **The data is messy.** Inconsistent formats, duplicates, contradictions, stale versions, scanned PDFs, tables, and things that barely parse. Profiling and cleaning the data is real, substantial work — and skipping it produces a system that retrieves garbage and answers confidently from it.
- **The data is permissioned.** Different users can see different things. Retrieval **must** respect the customer's access controls — a system that surfaces a document to someone who shouldn't see it is a security incident, not a bug. Permission-aware retrieval is a hard requirement, not a nice-to-have.
- **The data is incomplete and changing.** The answer to some questions isn't in the data at all (the system must say "I don't know," not invent), and the data changes constantly (so ingestion must re-sync, and the index must stay fresh — post 7's freshness problem).
- **The data lives in systems you don't control.** You integrate with the customer's sources loosely and defensively, because they'll change, break, and rate-limit you. This is the general FDE integration discipline applied to feeding an AI system.

## Grounding quality is a dial you tune

Grounding isn't binary — retrieval quality directly drives answer quality, and improving it is much of the pilot-to-production work:
- **Better chunking** — chunks that are coherent units of meaning retrieve better than arbitrary splits.
- **Better retrieval** — hybrid search (keyword + vector), reranking, and query rewriting improve which chunks reach the model; the right context is everything, because the model can only reason over what you retrieve.
- **Better prompting** — clear instructions to use only the provided context, cite sources, and abstain when the answer isn't present.
- **Evaluation-driven tuning** — you improve grounding by *measuring* retrieval and answer quality on the customer's real questions (post 5) and fixing what's weak, not by guessing.

The key insight: when a grounded system gives a wrong or vague answer, the cause is usually *retrieval* (the right information didn't reach the model), not the model itself. Debugging grounded AI is largely debugging retrieval — a very different skill from prompt-tweaking, and one the AI FDE lives in.

The takeaway: grounding is the technical heart of AI deployment — a frontier model knows the internet and nothing about the customer, so all the value comes from making it reason over the customer's own data via retrieval-augmented generation. The reference architecture is an offline ingestion path (connect, clean, chunk, embed into a permissioned vector store) and an online query path (retrieve, rerank, filter by permissions, ground the model via a gateway, return answers with citations). The hard part isn't the model — it's the customer's messy, permissioned, incomplete data living in systems you don't control, and the truth that when a grounded system answers badly, the fix is almost always better retrieval.

## Key takeaways

- An **ungrounded LLM guessing about a customer's business will confabulate** — all the value comes from **grounding** it in the customer's own data via **retrieval-augmented generation (RAG)**: retrieve relevant facts, put them in context, answer from them.
- The reference architecture has two flows: **offline ingestion** (connect → clean → chunk → embed into a **permissioned vector store**) and **online query** (embed query → retrieve → rerank → filter by permissions → ground the LLM → return answer **with citations**).
- The hard part is the **data reality the demo skipped**: it's **messy** (cleaning/chunking is real work), **permissioned** (retrieval must respect access controls — a hard security requirement), **incomplete and changing** (say "I don't know"; keep the index fresh), and lives in **systems you don't control**.
- Route the model call through an **AI gateway** for provider-independence, caching, cost control, and logging; return **citations** so users can verify — turning "trust the AI" into "check the AI," which is often what unlocks adoption.
- **Grounding quality is a dial** (chunking, hybrid retrieval + rerank, prompting, eval-driven tuning): when a grounded system answers wrong, the cause is usually **retrieval, not the model** — so debugging grounded AI is mostly debugging retrieval.

## Further reading

- [Retrieval-Augmented Generation for Knowledge-Intensive NLP Tasks — Lewis et al. (arXiv:2005.11401)](https://arxiv.org/abs/2005.11401)
- [Retrieval-augmented generation — overview](https://en.wikipedia.org/wiki/Retrieval-augmented_generation)
