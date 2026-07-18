# Runtime Context

*Passing per-request values to tools without leaking them into the model's schema.*

---

## What it demonstrates

Sometimes a tool needs a value that came from *this* request — a user id, a tenant — but that value has no business being in the tool's JSON schema where the model would try to fill it. Microsoft Agent Framework splits per-run state into three explicit buckets on `agent.run(...)`:

- `session=` — conversation state and history (read via `ctx.session`)
- `function_invocation_kwargs=` — values only tools and function middleware see (`ctx.kwargs`)
- `client_kwargs=` — chat-client-specific config (custom clients)

This lesson uses the first two: it passes a `user_id` through `function_invocation_kwargs`, reads it inside a tool, lets middleware fill a default `tenant`, and stashes state on the session.

## The code

```python
@tool(approval_mode="never_require")
def send_email(address, ctx: FunctionInvocationContext) -> str:
    user_id = ctx.kwargs["user_id"]          # per-run, not a tool argument
    tenant = ctx.kwargs.get("tenant", "default")
    if ctx.session is not None:
        ctx.session.state["last_email_to"] = address  # persists across runs
    return f"Queued email for {address} from {user_id} ({tenant})"
```

Middleware sees the *same* `FunctionInvocationContext`, so it can enrich kwargs before the tool runs: `context.kwargs.setdefault("tenant", "contoso")`, then `await call_next()`.

## The gotcha

Any parameter annotated `FunctionInvocationContext` is injected regardless of its name and is **hidden from the tool's schema**. Read per-run values with `ctx.kwargs["..."]` — do not add blanket `**kwargs` to tools, because unexpected runtime kwargs are rejected. Consume them through the context object instead.

## Azure / MAF mapping

The agent is a `FoundryChatClient` against Azure AI Foundry with `AzureCliCredential()`. Runtime context is framework plumbing that rides alongside the Foundry call: `function_invocation_kwargs` never reach the model, and `session.state` written inside a tool survives across runs on the same session.

## Run it

`uv run tutorial/02-agents/middleware/07_runtime_context.py` — needs Foundry creds. It queues the email and prints `[session] last_email_to = finance@example.com`.

---

Next: [Foundry](/blog/posts/maf-py-35-foundry.html)
