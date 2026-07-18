# Agent Vs Run Scope

*Where you attach middleware decides when it fires — every run, or just one.*

---

## What it demonstrates

Middleware can be attached in two places, and the location determines the timing. **Agent scope** — passed to `Agent(..., middleware=[...])` — runs on EVERY call to `agent.run()`; use it for cross-cutting policy that must always apply (a security gate, perf monitoring). **Run scope** — passed to `agent.run(query, middleware=[...])` — runs ONLY for that one call; use it for per-request behaviour like debug tracing that shouldn't leak into other runs.

## One real excerpt

```python
class SecurityAgentMiddleware(AgentMiddleware):
    async def process(self, context: AgentContext, call_next) -> None:
        last = context.messages[-1] if context.messages else None
        if last and last.text and any(w in last.text.lower() for w in ("password", "secret")):
            return  # short-circuit: the agent never runs
        context.metadata["security_validated"] = True
        await call_next()

# run-scope: exists only for this call
r = await agent.run("What's the weather in Tokyo?", middleware=[debugging_middleware])
```

## The gotcha

The same `middleware=[...]` keyword is used at both scopes. Execution nests: for agent middleware `[A1, A2]` and run middleware `[R1]`, the order is `A1 → A2 → R1 → Agent → R1 → A2 → A1`. Skipping `await call_next()` short-circuits the chain. A middleware is either an `AgentMiddleware` subclass (override async `process`) or a plain `async def(context, call_next)` — both take a context plus `call_next`. Agent-level `AgentContext.metadata` is visible to run-level middleware downstream. Function/tool middleware (`FunctionInvocationContext`) fires inside agent execution, once per tool call.

## Azure / MAF mapping

The agent runs over `FoundryChatClient` with tools; agent-scope middleware wraps every `agent.run()`, run-scope wraps a single call, and both nest around the same `FoundryChatClient`-backed run.

## Run it

`uv run tutorial/02-agents/middleware/02_agent_vs_run_scope.py` — partially offline. Worked if agent-scope middleware fires every run, run-scope only for its call, and the sensitive run is blocked.

---

Next: [Termination](/blog/posts/maf-py-30-termination.html)
