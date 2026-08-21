# Chat Engines and Memory

*A query engine answers one question in isolation; a chat engine holds a conversation. The difference is memory — and handling memory well is what separates a demo chatbot from one that stays coherent and affordable over a long dialogue.*

A query engine treats every question as standalone. But real users have conversations: they ask a follow-up, say "what about the second one?", refer back to something three turns ago. That requires **memory** — and a **chat engine**, which is a query engine plus conversational state. This fifth post in the LlamaIndex series covers conversational retrieval and the memory that makes it work.

## Why a query engine isn't enough

Consider the exchange: "What's our refund policy?" → *(answer)* → "Does it apply to sale items?" A bare query engine embeds "Does it apply to sale items?" and retrieves on that alone — but "it" is meaningless without the prior turn. The retrieval misses, and the answer is wrong. Conversation breaks isolated retrieval, and fixing it is exactly what a chat engine does.

## Chat engines: conversation over your data

A **chat engine** wraps retrieval in a stateful conversational interface:

```python
chat_engine = index.as_chat_engine()
chat_engine.chat("What's our refund policy?")
chat_engine.chat("Does it apply to sale items?")  # 'it' resolved from history
```

The chat engine keeps the conversation history and uses it so follow-ups make sense. LlamaIndex offers different **chat modes** that trade off simplicity against capability — two worth knowing:

- **Condense-question** — before retrieving, use the history to rewrite the follow-up into a standalone question ("Does the refund policy apply to sale items?"), then retrieve on that. Simple and effective: it fixes the "it" problem by making every query self-contained.
- **ReAct / agentic** — treat retrieval as a *tool* the LLM can choose to call. The model decides whether this turn even needs a retrieval, and what to search for — chit-chat gets answered directly, substantive questions trigger a search. This is the bridge to the agents in the next post.

Choosing a mode is choosing how much reasoning sits between the user's message and the retrieval: condense-question is a fixed rewrite-then-retrieve; the agentic mode lets the model decide.

## Memory: the conversation's state

**Memory** is where the conversation history lives, and it's the piece that needs real engineering. The naive approach — keep every turn and stuff the whole history into each prompt — breaks down fast: the context window fills, cost and latency climb with every turn, and eventually the earliest (often most important) turns get truncated. LlamaIndex provides a memory abstraction (a chat memory buffer) that manages this, and the strategies mirror the trade-offs from the [context engineering](/blog/series/context-engineering/) series:

- **Buffer with a token limit** — keep the most recent turns up to a budget, dropping the oldest. Simple, bounded, but forgets early context.
- **Summarizing memory** — condense older turns into a running summary so their gist survives without their full token cost. Preserves long-range context affordably.
- **Hybrid** — keep recent turns verbatim and older ones as a summary — the common production choice.

The underlying reality is that context is finite and grows every turn, so memory is fundamentally about *deciding what to keep, what to compress, and what to drop* — a curation problem, not a storage problem.

## The distinction that matters: memory vs. retrieval

It's worth separating two things a chat engine juggles, because conflating them causes bugs. **Conversation memory** is the dialogue history — what the user and assistant said. **Retrieval** brings in knowledge from your indexed data. They're different sources with different lifecycles: memory is per-conversation and ephemeral; the knowledge base is shared and persistent. A good chat engine uses memory to *understand* the current turn (resolve references, track what's been discussed) and retrieval to *ground* the answer in your data. Keeping them distinct — rather than dumping retrieved chunks into memory or treating history as a knowledge source — keeps the system coherent as conversations grow.

## Key takeaways

- A query engine answers questions in isolation; a chat engine adds conversational state so follow-ups and references ("it", "the second one") resolve correctly.
- Chat modes trade simplicity for capability: condense-question rewrites the follow-up into a standalone query before retrieving; ReAct/agentic mode lets the LLM decide whether and what to retrieve (the bridge to agents).
- Memory manages finite context: token-limited buffers (bounded but forgetful), summarizing memory (preserves long-range gist affordably), or a hybrid of recent-verbatim + older-summary (the common production choice).
- Memory is a curation problem — what to keep, compress, or drop — because context is finite and grows every turn.
- Keep conversation memory (ephemeral dialogue history) distinct from retrieval (persistent knowledge base); use memory to understand the turn and retrieval to ground the answer.

## Further reading

- [LlamaIndex documentation](https://docs.llamaindex.ai)
- [Context Engineering series](/blog/series/context-engineering/)
- [LlamaIndex, Concept by Concept — start of the series](/blog/posts/llamaindex-01-what-is-llamaindex.html)
