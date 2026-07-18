# 03 · Multi-Turn Conversation

*One Session threaded through every call turns two stateless one-shots into a single conversation that remembers.*

---

## What this lesson demonstrates

On its own, every `RunText` call is stateless — the model sees only the message you hand it. A **Session** threads the earlier turns back into the next call, so a follow-up like "now add emojis to *the joke*" actually refers to the joke told a moment ago. The agent builder here is byte-for-byte the one from `01_hello_agent`; the only new ingredient is `agent.WithSession`. Multi-turn is purely additive.

## The code

Create a session once, then pass it to every call:

```go
session, err := a.CreateSession(ctx)
// ...

// Turn 1: set up the joke.
resp, err := a.RunText(ctx, "Tell me a joke about a pirate.", agent.WithSession(session)).Collect()

// Turn 2: "the joke" refers back to turn 1 — only works because the same
// session is threaded through.
resp, err = a.RunText(ctx,
    "Now add some emojis to the joke and tell it in the voice of a pirate's parrot.",
    agent.WithSession(session),
).Collect()
```

## What to notice

- **One session, threaded through both calls.** `a.CreateSession(ctx)` returns a `*agent.Session`, and passing `agent.WithSession(session)` to each `RunText` is the whole mechanism. Drop `WithSession` from turn 2 and the model forgets turn 1 entirely — that's the gotcha worth seeing once on purpose.
- **The session is in-memory state.** For the Foundry provider, `CreateSession` allocates a plain `*Session` with no network round-trip; the agent appends each turn's user and assistant messages to it as history.
- **A Session is JSON-serializable.** Because it's just data, it *can* be persisted and restored — which is exactly what the next lesson builds on.

## How it maps to Azure AI Foundry

With a session, each request to Foundry carries the prior turns as context, not just the latest message. The model resolves references like "the joke" because it literally receives the earlier exchange again. This is client-side conversation history managed by the SDK — the session holds the transcript and replays it on every `POST /responses`, which is why serializing the session is enough to carry a conversation across process boundaries later.

## Run it

```bash
go run ./tutorial/01-get-started/03_multi_turn
```

Expected: a pirate joke, then the *same* joke re-told with emojis in a parrot's voice — proof turn 2 saw turn 1. Offline, `TestNewJoker_Wiring` checks the agent name and `TestCreateSession_Offline` confirms the session round-trips a stored value — no network. The two-turn live conversation is `TestMultiTurn_Live`, gated behind `AF_LIVE=1`.

---

Next: [04 · Memory](/blog/posts/maf-go-05-04-memory.html)
