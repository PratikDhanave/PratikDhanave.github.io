# Dependency Injection

*Dependency injection is the least flashy Pydantic AI feature and quietly one of the most important — it's what lets your agents reach real databases, API clients, and user context without hard-wiring them, and it's the single biggest reason Pydantic AI agents are so testable. Borrowed straight from how good backend frameworks work, applied to agents.*

Tools and dynamic prompts both needed access to *things* — a database, an API client, the current user, config. **Dependency injection (DI)** is how Pydantic AI provides those things: a typed, explicit mechanism for supplying an agent (and its tools and prompts) with the data and services it needs at run time. This post covers what DI is, why Pydantic AI made it a core feature, and why it's the foundation of the framework's excellent testability. It's a familiar backend pattern brought to agents.

## What dependency injection means here

**Dependency injection** is providing a component with its dependencies from the outside rather than having it create or fetch them itself. Instead of a tool reaching for a global database connection, the connection is *injected* — passed in — so the tool just uses what it's given. In Pydantic AI, you declare a **dependency type** for an agent (its `deps_type`), and when you run the agent, you supply an instance of that type; the agent's tools and dynamic prompts then access it (via the `RunContext` from the tools post):

```python
# Illustrative shape — see the Pydantic AI docs for exact API.
from dataclasses import dataclass
from pydantic_ai import Agent, RunContext

@dataclass
class Deps:
    db: Database
    user_id: int

agent = Agent("openai:gpt-...", deps_type=Deps)

@agent.tool
def recent_orders(ctx: RunContext[Deps]) -> list[Order]:
    return ctx.deps.db.recent_orders(ctx.deps.user_id)

# at run time, you INJECT the dependencies:
result = agent.run_sync("Show my recent orders", deps=Deps(db=real_db, user_id=42))
```

The agent's tools and prompts get their `db` and `user_id` from the injected `Deps`, not from globals. You define *what* the agent needs (the typed `deps_type`) once, and *provide* it (a `Deps` instance) at each run. That separation — declare the need, supply it at run time — is the whole idea.

## Why it's typed, and why that matters

Consistent with the framework's philosophy, dependencies are **typed**: `deps_type=Deps` means the agent's context is `RunContext[Deps]`, so tools and prompts access `ctx.deps` with full type safety — the IDE knows `ctx.deps.db` is a `Database` and `ctx.deps.user_id` is an `int`. This typing delivers real benefits:

- **Type checking and autocomplete** — tools accessing dependencies are checked by your tooling; a typo or wrong attribute is caught before runtime.
- **Explicit contracts** — an agent's `deps_type` documents exactly what it needs to run. You can read the type and know its requirements, rather than discovering them by tracing which globals it touches.
- **No hidden ambient state** — dependencies flow explicitly through the typed context, not through module globals or thread-locals, so what an agent depends on is visible and controlled.

This is the same reason typed DI is valued in backend frameworks: it makes dependencies explicit, checked, and controlled rather than implicit and scattered. Pydantic AI brings that discipline to agents, where the temptation to reach for globals (the model, the DB, the config) is strong and leads to tangled, untestable code.

## The payoff: testability

Here is the feature's biggest practical benefit, and a major reason to choose Pydantic AI: **dependency injection makes agents genuinely testable.** Because an agent gets its dependencies injected rather than creating them, you can inject *test* dependencies — a fake database, a stub API client, a fixed user — and test the agent and its tools *without touching real systems*:

- **Unit-test tools** with fake dependencies — call a tool with a `Deps` holding a fake DB and assert on the typed result, no real database needed.
- **Test agent behavior** by injecting controlled dependencies, so tests are deterministic and isolated.
- **Combine with test models** (the next post) — inject fake dependencies *and* use a model that doesn't call a real LLM, and you can test agent logic end-to-end, fast, offline, and deterministically.

This is transformative because LLM agents are notoriously hard to test — they call unpredictable models and reach into real systems. DI removes the "reach into real systems" half of that problem: with dependencies injected, the agent's own logic (its tools, its prompt construction, its flow) is testable in isolation with fakes. The result is that Pydantic AI agents can have real test suites, not just manual "run it and see" checks — a rarity in agent development and a direct consequence of the DI design.

## DI powers dynamic prompts and tools together

Dependency injection isn't a standalone feature; it's the *substrate* that several other features rely on, which is why it's foundational:

- **Dynamic system prompts** (the Agents post) read from injected dependencies to build run-time context — a prompt that includes the current user's name gets it from `ctx.deps`.
- **Tools** (the last post) access dependencies through the `RunContext` to do their work — the database, the API client, the user.
- **Output validators** can use dependencies to validate outputs against real data or rules.

So DI is the common mechanism by which *runtime context* flows into everything an agent does. Understanding it as "the typed channel through which the agent's prompts, tools, and validators receive the data and services they need" ties the framework together: the Agent declares the dependency type, and DI carries typed context to every part that needs it. This is why DI, despite being unglamorous, is central — it's the plumbing that makes the typed, testable, context-aware agent design actually work.

## Using dependency injection well

- **Model dependencies as a typed container** — a dataclass or Pydantic model holding the services and data your agent needs (DB, clients, user, config), declared as the agent's `deps_type`.
- **Inject, don't reach for globals** — access dependencies through the `RunContext` in tools and prompts, keeping the agent free of hidden ambient state.
- **Design for testability** — because dependencies are injected, structure them so you can supply fakes in tests (interfaces/protocols the real and fake implementations share).
- **Keep dependencies focused** — include what the agent actually needs; the `deps_type` is a contract, so a lean, meaningful set is clearer than a grab-bag.

Dependency injection is the quiet foundation that makes Pydantic AI's agents both context-aware and testable — the backend-framework discipline that turns agents from untestable globals-tangles into clean, injected, verifiable components. The next post builds on it to cover the framework's standout strength: testing and evaluating agents.

## Key takeaways

- Dependency injection supplies an agent (and its tools and prompts) with the data and services it needs from the outside: you declare a typed `deps_type` and provide an instance at each run, which tools/prompts access via the `RunContext` — declare the need once, supply it per run.
- Dependencies are typed, so tools access `ctx.deps` with full type safety (checked, autocompleted), the `deps_type` documents an agent's requirements explicitly, and there's no hidden ambient/global state.
- The biggest payoff is testability: because dependencies are injected, you can inject fakes (a fake DB, stub client) to unit-test tools and agent logic without touching real systems — solving half of what makes agents hard to test.
- DI is the substrate for dynamic system prompts (which read injected context), tools (which use injected services), and output validators — the typed channel through which runtime context flows into everything an agent does.
- Use it well by modeling dependencies as a typed container, injecting rather than reaching for globals, designing for fakes in tests (shared interfaces), and keeping the dependency set focused and meaningful.

## Further reading

- [Tools and function calling (previous post)](/blog/posts/pydai-04-tools-and-function-calling.html)
- [Pydantic AI documentation — dependencies](https://ai.pydantic.dev/)
- [Evaluating Agents in Go — the testing mindset for agents](/blog/series/evaluating-agents-in-go/)
