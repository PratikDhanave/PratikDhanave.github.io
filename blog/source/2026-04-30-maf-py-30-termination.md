# Termination

*Building guardrails by raising MiddlewareTermination to stop a run.*

---

## What it demonstrates

Inside `process(context, call_next)` you decide whether to let a run proceed (`await call_next()`) or STOP it. To stop, you raise `MiddlewareTermination` — optionally after setting `context.result` to a canned response. This is the guardrail pattern: block disallowed input BEFORE the model is called (pre-termination), or cap how many times an agent may respond (post-termination).

## One real excerpt

```python
class PostTerminationMiddleware(AgentMiddleware):
    def __init__(self, max_responses: int = 1):
        self.max_responses = max_responses
        self.response_count = 0

    async def process(self, context: AgentContext, call_next) -> None:
        if self.response_count >= self.max_responses:
            raise MiddlewareTermination  # cap reached
        await call_next()
        self.response_count += 1
```

## The gotcha

Terminate by raising `MiddlewareTermination`; short-circuiting means not calling `call_next()`. Pre-termination raises it INSTEAD of awaiting `call_next()` so the model is never hit — set `context.result = AgentResponse(...)` first, then raise `MiddlewareTermination(result=context.result)` so the caller gets a sensible answer rather than an exception bubbling up. Middleware instances carry state across runs (like `self.response_count`), so a single agent object can enforce a running quota — handy for rate limiting. `context.messages[-1].text` is the latest user turn.

## Azure / MAF mapping

Middleware are `AgentMiddleware` subclasses registered with `Agent(..., middleware=[Instance(), ...])`, which forms a chain wrapping every `agent.run()` over `FoundryChatClient`. The pre-termination guardrail saves a model call entirely when input is blocked.

## Run it

`uv run tutorial/02-agents/middleware/03_termination.py` — partially offline. Worked if a blocked word is refused and a second response is capped.

---

Next: [Result Overrides](/blog/posts/maf-py-31-result-overrides.html)
