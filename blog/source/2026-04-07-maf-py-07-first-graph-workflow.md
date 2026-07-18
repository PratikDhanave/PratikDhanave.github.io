# First Graph Workflow

*The functional API hid the graph. Here it's explicit: executors are nodes, edges join them, and a message flows from the start executor along the edges.*

---

## What this lesson demonstrates

A workflow is a set of EXECUTORS (nodes) joined by EDGES. A message enters the start executor and flows along the edges; each executor either forwards a message with `ctx.send_message` or emits a final result with `ctx.yield_output`. This lesson builds a two-node graph — uppercase, then reverse — and shows both ways to write an executor. No model call, so it runs credential-free.

## The code

Two executor styles: subclass `Executor` with a `@handler`, or decorate a module-level async function with `@executor`:

```python
class Upper(Executor):
    @handler
    async def process(self, text: str, ctx: WorkflowContext[str]) -> None:
        await ctx.send_message(text.upper())

@executor(id="reverse")
async def reverse_text(text: str, ctx: WorkflowContext[Never, str]) -> None:
    await ctx.yield_output(text[::-1])

workflow = WorkflowBuilder(start_executor=up).add_edge(up, reverse_text).build()
```

## What to notice

- **The type hint carries routing intent.** `WorkflowContext[str]` means the node will `send_message(str)` onward; `WorkflowContext[Never, str]` marks the node terminal — it only `yield_output(str)`.
- **Streaming yields discriminated events.** `workflow.run(..., stream=True)` emits `WorkflowEvent`s keyed by `.type` ("executor_invoked", "executor_completed", "output") — there are no per-kind classes to import.
- **The gotcha:** `send_message` versus `yield_output` is the whole distinction — one forwards to the next edge, the other ends the workflow. Get them backwards and your graph either never terminates or terminates too early.

## How it maps to Azure AI Foundry

Nothing Foundry-specific — this is the pure graph engine that later executors will use to run agents. Once you swap a plain executor for one that calls a `FoundryChatClient` agent, the same builder and edges orchestrate model calls.

## Run it

```bash
uv run tutorial/01-get-started/07_first_graph_workflow.py
```

Runs offline — no Azure creds needed. Expected: a reversed, uppercased non-streaming output, then the same run as a stream of events.

---

Next: [Host Your Agent](/blog/posts/maf-py-08-host-your-agent.html)
