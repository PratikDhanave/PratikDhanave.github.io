# custom_agent_executors — agents as custom workflow executors with a feedback loop

*How two Foundry agents cooperate inside a cyclic graph workflow where one of them owns the loop control.*

---

## What this lesson demonstrates

This is the first `03-workflows/agents` lesson. Where the earlier agent lessons ran a single agent per program, here two agents cooperate inside a **graph workflow with a cycle**. A `SloganWriter` drafts a slogan; a `FeedbackProvider` critiques it and either accepts it (yields the workflow output) or bounces it back for another draft. The two executors form a loop:

```
SloganWriter → FeedbackProvider → SloganWriter → …
```

The twist is that each agent is wrapped in a **hand-written `workflow.Executor`** — the "custom agent executor" the lesson is named for — so *you* decide how each agent's typed result flows to the next node. The `FeedbackProvider` owns the loop control: it stops when the rating clears a threshold or a maximum number of attempts is hit.

## The graph

Construction is factored out of `main` so the offline test can build the identical graph with a fake credential — no network happens at build time.

```go
return workflow.NewBuilder(sloganWriter).
	AddEdge(sloganWriter, feedbackProvider).
	AddEdge(feedbackProvider, sloganWriter).
	WithOutputFrom(feedbackProvider).
	Build()
```

Two edges form the cycle; `WithOutputFrom` marks the node whose `YieldOutput` becomes the workflow's result.

## What to notice

- **A workflow graph is allowed to contain cycles.** Termination is the *executors'* responsibility, not the graph's. The `FeedbackProvider` either calls `ctx.YieldOutput(...)` (ends the run) or `ctx.SendMessage("", feedback)` (pushes work back to the writer). Its `attempts` counter lives in the executor factory closure, so it persists across the cycle for a single run — that's what caps the revisions.
- **Typed messages route the graph.** `AddHandlerRaw(msgType, outType, …)` registers a handler keyed by the Go type of the incoming message. The `SloganWriter` has *two* handlers — one for the initial `string` prompt, one for a returning `FeedbackResult` — and both emit a `SloganResult`.
- **Structured output is the glue.** Each executor runs its agent with `agent.WithStructuredOutput(&result)`, so the model's answer arrives as a typed Go struct (`SloganResult` / `FeedbackResult`) rather than free text — that's what makes it routable between nodes.
- **Custom events.** `SloganGeneratedEvent` and `FeedbackEvent` implement the SDK's event interface (a `Data() any` method) and are raised with `ctx.AddEvent`, so the run loop can watch each step's structured result live.

## How it maps to the Agent Framework Go SDK

The building blocks come straight from the SDK: `workflow.NewBuilder` / `AddEdge` / `WithOutputFrom` for the graph, `workflow.BindNewExecutorFunc` + `ConfigureProtocol` for a stateful custom executor, and `foundryprovider.NewAgent` to back each node with a real Azure AI Foundry model. This is the pattern that lets you drop LLM agents into a deterministic control-flow graph and keep the orchestration logic in your own hands.

## Run it

```bash
# offline structural test (asserts the wiring — no network)
go test ./tutorial/03-workflows/agents/custom_agent_executors

# live: needs az login + FOUNDRY_PROJECT_ENDPOINT (+ FOUNDRY_MODEL)
go run ./tutorial/03-workflows/agents/custom_agent_executors
```

Most lessons build and test offline; live model calls are gated behind credentials (and elsewhere behind `AF_LIVE=1`).

---

Next: [group_chat_tool_approval · Human-in-the-loop inside a group chat](/blog/posts/maf-go-69-group-chat-tool-approval.html)
