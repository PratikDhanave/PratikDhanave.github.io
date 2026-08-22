# What Is Pydantic AI?

*Most agent frameworks treat the LLM's output as text you hope to parse. Pydantic AI treats it as typed, validated data — bringing the discipline that made Pydantic the backbone of Python data validation to the messy world of LLM agents. If you've ever wished your agent's output was a real typed object instead of a string you cross your fingers over, this framework was built for you.*

Pydantic AI is an agent framework from the team behind **Pydantic** — the library that underpins data validation across the Python ecosystem (including FastAPI). Its premise is distinctive: bring *type safety and validation* to LLM agents, so building agentic applications feels like the robust, typed Python you already write. This series builds Pydantic AI concept by concept; this first post covers what it is, the philosophy that sets it apart, and when to reach for it.

## The problem Pydantic AI solves

LLMs output text, but applications need *data* — structured, typed, validated values you can pass to the rest of your program with confidence. The gap between "the model returned a string" and "I have a validated `Order` object" is where a huge amount of agent code lives, and it's usually brittle: prompt the model to return JSON, parse it, hope the shape is right, handle the cases where it isn't. Pydantic AI closes that gap by making **typed, validated output a first-class feature**: you declare the type you want as a Pydantic model, and the framework ensures the model's output conforms to it — validated, retried on failure, and handed back as a real typed object.

More broadly, Pydantic AI brings the *engineering ergonomics* Python developers expect — type hints, IDE autocomplete, static checking, dependency injection, testability — to building agents. Its pitch is essentially "FastAPI for agents": take the patterns that made building typed, testable Python APIs pleasant, and apply them to LLM applications. If your mental model of good Python is "typed, validated, tested," Pydantic AI is the agent framework that matches it.

## The core philosophy: type safety

The organizing idea, running through every feature, is **type safety**. Pydantic AI is built so that:

- **Outputs are typed and validated** — you specify the output type (a Pydantic model), and you get back a validated instance, not a string to parse. This is the flagship feature (its own post).
- **Dependencies are typed** — data and services your agent needs are injected with declared types (dependency injection, its own post), so tools and prompts access them type-safely.
- **Tools are typed** — a tool's parameters and return are typed Python, and the framework generates the schema the model needs from those types.
- **It's checked by your tooling** — because everything is typed, your IDE and static type checkers (mypy, pyright) understand your agent code, catching errors before runtime.

This matters because LLM applications are unusually error-prone — the model is unpredictable, outputs vary, and failures are often silent (a slightly-wrong string that breaks something three steps later). Type safety and validation catch a whole class of those failures *at the boundary* (the model's output) rather than letting malformed data propagate. Pydantic AI's bet is that the rigor that tamed data validation elsewhere in Python is exactly what agent development needs.

## Model-agnostic by design

A second defining property: Pydantic AI is **model-agnostic**. You write your agent once, and it works across model providers (OpenAI, Anthropic, Gemini, and others) — swapping the model is a configuration change, not a rewrite. This reflects the "keep the model swappable" principle from the [AI Architecture Decisions](/blog/posts/ai-decisions-01-how-to-choose.html) series: your application logic, tools, and typed outputs stay the same while the underlying model is a pluggable choice. This protects you from lock-in and lets you route different tasks to different models — a practical strength for real applications.

## What Pydantic AI gives you

Concretely, the framework provides a coherent set of primitives, each a later post:

- **Agents** — the central abstraction: an LLM plus a system prompt, tools, typed dependencies, and a typed output, that you run against a query.
- **Structured outputs** — declare a Pydantic model as the output type and get validated, typed results (the flagship feature).
- **Tools** — typed Python functions the agent can call, with schemas generated from their type hints.
- **Dependency injection** — a typed way to provide data and services (a database connection, an API client, config) to your agent's tools and prompts.
- **Messages and streaming** — conversation history and streamed responses.
- **Testing support** — because of the typing and DI, agents are unusually testable, including with test models that don't call a real LLM.

These combine into an agent-building experience that feels like writing ordinary, well-structured Python — typed, injected, testable — rather than wrangling strings and JSON.

## When to use Pydantic AI

Like any framework, it fits some situations better than others (the [agent-framework comparison](/blog/posts/ai-decisions-02-agent-frameworks.html) covers the broader choice):

- **Reach for it when** you're building in Python, value type safety and validation, need reliable **structured outputs**, and want a framework that feels like idiomatic modern Python with strong testing and IDE support. It's especially compelling if you already use Pydantic/FastAPI — the patterns and mental model carry straight over.
- **It shines for** applications where the agent's output must be *structured data* your program consumes (extraction, classification, form-filling, tool-driven workflows returning typed results) — its typed-output strength is most valuable exactly there.
- **Consider alternatives when** you need a different paradigm — heavy graph-based stateful orchestration (LangGraph), a multi-agent-team metaphor (CrewAI), or a non-Python stack. Pydantic AI is a *Python, type-first, agent* framework; if that's not your shape, another framework may fit better.

The through-line: Pydantic AI is what you choose when you want LLM agents built with the same typed, validated, testable discipline as the rest of your Python. The next post starts with its central primitive — the Agent.

## Key takeaways

- Pydantic AI is an agent framework from the Pydantic team that brings type safety and validation to LLM agents — closing the gap between "the model returned a string" and "I have a validated typed object."
- Its guiding philosophy is type safety throughout: typed and validated outputs, typed dependencies, typed tools, all checked by your IDE and static type checkers — catching a class of LLM-application errors at the model-output boundary.
- It's often described as "FastAPI for agents": it brings the typed, injected, testable ergonomics that made modern Python APIs pleasant to building agents.
- It's model-agnostic by design — write the agent once and swap providers (OpenAI/Anthropic/Gemini) via configuration — reflecting the keep-the-model-swappable principle.
- Reach for it when you build in Python, value type safety, and need reliable structured outputs (extraction, classification, typed tool results); consider other frameworks for graph-based orchestration, multi-agent-team metaphors, or non-Python stacks.

## Further reading

- [Pydantic AI documentation](https://ai.pydantic.dev/)
- [AI Architecture Decisions: choosing an agent framework](/blog/posts/ai-decisions-02-agent-frameworks.html)
- [CrewAI, Concept by Concept series](/blog/series/crewai-concept-by-concept/)
