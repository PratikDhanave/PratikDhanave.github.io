# 05 · Subworkflows (composing workflows)

*This lesson teaches how to embed a whole built workflow as a single executor inside a larger one — workflows compose.*

---

## What this lesson demonstrates

A workflow is a graph of executors joined by edges. This lesson's move is composition: build a small, reusable **subworkflow** and then drop that *entire workflow* into a larger **parent** workflow as if it were one node.

The subworkflow is three pure string transforms:

```
Uppercase  →  Reverse  →  Append suffix " [PROCESSED]"
```

The parent wraps it between two more executors:

```
Prefix "INPUT: "  →  [ subworkflow ]  →  PostProcess "[FINAL] … [END]"
```

Running the parent on `"hello"` yields `Final output: [FINAL] OLLEH :TUPNI [PROCESSED] [END]`. Like the first streaming lesson, it is pure in-process computation — no model, no credential.

## The bridge: BindSubworkflowAsExecutor

Two ordinary `NewBuilder(...).AddEdge(...).WithOutputFrom(...).Build()` chains build the two workflows. The crux is the one line that turns the first into a node of the second:

```go
prefix := textTransformExecutor("PrefixExecutor", func(input string) string {
    return "INPUT: " + input
})
textProcessingExecutor := inproc.BindSubworkflowAsExecutor(textProcessing, "TextProcessingSubWorkflow")
postProcess := textTransformExecutor("PostProcessExecutor", func(input string) string {
    return "[FINAL] " + input + " [END]"
})

return workflow.NewBuilder(prefix).
    AddEdge(prefix, textProcessingExecutor).
    AddEdge(textProcessingExecutor, postProcess).
    WithOutputFrom(postProcess).
    Build()
```

`inproc.BindSubworkflowAsExecutor(textProcessing, "TextProcessingSubWorkflow")` converts a built `*workflow.Workflow` into an `ExecutorBinding` that carries an ID and slots into `AddEdge` exactly like a leaf executor.

## What to notice — the subworkflow is opaque to the parent

Nothing about the subworkflow is special until it gets embedded — it is an ordinary workflow you could run on its own. Once embedded, its three inner nodes are **invisible** to the parent, which sees one executor whose input is the prefixed string and whose output is whatever the subworkflow yields via its own `WithOutputFrom`. That encapsulation is the payoff: the parent's wiring assertions don't change when you add a stage *inside* the subworkflow, because the parent doesn't care what's in there.

Data flows by output → input: each executor returns a string, and the edge forwards it to the next node's input. Execution is streaming — `WatchStream(ctx)` yields `ExecutorCompletedEvent`, `OutputEvent`, `ErrorEvent`, and `ExecutorFailedEvent`, and the program prints the final `OutputEvent`.

## How it maps to the Agent Framework Go SDK

`inproc.BindSubworkflowAsExecutor` is the SDK's composition primitive: it lets you package a tested workflow and reuse it as a black-box node wherever an executor fits. Because the binding is just another `ExecutorBinding`, the same subworkflow can be embedded twice (with distinct IDs) or mixed with agent-backed executors. The dedicated `subworkflows/nested_order_processing` lesson later in this module scales the idea up to a realistic nested pipeline.

**Run it:** `go run ./tutorial/03-workflows/01-start-here/05_subworkflow`. This lesson makes no model call, so it runs entirely offline — the test both asserts the parent/child wiring and runs the parent end-to-end to confirm the composed output.

---

Next: [06 · Mixed Workflow — Agents and Executors in One Graph](/blog/posts/maf-go-66-06-mixed-workflow-agents-and-executors.html)
