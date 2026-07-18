# Result Overrides

*Rewriting a run's output after the model finishes, without touching instructions.*

---

## What it demonstrates

Result-override middleware intercepts the OUTPUT of a run and modifies it before it reaches the caller. The pattern is always the same: `await call_next()` to let the model (and inner middleware / tools) finish, then read and rewrite `context.result`. This is where you enrich answers, inject disclaimers, redact, or replace the response — without editing the agent's instructions. Two layers can override and they nest: chat middleware sees a `ChatResponse` per model call; agent middleware wraps the whole run with an `AgentResponse`.

## One real excerpt

```python
@chat_middleware
async def disclaimer_middleware(context: ChatContext, call_next) -> None:
    await call_next()  # let the model produce its answer first
    if context.result is None:
        return
    original = context.result.text or ""
    context.result = ChatResponse(messages=[Message(
        role="assistant",
        contents=[f"{original}\n\n(Disclaimer: AI-generated, not financial advice.)"],
    )])
```

## The gotcha

Override AFTER `await call_next()` — before it, `context.result` is still `None`, so always guard with `if context.result is None: return`. Replace by assigning a fresh response object: a `ChatResponse` for chat middleware, an `AgentResponse` for agent middleware. Agent middleware is outermost, so it sees whatever the chat layer already produced. For streaming runs (`context.stream is True`), the result is a `ResponseStream` — you don't reassign text, you attach hooks like `context.result.with_transform_hook(...)`. A `Message` is built from `contents=[...]`, a list, not a bare string.

## Azure / MAF mapping

Both `@chat_middleware` and `@agent_middleware` decorators register via `Agent(..., middleware=[...])` over `FoundryChatClient`. Chat-level overrides run per model call; agent-level wraps the entire run, so a single response can carry both a disclaimer and an audit stamp.

## Run it

`uv run tutorial/02-agents/middleware/04_result_overrides.py` — needs Foundry creds. Worked if the answer ends with a disclaimer and an `[audited ✓]` stamp.

---

Next: [Exception Handling](/blog/posts/maf-py-32-exception-handling.html)
