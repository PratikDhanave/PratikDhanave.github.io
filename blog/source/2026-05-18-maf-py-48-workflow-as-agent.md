# Workflow As Agent

*A workflow and an agent both expose .run() — so package a whole workflow as an agent and drop it anywhere an agent is expected.*

---

## What this lesson demonstrates

Both a workflow and an agent expose `.run(...)`, so a whole workflow can be packaged as an agent with `workflow.as_agent(name=...)` and used anywhere an agent fits — inside another workflow, behind DevUI, or as a tool for a third agent. This lesson wraps a one-node title-casing workflow and calls it exactly like the very first agent lesson — no workflow vocabulary at the call site. Pure executors, zero credentials.

## The code

Build an ordinary workflow, then wrap it so it quacks like an agent:

```python
workflow = WorkflowBuilder(start_executor=Headline(id="headline"), name="Headliner").build()
agent = workflow.as_agent(name="HeadlinerAgent")
response = await agent.run("the quick brown fox jumps over the lazy dog")
print(f"agent.run() → {response.text!r}")
```

The start executor is typed to accept what the wrapper feeds it:

```python
async def run(self, messages: list[Message], ctx: WorkflowContext[Never, str]) -> None:
    text = messages[-1].text  # the latest user turn
    await ctx.yield_output(text.strip().title())
```

## What to notice

- **`as_agent()` gives the workflow an agent interface.** The caller uses `agent.run("...")` with a plain string, exactly as with any agent — the workflow machinery is hidden.
- **The wrapper normalizes inputs to `list[Message]`.** A string, a `Message`, or a list of messages all arrive at the start executor as `list[Message]`.
- **Read the latest turn from the list.** `messages[-1].text` pulls the most recent user turn; earlier entries are prior conversation context.

## The gotcha

The one hard rule: the workflow's *start* executor must accept `list[Message]` as its input type. The `as_agent()` wrapper converts every agent-shaped input into `list[Message]` before handing it to the workflow, so a start node typed for `str` or `int` will fail to receive the message.

## How it maps to MAF and Foundry

This unifies the two abstractions the series has built separately. Anything that consumes an agent — an orchestration, DevUI hosting, another agent's tool list — can now consume a full multi-step workflow through the same `.run()` contract. Composition scales: workflows nest inside agents inside workflows, all speaking one interface, with or without a Foundry model behind any given node.

## Run it

```bash
uv run tutorial/03-workflows/05_workflow_as_agent.py
```

Runs offline — no Azure creds. Success: the wrapped workflow title-cases the phrase via `.run()`.

---

Next: [Events](/blog/posts/maf-py-49-events.html)
