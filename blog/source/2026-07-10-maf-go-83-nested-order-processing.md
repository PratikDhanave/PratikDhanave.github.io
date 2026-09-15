# subworkflows · Nested Order Processing

*How a whole workflow binds as a single executor inside a larger workflow, so pipelines compose two levels deep.*

---

## What this lesson demonstrates

A whole *workflow* can be bound as a single executor inside a larger workflow via `inproc.BindSubworkflowAsExecutor`. This lesson builds an order-processing pipeline out of three reusable subworkflows nested two levels deep:

```
OrderProcessing
  OrderReceived → [Payment] → [Shipping] → OrderCompleted
                     │
    Payment: ValidatePayment → [FraudCheck] → ChargePayment
                                   │
      FraudCheck: AnalyzePatterns → CalculateRiskScore
```

> **▸ [Open the interactive diagram](/blog/diagrams/maf-go-83-nested-order-processing.html)** — pan, zoom, and trace every step (light/dark, self-contained).

Each subworkflow is an ordinary `*workflow.Workflow` built with its own `NewBuilder`/`AddEdge`/`WithOutputFrom`; the parent simply treats it as an executor node.

## The real code

Two whole subworkflows appear in the parent graph as if they were plain nodes:

```go
payment := inproc.BindSubworkflowAsExecutor(paymentWorkflow, "Payment")
shipping := inproc.BindSubworkflowAsExecutor(shippingWorkflow, "Shipping")

return workflow.NewBuilder(orderReceived).
    AddEdge(orderReceived, payment).
    AddEdge(payment, shipping).
    AddEdge(shipping, orderCompleted).
    WithOutputFrom(orderCompleted).
    Build()
```

`Payment` itself nests `FraudCheck` the same way, so the composition is recursive: a subworkflow's builder can bind *its* subworkflow as a node.

## What to notice

- **Nesting does not hide observability.** Deep inside `FraudCheck`, `CalculateRiskScore` raises a `FraudRiskAssessedEvent` via `ctx.AddEvent(...)`. Because a subworkflow's events bubble up, that event appears on the *top-level* run's stream — the driver's `WatchStream` sees it two levels up.
- **One payload crosses every boundary.** The same `OrderInfo` struct flows through all levels, each executor enriching it (payment fills `PaymentTransactionID`, shipping fills `Carrier`/`TrackingNumber`). Subworkflow boundaries don't reshape the message.
- **Scoped state works inside a subworkflow.** `FraudCheck`'s two executors hand `patternsFound` to each other through `ctx.QueueStateUpdate` / `ctx.ReadState` under `fraudStateScope` — the state API from the shared-states lesson, now local to a nested graph.
- **A subworkflow's output feeds the parent edge.** Each subworkflow declares `WithOutputFrom`; that output becomes the message on the parent's outgoing edge.
- **Build order is bottom-up.** The leaf (`FraudCheck`) is built first, nested into `Payment`, which is nested into `OrderProcessing`.

## How it maps to the Agent Framework

In the Microsoft Agent Framework Go SDK, subworkflows are how you keep large graphs modular and testable — a fraud-check pipeline, a payment pipeline, a shipping pipeline, each built and tested on its own, then composed. `inproc.BindSubworkflowAsExecutor` gives you encapsulation (each subworkflow owns its state scope and start node) without giving up cross-level observability (events still surface at the top). It runs fully in-process with no model or credentials, so the composition mechanics are the whole focus.

## Run it

```bash
go run ./tutorial/03-workflows/subworkflows/nested_order_processing
```

Fully offline — no model, no provider. The test builds the identical nested graph, asserts its wiring, runs it end-to-end, and checks the nested `FraudRiskAssessedEvent` surfaces at the top level.

## Key takeaways

- A whole `*workflow.Workflow` binds as a single executor inside a larger workflow via `inproc.BindSubworkflowAsExecutor`, and the composition is recursive — a subworkflow's builder can bind *its* subworkflow as a node.
- Nesting does not hide observability: an event raised deep inside `FraudCheck` (`ctx.AddEvent`) bubbles up to the *top-level* run's `WatchStream`, so encapsulation doesn't cost you cross-level tracing.
- One payload crosses every boundary — the same `OrderInfo` struct flows through all levels, each executor enriching it — and subworkflow boundaries don't reshape the message.
- Scoped shared state works inside a subworkflow (`ctx.QueueStateUpdate` / `ctx.ReadState` under a local scope), and each subworkflow's `WithOutputFrom` output becomes the message on the parent's outgoing edge.
- Build order is bottom-up (leaf first), which is how you keep large graphs modular and independently testable — a fraud-check, payment, and shipping pipeline each built and tested on its own, then composed.

## Further reading

- [shared-states · Coordinating executors through shared state](/blog/posts/maf-go-82-shared-states.html)
- [Subworkflow — Microsoft Agent Framework in Go](/blog/posts/maf-go-65-05-subworkflow.html)
- [microsoft/agent-framework-go on GitHub](https://github.com/microsoft/agent-framework-go)

---

Next: [A2A Client](/blog/posts/maf-go-84-a2a-client.html)
