# Query Transformation

*The user's question is written to be asked, not to be searched, so the first thing an agentic RAG system should do is turn that question into queries that actually retrieve well.*

The cheapest, highest-return step up from naive RAG is to stop searching with the raw user question. Real questions are conversational, underspecified, multi-part, or phrased nothing like the documents that answer them — and embedding them directly retrieves poorly. Query transformation is the agentic step of *reasoning about what to search for* before searching. This third post in the Agentic RAG series covers the main transformations — rewriting, decomposition, expansion, and hypothetical documents — and when each helps.

## Why the raw query is the wrong query

Similarity search matches the query against how answers are *written*. A user asking "why does my thing keep crashing on startup?" is semantically distant from a doc titled "Resolving initialization failures." Follow-up questions are worse: "what about the second option?" carries no standalone meaning for a retriever. And compound questions ("compare X and Y on cost and latency") bundle multiple information needs into one embedding that matches none of them well. In every case, the fix is the same: transform the question into one or more queries built for retrieval, not conversation.

## Query rewriting

The most basic transformation is rewriting the query into a cleaner, more retrievable form. This includes resolving context — turning "what about the second one?" into "what are the drawbacks of the second option, the managed database?" using the conversation history — and rephrasing toward the vocabulary the documents likely use. An LLM does this well: given the question and recent context, it produces a self-contained, well-phrased search query. Rewriting alone fixes a large share of naive RAG's retrieval misses, because so many come from conversational, context-dependent phrasing that the raw embedding cannot handle.

## Query decomposition

Compound and multi-part questions need *splitting*, not just rephrasing. Decomposition breaks a complex question into several focused sub-questions, each retrievable on its own. "Compare our Postgres and DynamoDB options on cost and operational burden" becomes separate queries for Postgres cost, DynamoDB cost, Postgres ops, and DynamoDB ops. Each sub-query retrieves cleanly, and the answers are composed at generation time. Decomposition is what lets a single user question fan out into the several retrievals it actually requires — and it is the bridge to multi-hop retrieval, which decomposes *and* chains when later sub-questions depend on earlier answers.

## Query expansion

Sometimes the problem is that one phrasing retrieves too narrowly and misses relevant documents worded differently. Query expansion generates several variations or related phrasings of the query, retrieves for each, and merges the results. Where the user said "car," a document might say "vehicle" or "automobile"; expansion casts a wider net across those variants so relevant content is not missed for a vocabulary mismatch. The cost is more retrievals and the need to dedupe and rerank the merged results down to the best few — expansion widens recall, and you then narrow back to precision.

## HyDE: search with a hypothetical answer

A clever transformation flips the matching problem. The insight behind [HyDE (Gao et al., 2022)](https://arxiv.org/abs/2212.10496) — Hypothetical Document Embeddings — is that a question and its answer often embed far apart, but an *answer* and the *real documents* embed close together. So instead of searching with the question, you have the model generate a hypothetical answer to the question, then search using *that* generated answer's embedding. The hypothetical answer, even if imperfect or partly wrong, looks much more like the real documents than the question did, so it retrieves them better. HyDE is especially useful for zero-shot retrieval where the question-to-document gap is wide; the generated document is a retrieval device, not the final answer.

## Choosing and combining transformations

These are not mutually exclusive — a system can rewrite, then decompose, then expand each sub-query. But each transformation adds model calls and retrievals, so apply them by need:

- **Rewriting** for conversational, context-dependent, or poorly-phrased questions — nearly always worth it, cheap and high-return.
- **Decomposition** for compound or multi-part questions that bundle several information needs.
- **Expansion** when vocabulary mismatch causes misses and recall is the problem.
- **HyDE** when the question-to-document semantic gap is wide and direct search retrieves poorly.

The agentic version is to let the model *decide* which transformation a given question needs rather than always applying all of them — a simple factual lookup needs none, a research question needs several. That decision is itself the reasoning-about-retrieval that defines agentic RAG.

## The payoff and the guardrail

Query transformation is the highest-leverage agentic-RAG technique because retrieval quality gates everything downstream — a better query retrieves better chunks, which produce a better answer, and the improvement compounds. The guardrail is the familiar one: transformations add cost and can occasionally *hurt* (a rewrite that drifts from intent, an expansion that adds noise), so validate against an evaluation set that the transformed queries actually retrieve better than the raw ones. Applied judiciously and measured, query transformation turns a large fraction of naive RAG's retrieval failures into hits before any other agentic machinery is added.

## Key takeaways

- The user's question is written to be asked, not searched; transforming it into retrieval-oriented queries fixes a large share of naive RAG's misses.
- Query rewriting resolves conversational context and rephrases toward document vocabulary — cheap, high-return, and worth it for most conversational questions.
- Decomposition splits compound/multi-part questions into focused sub-queries that each retrieve cleanly, and is the bridge to multi-hop retrieval.
- Expansion generates query variants to widen recall past vocabulary mismatch; HyDE searches with a generated hypothetical answer that embeds closer to real documents than the question does.
- Let the agent decide which transformation each question needs rather than always applying all; validate that transformed queries retrieve better, since transformations add cost and can occasionally drift.

## Further reading

- [Precise Zero-Shot Dense Retrieval without Relevance Labels (HyDE) — Gao et al., 2022](https://arxiv.org/abs/2212.10496)
- [Self-RAG: Learning to Retrieve, Generate, and Critique through Self-Reflection — Asai et al., 2023](https://arxiv.org/abs/2310.11511)
- [ReAct: Synergizing Reasoning and Acting in Language Models — Yao et al., 2022](https://arxiv.org/abs/2210.03629)
