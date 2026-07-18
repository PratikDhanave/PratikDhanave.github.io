# shared-states · Coordinating executors through shared state

*How one executor stores a value in scoped shared state and later executors read it back — instead of copying a whole payload down every edge.*

---

## What this lesson demonstrates

A workflow's executors don't have to pass a whole payload down every edge. Instead, one executor can **store** a value in shared state — a named key inside a scope — and later executors **read** it back. Here a `FileReadExecutor` loads a document into shared state and emits only a small file ID; two counting executors fan out, each reads the document from shared state, computes an independent statistic, and a **barrier fan-in** aggregator waits for both before yielding the total.

## The real code

The graph combines fan-out with a barrier fan-in:

```go
return workflow.NewBuilder(fileRead).
    // Fan out: FileReadExecutor's file ID goes to both counters in parallel.
    AddFanOutEdge(fileRead, []workflow.ExecutorBinding{wordCount, paragraphCount}).
    // Fan in with a barrier: the aggregator runs only once BOTH counters have delivered.
    AddFanInBarrierEdge([]workflow.ExecutorBinding{wordCount, paragraphCount}, aggregate).
    WithOutputFrom(aggregate).
    Build()
```

`FileReadExecutor` stores the document with `ctx.QueueStateUpdate(fileID, fileContentScope, sampleDocument)` and returns only `fileID`; each counter fetches it back with `ctx.ReadState(fileID, fileContentScope)`.

## What to notice

- **Scopes namespace keys.** `fileContentScope = "FileContentState"` keeps this document separate from any other state, so unrelated executors can't collide on a key name.
- **State updates are queued, not immediate.** It's `QueueStateUpdate`, not "set" — the write is applied by the runtime, which is what makes state consistent across the parallel fan-out reads.
- **The barrier is the synchronization point.** `AddFanInBarrierEdge` fires the aggregator *only after both* upstream executors deliver. The aggregator still buffers (`if len(e.collected) != 2 { return nil }`) — the barrier controls *when* it runs, the collected slice controls *what* it does with each arrival.
- **Passing an ID, not the payload, is the design lesson.** Both counters need the full document, but it travels through shared state once instead of being serialized down two edges.
- **The aggregator is bound per session** with `BindNewExecutorFunc`, and declares `YieldsOutputType(string)` so `WithOutputFrom` can surface its result.

## How it maps to the Agent Framework

In the Microsoft Agent Framework Go SDK, scoped shared state (`ctx.QueueStateUpdate` / `ctx.ReadState`) is how executors coordinate without fat message payloads — think a large retrieved document, a shared config, or accumulated context that many nodes need. Combined with `AddFanOutEdge` and `AddFanInBarrierEdge`, it's the map-reduce shape: split work across parallel executors, then join. It runs entirely in-process with no model or credentials, so it's a clean way to learn the state API before agents write to it.

## Run it

```bash
go run ./tutorial/03-workflows/shared-states
```

Fully offline — no model, no network. The test builds the same graph, asserts its structure, and runs it end-to-end.

---

Next: [subworkflows · Nested Order Processing](/blog/posts/maf-go-83-nested-order-processing.html)
