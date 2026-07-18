# Context And Memory

*Context providers with two hooks — and file-backed history that survives restarts.*

---

## What it demonstrates

A `ContextProvider` gives you two keyword-only hooks around every run:

- `before_run(*, agent, session, context, state)` — inject instructions, messages, or tools
- `after_run(*, agent, session, context, state)` — observe the response, update memory

On the `context` (a `SessionContext`) you inject via `context.extend_instructions(source_id, text)`, `context.extend_messages(...)`, and `context.extend_tools(source_id, tools)`. History providers are just context providers that persist the transcript: `InMemoryHistoryProvider()` (default, lost on exit) or `FileHistoryProvider("./sessions")` (one JSON-Lines file per session, survives restarts).

## The code

```python
class ToneAndTally(ContextProvider):
    def __init__(self) -> None:
        super().__init__(source_id="tone_and_tally")

    async def before_run(self, *, agent, session, context, state) -> None:
        context.extend_instructions(self.source_id, "Always answer in British English, one sentence.")

    async def after_run(self, *, agent, session, context, state) -> None:
        state["turns"] = state.get("turns", 0) + 1
        print(f"[provider] turns so far this session: {state['turns']}")
```

Both a `FileHistoryProvider("./sessions")` and this `ToneAndTally()` go into `Agent(..., context_providers=[...])` — providers stack, and the file history persists the transcript while `ToneAndTally` shapes style.

## The gotcha

Use the `state` dict, not instance attributes, when the count should travel with the session — the framework threads that per-provider dict through the session. Store the turn counter on `self` and it won't follow the session across reuse.

## Azure / MAF mapping

The agent runs on `FoundryChatClient` (Azure AI Foundry) with `AzureCliCredential`. Context providers live in the unified `context_providers=[...]` list — history and custom context alike — independent of the chat client.

## Run it

`uv run tutorial/02-agents/03_context_and_memory.py` — needs Foundry creds. It worked if you get two British-English answers with a turn counter and a persisted transcript under `./sessions/`.

---

Next: [Observability](/blog/posts/maf-py-12-observability.html)
