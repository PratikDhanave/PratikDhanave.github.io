# State Management

*Shared workflow state: any executor writes a keyed value, any later executor reads it back — so big payloads never have to be threaded through every message on the edge.*

---

## What this lesson demonstrates

Edges pass a message from one executor to the next, but sometimes downstream nodes need data that was **not** handed to them directly — a big document, an intermediate result, some side output. Shared workflow **state** is the answer: `ctx.set_state(key, value)` writes into shared state, and `ctx.get_state(key)` reads it back in a later executor (returning `None` if absent).

Here a Drafter writes a draft into state, a Counter reads that draft and stores a word count, and a Reporter reads **both** keys to assemble the final report. The messages on the edges only carry a tiny handoff token.

## One real excerpt

The Drafter stashes its output in state and sends only a "go" signal; the Reporter reads both keys back:

```python
class Drafter(Executor):
    @handler
    async def run(self, topic: str, ctx: WorkflowContext[str]) -> None:
        result = await self._agent.run(f"Write a short two-sentence blurb about: {topic}")
        ctx.set_state(DRAFT_KEY, result.text)
        await ctx.send_message("draft-ready")   # the draft itself never travels the edge

class Reporter(Executor):
    @handler
    async def run(self, _signal: str, ctx: WorkflowContext[Never, str]) -> None:
        draft = ctx.get_state(DRAFT_KEY)
        word_count = ctx.get_state(WORD_COUNT_KEY)
        await ctx.yield_output(f"Draft ({word_count} words):\n{draft}")
```

## The gotcha

`set_state` / `get_state` are plain (non-async) methods — only `send_message` and `yield_output` are awaited. A writer sees its own update immediately in the same handler, but **other** executors only see it from the next superstep onward, which is exactly why pipeline order matters. `get_state` returns `None` for a missing key, so guard rather than assume. And state lives on the workflow **instance**: build a fresh workflow per task so state never leaks between runs.

## How it maps to Azure AI Foundry

The Drafter embeds a `FoundryChatClient` agent (with `AzureCliCredential`); the client and agent construct lazily, so the graph is testable offline and only touches the network at `run()`.

## Run it

```bash
uv run tutorial/03-workflows/09_state_management.py
```

Needs Foundry credentials. Output is a `Draft (N words):` block built from the shared state keys.

---

Next: [Declarative Workflow](/blog/posts/maf-py-53-declarative-workflow.html)
