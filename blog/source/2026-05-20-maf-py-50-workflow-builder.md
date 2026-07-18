# Workflow Builder

*Wiring executors and edges into a graph with WorkflowBuilder — pick a start node, add edges, build, then run an input through the chain.*

---

## What this lesson demonstrates

A workflow ties **executors** (processing nodes) and **edges** (directed connections) into a graph, then manages execution. You build one with `WorkflowBuilder`: pick a start executor, wire nodes with `add_edge`, call `build()`, then `run()` an input through it. Messages flow node → node; the final node yields the output.

This lesson chains three nodes: `prepare` (a plain function executor) → `writer` (a Foundry agent wrapped in an `Executor`) → `finalize` (yields the output).

## One real excerpt

Two ways to declare a node — the `@executor` decorator for functions, an `Executor` subclass for stateful nodes — then the fluent builder:

```python
@executor(id="prepare")
async def prepare(topic: str, ctx: WorkflowContext[str]) -> None:
    await ctx.send_message(f"Write a two-sentence explainer about: {topic}")

@executor(id="finalize")
async def finalize(draft: str, ctx: WorkflowContext[Never, str]) -> None:
    await ctx.yield_output(draft.strip())

return (
    WorkflowBuilder(start_executor=prepare, output_from=[finalize])
    .add_edge(prepare, writer)
    .add_edge(writer, finalize)
    .build()
)
```

## The gotcha

`WorkflowBuilder` takes `start_executor=...` as a **keyword** arg, not positional. Handlers must be async and **type-annotated**: `WorkflowContext[T]` declares the message type sent downstream, while `WorkflowContext[Never, T]` means "sends no message, yields output `T`". Which executor's `yield_output` counts as the terminal answer is a build-time choice — pass `output_from=[...]` to the builder. A non-streaming `run` returns a `WorkflowRunResult`; read it with `result.get_outputs()`.

## How it maps to Azure AI Foundry

The `writer` node is a `FoundryChatClient` agent (with `AzureCliCredential`) wrapped in an `Executor` subclass, so agents drop into the graph as ordinary nodes. Construction is offline — the Foundry client only touches the network when `run()` executes.

## Run it

```bash
uv run tutorial/03-workflows/07_workflow_builder.py
```

Needs Foundry credentials. Output is a finalized two-sentence explainer about a message bus.

---

Next: [Agents In Workflows](/blog/posts/maf-py-51-agents-in-workflows.html)
