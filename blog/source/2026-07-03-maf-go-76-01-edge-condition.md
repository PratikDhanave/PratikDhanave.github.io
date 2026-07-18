# 01 · Edge Condition (conditional edges)

*How a graph workflow forks: a predicate on each edge decides whether a message may pass, turning the graph into an if/else expressed as data flow.*

---

## What this lesson demonstrates

This is the first `03-workflows` lesson. A **workflow** is a graph of *executors* — plain Go functions wrapped as nodes — joined by *edges*. Most edges are unconditional, but `AddDirectEdge` lets you attach a **condition**: a `func(any) bool` over the message flowing along that edge. When two edges leave the same executor with complementary conditions, the graph **forks**.

The scenario is email triage. A `SpamDetectionExecutor` classifies an incoming email string, then the message is routed either down the "assistant → send" path or to the "handle spam" terminal — depending only on a boolean in the emitted `DetectionResult`.

## The real code

The whole branch lives in the builder. The condition is the fourth argument to `AddDirectEdge`:

```go
return workflow.NewBuilder(detect).
    AddDirectEdge(detect, assistant, false, func(msg any) bool { return !msg.(DetectionResult).IsSpam }).
    AddEdge(assistant, send). // unconditional
    AddDirectEdge(detect, spam, false, func(msg any) bool { return msg.(DetectionResult).IsSpam }).
    WithOutputFrom(send, spam). // either terminal is a workflow output
    Build()
```

Both edges leave `detect`. The predicate on each decides which one the `DetectionResult` is actually delivered on, so exactly one branch runs.

## What to notice

- **Executors are just functions.** `workflow.NewExecutor(id, fn).Bind()` wraps a `func(In) Out` as a node; the framework routes a message to an executor when its input type matches. `DetectionResult` flows to the two branches, `string` flows on to `send`.
- **Conditions live on the edge, not the node.** This keeps the *routing* logic separate from the *work* each executor does. `AddEdge(src, dst)` is the unconditional shorthand.
- **Type-assert inside the predicate.** The condition receives `any`; here it does `msg.(DetectionResult).IsSpam`. The gotcha: the two conditions must be exact negations, or you can drop a message (no edge accepts it) or double-deliver it.
- **`WithOutputFrom(send, spam)`** marks both terminals as outputs; the run surfaces them as `workflow.OutputEvent`s you drain from `run.NewEvents()`.

Construction is factored into `buildWorkflow()` so the offline test builds the identical graph, asserts both edges leaving `detect` carry a condition, and *runs* the workflow on two inputs to prove the conditions route correctly.

## How it maps to the Agent Framework

In the Microsoft Agent Framework Go SDK, `workflow` is the graph-orchestration layer that sits above single agents. Conditional edges are the primitive every higher-level construct — switch cases, multi-selection fan-out, group-chat routing — is built on. Getting comfortable here means the rest of `03-workflows` reads as sugar over this one idea. Nothing calls a model, so this lesson is a clean way to learn the graph API before wiring Azure AI Foundry agents into it.

## Run it

```bash
go run ./tutorial/03-workflows/conditional-edges/01_edge_condition
```

Fully offline — every executor is a pure function, no credential needed. The built-in input contains both "prize" and "wire transfer", so it is flagged as spam and yields `Email marked as spam: matched suspicious wording`.

---

Next: [02 · Switch Case — multi-way conditional routing](/blog/posts/maf-go-77-02-switch-case.html)
