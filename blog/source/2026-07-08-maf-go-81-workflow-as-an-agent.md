# observability · Workflow as an Agent

*How WithTelemetry instruments a whole workflow with OpenTelemetry spans, then agentworkflow.NewAgent wraps the graph so it behaves like one agent.*

---

## What this lesson demonstrates

Two hosted agents — "French" then "English" — are chained by a workflow graph (`French → English`). **Telemetry is switched on at build time** via `WithTelemetry`, so every executor invocation and edge traversal opens an OpenTelemetry span. The finished workflow is then wrapped by `agentworkflow.NewAgent`, which turns the whole graph into *one* `*agent.Agent`: you call `RunText` on it exactly like a plain agent, and the two-stage pipeline runs underneath.

## The real code

Telemetry is a builder step, right alongside the edges and outputs:

```go
wf, err = workflow.NewBuilder(frenchBinding).
    AddEdge(frenchBinding, englishBinding).
    WithOutputFrom(englishBinding).
    WithTelemetry(
        workflowotel.New(workflowotel.Config{SourceName: sourceName}),
        workflow.TelemetryOptions{EnableSensitiveData: true},
    ).
    Build()
```

Then the whole workflow becomes one agent:

```go
return agentworkflow.NewAgent(wf, agentworkflow.AgentConfig{IncludeOutputsInResponse: true})
```

Callers run it with a plain `wfAgent.RunText(ctx, "...", agent.WithSession(session), agent.Stream(true))` — the French→English pipeline executes invisibly.

## What to notice

- **`SourceName` is the instrumentation scope.** `"Workflow.Sample.WorkflowAsAgent"` is the name a trace backend groups these spans under — the equivalent of a tracer name.
- **`EnableSensitiveData: true` is a deliberate choice.** It lets prompt/response content ride along in spans. Useful in a demo, but a real deployment weighs that against not logging user data.
- **`agentworkflow.New` vs. `agentworkflow.NewAgent`.** The first binds a single agent *as a workflow executor* (a node); the second wraps a *whole workflow* as one agent. This lesson uses both — two nodes built with `New`, the graph wrapped with `NewAgent`.
- **`IncludeOutputsInResponse` surfaces the final output.** Without it, the wrapped agent runs the pipeline but the terminal English output wouldn't appear in the response stream.
- **Port note:** the OpenTelemetry stdout exporter isn't in this repo's module graph, so the lesson keeps the *concept* — `workflowotel.New` + `WithTelemetry` — but relies on the global no-op tracer instead of exporting spans, and uses a tiny local logging middleware so each turn is still visible.

## How it maps to the Agent Framework

In the Microsoft Agent Framework Go SDK, `workflow/observability/opentelemetry` is the standard way to get distributed traces across a multi-agent graph — spans nest so you can see the French turn, the English turn, and the edge between them in a backend like Azure Monitor. Wrapping a workflow as an agent is the composition trick that lets a whole pipeline plug into anything expecting an `agent.Agent`. Running it live needs `az login`, `FOUNDRY_PROJECT_ENDPOINT`, and `FOUNDRY_MODEL` because both stages call the Azure AI Foundry model.

## Run it

```bash
go run ./tutorial/03-workflows/observability/workflow_as_an_agent
```

Runs live (both agents call Foundry); the offline test builds the same graph with a fake credential and asserts the French→English wiring with no network.

---

Next: [shared-states · Coordinating executors through shared state](/blog/posts/maf-go-82-shared-states.html)
