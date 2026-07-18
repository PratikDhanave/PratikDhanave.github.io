# 02 · Multi-turn (sessions)

*How an agent.Session carries conversation history so a second prompt can refer back to the first.*

---

## What this lesson demonstrates

In the basic Foundry lesson, each `RunText` call was independent — the model saw only that one message. This lesson introduces the piece that makes a conversation **multi-turn**: a *session*. You create one with `CreateSession` and thread it through every run with `agent.WithSession`. The session accumulates the history, so the second prompt ("...using the last joke as the anchor") can point back to the first without you resending the transcript.

## Creating and threading a session

The agent itself is the same `Joker` built in `ModelDeployment` mode. The new part is in `main`:

```go
// A session is the piece that makes this "multi-turn".
session, err := a.CreateSession(ctx)
// ...

// (1) First turn — establish the joke the next turn will build on.
resp, err := a.RunText(ctx, "Tell me a joke about a pirate.",
	agent.WithSession(session)).Collect()

// (2) Second turn — same session, so the model can see turn (1).
resp, err = a.RunText(ctx,
	"Now tell a joke about a cat and a dog using the last joke as the anchor.",
	agent.WithSession(session)).Collect()
```

`CreateSession` asks the provider for any per-conversation state it needs and hands back a `*Session`. Passing `agent.WithSession(session)` on both runs is what records turn 1 in history and makes it visible to turn 2.

## What to notice

The session here is **client-side**: the framework holds the accumulated messages in memory and replays them into each run. That is the crucial distinction from the next lesson, where the transcript lives on the Foundry service instead. With a local session, the second `RunText` call effectively resends the growing history — cheap for a couple of turns, but something to be aware of as conversations grow.

`CreateSession` on a Foundry project agent needs **no network** — the provider can hand you a fresh session offline. That is why the structural test can build the agent with a fake credential *and* create a session without any `az login`, then assert on the wiring. Only the actual `RunText` calls talk to the model.

## How it maps to the Agent Framework

`Session` is a cross-provider abstraction in the Go SDK — the same `agent.WithSession` option works whether you're backed by Foundry, OpenAI, or Anthropic. The provider decides how the history is transported; your calling code stays identical. This lesson is the "sessions live in your process" baseline before the server-side variant complicates it.

## Run it

```bash
go run ./tutorial/02-agents/providers/foundry/step02_1_multiturn
```

Tests build offline (including creating a session with a fake credential); the live two-turn conversation is gated behind `AF_LIVE=1` with `az login` and `FOUNDRY_PROJECT_ENDPOINT` set.

---

Next: [02 · Multi-turn with Server Conversations](/blog/posts/maf-go-41-2-multiturn-with-server-conversations.html)
