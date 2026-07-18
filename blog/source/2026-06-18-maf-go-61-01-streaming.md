# 01 · Streaming — your first workflow

*This lesson teaches how to build a two-executor pipeline and watch it run as a live stream of typed events.*

---

## What this lesson demonstrates

Everything before this was a single agent you called directly. `03-workflows` opens with a different primitive: a **workflow** is a directed graph of **executors** joined by **edges**, and messages flow along those edges from a start node to an output node.

The lesson keeps the concept pure — no model, no credential, no network — by using two plain `string -> string` functions as executors:

```
"Hello, World!"  →  UppercaseExecutor  →  "HELLO, WORLD!"
                 →  ReverseTextExecutor →  "!DLROW ,OLLEH"   (workflow output)
```

Because there is no model call anywhere, `go run` prints the same output every time, and even the streaming test runs offline.

## The graph, built in one chain

An executor is a function bound to an ID; the builder wires the edge and marks the output node.

```go
uppercase := workflow.NewExecutor("UppercaseExecutor", func(input string) string {
    return strings.ToUpper(input)
}).Bind()

reverse := workflow.NewExecutor("ReverseTextExecutor", func(input string) string {
    runes := []rune(input)
    slices.Reverse(runes)
    return string(runes)
}).Bind()

return workflow.NewBuilder(uppercase).
    AddEdge(uppercase, reverse).
    WithOutputFrom(reverse).
    Build()
```

`NewExecutor(id, fn).Bind()` turns a plain function into a graph node — no interface to implement for the simple case. `NewBuilder(start)` fixes the entry node, `AddEdge(src, dst)` draws a directed edge, and `WithOutputFrom(node)` marks whose result is the workflow's output. `Build()` validates the whole graph and returns a reusable `*workflow.Workflow`.

## What to notice — streaming is event-typed

Running is the interesting part. `inproc.Default.RunStreaming(ctx, wf, "Hello, World!")` kicks off the run and hands back a value whose `WatchStream(ctx)` yields an `iter.Seq2[workflow.Event, error]`. You `switch` on the concrete event type:

- `ExecutorCompletedEvent` — one per executor, carrying its `Result`.
- `OutputEvent` — the designated output node's final value.
- `ErrorEvent` / `ExecutorFailedEvent` — failures.

The gotcha worth internalizing: an executor **completing** is not the same as it being the workflow's **output**. Every node emits a completion event, but only the node named in `WithOutputFrom` emits an `OutputEvent`. Streaming lets you watch each step report live rather than blocking on one final answer.

## How it maps to the Agent Framework Go SDK

This is the `github.com/microsoft/agent-framework-go/workflow` package in miniature. The same `NewBuilder` / `AddEdge` / `WithOutputFrom` / `Build` shape, the same `inproc` in-process runner, and the same typed event stream underpin every richer workflow in this module — the ones that host agents, loop, fan out, or checkpoint. The concepts you just met (nodes, edges, an output node, a streaming event loop) are the vocabulary for all of them. Construction is factored into `buildWorkflow()` so the offline test builds the identical graph and asserts its wiring without running anything.

**Run it:** `go run ./tutorial/03-workflows/01-start-here/01_streaming`. This lesson is fully offline — the conventional `AF_LIVE=1` slot is a skip because there is no live model to call.

---

Next: [02 · Agents in Workflows (a translation pipeline)](/blog/posts/maf-go-62-02-agents-in-workflows.html)
