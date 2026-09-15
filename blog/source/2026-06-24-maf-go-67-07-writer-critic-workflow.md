# 07 · Writer ⇄ Critic Workflow (iterative refinement)

*This lesson teaches how to build a cyclic workflow where a Writer and Critic loop until approval, using `AddSwitch` to route on structured output.*

---

## What this lesson demonstrates

Every workflow so far has been a straight pipeline. This is the first that **loops**. Three agent-backed executors — Writer, Critic, Summary — are wired so the Critic can send work forward or back:

```
start ──▶ Writer ──▶ Critic ─┬─ Approved  ──▶ Summary  (output)
                             └─ !Approved ──▶ Writer   (loop back to revise)
```

> **▸ [Open the interactive diagram](/blog/diagrams/maf-go-67-07-writer-critic-workflow.html)** — pan, zoom, and trace every step (light/dark, self-contained).

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

## Key takeaways

- `AddSwitch(critic)` with two `AddCase` predicates — `Approved` → summary, `!Approved` → writer — is what turns a linear graph into a feedback loop; the back-edge to the writer is the whole lesson.
- The Critic emits a structured `CriticDecision` (via `agent.WithStructuredOutput`) so the switch routes on the `Approved` flag; `Content`/`Iteration` are `json:"-"` and set by the executor after the model responds.
- One executor can have two input shapes: `Writer` registers `string → *message.Message` (first draft) and `CriticDecision → *message.Message` (revise), letting it be both start node and loop-back target.
- Per-run `Context` state caps the loop: once `Iteration >= maxIterations` the Critic force-approves, so a fault-finding Critic can't loop forever — the answer every cyclic workflow needs.

## Further reading

- [06 · Mixed Workflow — Agents and Executors in One Graph](/blog/posts/maf-go-66-06-mixed-workflow-agents-and-executors.html) — the straight-line graph this one adds a cycle to
- [custom_agent_executors — a feedback loop you control](/blog/posts/maf-go-68-custom-agent-executors.html) — the same reflection pattern with hand-written executors owning the loop

---

Next: [custom_agent_executors — agents as custom workflow executors with a feedback loop](/blog/posts/maf-go-68-custom-agent-executors.html)
