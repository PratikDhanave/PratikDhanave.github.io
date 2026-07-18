# Middleware

*Wrapping an agent run to observe, guard, or short-circuit it — without touching the agent's logic.*

---

## What it demonstrates

Middleware is the seam for cross-cutting concerns: logging, guardrails, caching, retries. In Microsoft Agent Framework a middleware is a plain `async def mw(context, call_next)`, and there are three kinds:

- `@agent_middleware` — wraps the whole run (`context: AgentContext`)
- `@chat_middleware` — wraps each model call (`context: ChatContext`)
- `@function_middleware` — wraps each tool call (`context: FunctionInvocationContext`)

One `middleware=[...]` list may mix all three; the framework sorts them by type.

## The code

```python
@function_middleware
async def block_dangerous_locations(context: FunctionInvocationContext, call_next) -> None:
    """Guard a TOOL call: refuse to run get_weather for a blocked location."""
    if context.function.name == "get_weather" and context.arguments.get("location") == "Mordor":
        context.result = "Refused: weather service does not cover Mordor."
        raise MiddlewareTermination(result=context.result)  # short-circuit — tool never runs
    await call_next()
```

An `@agent_middleware` `timing` and this `block_dangerous_locations` both go into `Agent(..., middleware=[timing, block_dangerous_locations])`. Ask for Pune and the tool runs; ask for Mordor and the function middleware refuses before the tool executes.

## The gotcha

Two things trip people up. `call_next` takes **no arguments** and returns `None` — all state rides on `context`, not on a return value. And there is **no** `context.terminate`: to stop early you set `context.result` and `raise MiddlewareTermination(result=...)`.

## Azure / MAF mapping

The guarded agent is built on `FoundryChatClient(project_endpoint=..., model=..., credential=AzureCliCredential())` pointed at Azure AI Foundry. Middleware sits entirely outside the client, so the same guard works regardless of the underlying model provider.

## Run it

`uv run tutorial/02-agents/01_middleware.py` — needs Foundry credentials (`az login` plus `FOUNDRY_PROJECT_ENDPOINT` / `FOUNDRY_MODEL`). It worked if Pune returns weather and Mordor is refused.

---

Next: [Mcp Tools](/blog/posts/maf-py-10-mcp-tools.html)
