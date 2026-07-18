# Custom Provider

*Writing your own agent by subclassing BaseAgent — a drop-in for the built-in one.*

---

## What it demonstrates

A "custom provider" here does not mean a new model backend — it means writing your **own agent** instead of using a chat-client agent. You subclass `BaseAgent` (which satisfies the `SupportsAgentRun` protocol) and implement one `run()` method. Because you conform to the same protocol, your hand-rolled agent is a drop-in: same `run()`, same streaming, same sessions.

This lesson builds a deterministic `EchoAgent` (no LLM, runs anywhere) and stands a real Foundry `Agent` next to it to prove the interfaces match.

## The code

```python
def run(self, messages=None, *, stream=False, session=None, **kwargs):
    if stream:
        return ResponseStream(
            self._run_stream(messages=messages, session=session, **kwargs),
            finalizer=AgentResponse.from_updates,
        )
    return self._run(messages=messages, session=session, **kwargs)
```

`run()` is one method with two `@overload` signatures keyed on `stream`: `stream=False` returns an awaitable `AgentResponse`; `stream=True` returns a `ResponseStream`. Inside `_run`, coerce input with `normalize_messages(messages)` and build replies with `Content.from_text(...)` on a `Message(role="assistant", ...)`.

## The gotcha

The streaming branch must wrap its async generator in `ResponseStream(gen, finalizer=AgentResponse.from_updates)` — that finalizer is what lets callers still `await stream.get_final_response()`. Sessions are optional; if you want multi-turn history you persist it yourself via `session.state` (the lesson uses a `setdefault("memory", ...)` dict). And a custom agent is not required to call an LLM at all — the deterministic echo is what keeps the lesson runnable with zero model quota.

## Azure / MAF mapping

The payoff is parity: because `EchoAgent` implements `SupportsAgentRun`, swapping it for a live `Agent(client=FoundryChatClient(...))` against Azure AI Foundry (with `AzureCliCredential()`) needs no change to caller code. Same `run()` interface, model or no model.

## Run it

`uv run tutorial/02-agents/providers/02_custom_provider.py` — partial offline (the echo runs anywhere; the Foundry comparison needs creds). It echoes non-stream and stream, then the Foundry agent replies.

---

Next: [Function Tools](/blog/posts/maf-py-37-function-tools.html)
