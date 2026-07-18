# Agent Pipeline

*An Agent is a layered pipeline — knowing the layers tells you exactly where to plug in.*

---

## What it demonstrates

An `Agent` is not a single function call — it's a layered pipeline every request flows through, built by class composition:

```
Agent (outer)                     ← what you construct
  ├─ Agent Middleware + Telemetry ← wraps run(); logging/validation/spans
  ├─ RawAgent                     ← core logic; invokes context providers
  └─ Context Providers            ← history + extra context, per-run
ChatClient (separate, swappable)
  ├─ FunctionInvocation           ← the tool-calling loop
  ├─ Chat Middleware + Telemetry  ← runs per model call
  └─ RawChatClient                ← provider-specific LLM comms (Foundry here)
```

A request descends the Agent layers, crosses into the ChatClient pipeline, and the response flows back up.

## The code

```python
@agent_middleware
async def tracing_middleware(context: AgentContext, call_next) -> None:
    print("  [agent-middleware] entering pipeline — request handed to RawAgent")
    await call_next()  # descend: context providers -> ChatClient -> LLM -> back up
    print("  [agent-middleware] leaving pipeline — response has flowed back up")
```

`Agent(..., middleware=[tracing_middleware], context_providers=[InMemoryHistoryProvider()])` wires the outermost layer and the context layer. Turn 1 stores a name; turn 2 recalls it because the history provider replays turn 1 into the request before it reaches the ChatClient.

## The gotcha

Middleware is attached at construction (`Agent(..., middleware=[fn])`) and both history and RAG/context providers live in **one** unified `context_providers=[...]` list — there's no separate history argument. Providers run in list order and can even attach per-invocation chat/function middleware, which the agent flattens before entering the ChatClient pipeline.

## Azure / MAF mapping

The ChatClient is a separate, interchangeable component: swapping Foundry (`FoundryChatClient` + `AzureCliCredential`) for another provider changes only `RawChatClient` — the outer Agent layers are unchanged.

## Run it

`uv run tutorial/02-agents/07_agent_pipeline.py` — needs Foundry creds. It worked if turn 2 recalls 'Pratik' and the middleware enter/leave lines bracket each run.

---

Next: [Multimodal](/blog/posts/maf-py-16-multimodal.html)
