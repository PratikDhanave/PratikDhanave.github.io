# 02 · Switch Case — multi-way conditional routing

*How a switch builder fans one edge into three mutually-exclusive branches — the workflow analogue of switch/case/default.*

---

## What this lesson demonstrates

Where `01_edge_condition` forked into two branches with a pair of conditional edges, this lesson uses the higher-level **switch builder** to fan out into three mutually-exclusive branches. The detection step now returns a three-way `SpamDecision` — `NotSpam`, `Spam`, or `Uncertain` — and a switch with two cases plus a default routes the message to exactly one downstream executor.

A switch is sugar over conditional edges: it builds one fan-out edge whose *assigner* picks a single target per message, and it guarantees a fallback so nothing is dropped.

## The real code

```go
b := workflow.NewBuilder(detect)
b.AddSwitch(detect).
    AddCase(func(msg any) bool { return msg.(DetectionResult).Decision == NotSpam }, assistant).
    AddCase(func(msg any) bool { return msg.(DetectionResult).Decision == Spam }, spam).
    WithDefault(uncertain).
    AddToBuilder(b).
    AddEdge(assistant, send).             // unconditional: chain send after assistant
    WithOutputFrom(send, spam, uncertain) // every terminal is a workflow output
```

`AddSwitch` opens the switch on `detect`; each `AddCase(pred, target)` is a case; `WithDefault(uncertain)` is the fall-through. `AddToBuilder(b)` commits the switch back onto the builder so you can continue chaining plain edges.

## What to notice

- **The default is not optional in spirit.** With plain conditional edges you can drop a message if no predicate matches. A switch with `WithDefault` guarantees exactly one branch always fires — here, `Uncertain` emails land in the review queue rather than vanishing.
- **`AddToBuilder(b)` is the join back.** The switch is built on a sub-builder; you must commit it with `AddToBuilder` before the outer builder sees those edges. Forgetting it silently leaves the branches unwired.
- **Cases are evaluated in order.** The first matching predicate wins, so order your `AddCase` calls from most specific to least.
- **Classification stays a plain function.** `detectEmail` is a normal `func(string) DetectionResult`, kept outside the executor so both the node and the tests reason about it directly.

## How it maps to the Agent Framework

In the Microsoft Agent Framework Go SDK, `AddSwitch`/`AddCase`/`WithDefault` is the ergonomic way to express deterministic routing in a workflow graph — the kind of dispatch you'd otherwise hand-roll with several `AddDirectEdge` calls and a manually-maintained "else" edge. When you later route between Azure AI Foundry agents ("send billing questions to the finance agent, everything else to the general agent"), this is the construct you reach for. It stays fully offline here because the classifier is a pure function, not a model call.

## Run it

```bash
go run ./tutorial/03-workflows/conditional-edges/02_switch_case
```

Fully offline. The built-in input mentions "invoice", so the detector returns `Uncertain` and the switch's default branch routes it to `HandleUncertainExecutor`.

---

Next: [03 · Multi-Selection Fan-Out (edge assigner)](/blog/posts/maf-go-78-03-multi-selection.html)
