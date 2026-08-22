# Agents

*The Agent is where everything in Pydantic AI comes together — model, instructions, tools, typed dependencies, and typed output, bundled into one reusable, testable object you define once and run many times. Understanding the Agent as a configured, type-parameterized unit is the key that makes the rest of the framework fall into place.*

The last post introduced Pydantic AI's philosophy. This post covers its central primitive: the **Agent**. Everything else — structured outputs, tools, dependencies — hangs off the Agent, so understanding what it is and how it's constructed is foundational. The key idea is that a Pydantic AI agent is a *reusable, strongly-typed* object: you define it once with its configuration and types, then run it against many inputs.

## What an Agent is

An **Agent** in Pydantic AI bundles everything needed to accomplish a class of tasks into one object:

- **A model** — which LLM to use (though model-agnostic, so it's swappable).
- **Instructions / a system prompt** — the guidance that shapes the agent's behavior.
- **Tools** — the functions it can call (a later post).
- **Typed dependencies** — the data and services it needs, injected (a later post).
- **A typed output** — the structure of what it returns (the next post).

The important framing: an agent is defined *once* and reused. You don't construct it per request; you build it as a configured component of your application — like defining a route or a service — and then `run` it against different inputs repeatedly. This makes agents first-class, reusable pieces of your program rather than throwaway one-off calls, which is central to how Pydantic AI encourages you to structure applications.

```python
# Illustrative shape — see the Pydantic AI docs for exact API.
from pydantic_ai import Agent

agent = Agent(
    "openai:gpt-...",                    # the model (swappable)
    system_prompt="You are a helpful assistant.",
)

result = agent.run_sync("What is the capital of France?")
print(result.output)
```

Define the agent as a configured object; run it as needed. That reuse-oriented design is the first thing to internalize.

## The Agent is type-parameterized

What makes Pydantic AI's Agent distinctive is that it's **parameterized by types** — specifically, by its *dependency type* and its *output type*. Conceptually, an agent isn't just "an agent"; it's "an agent that takes *these typed dependencies* and produces *this typed output*." This is the type safety from the last post made concrete at the level of the core primitive:

- The **output type** declares what the agent returns (a Pydantic model, a plain type, or a string) — and the framework guarantees you get that type back, validated.
- The **dependency type** declares what the agent needs injected — so its tools and prompts access those dependencies type-safely.

Because the Agent carries these types, your IDE and type checker *understand* your agent: they know `result.output` is an `Order`, not an untyped blob, and they know what dependencies a tool can access. This is why building with Pydantic AI feels like typed Python — the Agent isn't an opaque object but a typed contract your tooling can reason about. The next two posts unpack the output type and dependency type in depth; the key point here is that the Agent is where those types are declared and enforced.

## System prompts: static and dynamic

The **system prompt** (instructions) shapes the agent's behavior, and Pydantic AI supports two forms, reflecting a real need:

- **Static system prompts** — fixed instructions set when you define the agent. The constant guidance ("you are a customer-support assistant that...").
- **Dynamic system prompts** — instructions computed *at run time*, often based on the injected dependencies. For example, a prompt that includes the current user's name or the current date — information not known when the agent was defined, but available (via dependency injection) when it runs.

Dynamic system prompts are more useful than they first appear: they let the agent's instructions incorporate runtime context (who the user is, what data is relevant now) while keeping the agent defined once. This connects directly to dependency injection — the dynamic prompt reads from the typed dependencies to build context-appropriate instructions. It's how a single reusable agent adapts its guidance to each specific run.

## Running an Agent

Pydantic AI gives you a few ways to run an agent, matching how your application executes:

- **Asynchronous run** — the primary mode (`run`), returning the result asynchronously, fitting modern async Python (and web frameworks like FastAPI).
- **Synchronous run** — a convenience (`run_sync`) for scripts and simple cases where you don't want async.
- **Streaming run** — stream the response as it's generated (a later post), for responsive UIs.

Whichever you use, the run produces a **result object** that carries the typed output (`result.output`) plus metadata (the messages exchanged, usage information). The result being a typed object — not a raw string — is the payoff of the type-parameterized agent: you run the agent and get back exactly the type you declared, ready to use in the rest of your typed program.

## The Agent as the unit of composition

Stepping back, the Agent is Pydantic AI's *unit of composition* — the piece you build, test, reuse, and combine. Because an agent is a self-contained, typed object with its model, prompt, tools, and dependencies, you can:

- **Build focused agents** — a specific agent for a specific job (an extraction agent, a classification agent, a support agent), each cleanly defined.
- **Test them in isolation** — the typing and dependency injection make agents unusually testable (a later post), including without calling a real model.
- **Compose them** — use agents together, or call agents from within tools of other agents, to build larger systems from typed, tested pieces.

This composability-of-typed-units is the structural benefit of the Agent design: instead of sprawling prompt-and-parse code, you get discrete, typed, testable agent components. With the Agent understood as the type-parameterized center of the framework, the next post covers its most distinctive feature — the typed output that makes `result.output` a validated object.

## Key takeaways

- The Agent is Pydantic AI's central primitive, bundling a model, instructions/system prompt, tools, typed dependencies, and a typed output into one reusable object — defined once and run against many inputs, not constructed per request.
- The Agent is type-parameterized by its dependency type and output type, so it's a typed contract your IDE and type checker understand (`result.output` is a known type) — the framework's type-safety philosophy made concrete at the core.
- System prompts can be static (fixed at definition) or dynamic (computed at run time from injected dependencies), letting one reusable agent adapt its instructions to each run's context.
- Running an agent (async `run`, sync `run_sync`, or streaming) produces a typed result object carrying `result.output` (the declared type, validated) plus metadata — you get back exactly the type you declared, not a raw string.
- The Agent is the unit of composition: build focused typed agents, test them in isolation (aided by typing and DI), and compose them into larger systems from discrete, tested pieces.

## Further reading

- [What is Pydantic AI? (previous post)](/blog/posts/pydai-01-what-is-pydantic-ai.html)
- [Pydantic AI documentation — agents](https://ai.pydantic.dev/)
- [DSPy, Concept by Concept — a different typed-programming take on LLMs](/blog/series/dspy-concept-by-concept/)
