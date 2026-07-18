# Agent Executor

*Wrapping agents as AgentExecutors explicitly — controlling the id, the context mode, and chaining a writer to a translator that sees only the previous agent's reply.*

---

## What this lesson demonstrates

A workflow graph routes typed **messages** between executors. An AI agent isn't an executor on its own — it must be wrapped in an `AgentExecutor` so the engine can feed it messages, manage its session, and hand its `AgentExecutorResponse` to the next node. `WorkflowBuilder(start_executor=agent)` wraps agents *implicitly*; this lesson does it **explicitly** so we control the executor id, the context mode, and can chain two agents.

## One real excerpt

Explicit wrapping with `context_mode="last_agent"`, so the translator sees only the writer's sentence — not the original topic prompt:

```python
writer = AgentExecutor(writer_agent, id="writer")
translator = AgentExecutor(translator_agent, id="translator", context_mode="last_agent")

workflow = (
    WorkflowBuilder(start_executor=writer)
    .add_edge(writer, translator)
    .build()
)

request = AgentExecutorRequest(
    messages=[Message(role="user", contents=["a lighthouse at dawn"])],
    should_respond=True,
)
result = await workflow.run(request)
```

## The gotcha

`AgentExecutor(agent, id=..., context_mode="full"|"last_agent"|"custom", ...)` — the `context_mode` is the key knob: `"last_agent"` makes a downstream agent consume **only** the previous agent's reply, ideal for translate/refine pipelines. The canonical input is `AgentExecutorRequest(messages=[Message(role="user", contents=[...])], should_respond=True)`. Each executor emits an `AgentExecutorResponse` carrying `.agent_response`, `.full_conversation` (used for chaining), and `.executor_id`. Non-streaming `run` returns terminal outputs via `result.get_outputs()`, each an `AgentResponse`.

## How it maps to Azure AI Foundry

Both `writer_agent` and `translator_agent` are ordinary `FoundryChatClient` agents (with `AzureCliCredential`); the explicit `AgentExecutor` wrapping is what gives you routing ids and per-node context control over those Foundry calls. The upstream doc shows `client.as_agent()`; this repo uses `Agent(client=...)` — same executor.

## Run it

```bash
uv run tutorial/03-workflows/advanced/01_agent_executor.py
```

Needs Foundry credentials. Output is a French translation — only the translator's response, because of `context_mode="last_agent"`.

---

Next: [Execution Modes](/blog/posts/maf-py-57-execution-modes.html)
