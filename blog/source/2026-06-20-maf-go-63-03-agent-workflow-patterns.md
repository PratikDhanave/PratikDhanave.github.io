# 03 · Agent Workflow Patterns (sequential · concurrent · group chat)

*This lesson teaches that orchestration is a property of the workflow, not the agents — the same three agents drop into three different built-in graph shapes.*

---

## What this lesson demonstrates

Take three translation agents — **French**, **Spanish**, **English**, each instructed to answer *only* in its language — and drop the *same* three agents into whichever orchestration graph a `WORKFLOW_PATTERN` env var selects:

| `WORKFLOW_PATTERN` | Builder | Shape |
|---|---|---|
| `sequential` (default) | `NewSequentialWorkflowBuilder` | a chain: each agent sees the previous agent's output |
| `concurrent` | `NewConcurrentWorkflowBuilder` | fan-out/fan-in: all agents run on the same input, results aggregate |
| `groupchat` | `NewGroupChatWorkflowBuilder` + `NewRoundRobinGroupChatManager` | agents take turns under a manager (round-robin, ≤ 5 iterations) |

The agents never change — only the graph the builder produces does. That is the whole point.

## The builders own the graph

```go
switch pattern {
case "sequential":
    return agentworkflow.NewSequentialWorkflowBuilder(agents...).Build()
case "concurrent":
    return agentworkflow.NewConcurrentWorkflowBuilder(agents...).Build()
case "groupchat":
    return agentworkflow.NewGroupChatWorkflowBuilder(func(agents []*agent.Agent) *agentworkflow.GroupChatManager {
        return agentworkflow.NewRoundRobinGroupChatManager(agents, agentworkflow.RoundRobinGroupChatOptions{MaximumIterationCount: 5})
    }, agents...).
        WithName("Translation Round Robin Workflow").
        WithDescription("A workflow where three translation agents take turns responding in a round-robin fashion.").
        Build()
}
```

Each builder returns a `*workflow.Workflow` — a graph of executors and edges — so the difference between the patterns lives entirely in the wiring the builder emits, not in the agents. The group-chat path also shows fluent options: `.WithName(...).WithDescription(...)` ride the builder and land on the workflow, readable back via `wf.Name()` / `wf.Description()`.

## What to notice — running is uniform

Whatever the pattern, the run loop is identical: `inproc.Default.RunStreaming`, then push a `workflow.TurnToken{EmitEvents: &true}` to start the turn, then range over `WatchStream` reacting to `OutputEvent` / `ErrorEvent` / `ExecutorFailedEvent`. The program prints each streamed chunk prefixed with the emitting executor's ID, and the *shape* of the interleaving — one agent after another, or all at once, or turn-taking — is the visible difference between the three patterns.

The gotcha: a group chat is bounded by `MaximumIterationCount`. Without that cap a round-robin of agents that always respond would never stop. Drop it to `1` and you get a single lap; raise it and the agents keep taking turns.

## How it maps to the Agent Framework Go SDK

`agentworkflow` ships these three orchestration builders so you don't hand-wire common topologies. Sequential and concurrent recur throughout `03-workflows` (later lessons like the multi-model service and the concurrent fan-out/fan-in build on them); group chat with a manager is the foundation for human-in-the-loop and tool-approval group chats further on. All three run on the same in-process runner and need `az login` + `FOUNDRY_PROJECT_ENDPOINT` for a live run.

**Run it:** `go run ./tutorial/03-workflows/01-start-here/03_agent_workflow_patterns` (or `WORKFLOW_PATTERN=concurrent` / `groupchat`). The offline test builds every pattern with a fake credential and asserts each graph's wiring; the live model run is gated behind `AF_LIVE=1`.

---

Next: [04 · Multi-Model Service (a sequential agent workflow)](/blog/posts/maf-go-64-04-multi-model-service.html)
