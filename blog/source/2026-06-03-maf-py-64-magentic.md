# Magentic

*For open-ended tasks with no known solution path: a manager agent plans, keeps a shared ledger, and round-by-round picks which specialist acts next. Ordering is dynamic, not a fixed graph.*

---

## What this lesson demonstrates

Magentic orchestration (from AutoGen's Magentic-One) is for **complex, open-ended tasks** where the solution path isn't known up front. A dedicated **manager** agent plans the work, keeps a shared task ledger, and — round by round — decides which specialist should act next based on evolving progress. Here a Researcher (gathers info) and a Coder (writes/runs code) collaborate under a Manager until the task is synthesized into a final answer. Unlike a fixed graph, ordering is chosen dynamically.

## One real excerpt

`participants`, `manager_agent`, and the inner-loop safety limits are all constructor kwargs:

```python
from agent_framework.orchestrations import MagenticBuilder

return MagenticBuilder(
    participants=[researcher_agent, coder_agent],
    intermediate_output_from=[researcher_agent, coder_agent],
    manager_agent=manager_agent,
    max_round_count=10,   # hard cap on coordination rounds
    max_stall_count=3,    # consecutive non-progress rounds before an auto-replan
    max_reset_count=2,    # times the manager may discard the plan and restart
).build()
```

## The gotcha

The manager reads each participant's **`description`** to decide who acts next, so make each capability distinct. The three limits guard the inner loop: `max_stall_count` triggers an auto-replan after consecutive non-progress rounds, `max_reset_count` caps full plan restarts. `intermediate_output_from=[...]` promotes participant outputs to `"intermediate"` events; the manager's synthesized answer stays the `"output"`. Planning milestones arrive as `event.type == "magentic_orchestrator"` (`event_type` = `PLAN_CREATED` / `REPLANNED` / `PROGRESS_LEDGER_UPDATED`). Plan review is **off** by default in Python (`enable_plan_review=False`), so it runs end-to-end without interaction; the final answer comes from `await stream.get_final_response().get_outputs()[-1]`.

## How it maps to Azure AI Foundry

Manager, Researcher, and Coder are all `FoundryChatClient` + `AzureCliCredential` agents; the Coder additionally gets `client.get_code_interpreter_tool()`, so it can actually run analysis code inside the Foundry-hosted interpreter while the manager coordinates.

## Run it

```bash
uv run tutorial/03-workflows/orchestrations/05_magentic.py
```

Needs Foundry credentials (`az login`). You should see orchestrator `PLAN` events plus delegated turns, then a `=== Final Answer ===`.

---

Next: [Devui](/blog/posts/maf-py-65-devui.html)
