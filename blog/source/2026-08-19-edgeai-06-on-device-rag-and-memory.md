# On-Device RAG and Memory

*An on-device model only knows what's baked into its weights — nothing about the user's notes, messages, or documents. On-device RAG fixes that by doing retrieval entirely on the phone: embed the user's data locally, store the vectors locally, and retrieve locally, so the model can reason over personal data that never touches a server. It's the technique that makes a private assistant actually useful.*

A local Gemma model is capable but ignorant of the user's world. To answer "what did I spend on groceries last month?" or "summarize my notes about the project," it needs the user's *data* — and the whole point of on-device AI is that this data must not leave the device. **On-device RAG** (retrieval-augmented generation) is how you square that circle: the entire retrieval pipeline runs locally. This post adapts the RAG concepts from the [Agentic RAG](/blog/series/agentic-rag/) series to the edge, where "no server" is the defining constraint.

## Why RAG, and why on-device changes it

RAG's premise (from the Agentic RAG series) is unchanged: rather than relying on a model's baked-in knowledge, you *retrieve* relevant information and put it in the model's context so it answers from real, current, specific data. On the edge, RAG is doubly important, because on-device models are *small* — they have less baked-in knowledge than a frontier model, so grounding them in retrieved facts matters even more for quality.

What changes is that **every stage must run locally**. Normal RAG assumes servers: a cloud embedding API, a hosted vector database, a big model. On-device RAG replaces each with a local equivalent:

```text
Cloud RAG:                          On-device RAG:
  embed via API             →         embed with a local embedding model
  store in hosted vector DB  →        store in an on-device vector store
  retrieve over network      →        retrieve locally (no network)
  generate with cloud LLM    →        generate with on-device Gemma
```

The payoff is that the user's data — their most private data, the kind you'd never send to a server — becomes usable by the assistant *without ever leaving the device*. That's a capability cloud RAG structurally cannot offer for truly sensitive data.

## The local pipeline, stage by stage

Each RAG stage has an on-device form, and the good news is that modern on-device stacks (including `flutter_gemma`, which supports embeddings and RAG) provide the building blocks.

- **Ingestion and chunking** — split the user's documents/notes/messages into chunks, exactly as in the [documents-and-nodes](/blog/posts/agentic-rag-01-why-naive-rag-falls-short.html) thinking of any RAG pipeline. This is pure local text processing — no model needed — and the chunking principles (coherent, appropriately-sized chunks) apply unchanged.
- **Local embeddings** — run a small **embedding model on-device** to turn each chunk into a vector. This is the key on-device capability: embedding is cheaper than generation (a single forward pass per chunk, no autoregressive loop), so a small embedding model runs efficiently even on modest hardware. The user's text is embedded locally; the vectors never leave the phone.
- **Local vector storage** — store the vectors in an **on-device store**. This can be as simple as vectors in the app's local database (SQLite, which most Flutter local-first apps already use) with a similarity search, or a purpose-built local vector index. At personal-data scale (a user's own notes/messages — thousands to tens of thousands of chunks, not billions), even a straightforward local similarity search is fast enough, so you rarely need the heavy vector-DB machinery of the cloud.
- **Local retrieval** — at query time, embed the user's question locally, find the nearest chunks in the local store (cosine similarity), and select the top few — no network call.
- **Local generation** — put the retrieved chunks into Gemma's context (respecting the small model's limited context window) and generate the answer on-device.

The entire loop — embed, store, retrieve, generate — happens on the phone. There is no server anywhere in the path, which is precisely what makes it private.

## Edge-specific RAG design

On-device RAG isn't just cloud RAG with local parts; the edge constraints reshape the design decisions:

- **Context is precious.** Small on-device models have limited context windows, and (from the constraints post) a bigger context inflates the KV cache and slows generation. So retrieval must be *tight* — return few, highly relevant chunks, not a generous set. Reranking to keep only the best chunks (the two-stage retrieve-broadly-then-narrow pattern) matters even more when every token of context costs scarce memory and speed.
- **Retrieval scope is one user.** Cloud RAG often searches a huge shared corpus; on-device RAG searches *this user's* data — a much smaller set. That makes local search feasible without specialized infrastructure, and it means the access-control problem (whose data can this query see?) largely disappears — there's only one user's data on the device.
- **Incremental indexing.** As the user adds notes or messages, embed and store the new chunks incrementally (the ingestion-pipeline idea from the RAG/LlamaIndex series), and remove vectors when the user deletes data — deletion propagation matters for privacy: if the user deletes a note, its vectors must go too.
- **Cost is free, so index generously.** Unlike cloud RAG where embedding is a metered API cost, on-device embedding is free (the user's hardware). You can embed all of the user's data without a per-token bill — a genuine edge advantage.

## Memory: the assistant that remembers

RAG over documents naturally extends to **conversational memory** — an on-device assistant that remembers past interactions. The same machinery applies: store past conversation turns (or summaries of them) locally, embed them, and retrieve relevant past context when it bears on the current query. This gives a local assistant long-term, *private* memory — it remembers what the user told it weeks ago, entirely on-device, with nothing stored on a server.

The distinction from the LLM serving series holds: **conversation memory** (what was said) and **retrieved knowledge** (the user's documents) are different sources, and a good on-device assistant uses both — short-term chat history in the context window, plus retrieval over a local store of long-term memories and documents. Bounding and summarizing older memory (the memory-management strategies from the serving series) keeps it within the phone's limits.

## Putting it together for a private assistant

- **Run the whole pipeline locally** — local embedding model, local vector store (often just SQLite + similarity search at personal scale), local retrieval, on-device Gemma — so the user's data never leaves the device.
- **Retrieve tightly** — few, well-reranked chunks, because small models have small context windows and every token costs scarce KV-cache memory.
- **Index incrementally and delete propagated** — embed new user data as it arrives, and remove vectors when the user deletes data (privacy requires it).
- **Combine document RAG with conversational memory** for an assistant that knows the user's data *and* remembers past interactions — both privately.
- **Embed generously** — on-device embedding is free, so grounding a small model well costs nothing but compute the user already owns.

On-device RAG is what turns a local model from a generic chatbot into a *personal* assistant grounded in the user's own private world. The last two posts cover the architecture that keeps it trustworthy (privacy and local-first design) and the practicalities of getting it into users' hands (shipping).

## Key takeaways

- On-device RAG runs the entire retrieval pipeline locally — local embedding model, local vector store, local retrieval, on-device generation — so a small model can reason over the user's private data without any of it leaving the device.
- It matters more on the edge because on-device models are small (less baked-in knowledge), so grounding them in retrieved facts is essential to quality — and it enables using the most sensitive data, which cloud RAG structurally can't.
- At personal-data scale (one user's notes/messages), a simple local store (SQLite + cosine similarity) is usually enough — no cloud vector DB — and access control largely vanishes since only one user's data is present.
- Edge constraints reshape design: retrieve tightly (few reranked chunks) because context windows are small and every token costs KV-cache memory; index incrementally and propagate deletions for privacy; and embed generously since on-device embedding is free.
- The same machinery gives private long-term memory — store/embed/retrieve past conversation turns locally — so a local assistant remembers the user privately, combining conversational memory with document retrieval.

## Further reading

- [Agentic RAG series](/blog/series/agentic-rag/)
- [Gemma on Flutter (previous post)](/blog/posts/edgeai-05-gemma-on-flutter.html)
- [LlamaIndex, Concept by Concept series](/blog/series/llamaindex-concept-by-concept/)
