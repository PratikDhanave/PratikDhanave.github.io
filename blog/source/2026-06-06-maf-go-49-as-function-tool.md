# step11 · An Agent as a Function Tool

*This lesson teaches the simplest form of multi-agent delegation: wrapping one agent as a tool another agent can call.*

---

## What this lesson demonstrates

A tool doesn't have to be a plain function. Here a specialist **WeatherAgent** (which itself owns an ordinary `weather` function tool) is wrapped by `agenttool.New` into a `tool.Tool`, then handed to a second, French-speaking **TravelAgent**. When the travel agent decides it needs the forecast, it *calls the weather agent as a tool* — one model orchestrating another, with no workflow engine involved.

## The seam: an agent adapted into a tool

The whole lesson is one adapter call. `agenttool.New` borrows the agent's `Name` and `Description` for the tool the model sees, and running the tool runs the agent's own `RunText` loop:

```go
func agentToolFor(a *agent.Agent) tool.Tool {
	return agenttool.New(a, agenttool.Config{})
}
```

The travel agent then wires that adapted specialist straight into its `agent.Config.Tools` — the same `[]tool.Tool` slot a plain function tool would occupy.

## What to notice / the gotcha

- **The adapter borrows identity.** The agent-tool's `Name()` and `Description()` come from the wrapped agent, so the orchestrator's model discovers the specialist by the agent's own identity — this is why `WeatherAgent` needs a `Name` **and** a `Description`. Leave the description empty and the model has nothing to route on.
- **Two layers of tools.** The weather agent owns a *plain* function tool (`functool.MustNew` from a `func(ctx, location string) (string, error)`); the travel agent owns an *agent* tool. The framework doesn't care which is which — same slot, same interface.
- **Delegation without a workflow.** Calling the agent-tool runs the specialist's `RunText` loop under the hood. That's the entire multi-agent mechanism: no router, no graph — just a tool call that happens to be another agent.

## How it maps to the Agent Framework

`agenttool.New` is the Go SDK's bridge from `*agent.Agent` to `tool.Tool`. It's the building block beneath the framework's group-chat and orchestration patterns: before you reach for a workflow graph, an agent-as-tool gives you nested delegation with nothing but the tool interface you already know.

## Run it

```bash
go run ./tutorial/02-agents/providers/foundry/step11_as_function_tool
```

The live run needs `az login` and `FOUNDRY_PROJECT_ENDPOINT`. The offline tests build both agents with a fake credential and assert the agent-tool bridge (its `Name`/`Description` equal the weather agent's); the live model call is gated behind `AF_LIVE=1`.

---

Next: [step12 · Middleware (guardrail + logger)](/blog/posts/maf-go-50-middleware.html)
