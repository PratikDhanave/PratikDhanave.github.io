# Agents In Workflows

*An agent can be a graph node directly — no custom Executor subclass. Writer drafts, a direct edge hands its output to Reviewer, and streamed tokens group by author.*

---

## What this lesson demonstrates

A workflow is a graph of executors wired by edges — and an **agent can be an executor node directly**, with no custom `Executor` subclass. Here a Writer agent drafts content, then a direct edge hands its output to a Reviewer agent that critiques it. Output flows down the pipeline; latency is sequential (Writer, then Reviewer).

## One real excerpt

Agents *are* the executors — the Writer is the start node, an edge feeds the Reviewer, and streamed updates are grouped by their author agent:

```python
return (
    WorkflowBuilder(start_executor=writer_agent)
    .add_edge(writer_agent, reviewer_agent)
    .build()
)

async for event in workflow.run(prompt, stream=True):
    if event.type == "output" and isinstance(event.data, AgentResponseUpdate):
        update = event.data
        if update.author_name != last_author:
            print(f"\n{update.author_name}: {update.text}", end="", flush=True)
            last_author = update.author_name
        else:
            print(update.text, end="", flush=True)
```

## The gotcha

`workflow.run(prompt, stream=True)` yields `WorkflowEvent`s: filter `event.type == "output"` **and** check `isinstance(event.data, AgentResponseUpdate)` to read streamed agent tokens. Each update carries `.author_name` (which agent) and `.text` (the token chunk), so you group consecutive chunks by author to reconstruct each agent's message. The upstream doc builds agents via `client.as_agent(...)`; this repo's house style uses the `Agent(client=...)` constructor — same resulting executor.

## How it maps to Azure AI Foundry

Both agents share one `FoundryChatClient` (with `AzureCliCredential`), so the whole pipeline runs against a single Foundry model deployment. Wiring agents as nodes is how you compose multi-agent behavior (draft → review → edit) without leaving the workflow graph.

## Run it

```bash
uv run tutorial/03-workflows/08_agents_in_workflows.py
```

Needs Foundry credentials. You'll see streamed `Writer:` then `Reviewer:` output, grouped by author.

---

Next: [State Management](/blog/posts/maf-py-52-state-management.html)
