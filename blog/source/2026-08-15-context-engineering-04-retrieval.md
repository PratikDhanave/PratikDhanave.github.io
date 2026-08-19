# Retrieval: Bringing in the Right Context

*Retrieval is how you put external, current knowledge into a model's window, and doing it well is a context-engineering problem — the goal is not the most documents, but the right ones.*

A model's weights hold general knowledge, frozen at training time and unaware of your data. Retrieval is how you close that gap: fetch relevant information at query time and place it in the context so the model can use it. This is the mechanism behind retrieval-augmented generation, and seen through the lens of this series, it is pure context engineering — you are deciding what external knowledge earns a place in the budget. This fourth post covers retrieval as a context problem: getting the right content in, keeping the wrong content out.

## Why retrieval is a context decision

It is tempting to treat retrieval as a separate subsystem — an index, an embedding model, a similarity search — that hands results to the LLM. But the quality of a retrieval-augmented answer is often decided *before* the model runs, by what you retrieved. Retrieve the passage that contains the answer and the model looks authoritative; retrieve six loosely-related passages and it will either miss the answer or synthesize a plausible-sounding wrong one from the noise. The retriever is, in effect, choosing what the model knows for this query. That makes retrieval a first-class context-engineering concern, not an afterthought.

## The core loop

The basic retrieval loop has three steps, and each is a lever on context quality:

1. **Index.** Break your source material into chunks and store them so they can be searched — commonly by embedding each chunk into a vector and storing it in a vector index, often alongside keyword search.
2. **Retrieve.** At query time, find the chunks most relevant to the user's question — by vector similarity, keyword match, or both.
3. **Assemble.** Place the selected chunks into the context window, formatted and ordered, for the model to use.

Most retrieval failures trace to a specific step. Bad chunking corrupts the index; weak retrieval surfaces the wrong chunks; careless assembly buries good chunks or floods the window. Let us take the levers in turn.

## Chunking: the quality of the pieces

You cannot retrieve better than your chunks allow. If a chunk splits a concept in half, neither half retrieves well; if a chunk crams several unrelated topics together, it matches queries loosely and pollutes the context. Good chunking keeps each chunk about *one* thing, sized so it is specific enough to match precisely but complete enough to stand alone. Respecting the document's natural structure — sections, paragraphs — usually beats blindly splitting every N characters. Chunking is unglamorous and decisive: it sets the ceiling on everything downstream.

## Retrieval quality: relevance over recall

The instinct to retrieve *more* — top-20 instead of top-5 — usually backfires, for the budget reasons from the previous post: more chunks cost more, and padding the window with marginal matches strands the good ones and dilutes attention. The goal is precision, not volume. Two techniques help sharpen it:

- **Hybrid search** combines semantic (vector) similarity with keyword/lexical matching. Vectors catch meaning and paraphrase; keywords catch exact terms, names, and codes that embeddings blur. Together they retrieve better than either alone.
- **Reranking** takes an initial candidate set and re-scores it with a more precise (often cross-encoder) model to put the genuinely-best chunks on top. You retrieve a slightly wider net cheaply, then rerank down to the few that actually go in the window.

The pattern is: cast a reasonable net, then *narrow* to the highest-relevance few. What lands in the context should be the chunks most likely to contain the answer, not the largest set that plausibly might.

## Assembly: how retrieved context enters the window

Once you have the right chunks, how you place them still matters. Order them with the most relevant near the edges rather than the middle, given how models weight long inputs. Label each chunk with its source so the model can cite and you can trace answers back. Deduplicate near-identical chunks so you are not spending budget on repetition. And keep the retrieved block clearly delimited from instructions and the user query, so the model treats it as reference material — and so injected instructions hiding inside a retrieved document are less likely to be obeyed.

## Knowing when not to retrieve — and when it is not enough

Retrieval is a tool, not a reflex. If the answer is in the model's general knowledge or already in the conversation, retrieving adds cost and noise for nothing. Route queries: retrieve when the task needs specific, external, or current information; skip it when it does not. And recognize retrieval's limits — for questions that require reasoning across many scattered facts, or aggregating over a whole corpus, naive top-k retrieval falls short, and you need richer strategies (multi-step retrieval, structured queries, or graph-based approaches). The advanced techniques are their own subject; the context-engineering point stands: retrieval succeeds when it puts the *right* information in the window, and that is a decision you design, measure, and tune — not one the vector index makes for you.

## Key takeaways

- Retrieval puts external, current knowledge into the context, and the answer's quality is often decided before the model runs — by what you retrieved — making it a first-class context-engineering concern.
- The loop is index → retrieve → assemble; most failures trace to bad chunking, weak retrieval, or careless assembly.
- Chunking sets the ceiling: keep each chunk about one thing, sized to be specific yet self-contained, respecting the document's structure.
- Favor precision over volume — retrieving more usually hurts; use hybrid search (semantic + keyword) and reranking to narrow to the highest-relevance few.
- Assemble deliberately: most-relevant chunks at the edges, labeled with sources, deduplicated, and delimited from instructions; retrieve only when the task needs it, and reach for richer strategies when top-k is not enough.

## Further reading

- [Lost in the Middle: How Language Models Use Long Contexts — Liu et al., 2023](https://arxiv.org/abs/2307.03172)
- [OpenAI Cookbook](https://github.com/openai/openai-cookbook)
- [Anthropic documentation](https://docs.anthropic.com)
