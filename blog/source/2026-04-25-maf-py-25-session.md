# Session

*Carrying conversation state across separate agent.run() calls with AgentSession.*

---

## What it demonstrates

A bare `agent.run()` starts cold every time — the agent has no memory of the last call. An `AgentSession` is the state container that fixes this: it holds the history and scratch state, and passing the SAME session into every `run()` is what makes turn 2 remember turn 1. This lesson also shows that a session is serializable, so a conversation can be paused and resumed later.

## One real excerpt

```python
# One session shared across turns == the agent's working memory.
session = agent.create_session()

first = await agent.run("My name is Alice.", session=session)
second = await agent.run("What is my name?", session=session)  # recalls "Alice"

# Serialize the live session, then restore it into a fresh AgentSession.
serialized = session.to_dict()
resumed = AgentSession.from_dict(serialized)
third = await agent.run("And what did I just ask you?", session=resumed)
```

## The gotcha

`agent.create_session()` is synchronous in Python — no `await`. Threading is entirely manual: if you forget to pass `session=session` into a `run()`, that turn starts cold and the memory chain breaks. A session exposes both a local `session_id` and a `service_session_id` (the remote conversation id), plus a mutable `state` dict shared with context/history providers. Sessions are agent- and service-specific — reusing one across a different agent configuration or provider can produce invalid context.

## Azure / MAF mapping

The agent is a plain `Agent` over `FoundryChatClient` (`project_endpoint` + `model` + `AzureCliCredential`), so history lives client-side in the session. Serialize with `session.to_dict()` and restore with `AgentSession.from_dict(...)` to persist a conversation across process restarts — the next lessons cover where that serialized state actually lives.

## Run it

`uv run tutorial/02-agents/conversations/01_session.py` — needs Foundry creds (run `az login` first). Worked if turn 2 recalls the name and the resumed session recalls the earlier question.

---

Next: [Storage](/blog/posts/maf-py-26-storage.html)
