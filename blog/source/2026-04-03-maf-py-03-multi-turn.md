# Multi Turn

*An Agent is stateless — two runs are strangers. What carries history from one turn to the next is an AgentSession.*

---

## What this lesson demonstrates

`agent.run("A")` then `agent.run("B")` are two unrelated calls: the model never sees "A" while answering "B". The lesson proves this with a stateless demo (the second turn has amnesia), then fixes it by threading one `AgentSession` through both runs so turn two can see turn one. The agent stays stateless; the *session* is the memory.

## The code

Create a session once, pass it to every run in the conversation:

```python
session = agent.create_session()          # an in-memory conversation buffer
await agent.run("My name is Pratik and I bank with HDFC.", session=session)
r = await agent.run(
    "Draft a one-line message to my bank's support desk, signed with my name.",
    session=session,
)
print(f"Agent: {r}")
```

Without `session=`, the same two turns produce an agent that has no idea who "me" is or which bank.

## What to notice

- **The Agent holds no history — by design.** That separation is exactly why one agent can serve many users at once: one session per conversation, all sharing the same stateless agent.
- **The session is an in-memory buffer.** `create_session()` returns a fresh conversation; each `run(..., session=session)` appends that turn so the model sees the full prior history.
- **The gotcha:** forgetting `session=` on any turn silently drops it out of history. The probe question here can only be answered by combining name and bank from turn one — a good way to prove your session is actually threaded through.

## How it maps to Azure AI Foundry

The session accumulates the message list that gets sent to the Foundry Responses API on each call. Foundry itself is stateless per request; the SDK's session is what replays prior turns so the model has context. Same `FoundryChatClient` + `AzureCliCredential`.

## Run it

```bash
uv run tutorial/01-get-started/03_multi_turn.py
```

Expected: the stateless run forgets the bank; the stateful run remembers name and bank. Needs Foundry creds and `az login`.

---

Next: [Memory](/blog/posts/maf-py-04-memory.html)
