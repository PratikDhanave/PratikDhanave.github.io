# Storage

*Where conversation history actually lives — local session state vs service-managed.*

---

## What it demonstrates

A session's history has to be stored somewhere. Agent Framework gives you two modes: **local session state**, where the full transcript is kept in the session and re-sent on each run (you opt in with an `InMemoryHistoryProvider`, or a DB/Redis-backed one), and **service-managed**, where the service holds the conversation and the session only carries a remote id. Either way, to survive a process restart you persist the WHOLE `AgentSession`, not just the message text.

## One real excerpt

```python
return Agent(
    client=client,
    name="StorageAgent",
    instructions="You are a helpful assistant with a good memory.",
    context_providers=[InMemoryHistoryProvider("memory", load_messages=True)],
)
```

The provider replays the stored transcript on each run because `load_messages=True`. Swap `InMemoryHistoryProvider` for a database-backed provider and the rest of the flow is identical — that provider seam is the whole point.

## The gotcha

Only ONE history provider per agent may set `load_messages=True`, otherwise the transcript double-loads. Persist with `session.to_dict()` and restore with `AgentSession.from_dict()`, treating the payload as opaque — then rebuild the SAME agent/provider configuration to resume it. `require_per_service_call_history_persistence=True` keeps local history around each model call (handy with tool-calling), but it errors if the run is already bound to a service-managed conversation. Don't mix the two persistence models.

## Azure / MAF mapping

A chat-completions client like `FoundryChatClient` uses local history (the provider above); a responses-style service that persists conversations exposes `session.service_session_id` instead, which you rehydrate with `agent.get_session(service_session_id=...)`. Don't hand-write that id — read it off the session.

## Run it

`uv run tutorial/02-agents/conversations/02_storage.py` — needs Foundry creds. Worked if recall works in-session AND after a deserialize into a fresh agent.

---

Next: [Compaction](/blog/posts/maf-py-27-compaction.html)
