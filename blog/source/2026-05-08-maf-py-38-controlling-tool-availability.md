# Controlling Tool Availability

*Growing and shrinking the tool set from inside a running turn.*

---

## What it demonstrates

You don't have to hand the model every tool up front. Inside a running turn you can grow or shrink the tool set **from within a tool itself**, using the `FunctionInvocationContext` the framework injects. This loader/gating pattern keeps the initial schema small — better tool selection, lower cost — and lets you enforce ordering like "read before write" without spinning up a full workflow.

This lesson shows two patterns: a loader tool that reveals a hidden `factorial`, and a gate that unlocks `update_record` only after `get_record` runs. It also uses `tool_choice` to force a specific first call.

## The code

```python
@tool(approval_mode="never_require")
def get_record(record_id: str, ctx: FunctionInvocationContext) -> str:
    """Fetch a record. Unlocks update_record once a record has been read."""
    ctx.add_tools(update_record)  # visible to the model on the NEXT loop iteration
    return f"Record {record_id}: title='Example record', status='open'"
```

The mutation API lives on the context: `ctx.add_tools(...)`, `ctx.remove_tools(...)`, and the live mutable list `ctx.tools`. To force the first call you pass a `ToolMode`: `{"mode": "required", "required_function_name": "get_record"}` via `options={"tool_choice": ...}`.

## The gotcha

Changes take effect on the **next** iteration of the function-calling loop — tool calls already dispatched in the current batch still run first. The tool list also **resets to the original set on every new `agent.run()`**, so gates re-arm per turn. This API is experimental (feature id `PROGRESSIVE_TOOLS`): it emits an `ExperimentalWarning` on first use, and calling add/remove outside the loop (when `ctx.tools is None`) raises `RuntimeError`. The framework resets `tool_choice` to `None` after the first iteration, so later steps are free to pick the newly unlocked tool.

## Azure / MAF mapping

The `ctx` parameter is injected by the Foundry-backed agent (`FoundryChatClient` + `AzureCliCredential()`) and is invisible to the model — same injection mechanism as runtime context. Progressive exposure is a client-side gate around the Azure AI Foundry call loop.

## Run it

`uv run tutorial/02-agents/tools/02_controlling_tool_availability.py` — needs Foundry creds. The progressive section computes `5! = 120`; the gating section fetches then updates a record.

---

Next: [Tool Approval](/blog/posts/maf-py-39-tool-approval.html)
