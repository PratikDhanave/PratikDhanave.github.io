# 07 · Writer ⇄ Critic Workflow (iterative refinement)

*This lesson teaches how to build a cyclic workflow where a Writer and Critic loop until approval, using `AddSwitch` to route on structured output.*

---

## What this lesson demonstrates

Every workflow so far has been a straight pipeline. This is the first that **loops**. Three agent-backed executors — Writer, Critic, Summary — are wired so the Critic can send work forward or back:

```
start ──▶ Writer ──▶ Critic ─┬─ Approved  ──▶ Summary  (output)
                             └─ !Approved ──▶ Writer   (loop back to revise)
```

The Critic emits a structured `CriticDecision`, an `AddSwitch` routes on its `Approved` flag, and per-run state in the workflow `Context` caps the loop at `maxIterations` so it always terminates.

## The switch is the cycle

```go
b := workflow.NewBuilder(writer).
    AddEdge(writer, critic)

b.AddSwitch(critic).
    AddCase(func(msg any) bool { return msg.(CriticDecision).Approved }, summary).
    AddCase(func(msg any) bool { return !msg.(CriticDecision).Approved }, writer).
    AddToBuilder(b).
    WithOutputFrom(summary)

return b.Build()
```

`AddSwitch(critic)` with two `AddCase` predicates — `Approved` → `summary`, `!Approved` → `writer` — is what turns a linear graph into a feedback loop. The back-edge to `writer` is the whole lesson.

## What to notice — structured output, two input shapes, and a budget

**Structured output drives routing.** The Critic runs its agent with `agent.WithStructuredOutput(&decision)`. Its `CriticDecision` has `Approved bool` and `Feedback string` as JSON fields, but `Content` and `Iteration` carry `json:"-"` so the model never fills them — the executor sets them *after* the model responds, letting the switch route on `Approved` while Writer still receives the content to revise.

**One node, two input shapes.** `Writer` is built with `BindNewExecutorFunc` and registers two raw handlers — `string → *message.Message` (the first draft) and `CriticDecision → *message.Message` (revise-with-feedback). That lets the same executor be both the start node and the loop-back target.

**State bounds the loop.** `readFlowState` / `saveFlowState` use `ctx.ReadOrInitState` + `ctx.QueueStateUpdate`. The Critic increments the iteration count on each non-approval, and once `state.Iteration >= maxIterations` it force-approves:

```go
if !decision.Approved && state.Iteration >= maxIterations {
    decision.Approved = true
    decision.Feedback = ""
}
```

Without that guard, a Critic that keeps finding faults would loop forever — the gotcha every cyclic workflow has to answer.

## How it maps to Azure AI Foundry

This is the reflection / self-critique pattern realized as a graph: one Foundry agent produces, a second evaluates against structured criteria, and the loop continues until quality is met or a budget is spent. `WithStructuredOutput`, conditional `AddSwitch` routing, and workflow `Context` state are the SDK features that make it declarative rather than a hand-rolled `for` loop. The Writer/Critic/Summary executors each call a Foundry-backed agent, so a live run needs `az login` + `FOUNDRY_PROJECT_ENDPOINT` (+ `FOUNDRY_MODEL`).

**Run it:** `go run ./tutorial/03-workflows/01-start-here/07_writer_critic_workflow`. The offline test builds the identical graph with a fake credential and asserts `Build()` succeeds (proving executors, edges, switch cases, and `WithOutputFrom` are consistent), plus unit-tests the switch predicates. The live loop is gated behind `AF_LIVE=1`.

---

Next: [custom_agent_executors — agents as custom workflow executors with a feedback loop](/blog/posts/maf-go-68-custom-agent-executors.html)
