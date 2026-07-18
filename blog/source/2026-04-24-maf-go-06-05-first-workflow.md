# 05 · First Workflow

*The other primitive: a directed graph of executors wired by edges, running fully offline with no model, no credential, no Foundry.*

---

## What this lesson demonstrates

The first four lessons were about a single agent calling a model. A **Workflow** is the framework's other primitive: a directed graph of *executors* (processing units) connected by *edges* (data-flow paths). No model is involved at all — each executor is a plain Go function. This is the smallest possible workflow: two executors in a line. For input `"Hello, World!"` the pipeline uppercases to `"HELLO, WORLD!"` then reverses it, producing `"!DLROW ,OLLEH"`.

## The code

Each executor wraps a plain function; the builder wires them and picks the output node:

```go
uppercase := workflow.NewExecutor("UppercaseExecutor", func(input string) string {
    return strings.ToUpper(input)
}).Bind()

reverse := workflow.NewExecutor("ReverseExecutor", func(input string) string {
    runes := []rune(input)
    slices.Reverse(runes)
    return string(runes)
}).Bind()

return workflow.NewBuilder(uppercase).
    AddEdge(uppercase, reverse).
    WithOutputFrom(reverse).
    Build()
```

## What to notice

- **Executors wrap plain functions.** `workflow.NewExecutor(name, func(string) string {…})` turns an ordinary Go func into a graph node; `.Bind()` produces an `ExecutorBinding` the builder can reference in edges.
- **The builder is fluent and validated.** `NewBuilder(uppercase)` sets the start node, `AddEdge(uppercase, reverse)` routes one's output into the other, `WithOutputFrom(reverse)` names the output node, and `Build()` validates the graph before returning a `*Workflow`. Forgetting `WithOutputFrom` is the easy gotcha — the graph runs but yields nothing.
- **Execution is event-driven.** `inproc.Default.Run(ctx, wf, input)` runs the graph in-process on a background goroutine and returns a `*Run`. Each executor that finishes emits an `ExecutorCompletedEvent` (`ExecutorID` + `Result`); ranging `run.NewEvents()` lets you watch data flow through the pipeline.

## How it maps to Azure AI Foundry

Nothing here touches Foundry — and that's the point. Workflows and agents are orthogonal primitives. An executor can call an agent (and later lessons put agents *inside* workflows), but the workflow engine itself is pure orchestration: build a graph, run it, iterate its events. Learning the graph mechanics with plain string functions first means the model calls later drop into a structure you already understand.

## Run it

```bash
go run ./tutorial/01-get-started/05_first_workflow
```

Expected output is the input followed by one line per executor as it completes, ending in `ReverseExecutor: !DLROW ,OLLEH`. This lesson is fully offline: `main_test.go` builds the same graph, runs it, and asserts the final output — no model, no credential, no `AF_LIVE` gate needed.

---

Next: [a2a · Remote Skills as Function Tools](/blog/posts/maf-go-07-as-function-tools.html)
