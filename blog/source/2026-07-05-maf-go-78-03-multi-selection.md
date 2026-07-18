# 03 · Multi-Selection Fan-Out (edge assigner)

*How an edge assigner delivers one message to a chosen subset of targets — a multi-way switch that may fall through to more than one case.*

---

## What this lesson demonstrates

A conditional edge is one true/false gate per edge, and a switch picks exactly one branch. This lesson goes further: a single analysis executor fans out to *many* targets, and an **edge assigner** chooses which *subset* each message goes to. Unlike default fan-out — which delivers to every target — the assigner can select several targets at once.

Concretely: a "not spam" email always goes to the assistant branch, and *additionally* to the summary branch when it is long. One message, two destinations.

## The real code

The assigner is a `func(int, any) iter.Seq[int]` that yields the *indexes* of the targets a message should reach:

```go
func routeAnalysis(_ int, msg any) iter.Seq[int] {
    return func(yield func(int) bool) {
        result := msg.(AnalysisResult)
        switch result.Decision {
        case Spam:
            yield(0) // spam
        case NotSpam:
            if !yield(1) { // assistant
                return
            }
            if result.EmailLength > longEmailThreshold {
                yield(2) // summary — assistant AND summary
            }
        case Uncertain:
            yield(3) // uncertain
        }
    }
}
```

It is attached with `AddFanOutEdge(analyze, targets, workflow.WithEdgeAssigner(routeAnalysis))`. The target slice order — `spam, assistant, summary, uncertain` — is what the yielded indexes refer to.

## What to notice

- **Indexes, not conditions.** The assigner yields into the target *slice by position*, so the order you pass to `AddFanOutEdge` is load-bearing. A reordered slice silently reroutes everything.
- **Yielding more than once is the whole point.** `NotSpam` yields `1` and, for long emails, `2` — the multi-selection case. Yield zero indexes and the message is dropped for that edge.
- **It composes with a plain conditional edge.** Alongside the fan-out, a separate `AddDirectEdge(analyze, log, false, ...)` audits short emails straight to the database. Assigners and conditional edges coexist on the same source node.
- **`iter.Seq[int]` respects back-pressure.** The `yield` returns a bool; honoring it (the `if !yield(1) { return }`) is the idiomatic Go 1.23 range-over-func pattern.

## How it maps to the Agent Framework

In the Microsoft Agent Framework Go SDK, `WithEdgeAssigner` is how you express "route this to whichever handlers apply" rather than "route to exactly one". That's the shape of real dispatch: a document might need both translation *and* summarization, or an alert might go to logging *and* an on-call agent. Because the classifier here is a pure function, the lesson stays fully offline — but swapping it for an Azure AI Foundry agent that emits a structured decision needs no change to the routing.

## Run it

```bash
go run ./tutorial/03-workflows/conditional-edges/03_multi_selection
```

Fully offline. The built-in email is long and ordinary, so the assigner routes it to *both* the assistant and summary branches and the workflow yields multiple outputs.

---

Next: [human_in_the_loop_basic · A Workflow That Asks a Human](/blog/posts/maf-go-79-human-in-the-loop-basic.html)
