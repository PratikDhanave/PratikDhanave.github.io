# Functional Workflow With Agents

*Compose several agents into a pipeline with the gentlest workflow API: decorate an async function with @workflow and call agents inside it with plain await.*

---

## What this lesson demonstrates

So far, one agent per program. A workflow composes several. The *functional* workflow API is the softest entry point: ordinary Python control flow (if / for / await) *is* the orchestration. Here a WRITER agent drafts a paragraph and an EDITOR agent tightens it — two roles, one line of glue each.

## The code

The `@workflow`-decorated function is the orchestration graph, written as normal async code:

```python
@workflow
async def draft_and_edit(topic: str) -> str:
    draft = await writer.run(topic)
    print(f"\n[writer draft]\n{draft.text}\n")
    final = await editor.run(draft.text)
    return final.text
```

Run it and pull the return value out of the result:

```python
result = await draft_and_edit.run("Deploying to production on a Friday")
print(result.get_outputs()[0])
```

## What to notice

- **The output of one step feeds the next as plain data.** `editor.run(draft.text)` consumes the writer's text — no message bus, no wiring, just `await`.
- **`.run()` returns a `WorkflowRunResult`, not the value.** Call `.get_outputs()` to get a list (a workflow can yield more than one output); `[0]` is the returned string.
- **The gotcha:** the functional workflow API is marked experimental in this SDK build, so you may see an experimental-feature warning at runtime — that is expected, not an error.

## How it maps to Azure AI Foundry

Both agents share one `FoundryChatClient`, so the workflow makes two sequential Foundry Responses calls — writer, then editor. Construction is offline; only `.run()` touches the model. Same `AzureCliCredential` for auth.

## Run it

```bash
uv run tutorial/01-get-started/05_functional_workflow_with_agents.py
```

Expected: a writer draft, then the editor's tightened two-sentence version. Needs Foundry creds and `az login`.

---

Next: [Functional Workflow Basics](/blog/posts/maf-py-06-functional-workflow-basics.html)
