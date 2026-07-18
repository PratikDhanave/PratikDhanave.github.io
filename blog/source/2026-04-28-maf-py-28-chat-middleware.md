# Chat Middleware

*Wrapping every model call to inspect, mutate, or short-circuit it.*

---

## What it demonstrates

Chat middleware sits between the agent and the underlying chat client, running on EVERY call to the model. Each middleware receives a `ChatContext` and a `call_next` continuation: you inspect or mutate `context.messages` before the model sees them, `await call_next()` to invoke the model (and any inner middleware), then inspect `context.result` afterward. You can also skip the model entirely — set `context.result` yourself and raise `MiddlewareTermination`.

## One real excerpt

```python
@chat_middleware
async def security_middleware(context: ChatContext, call_next) -> None:
    blocked = ["password", "secret", "api_key", "token"]
    for msg in context.messages:
        if msg.text and any(term in msg.text.lower() for term in blocked):
            context.result = ChatResponse(messages=[Message(
                role="assistant",
                contents=["I can't process requests containing sensitive data. Please rephrase."],
            )])
            raise MiddlewareTermination  # override without calling the model
    await call_next()
```

## The gotcha

The decorated function signature is `(context: ChatContext, call_next) -> None` — it returns `None`, so you communicate results by mutating `context`, never by returning a value. To edit the message list, mutate in place with `context.messages[:] = new_list`; rebinding the local name would not propagate. To override a response without hitting the model, set `context.result` to a `ChatResponse` and raise `MiddlewareTermination` — do NOT call `call_next()`.

## Azure / MAF mapping

Register with the `@chat_middleware` decorator, then pass `middleware=[...]` to `Agent`. Agent-level middleware applies to all runs, outermost first; you can also pass `middleware=[...]` on a single `agent.run()` for that call only. The agent runs over `FoundryChatClient` as usual.

## Run it

`uv run tutorial/02-agents/middleware/01_chat_middleware.py` — partially offline. Worked if a normal query logs each call and a sensitive query is blocked with the canned reply.

---

Next: [Agent Vs Run Scope](/blog/posts/maf-py-29-agent-vs-run-scope.html)
