# Visualization

*WorkflowViz renders a built workflow's graph as a Mermaid diagram, a Graphviz DOT string, or an exported image — so you can eyeball fan-out/fan-in structure without running the agents.*

---

## What this lesson demonstrates

A workflow with several executors and fan-out/fan-in edges is hard to read from code alone. `WorkflowViz` takes a built `Workflow` and renders its graph — as a Mermaid diagram, a Graphviz DOT string, or an exported image file — so you can confirm the structure matches the design you intended.

## One real excerpt

Build a fan-out/fan-in graph, wrap it in `WorkflowViz`, and emit the text formats:

```python
workflow = (
    WorkflowBuilder(start_executor=dispatcher)
    .add_fan_out_edges(dispatcher, [researcher, marketer, legal])
    .add_fan_in_edges([researcher, marketer, legal], aggregate)
    .build()
)

viz = WorkflowViz(workflow)
print(viz.to_mermaid())      # no extra deps
print(viz.to_digraph())      # Graphviz DOT source

try:
    svg_path = viz.save_svg("workflow.svg")   # needs graphviz pkg + binary
except Exception as exc:
    print(f"[skip] image export unavailable: {exc}")
```

## The gotcha

Text output (`to_mermaid()`, `to_digraph()`) needs **no** extra dependencies. Image export (`export(format=...)`, `save_svg/png/pdf`) requires both the `graphviz` Python package **and** the GraphViz system binary — hence the try/except so the lesson still prints something without them. Visualization only reads the graph *shape*; it does **not** run the agents, so no model call is made just to draw the diagram. The start executor renders green "(Start)", fan-in nodes render as a golden ellipse, and conditional edges render dashed. Note the fan-in target must be a plain `@executor` accepting a `list[AgentExecutorResponse]` — an agent-executor can't be a direct fan-in target since its input is a single message.

## How it maps to Azure AI Foundry

The four branch nodes are `FoundryChatClient` agents (with `AzureCliCredential`), but drawing the diagram touches none of them — `WorkflowViz` inspects the wiring, not the model. It's the fastest way to sanity-check a Foundry-backed graph before you spend a single token running it.

## Run it

```bash
uv run tutorial/03-workflows/12_visualization.py
```

Partly offline (drawing needs no creds). Mermaid and DOT source print; an SVG is written if GraphViz is installed.

---

Next: [Agent Executor](/blog/posts/maf-py-56-agent-executor.html)
