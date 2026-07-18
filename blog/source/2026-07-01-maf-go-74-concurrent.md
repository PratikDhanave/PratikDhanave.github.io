# concurrent · Fan-out / Fan-in Workflow

*How to broadcast one input to several executors in parallel and join their answers with a barrier — the core workflow graph primitives, with no LLM in the way.*

---

## What this lesson demonstrates

This lesson teaches the **graph primitives** deliberately without an agent. A *start* executor broadcasts a question; a **fan-out edge** hands it to two domain experts (a physicist and a chemist) that run concurrently; a **fan-in barrier edge** waits for *both* to answer, then delivers their outputs together to an *aggregation* executor that joins them into the workflow's result.

Because every executor is a plain `string → string` Go function, the whole thing runs in-process — no model, no credential, no network — so you can run it (and its test) with nothing configured.

## The graph

Construction is factored into `buildWorkflow()`, and the topology is expressed in four builder calls:

```go
return workflow.NewBuilder(start).
	AddFanOutEdge(start, []workflow.ExecutorBinding{physics, chemistry}).
	AddFanInBarrierEdge([]workflow.ExecutorBinding{physics, chemistry}, aggregate).
	WithOutputFrom(aggregate).
	Build()
```

The start executor broadcasts with `ctx.SendMessage("", question)` — the empty target ID means "send onto all my outgoing edges", which the fan-out edge picks up.

## What to notice

- **The barrier is what makes it a join, not a race.** `AddFanInBarrierEdge` holds delivery until *every* source executor has produced a message, so the aggregator always sees both answers. Drop the barrier and you'd get whichever finished first.
- **Stateful executor ⇒ `BindNewExecutorFunc`.** The aggregator accumulates messages in a slice, so it's created per-run via `BindNewExecutorFunc` (a fresh instance each run) rather than shared. `OnMessageDeliveryFinishedFunc` is where it joins the collected strings and calls `ctx.YieldOutput(...)` once the turn's delivery is done.
- **Protocol declarations via `Extend` + `ConfigureProtocol`.** The start executor declares it `SendsMessageType(string)` and the aggregator declares it `YieldsOutputType(string)`; the builder type-checks the graph before it runs.
- **Three graph pieces.** `workflow.NewExecutor(id, fn)` wraps a function as a node; the fan-out / fan-in edges wire the topology; `WithOutputFrom(aggregate)` names which executor's `YieldOutput` is the workflow's result.

## How it maps to the Agent Framework Go SDK

`AddFanOutEdge` and `AddFanInBarrierEdge` are the SDK's structural concurrency edges — the same primitives that back `NewConcurrentWorkflowBuilder` (the bilingual "workflow as an agent" lesson used exactly this fan-out/fan-in shape under the hood). Learning them at the raw level here is what lets you later mix agents and plain executors in one graph and reason about when a node actually fires.

## Run it

```bash
go run  ./tutorial/03-workflows/concurrent/concurrent
go test ./tutorial/03-workflows/concurrent/concurrent
```

Both lines of output may appear in either order — the experts run concurrently; the barrier only guarantees both are present before the aggregator fires. There's no live model path here; the offline test actually runs the workflow and asserts both experts' answers reach the aggregated output.

---

Next: [concurrent · Map-Reduce Workflow](/blog/posts/maf-go-75-map-reduce.html)
