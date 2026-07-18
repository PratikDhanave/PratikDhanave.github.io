# 02 · Multi-Turn Conversation

*How an agent.Session carries conversation history across RunText calls so the model remembers earlier turns.*

---

## What this lesson demonstrates

In `01_hello_agent` every call was independent. Here the agent creates a **session** once and passes it to every turn with `agent.WithSession(session)`. The second prompt — *"now add some emojis and tell it in the voice of a pirate's parrot"* — only makes sense because the session remembers the joke from the first turn. Start a *new* session and the conversation begins fresh, which the lesson demonstrates by running a second streamed conversation on `session2` that never sees the first.

A small `turnLogger` middleware prints a `===== Run N =====` banner before each run — a first look at wrapping the agent loop while also threading memory through it.

## The core code

`CreateSession` returns a `*agent.Session`; passing it via `agent.WithSession(...)` on each `RunText` is what threads history forward:

```go
session, err := a.CreateSession(ctx)
// ...
resp, err := a.RunText(ctx, "Tell me a joke about a pirate.",
	agent.WithSession(session)).Collect()
resp, err = a.RunText(ctx,
	"Now add some emojis to the joke and tell it in the voice of a pirate's parrot.",
	agent.WithSession(session)).Collect()
```

## What to notice

- **The session is the memory.** The agent appends every turn to the session and replays the whole history to the model on the next request. Nothing about the *agent* changes between turns — the state lives entirely in the `Session` value you pass.
- **New session = fresh context.** The streamed turns use a *second* session, so they don't see the first conversation. The gotcha: forgetting to pass the same session (or accidentally creating a new one) silently drops memory — the model just won't remember.
- **Construction is separated from `main`.** `newJoker(...)` returns both the agent and its `turnLogger`, so the offline test builds the identical wiring and drives the middleware directly, asserting it counts one run per turn.

## How it maps to Azure AI Foundry

The agent runs against Foundry's Responses API via `foundryprovider.ModelDeployment(model)`. The `Session` abstraction is the SDK's portable notion of conversation state — the same `WithSession` option works across providers, and later lessons show the session being persisted to disk (step06) or a third-party store (step07). Sessions are how the Microsoft Agent Framework keeps multi-turn context without you hand-managing message arrays.

## Run it

```bash
go run ./tutorial/02-agents/agents/step02_multiturn_conversation
```

The program needs Foundry (`az login` + a project endpoint); the offline tests build the agent with a fake credential and drive the middleware with no network. The live turn is gated behind `AF_LIVE=1`.

---

Next: [02 · step03 — Using Function Tools](/blog/posts/maf-go-13-using-function-tools.html)
