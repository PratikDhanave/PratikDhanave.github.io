# Exception Handling

*Catching tool failures in middleware and turning them into graceful replies.*

---

## What it demonstrates

Middleware is the natural seam for error handling: wrap the `await call_next()` call in a try/except and you get one central place to catch failures from tool functions, apply retry/fallback logic, and turn raw exceptions into a friendly reply instead of crashing the run. Here an unstable tool always raises `TimeoutError`; the middleware catches it and overrides the tool's result with a graceful message the model then relays to the user.

## One real excerpt

```python
async def exception_handling_middleware(context: FunctionInvocationContext, call_next) -> None:
    try:
        await call_next()
    except TimeoutError as e:
        print(f"[ExceptionHandlingMiddleware] Caught TimeoutError: {e}")
        # Override the tool result so the exception never reaches the user.
        context.result = (
            "Request Timeout: The data service is taking longer than expected. "
            "Respond with message - 'Sorry for the inconvenience, please try again later.'"
        )
```

## The gotcha

Function-level middleware takes `(context: FunctionInvocationContext, call_next)`, where `call_next` takes no args and returns `None`. To recover from a caught exception, set `context.result` to a substitute value — this replaces the tool output so the exception never reaches the end user. `context.function.name` gives you the name of the tool being invoked. Swallow only the exceptions you intend to handle and re-raise the rest; a bare `except` that silently drops everything hides real bugs.

## Azure / MAF mapping

The middleware is registered via `Agent(..., middleware=[...])` alongside the tool and `FoundryChatClient`. Because it wraps `FunctionInvocationContext`, it fires per tool call inside the agent's run — the model still gets a valid tool result and can compose a coherent apology.

## Run it

`uv run tutorial/02-agents/middleware/05_exception_handling.py` — partially offline. Worked if the tool times out, is caught, and the agent apologizes gracefully.

---

Next: [Shared State](/blog/posts/maf-py-33-shared-state.html)
