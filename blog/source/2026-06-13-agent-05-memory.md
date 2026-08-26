# Agent Memory

*An LLM is, fundamentally, stateless — it remembers nothing between calls except what you put in its context window. For an agent that takes many steps or works across many sessions, that's a serious problem: without memory, every step starts from scratch, and nothing is ever learned. Memory is how agents overcome statelessness — holding the context of the current task, and carrying knowledge across tasks and time. Understanding the kinds of agent memory, and their limits, is essential to building agents that can handle real, extended work.*

**Memory** is how agents maintain *state* — remembering within a task and across tasks. This post covers why memory matters (LLM statelessness), the distinction between short-term and long-term memory, the types of long-term memory, and the practical realities (the context window and its limits). Memory is what lets agents work over many steps and sessions rather than treating each moment in isolation, and it's a core agent design area.

## Why agents need memory

The fundamental reason agents need memory: **LLMs are stateless** — a model call remembers nothing except what's in its input (context). For an agent, this is a real limitation:

- **LLMs don't remember between calls.** Each LLM call is independent — the model has no memory of previous calls except what you *include* in the current input (the context window). So an agent taking many steps (many LLM calls in the loop) would, by default, *forget everything* from step to step unless that information is carried forward. Statelessness means no memory unless you provide it.
- **Agents need continuity within a task.** An agent working through a multi-step task must *remember* what it's done, what it's learned, and where it is — the context of the ongoing task — across the loop's iterations. Without this within-task memory, each step would be blind to the previous ones, making multi-step work impossible. The agent needs to maintain the task's state across steps.
- **Agents often need continuity across tasks/sessions.** Beyond a single task, agents often benefit from remembering *across* tasks and sessions — past interactions, learned information, user preferences, accumulated knowledge. An agent that forgets everything between sessions can't learn or personalize over time. Cross-task memory enables agents that improve and remember. Statelessness would prevent this too.

Agents need memory because LLMs are stateless (remembering only what's in the current context) — so memory is what provides *continuity*, both within a task (across the loop's steps) and across tasks/sessions (over time). Memory overcomes statelessness to let agents do extended, multi-step, and ongoing work. The two kinds of continuity map to two kinds of memory: short-term and long-term.

## Short-term vs long-term memory

Agent memory divides into **short-term** (within-task, the working context) and **long-term** (across-task, persistent) — a fundamental distinction:

- **Short-term memory = the working context.** *Short-term* (or working) memory is the information the agent holds *during the current task* — what it's done, observed, and reasoned so far — typically maintained in the *context window* (the LLM's input). It's the agent's "working memory" for the ongoing task, carried across the loop's iterations by including the relevant history in each LLM call. It's transient (specific to the current task) and lives largely in the context. This is what makes multi-step work coherent.
- **Long-term memory = persistent knowledge.** *Long-term* memory is information the agent retains *across* tasks and sessions — stored *outside* the context window (in a database, vector store, or file) and *retrieved* when relevant. It persists beyond any single task, letting the agent remember past interactions, learned facts, and preferences over time. Long-term memory is *external storage the agent reads from and writes to*, since it can't all fit in the context. It's what lets agents accumulate knowledge.
- **The two work together.** Short-term memory handles the immediate task (in context); long-term memory provides relevant persistent knowledge (retrieved into context when needed). A capable agent uses both — working memory for the current task, and long-term memory to bring in relevant past knowledge. Managing both, and the flow between them (what to persist to long-term, what to retrieve into short-term), is core to agent memory design.

The short-term (working context, transient, in the context window) vs long-term (persistent, external storage, retrieved when relevant) distinction is the foundation of agent memory — analogous to human working vs long-term memory. Short-term makes multi-step tasks coherent; long-term lets agents remember and learn across time. Long-term memory has further useful structure.

## Types of long-term memory

Long-term memory is often broken into types (borrowing from cognitive science), each serving a different role — a useful framing for designing agent memory:

