# Handoff

*A mesh of specialists where any agent can transfer the whole conversation to a better-suited peer — no central orchestrator. Control passes agent-to-agent via an auto-injected handoff tool call.*

---

## What this lesson demonstrates

Handoff orchestration wires specialist agents into a **mesh** where any agent can transfer ("hand off") the whole conversation to a better-suited peer. There is no central orchestrator: control passes agent-to-agent via an auto-injected handoff tool call, and the receiving agent takes full ownership with the complete conversation context. Think customer-support triage routing to refund / order / return specialists.

The lesson builds a triage agent plus three tool-owning specialists and lets a "damaged order, want a refund" request route itself through the mesh.

## One real excerpt

`with_start_agent` picks who receives the first message; `add_handoff(src, [dst, ...])` restricts routing:

```python
from agent_framework.orchestrations import HandoffBuilder

workflow = (
    HandoffBuilder(name="customer_support_handoff",
                   participants=[triage_agent, order_agent, return_agent, refund_agent])
    .with_start_agent(triage_agent)
    .add_handoff(triage_agent, [order_agent, return_agent])
    .add_handoff(return_agent, [refund_agent])
    .with_autonomous_mode(turn_limits={triage_agent.name: 3})   # run unattended
    .build()
)
```

## The gotcha

Handoff is **inherently interactive**. A handoff is a special tool call; if an agent answers instead of handing off, the workflow can't know what's next, so it emits a `request_info` event (a `HandoffAgentUserRequest`) and waits for human input. To run unattended, call `.with_autonomous_mode()` — an experimental feature that auto-replies to those requests; `turn_limits` caps autonomous turns so it can't loop forever. Each specialist needs `require_per_service_call_history_persistence=True` so local context survives the handoff short-circuits. Only user/agent messages are broadcast for context — handoff tool calls and results are filtered out. Import `HandoffBuilder` from `agent_framework.orchestrations`, not the top-level package.

## How it maps to Azure AI Foundry

Every agent is a `FoundryChatClient` + `AzureCliCredential` agent; each specialist owns a plain `@tool` function (order lookup, return, refund). The handoff tool itself is injected by the builder — you don't write it.

## Run it

```bash
uv run tutorial/03-workflows/orchestrations/03_handoff.py
```

Needs Foundry credentials (`az login`). You should see per-speaker `[executor_id]` headers as control hands off between agents.

---

Next: [Group Chat](/blog/posts/maf-py-63-group-chat.html)
