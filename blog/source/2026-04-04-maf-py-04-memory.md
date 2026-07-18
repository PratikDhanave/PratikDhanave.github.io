# Memory

*A session remembers within one conversation. A ContextProvider remembers across all of them — durable facts injected into every run.*

---

## What this lesson demonstrates

The last lesson gave an agent memory *within* one conversation via a session. But real assistants remember across conversations — "you told me last week you bank with HDFC." That durable knowledge lives in a `ContextProvider`, an object the agent consults on every run regardless of which session. Because the provider instance persists between runs, what it injects survives even a brand-new session.

## The code

Subclass `ContextProvider` and use its two keyword-only hooks. `before_run` slips facts into this run's system prompt; `after_run` is where you'd learn new ones:

```python
class ProfileMemory(ContextProvider):
    def __init__(self) -> None:
        super().__init__(source_id="profile_memory")  # source_id is required
        self.facts: list[str] = []

    async def before_run(self, *, agent, session, context, state) -> None:
        if self.facts:
            note = "Known facts about the user: " + "; ".join(self.facts) + "."
            context.extend_instructions(self.source_id, note)
```

Attach it with `context_providers=[memory]`, then two *different* sessions both know the user.

## What to notice

- **Facts live on `self`, not in a session.** The provider outlives any `AgentSession`, so its facts carry across conversations — which is exactly what a session cannot do.
- **`context.extend_instructions(source_id, text)`** injects a note into the system prompt for one run only; the persistence comes from the provider instance holding the facts.
- **The gotcha:** `source_id` is required in `super().__init__()`, and both hooks are keyword-only (`*, agent, session, context, state`). Miss the keyword-only star and the framework won't call them as expected.

## How it maps to Azure AI Foundry

Nothing Foundry-specific here — the provider runs client-side, extending the instructions sent to the Foundry Responses API on each request. A production `after_run` would extract facts with an LLM call or tool; the lesson keeps it deterministic and offline. Same `FoundryChatClient` + `AzureCliCredential`.

## Run it

```bash
uv run tutorial/01-get-started/04_memory.py
```

Expected: session two still knows the user because the facts live in the provider. Needs Foundry creds and `az login`.

---

Next: [Functional Workflow With Agents](/blog/posts/maf-py-05-functional-workflow-with-agents.html)
