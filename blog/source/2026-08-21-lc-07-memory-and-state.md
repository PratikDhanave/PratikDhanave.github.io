# Memory and State

*A chain answers one call; a conversation needs to remember. LangChain handles memory by treating conversation history as data you manage and pass in — and, for anything beyond simple chat history, hands state management to LangGraph. Knowing which is which keeps your stateful applications clean instead of tangled.*

The chains built so far are stateless — each invocation stands alone. Real conversational applications need **memory**: the record of prior turns, so the model has context. This post covers how LangChain handles conversation history and state, the shift toward explicit message management and LangGraph for richer state, and the context-management realities that come with any memory. It's the piece that turns one-shot chains into conversational applications.

## The problem: chains are stateless

A chain invocation takes an input and produces an output with no memory of previous invocations. Ask a chain "What's the capital of France?" then "What's its population?" and the second call has no idea what "its" refers to — the chain didn't retain the first exchange. **Memory** is the mechanism for carrying conversation history across invocations so follow-ups and references resolve, exactly the problem the [LlamaIndex chat post](/blog/posts/llamaindex-05-chat-and-memory.html) and the LLM-serving memory discussion covered. The question is *how* LangChain manages that history.

## The modern approach: history as explicit data

The modern LangChain approach treats conversation history as **explicit messages you manage and pass in**, rather than hidden mutable state inside a chain object. You keep the list of messages (human and AI turns), and on each new turn you include the prior history in the input to the chain, typically via a message-history placeholder in the prompt:

```python
# Illustrative shape — see the LangChain docs for exact API.
prompt = ChatPromptTemplate.from_messages([
    ("system", "You are a helpful assistant."),
    ("placeholder", "{history}"),     # prior turns go here
    ("human", "{input}"),
])
chain = prompt | model
# you supply the accumulated history each turn:
chain.invoke({"history": past_messages, "input": "What's its population?"})
```

This explicit-history model — the same one the Pydantic AI messages post described — has the same benefits: **you control where history is stored** (memory, database, session store), it's **serializable** (so conversations span requests and sessions, fitting stateless backends), and the chain stays **stateless and reusable** across many concurrent conversations because it doesn't hold the state itself. LangChain provides helpers to wire message history into a chain (managing sessions by an ID), but the underlying model is that history is *your* data flowing through the chain, not opaque internal state. This is a deliberate move away from older, more magical memory abstractions toward explicit, controllable state.

## Beyond chat history: LangGraph for real state

Simple conversation history is one kind of state; complex applications have *more* — accumulated results across steps, agent scratchpads, evolving task state, checkpoints to resume from. For anything beyond straightforward message history, the modern LangChain answer is **LangGraph** (its own series), which is fundamentally a *stateful* orchestration engine:

- **LangGraph manages state as a first-class concept** — a state object that flows through and is updated by the graph's nodes, purpose-built for the stateful, multi-step, cyclic applications chains aren't meant for.
- **Persistence and checkpointing** — LangGraph can checkpoint state, so a conversation or workflow can be paused, resumed, and recovered — real durable state, not just an in-memory message list.
- **This is the right tool for complex stateful agents** — where state is more than "the last few messages" and involves evolving, persisted, structured state across a cyclic flow.

So the division mirrors the chains-vs-graphs boundary throughout this series: **LangChain handles simple conversation history as explicit passed-in messages; LangGraph handles rich, persisted, evolving state for complex applications.** If your state need is "remember the conversation," explicit message history in a chain suffices; if it's "manage evolving structured state across a stateful multi-step agent," that's LangGraph. Using the right one keeps stateful applications clean.

## Managing context: the same finite-window reality

Whatever holds the history, the finite-context-window reality from the LLM-serving and context-engineering series applies: **conversation history grows, context windows are finite**, so you can't pass ever-growing history forever without rising cost, latency, and eventual truncation. Because LangChain history is explicit data you control, you manage it with the familiar strategies:

- **Trim** — pass only recent messages, dropping older ones as history grows.
- **Summarize** — condense older turns into a running summary carried forward instead of full messages, preserving gist at lower token cost.
- **Hybrid** — recent turns verbatim plus a summary of older ones (the common production choice).

LangChain provides utilities to trim and manage message history, and the responsibility is yours because history is your data — a tractable responsibility precisely because the history is explicit and manipulable rather than hidden. This is the same memory-as-curation lesson from across the blog: memory is deciding what to keep, compress, and drop, not just accumulating everything.

## Memory and retrieval are different

One clarification worth repeating from the LlamaIndex and LLM-serving series, because conflating them causes bugs: **conversation memory and retrieval are distinct.** Memory is the *dialogue history* (what was said in this conversation) — ephemeral, per-conversation. Retrieval (the RAG post) brings in *knowledge from your data* — persistent, shared. A good conversational LangChain app uses *both*: memory (message history) to understand the current turn and resolve references, and retrieval to ground answers in your data. Keeping them separate — not dumping retrieved documents into conversation memory, nor treating history as a knowledge base — keeps the application coherent as conversations grow. They're different components with different lifecycles, composed together.

## State in the LangChain world

The mental model to carry: LangChain handles conversation memory as **explicit message history you manage and pass into chains** — controllable, serializable, keeping chains stateless and reusable — while richer, persisted, evolving state belongs to **LangGraph**. Manage the growing history with trim/summarize/hybrid strategies (your responsibility, made tractable by explicit history), and keep conversation memory distinct from retrieval. This explicit, layered approach to state is consistent with the framework's broader design — give you control rather than hidden magic — and it's what makes LangChain conversational applications clean and scalable. The final post covers operating all of this in production with LangSmith.

## Key takeaways

- Chains are stateless (each invocation stands alone), so memory carries conversation history across invocations to resolve follow-ups and references — the same problem the LlamaIndex/serving memory discussions cover.
- The modern approach treats history as explicit messages you manage and pass in (via a history placeholder), not hidden chain state — so you control storage, it's serializable (spanning requests/sessions), and chains stay stateless and reusable across conversations.
- For state beyond simple chat history (evolving results, agent state, checkpoints/persistence), LangGraph is the answer — a first-class stateful orchestration engine — mirroring the chains-vs-graphs boundary: LangChain for simple message history, LangGraph for rich persisted state.
- Finite context windows mean growing history must be managed with trim/summarize/hybrid strategies; because LangChain history is explicit data you control, this is your (tractable) responsibility — memory is curation, not accumulation.
- Conversation memory (ephemeral dialogue history) and retrieval (persistent knowledge from your data) are distinct components with different lifecycles; use both, kept separate, for a coherent conversational app.

## Further reading

- [Tools and agents (previous post)](/blog/posts/lc-06-tools-and-agents.html)
- [LangGraph, Concept by Concept — first-class state management](/blog/series/langgraph-concept-by-concept/)
- [Context Engineering series — managing finite context](/blog/series/context-engineering/)
