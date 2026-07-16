# Advanced Workflows — MAF in Go

*Durable workflows in Go: checkpoint and rehydrate, pause on a RequestPort for a human, nest sub-workflows, and coordinate through scoped shared state.*

---

A workflow graph is only useful in production if it can survive a crash, stop to ask a person, and be built from reusable pieces. The Go Agent Framework layers all of that onto the same `workflow.NewBuilder` graph from the last post. What made it click for me: **state lives in the executor, but the durability lives in the runtime** — you opt an executor into checkpointing with two hooks and let the runner do the persisting.

## Checkpointing: snapshot every super-step

Wrap the runner with a checkpoint manager and it snapshots the graph after each super-step:

```go
manager := checkpoint.NewInMemoryManager()
run, _ := inproc.Default.
    WithCheckpointing(manager).
    RunStreaming(ctx, wf, Init)

for evt, err := range run.WatchStream(ctx) {
    if e, ok := evt.(workflow.SuperStepCompletedEvent); ok &&
        e.CompletionInfo != nil && e.CompletionInfo.CheckpointInfo != nil {
        checkpoints = append(checkpoints, *e.CompletionInfo.CheckpointInfo)
    }
}
```

Each executor contributes its own state through two lifecycle hooks attached in its `Extend` block — `OnCheckpointFunc` queues state with `ctx.QueueStateUpdate(key, "", value)`, and `OnCheckpointRestoredFunc` reads it back with `ctx.ReadState(key, "")`:

```go
func (g *guessNumberExecutor) OnCheckpoint(ctx *workflow.Context) error {
    return ctx.QueueStateUpdate(stateKey, "", guessState{g.lowerBound, g.upperBound})
}
```

To resume, you rewind the live run — `run.RestoreCheckpoint(ctx, checkpoints[5])` — and it replays from that snapshot. **Rehydration is even stronger**: throw the running workflow away, call `buildWorkflow()` to construct a *fresh* graph, and `ResumeStreaming(..., savedCheckpoint)` — `Reset` gives a clean slate, then `OnCheckpointRestored` overwrites it. A missing key falls back to the reset value. All of this runs offline: it's a binary-search guessing game, no model, no credential.

## Human-in-the-loop: a RequestPort

To pause for a person you add a `workflow.RequestPort` — a typed door to the outside world. `.Bind()` turns it into a node you wire like any other:

```go
guessPort := workflow.RequestPort{
    ID:       "GuessNumber",
    Request:  reflect.TypeFor[NumberSignal](), // what we ask the human
    Response: reflect.TypeFor[int](),           // what they hand back
}
ask := guessPort.Bind()
wf, _ := workflow.NewBuilder(ask).
    AddEdge(ask, judge).
    AddEdge(judge, ask).       // Judge's Above/Below signal loops back
    WithOutputFrom(judge).
    Build()
```

At runtime the workflow pauses at the port and the stream emits a `RequestInfoEvent`. You answer it and resume — no separate "resume" call, just feed the response back into the same run:

```go
case workflow.RequestInfoEvent:
    guess := askHuman(e.Request)          // your prompt / UI
    resp, _ := e.Request.CreateResponse(guess)
    _ = run.SendResponse(ctx, resp)
case workflow.OutputEvent:
    fmt.Println(e.Output)                 // "42 found in N tries!"
```

The Judge reads its `tries` counter from workflow state with `ctx.ReadOrInitState`, bumps it, and either `YieldOutput`s the win or `SendMessage`s an `Above`/`Below` signal back to the port. Combine both lessons and you get a workflow that pauses for a human *and* checkpoints every super-step — rewind it and the Judge's `tries` count comes back too.

## Sub-workflows and shared state

A compiled `*workflow.Workflow` **is** an executor. `inproc.BindSubworkflowAsExecutor(wf, "Payment")` turns a child workflow into a binding you drop into a parent with `AddEdge` — the parent only sees the child's input and output types, never its internal nodes. Build leaf-first: I nested a FraudCheck workflow inside Payment, then Payment and Shipping inside the top-level order pipeline, two levels deep. Events raised deep inside (`ctx.AddEvent`) still bubble up to the top-level `WatchStream`.

**Scoped shared state** decouples where a value is produced from where it's consumed. `ctx.QueueStateUpdate(key, scope, value)` writes it, `ctx.ReadState(key, scope)` reads it — the scope namespaces keys so unrelated executors don't collide. In the shared-states lesson a file reader stashes a document in state and passes only a small file ID down the graph; a fan-out to two counters reads it back, and a `AddFanInBarrierEdge` aggregator waits for both before yielding. Only the ID rides the edges; the payload never does.

## The mental model

- **`WithCheckpointing(manager)` + `OnCheckpoint`/`OnCheckpointRestored`** — runtime persists, executor supplies its state.
- **`RestoreCheckpoint` vs `ResumeStreaming`** — rewind the live run, or rehydrate a fresh graph.
- **`RequestPort` + `RequestInfoEvent` → `SendResponse`** — pause for a human, resume in the same stream.
- **`BindSubworkflowAsExecutor`** — a workflow is a node; compose leaf-first.
- **`QueueStateUpdate` / `ReadState` with a scope** — thin edges, scoped shared payloads.

Each capability is the same graph with one runtime affordance added. Next I'll host these workflows behind a real service and pull the series together into a capstone app.

---

Next: [Hosting and the Capstone App — MAF in Go](/blog/posts/maf-go-12-hosting-and-capstone.html)
