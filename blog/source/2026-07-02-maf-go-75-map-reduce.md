# concurrent · Map-Reduce Workflow

*How to express the classic MapReduce word-count as a five-stage workflow graph — fan-out to mappers, barrier to a shuffler, fan-out to reducers, barrier to completion.*

---

## What this lesson demonstrates

This is MapReduce built entirely on the **workflow engine** — no agent, no LLM, just five stages wired with structural edges that coordinate through **shared state** and **file-backed intermediate results**. Messages on the edges stay tiny ("I'm done, here's a path"); the bulk word-count data travels through files under a temp dir. It runs fully offline and deterministically.

## The five-stage graph

Construction is parameterised (`mapperCount`, `reducerCount`) so tests can build smaller graphs; `main` uses `buildWorkflow(3, 4)`:

```go
return workflow.NewBuilder(splitter).
	AddFanOutEdge(splitter, mappers).
	AddFanInBarrierEdge(mappers, shuffler).
	AddFanOutEdge(shuffler, reducers).
	AddFanInBarrierEdge(reducers, completion).
	WithOutputFrom(completion).
	Build()
```

A `FanOutEdge` broadcasts to every target; a `FanInBarrierEdge` holds a target back until *all* its sources have fired — so the shuffler runs exactly once after all three maps, and completion runs once after all four reduces.

## What to notice

- **Selective fan-out.** Every reducer receives every `ShuffleComplete`; a `if msg.ReducerID != id { return nil }` guard makes each reducer process only its own shard. This is the common pattern when a broadcast edge feeds addressed work.
- **Two ways to hold state.** Splitter and reducers are stateless `NewExecutor` closures. The shuffler and completion node accumulate across their barriers, so they use `BindNewExecutorFunc`, which hands each *run* a fresh executor value closing over its own `mapResults` / `paths` slice.
- **State + files, not big messages.** The full word list and each mapper's chunk range go through `ctx.QueueStateUpdate` / `ctx.ReadState` (scoped under a `MapReduceState` key); per-stage results go to files. The workflow's final output is just the slice of reduced-file paths, emitted with `ctx.YieldOutput`.
- **Barrier counting is explicit.** The shuffler and completion executors compare their accumulated count against the `expected` source count before firing — the barrier delivers all sources together, and the executor decides what "all arrived" means.

## How it maps to the Agent Framework Go SDK

This lesson stacks the SDK's `AddFanOutEdge` / `AddFanInBarrierEdge` primitives twice to build a real dataflow topology, and shows the two coordination channels the workflow engine gives you: typed edge messages for control signals and `QueueStateUpdate` / `ReadState` shared state for data. It's the deterministic, model-free counterpart to the concurrent agent workflows — proof the same engine scales from a two-node join to a multi-stage pipeline.

## Run it

```bash
go run  ./tutorial/03-workflows/concurrent/map_reduce
go test ./tutorial/03-workflows/concurrent/map_reduce
```

The offline tests assert both the graph wiring and an end-to-end word count (`a:2, b:1, c:3` on `"a a b c c c"`). `TestMapReduce_Live` is a skipped placeholder gated on `AF_LIVE=1`, kept only for consistency with the model-backed lessons — this workflow has no model call.

---

Next: [01 · Edge Condition (conditional edges)](/blog/posts/maf-go-76-01-edge-condition.html)
