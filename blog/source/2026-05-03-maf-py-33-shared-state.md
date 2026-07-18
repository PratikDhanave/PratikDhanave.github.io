# Shared State

*Passing data between middleware by putting them on one object.*

---

## What it demonstrates

Middleware in a chain often needs to hand data forward: a request id, timing, or accumulated metrics. Microsoft Agent Framework's Python function-middleware signature is deliberately minimal — `async def mw(context, call_next)` — with no shared bag baked in. The idiomatic trick is to put both middleware **on the same object** and let them read and write instance attributes. That instance *is* the shared state.

This lesson builds a `MiddlewareContainer` holding a `call_count`. The first middleware increments it; the second reads it back to stamp each tool result with its call number.

## The code

```python
class MiddlewareContainer:
    def __init__(self) -> None:
        self.call_count: int = 0  # the shared state both methods touch

    async def call_counter_middleware(self, context, call_next):
        self.call_count += 1
        await call_next()

    async def result_enhancer_middleware(self, context, call_next):
        await call_next()  # tool runs first — result only exists after
        if context.result:
            context.result = f"[Call #{self.call_count}] {context.result}"
```

You wire them in by passing **bound methods of one instance**: `middleware=[container.call_counter_middleware, container.result_enhancer_middleware]`.

## The gotcha

Order matters, and so does *when* you read `context.result`. You must `await call_next()` to continue the chain, and the tool's output only exists *after* that inner call runs — so read or mutate `context.result` after the await, not before. The counter middleware also has to run before the enhancer, or the enhancer stamps a stale count. Mutate the tool output by assigning to `context.result`.

## Azure / MAF mapping

The container pattern is pure Python — no framework API for shared state. The framework contract is `FunctionInvocationContext` plus a zero-argument `call_next`. The agent itself is a plain `Agent(client=FoundryChatClient(...))` against Azure AI Foundry with `AzureCliCredential()`, so the middleware runs around every tool call the model makes.

## Run it

`uv run tutorial/02-agents/middleware/06_shared_state.py` — needs Foundry creds (`az login`). Three queries share the counter and it ends with `Total function calls made: 3`.

---

Next: [Runtime Context](/blog/posts/maf-py-34-runtime-context.html)
