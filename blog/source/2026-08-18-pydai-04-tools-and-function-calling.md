# Tools and Function Calling

*An agent that can only talk is a chatbot; an agent that can act needs tools. In Pydantic AI, a tool is just a typed Python function you decorate — the framework reads its type hints to tell the model how to call it, validates the model's arguments, and runs it. Function calling stops being schema-wrangling and becomes writing ordinary typed functions.*

Structured outputs let an agent return typed data. **Tools** let it *do things* along the way — look something up, call an API, query a database, compute a result. This post covers how Pydantic AI does tools: turning typed Python functions into agent capabilities, how the type hints become the schema the model needs, and how tools access the agent's dependencies. It's function calling with the framework's type-first ergonomics.

## What tools are and why agents need them

A base LLM only knows what's in its training and its prompt; it can't look up current data, access your systems, or perform actions. **Tools** are functions the agent can invoke to reach beyond itself — the agent decides, mid-run, that it needs to call a tool, the framework runs it, and the result goes back to the model to continue reasoning. This is the function-calling / tool-use pattern common to agent frameworks, and it's what turns an LLM into an *agent* that can act, not just answer.

Typical tools: fetch a record from a database, call an external API, do a calculation, search, or trigger an action. The agent's power comes largely from the tools you give it — the model provides reasoning and language, the tools provide capability and grounding in real data.

## Tools are typed Python functions

Pydantic AI's approach to tools reflects its whole philosophy: **a tool is just a typed Python function** you register with the agent (typically via a decorator). You write an ordinary function with type-hinted parameters and a return type, and the framework does the rest:

```python
# Illustrative shape — see the Pydantic AI docs for exact API.
from pydantic_ai import Agent

agent = Agent("openai:gpt-...")

@agent.tool_plain
def get_weather(city: str) -> str:
    """Get the current weather for a city."""
    return fetch_weather(city)   # your real implementation
```

The elegance is in what you *don't* do: you don't hand-write a JSON schema describing the tool's parameters, and you don't manually parse the model's arguments. Pydantic AI **generates the tool's schema from the function's type hints** and **validates the model's arguments against them** before calling your function. Your `city: str` parameter becomes a schema the model sees, and when the model calls the tool, its argument is validated as a `str` before your function runs. Function calling becomes: write a typed function, and the type-and-schema plumbing is automatic — the same generate-schema-from-types idea as structured outputs, applied to inputs.

## The docstring is part of the tool

A subtle but important point: the function's **docstring** matters, because it becomes the tool's *description* that the model uses to decide when and how to call it. This echoes the tool-design lesson from other agent series — a tool's description is what the model reasons over, so a clear, accurate docstring is essential for the agent to use the tool correctly. Pydantic AI can even extract parameter descriptions from the docstring to enrich the schema. So in Pydantic AI, good tool design is good *typed, documented* function design: precise type hints (so arguments are validated correctly) and a clear docstring (so the model knows when to call it). The function *is* the tool spec — types and docstring together.

## Tools and dependencies: the RunContext

Tools often need access to things: a database connection, an API client, the current user, configuration. Pydantic AI provides this through **dependency injection** (the next post's subject), and tools access injected dependencies via a **`RunContext`**. A tool that needs dependencies takes a context parameter as its first argument, through which it reaches the agent's typed dependencies:

```python
# Illustrative shape.
from pydantic_ai import Agent, RunContext

agent = Agent("openai:gpt-...", deps_type=MyDeps)

@agent.tool
def get_user_orders(ctx: RunContext[MyDeps], status: str) -> list[Order]:
    """Get the current user's orders with a given status."""
    return ctx.deps.db.query_orders(ctx.deps.user_id, status)
```

Two things to notice. First, the tool reaches its dependencies (`ctx.deps.db`, `ctx.deps.user_id`) *type-safely* — because `RunContext[MyDeps]` carries the typed dependencies, the tool accesses them with full type checking, not from globals or ambient state. Second, this makes tools **testable**: since dependencies are injected through the context rather than hard-wired, you can run the tool with test dependencies (a fake database) without touching real systems. The distinction between `tool` (with context/dependencies) and `tool_plain` (no dependencies needed) reflects this — use the context form when the tool needs injected data or services. This typed, injected tool design is what keeps Pydantic AI tools clean and testable rather than tangled with global state.

## How the agent uses tools

At run time, tools plug into the agent's reasoning loop:

- The agent, given a query, decides whether it needs a tool to answer.
- If so, it calls the tool with arguments (which Pydantic AI validates against the type hints).
- Your function runs and returns a (typed) result.
- The result goes back to the model, which continues — possibly calling more tools — until it can produce the final (typed) output.

This is the standard think-act-observe agent loop, but with Pydantic AI's guarantees at each step: validated tool arguments in, typed results back, typed final output at the end. The same reliability disciplines from the other agent series apply — give the agent *few, well-described* tools rather than many overlapping ones (so tool selection stays reliable), handle tool errors so the agent can recover, and keep tools focused. Pydantic AI's typing helps here: a tool's contract is explicit in its signature, and argument validation catches malformed calls before your code runs.

## Tools as the agent's capabilities

The mental model to carry: in Pydantic AI, you extend an agent's capabilities by writing typed, documented Python functions and registering them as tools. There's no separate tool-definition language or manual schema — the function, with its type hints and docstring, *is* the tool. This keeps tool-building squarely in the language of ordinary Python, with the framework handling the schema generation, argument validation, and dependency access. Combined with structured outputs (typed results) and dependency injection (typed context), tools complete the picture of an agent as typed Python throughout — from the dependencies it's given, through the tools it calls, to the validated output it returns. The next post details the dependency injection that tools and dynamic prompts rely on.

## Key takeaways

- Tools are functions the agent can invoke to act beyond itself (look up data, call APIs, compute) — turning an LLM into an agent that can act and stay grounded in real data; the agent's power comes largely from its tools.
- In Pydantic AI a tool is just a typed Python function you register (via a decorator): the framework generates the tool's schema from its type hints and validates the model's arguments against them, so you never hand-write JSON schemas or parse arguments.
- The docstring is part of the tool — it becomes the description the model uses to decide when to call it — so good tool design is precise type hints plus a clear docstring; the function is the tool spec.
- Tools access injected dependencies type-safely via a `RunContext` (the `tool` form), keeping them free of global state and making them testable with fake dependencies; `tool_plain` is for tools needing no dependencies.
- Tools plug into the agent's think-act-observe loop with Pydantic AI's guarantees (validated arguments in, typed results back, typed final output); apply the usual disciplines — few well-described tools, handle errors, keep them focused.

## Further reading

- [Structured outputs (previous post)](/blog/posts/pydai-03-structured-outputs.html)
- [Pydantic AI documentation — tools](https://ai.pydantic.dev/)
- [Model Context Protocol from Scratch — tools across the ecosystem](/blog/series/model-context-protocol-from-scratch/)
