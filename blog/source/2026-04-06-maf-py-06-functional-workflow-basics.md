# Functional Workflow Basics

*A workflow is not an LLM thing — it's a way to compose steps with checkpointing and events. This one has no agent and no model call, so it runs with zero credentials.*

---

## What this lesson demonstrates

To see the workflow *mechanics* without the LLM in the way, this program strips out the agents entirely. It classifies a string as "short" or "long" using two `@step` functions composed by a `@workflow`. No model, no `az login`, no network — just the orchestration machinery, isolated.

## The code

A `@step` is an async unit of work whose result is cached and checkpointed; a `@workflow` composes steps with ordinary control flow:

```python
@step
async def normalize(text: str) -> str:
    return text.strip().lower()

@step
async def word_count(text: str) -> int:
    return len(text.split())

@workflow
async def summarize_input(raw: str) -> str:
    clean = await normalize(raw)
    count = await word_count(clean)
    verdict = "short" if count < 5 else "long"
    return f"{count} words ({verdict}): {clean!r}"
```

## What to notice

- **Plain Python is the orchestration.** Sequential `await`s and an ordinary `if` branch — no DSL to learn before the graph API arrives in the next lesson.
- **`@step` is where checkpointing lives.** Each step's result is cached/checkpointed, which is what makes workflows resumable later; here it just runs top to bottom.
- **The gotcha:** `.run()` returns a `WorkflowRunResult`, so read the value with `result.get_outputs()[0]` — `get_outputs()` returns a list because a workflow can yield more than one output.

## How it maps to Azure AI Foundry

Nothing — deliberately. This lesson has no `FoundryChatClient` and makes no Foundry call, which is the point: it isolates the workflow engine from the model so you can reason about steps, caching, and outputs on their own before adding agents back in.

## Run it

```bash
uv run tutorial/01-get-started/06_functional_workflow_basics.py
```

Runs offline — no Azure creds needed. Expected: one line classifying a 5-word string as "long".

---

Next: [First Graph Workflow](/blog/posts/maf-py-07-first-graph-workflow.html)
