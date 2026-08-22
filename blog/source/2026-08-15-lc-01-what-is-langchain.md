# What Is LangChain?

*LangChain is the framework everyone starts with and everyone has opinions about — a vast toolkit for building LLM applications whose real value isn't any one feature but the standardization it brings: one interface across every model, vector store, and tool, so you write your application once and swap the pieces underneath. Understanding what it is (and its relationship to LangGraph) cuts through the confusion.*

LangChain is one of the most widely used frameworks for building LLM applications — and one of the most debated, precisely because it's so broad. This series covers it concept by concept, distinct from the [LangGraph series](/blog/series/langgraph-concept-by-concept/) already on this blog. This first post establishes what LangChain actually is, the standardization that is its core value, its sprawling ecosystem, and — crucially — how it relates to LangGraph, which is the single most confusing thing about the LangChain world.

## What LangChain is

LangChain is a framework for developing applications powered by language models. It provides building blocks — interfaces to models, prompts, output parsers, retrievers, tools, memory — and a way to compose them into applications, plus an enormous ecosystem of **integrations** with model providers, vector stores, document sources, and tools. Its scope is deliberately wide: from a simple "call a model with a prompt" to complex retrieval and tool-using applications.

That breadth is both LangChain's strength and the source of its mixed reputation. It gives you a component and an integration for almost everything, which accelerates building — but it's also large, has evolved significantly over time, and can feel like a lot of abstraction. The way to understand LangChain productively is to see past the sprawl to its *core value*, which isn't the quantity of features but one specific thing: **standardization**.

## The core value: standardization

LangChain's most important contribution is a **standard interface** across the fragmented LLM ecosystem. Every model provider has a different API; every vector store, document loader, and tool has its own interface. LangChain wraps them behind *common abstractions*, so your code talks to "a chat model," "a retriever," "a vector store" — not to OpenAI's specific API or a particular vector database's specific client:

- **Model-agnostic** — swap OpenAI for Anthropic for a local model by changing which model object you instantiate; your application code, using the standard chat-model interface, stays the same (the keep-the-model-swappable principle from the [AI Architecture Decisions](/blog/posts/ai-decisions-01-how-to-choose.html) series).
- **Store-agnostic and tool-agnostic** — the same standard interfaces for vector stores, retrievers, and tools, so those pieces are swappable too.
- **A huge integration catalog** — because so many providers implement LangChain's standard interfaces, you get a vast library of ready-made integrations, so you rarely write provider-specific plumbing.

This standardization is why LangChain is so widely adopted: it lets you build against stable, common interfaces and swap the underlying providers freely, protecting you from lock-in and letting you use the best (or cheapest) option for each piece. When people say LangChain is valuable, this — the common interface and the integration ecosystem — is usually what they mean, more than any single feature.

## The ecosystem: LangChain, LangGraph, LangSmith

"LangChain" is often used loosely for a whole ecosystem, and separating the pieces is essential to using it well:

- **LangChain** — the core framework: the standard interfaces (models, prompts, retrievers, tools), the composition model (LCEL/Runnables, a later post), and the integrations. This is what this series covers. It's best for **chains** — relatively linear compositions of LLM calls and components.
- **LangGraph** — a separate library (covered in [its own series](/blog/series/langgraph-concept-by-concept/)) for **stateful, graph-based orchestration** of complex, cyclic agent workflows — state, nodes, edges, checkpointing, human-in-the-loop. It's the tool when you outgrow linear chains and need controllable, stateful agent flows.
- **LangSmith** — the observability and evaluation platform (a later post): tracing, debugging, and evaluating LLM applications built with either.

The relationship that trips everyone up: **LangChain and LangGraph are complementary, not competitors.** LangChain provides the components and standard interfaces; LangGraph provides the orchestration for complex stateful flows. You often use them *together* — LangChain's model/retriever/tool abstractions *inside* LangGraph's graph. The rough guidance: reach for LangChain (chains/LCEL) for straightforward, mostly-linear pipelines, and LangGraph when you need stateful, branching, cyclic agent orchestration. Knowing which layer you're working at dissolves most LangChain confusion.

## What LangChain gives you

The building blocks this series covers, each a component with a standard interface:

- **Models, prompts, output parsers** — the basics: talk to a chat model, template prompts, parse outputs into structured form.
- **LCEL and Runnables** — the composition model that lets you pipe components together into chains (the core abstraction).
- **Chains** — compositions of components into application pipelines.
- **Retrieval** — document loaders, splitters, embeddings, vector stores, and retrievers for RAG.
- **Tools and agents** — giving LLMs capabilities and letting them decide actions (with LangGraph as the modern orchestration for complex agents).
- **Memory** — conversation history and state.
- **LangSmith** — observability and evaluation in production.

Together these span "hello world with a model" to full retrieval-and-tool applications, all built on the standard, swappable interfaces.

## When to use LangChain

Like any framework, it fits some cases better (the [agent-framework comparison](/blog/posts/ai-decisions-02-agent-frameworks.html) covers the broader choice):

- **Reach for LangChain when** you want a broad, batteries-included toolkit with a huge integration ecosystem and standard interfaces that keep your providers swappable — especially for chains (linear-ish LLM pipelines), RAG, and getting moving quickly without writing provider-specific plumbing.
- **Its standout value** is the standardization and integration breadth — if you value not being locked to one provider and not writing integration glue, that's LangChain's core benefit.
- **Reach for LangGraph** (its own series) when you need stateful, cyclic, controllable agent orchestration; **consider Pydantic AI** (its own series) when type safety and structured outputs are paramount; **consider LlamaIndex** (its own series) when the app is fundamentally data/retrieval-centric. These aren't mutually exclusive — many apps mix them.

The through-line: LangChain is the broad, standardizing toolkit that makes the fragmented LLM ecosystem uniform and swappable. The next post starts with its most basic building blocks — models, prompts, and output parsers.

## Key takeaways

- LangChain is a broad framework for building LLM applications, providing standard building blocks (models, prompts, retrievers, tools, memory) and an enormous integration ecosystem — its breadth is both its strength and the source of its mixed reputation.
- Its core value is standardization: common interfaces across the fragmented ecosystem (models, vector stores, tools) so your code is model-/store-/tool-agnostic and providers are swappable, backed by a huge catalog of ready integrations — this, more than any feature, is why it's widely used.
- The ecosystem separates into LangChain (core components + standard interfaces + chains/LCEL), LangGraph (separate — stateful graph orchestration for complex cyclic agents), and LangSmith (observability/evaluation) — knowing which layer you're at dissolves most confusion.
- LangChain and LangGraph are complementary, not competitors: use LangChain's components for linear chains and inside LangGraph, and reach for LangGraph when you need stateful, branching, cyclic agent orchestration.
- Choose LangChain for a batteries-included, standardized, integration-rich toolkit (chains, RAG, swappable providers); reach for LangGraph (orchestration), Pydantic AI (type safety), or LlamaIndex (data-centric) when those shapes fit better — often in combination.

## Further reading

- [LangChain documentation](https://python.langchain.com/)
- [LangGraph, Concept by Concept series](/blog/series/langgraph-concept-by-concept/)
- [AI Architecture Decisions: choosing an agent framework](/blog/posts/ai-decisions-02-agent-frameworks.html)