- **Episodic memory: past experiences/interactions.** *Episodic* memory stores *specific past events* — previous interactions, conversations, tasks the agent did, what happened. It lets the agent recall "what happened before" (past sessions, prior exchanges with a user), enabling continuity and learning from past experience. It's the memory of specific episodes.
- **Semantic memory: facts and knowledge.** *Semantic* memory stores *general facts and knowledge* — information the agent has learned or been given (facts about a domain, user preferences, learned knowledge), independent of when it was learned. It's the agent's knowledge base of *what it knows*, retrieved when relevant. (This connects closely to RAG — retrieving relevant knowledge into context.)
- **Procedural memory: how to do things.** *Procedural* memory stores *how to do things* — learned skills, procedures, or successful approaches the agent can reuse. It's less common but represents an agent remembering *methods* that worked, to apply again. (This connects to agents that learn and reuse skills over time.)
- **How it's implemented: retrieval.** Practically, long-term memory is usually implemented with *retrieval* — storing information externally (often as embeddings in a vector store, like RAG) and *retrieving the relevant pieces* into the context when needed. The agent searches its memory for what's relevant to the current situation and brings it into short-term (context). So long-term memory is essentially *retrieval over stored knowledge/experience* — the same mechanism as RAG, applied to the agent's own accumulated memory. Retrieval is how external memory reaches the context-bound model.

The types of long-term memory — episodic (past experiences), semantic (facts/knowledge), and procedural (how-to) — provide a useful structure for what an agent should remember, and they're typically implemented via *retrieval* over external storage (vector stores, like RAG) that brings relevant memories into the context. This structure helps design what an agent persists and recalls. But all memory ultimately funnels through one constraint: the context window.

## The context window and its limits

A crucial practical reality shapes all agent memory: the **context window** — the LLM's finite input — is limited, and managing it is central to agent memory:

- **Everything the model uses must fit in context.** The LLM only "sees" what's in its context window (its input) — so *all* the memory the model actually uses (short-term working memory, and any long-term memory retrieved) must *fit* in the finite context. The context window is the bottleneck through which all memory reaches the model. This constraint drives much of memory design.
- **Context is finite, so you can't include everything.** Context windows, though growing, are *limited* — you can't just stuff all history and knowledge in. For long tasks or lots of knowledge, the relevant information exceeds the context, forcing *choices* about what to include. This is why long-term memory lives *outside* context and is *retrieved* selectively — you bring in only the relevant pieces. Managing what's in the limited context is a core agent challenge.
- **Context management techniques.** Because context is limited, agents use techniques to manage it: *summarizing* older history (compressing the task's history to save space), *retrieving* only relevant long-term memory (not everything), *pruning* irrelevant context, and structuring what's included. Effective *context management* — keeping the most relevant information in the limited window — is essential for agents on long or knowledge-heavy tasks. (This is an active area — "context engineering.") It's often what makes or breaks long-running agents.
- **Longer context isn't a full solution.** Even as context windows grow, they remain finite and have costs (more context = more compute/cost, and models can attend less well to very long contexts). So even with large contexts, *managing* memory (what to keep in context vs store externally and retrieve) remains necessary. Bigger context helps but doesn't eliminate memory management. The finite context is a permanent design consideration.

Agent memory overcomes LLM statelessness to provide continuity — short-term (working context, transient) for within-task coherence, and long-term (persistent external storage, retrieved when relevant, in episodic/semantic/procedural types) for across-task knowledge — all constrained by the finite context window, which makes context management central. Memory is what lets agents do extended and ongoing work. Next: reflection and self-correction — how agents evaluate and improve their own work.

## Key takeaways

- Agents need memory because LLMs are *stateless* (each call remembers only what's in its context) — so memory provides continuity both within a task (across the loop's steps, or each step would be blind to the last) and across tasks/sessions (or the agent couldn't learn or personalize over time).
- Memory divides into short-term (working memory for the current task, transient, held in the context window, carried across loop iterations — makes multi-step work coherent) and long-term (persistent knowledge across tasks/sessions, stored *externally* and retrieved when relevant — lets agents accumulate knowledge and remember over time); the two work together.
- Long-term memory has useful types: episodic (specific past experiences/interactions), semantic (general facts/knowledge — closely related to RAG), and procedural (learned how-to/skills) — providing structure for what an agent should remember.
- Long-term memory is typically implemented via retrieval over external storage (often embeddings in a vector store, like RAG): the agent searches its stored memory for what's relevant and brings it into the context — retrieval is how external memory reaches the context-bound model.
- The finite context window is the bottleneck through which all memory reaches the model, so context management is central — summarizing older history, retrieving only relevant long-term memory, pruning, and structuring context ("context engineering") — and even growing context windows (finite, costly, imperfect attention over very long inputs) don't eliminate the need to manage memory.

## Further reading

- [Retrieval-augmented generation — the retrieval mechanism behind long-term memory (Wikipedia)](https://en.wikipedia.org/wiki/Retrieval-augmented_generation)
- [A Survey on Large Language Model based Autonomous Agents — memory in agents (Wang et al., 2023)](https://arxiv.org/abs/2308.11432)
- [Planning and decomposition (previous post)](/blog/posts/agent-04-planning-and-decomposition.html)
