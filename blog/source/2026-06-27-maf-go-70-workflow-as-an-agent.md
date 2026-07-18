# workflow_as_an_agent · A Workflow, Wrapped as One Agent

*How to collapse a whole multi-agent workflow into a single agent so callers use it exactly like any leaf agent.*

---

## What this lesson demonstrates

Two Foundry agents — **French** and **English** — are wired into a **concurrent** workflow that fans one prompt out to both in parallel. Then `agentworkflow.NewAgent` hosts that whole workflow as a **single agent** (`BilingualWorkflowAgent`). The caller in `main` never touches the graph: it calls `RunText` on one agent and receives the merged bilingual answer. This is the composition payoff — any workflow you can build can be collapsed into an agent, and then dropped inside a *larger* workflow, because it now *is* an agent.

## Wrapping the workflow

Construction is factored into `buildWorkflowAgent(...)` so the offline test can build the identical structure with a fake credential. The concurrent workflow is built first, then hosted:

```go
wf, err := agentworkflow.NewConcurrentWorkflowBuilder(french, english).
	WithName("bilingual-workflow").
	Build()
...
wfAgent, err := agentworkflow.NewAgent(wf, agentworkflow.AgentConfig{
	IncludeOutputsInResponse: true,
	Config:                   agent.Config{Name: "BilingualWorkflowAgent"},
})
```

`NewAgent` returns an ordinary `*agent.Agent`. Everything downstream — `CreateSession`, `RunText`, `agent.Stream(true)` — is the same API you use on a single leaf agent.

## What to notice

- **`IncludeOutputsInResponse: true` is the crux.** Without it, only `ResponseUpdate`s emitted by hosted agents surface; with it, the workflow's terminal `OutputEvent` payload (the merged French + English messages) is surfaced in the wrapping agent's response stream. Leave it off and the combined answer would be silently dropped.
- **Concurrent = fan-out / fan-in.** `NewConcurrentWorkflowBuilder(french, english)` dispatches the same input to both agents in parallel and aggregates their outputs into one batch. Swap in a sequential builder and the *same wrapping code* turns it into a pipeline instead — the caller never notices.
- **Sessions keep the run alive.** The first `RunText` opens a streaming workflow run; passing the same `agent.WithSession(session)` on the next turn reuses it rather than starting fresh:

```go
session, _ := wfAgent.CreateSession(ctx)
for _, input := range prompts {
	for update, err := range wfAgent.RunText(ctx, input, agent.WithSession(session), agent.Stream(true)) {
		demo.Print(update, err)
	}
}
```

## How it maps to the Agent Framework Go SDK

`agentworkflow.NewAgent` is the SDK seam that makes workflows *composable as units*: a graph becomes indistinguishable from a leaf agent, so multi-agent subsystems nest cleanly. This is the same wrapping used later in the observability lessons — here it's the minimal, model-backed introduction to the pattern.

## Run it

```bash
go test ./tutorial/03-workflows/agents/workflow_as_an_agent            # offline
AF_LIVE=1 go test ./tutorial/03-workflows/agents/workflow_as_an_agent  # + live (needs az login)
go run  ./tutorial/03-workflows/agents/workflow_as_an_agent            # needs Foundry
```

The offline test builds the workflow + wrapping agent with a fake credential and confirms the structure constructs and `CreateSession` succeeds with no network; the live model call is gated behind `AF_LIVE=1`.

---

Next: [checkpoint_and_rehydrate](/blog/posts/maf-go-71-checkpoint-and-rehydrate.html)
