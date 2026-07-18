# Execution Modes

*The same `workflow.run(...)` graph, consumed two ways — await it to completion, or stream its events live. The `.NET` OffThread/Lockstep modes don't apply to Python.*

---

## What this lesson demonstrates

A workflow is defined once, but you can **consume its run in two modes** without changing the graph. Non-streaming — `result = await workflow.run(msg)` — runs to completion, then you read collected outputs off the result. Streaming — `workflow.run(msg, stream=True)` — returns an async stream you iterate with `async for`, receiving `output` and `intermediate` events as each superstep produces them.

The lesson builds one tiny two-agent graph (a writer drafts, an editor tightens) and runs it both ways so you can see the graph is identical; only how you consume events differs.

## One real excerpt

Streaming mode drains events live, then recovers the same result the non-streaming call would return:

```python
stream = workflow.run(topic, stream=True)
async for event in stream:
    if event.type in ("intermediate", "output") and isinstance(event.data, AgentResponseUpdate):
        label = "FINAL" if event.type == "output" else "step "
        print(f"[{label}] {event.executor_id}: {event.data.text}")

# After draining the stream, the same WorkflowRunResult is available.
result = await stream.get_final_response()
print(f"final state : {result.get_final_state()}")
```

## The gotcha

The `.NET` "OffThread" vs "Lockstep" execution modes **do not apply to Python**. Python has a single execution model driven by an async generator — the consumer must keep pulling events for supersteps to advance. Streaming vs non-streaming is just the `stream=` flag on `run`, not a separate engine. Non-streaming returns a `WorkflowRunResult`: use `.get_outputs()` for terminal outputs, `.get_intermediate_outputs()` for progress emissions, `.get_final_state()` for the run state. In streaming mode, `await stream.get_final_response()` after the loop hands you that same result object.

## How it maps to Azure AI Foundry

The mode plumbing is client-agnostic, but both runs drive real agents built on `FoundryChatClient` + `AzureCliCredential`. Streaming is the mode you'd wire to a UI or progress bar; non-streaming fits batch jobs where you only care about the terminal output.

## Run it

```bash
uv run tutorial/03-workflows/advanced/02_execution_modes.py
```

Needs Foundry credentials (`az login`). You should see a `=== NON-STREAMING ===` block, then a `=== STREAMING ===` block with per-step lines for the same job.

---

Next: [Resettable Executors](/blog/posts/maf-py-58-resettable-executors.html)
