# Events

*Streaming a workflow run so you can watch progress live — built-in lifecycle events plus your own custom ones — all discriminated by a single `.type` string.*

---

## What this lesson demonstrates

A workflow doesn't have to be a black box. As it runs, it **emits events** at every step, and `workflow.run(x, stream=True)` hands them to you one at a time as an async iterator — so you can show progress, log diagnostics, or relay domain data live instead of only seeing the final output.

The Python SDK has **no per-kind event classes**: every event is a single `WorkflowEvent` discriminated by a `.type` string — `"executor_invoked"`, `"executor_completed"`, `"output"`, `"intermediate"`, `"error"`. Executors can also emit **custom** events with any `type=` string plus a `data=` payload.

## One real excerpt

An executor emits a custom `"progress"` event, then the caller filters on `.type`:

```python
class Summarize(Executor):
    @handler
    async def run(self, text: str, ctx: WorkflowContext[str]) -> None:
        await ctx.add_event(WorkflowEvent(type="progress", data="summarize: calling model"))
        reply = await agent.run(text)
        await ctx.send_message(reply.text.strip())

async for event in workflow.run(ARTICLE, stream=True):
    if event.type == "executor_invoked":
        print(f"  → invoked   : {event.executor_id}")
    elif event.type == "progress":            # our custom event
        print(f"  · progress  : {event.data}")
    elif event.type == "output":              # terminal, from ctx.yield_output
        print(f"  ★ output    : {event.data!r}")
```

## The gotcha

Streaming is `workflow.run(x, stream=True)` — there is **no** `run_stream()`. And the types `"started"`, `"status"`, and `"failed"` are **reserved** for framework lifecycle: if an executor tries to emit one, the event is silently dropped and a warning logged. Note also that `"output"` is terminal output (via `ctx.yield_output`, read with `result.get_outputs()`) while `"intermediate"` is observational (read with `result.get_intermediate_outputs()`); `"data"` is a deprecated alias for `"intermediate"`.

## How it maps to Azure AI Foundry

The event plumbing is client-agnostic — but this lesson runs a `FoundryChatClient` agent inside one executor (`FoundryChatClient` + `AzureCliCredential`), so the streamed `executor_invoked`/`progress`/`executor_completed`/`output` sequence wraps a real model call. In production you'd forward the same events to a UI or an OpenTelemetry pipeline.

## Run it

```bash
uv run tutorial/03-workflows/06_events.py
```

Needs Foundry credentials (`az login`). You should see interleaved invoked/progress/completed/output lines, then a `[SUMMARY]` block as the terminal output.

---

Next: [Workflow Builder](/blog/posts/maf-py-50-workflow-builder.html)
