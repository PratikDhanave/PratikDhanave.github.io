# 06 · Mixed Workflow — Agents *and* Executors in One Graph

*This lesson teaches how deterministic function executors and agent-backed executors compose in one graph with the same `AddEdge` wiring.*

---

## What this lesson demonstrates

Earlier lessons kept the two node kinds apart: pure functions (streaming, subworkflow) or all agents (translation pipeline, multi-model service). This one **mixes** them in a single graph that classifies an input for jailbreak / prompt-injection and then answers it:

```
UserInput → Inverter1 → Inverter2 → StringToChat
          → JailbreakDetector (agent) → JailbreakSync
          → ResponseAgent (agent) → FinalOutput
```

Most nodes are deterministic — `UserInput`, the two inverters (which reverse the text and reverse it back, cancelling out so the agents see the original), `StringToChat`, `JailbreakSync`, `FinalOutput`. Two nodes are agents hosted via `agentworkflow.New`: a **JailbreakDetector** that classifies, and a **ResponseAgent** that answers or refuses. The graph does not care which kind a node is.

## One builder, both node kinds

```go
inverter1 := workflow.NewExecutor("Inverter1", textInverted).Bind()
stringToChat := workflow.NewExecutor("StringToChat", stringToChatMessageExecutor{}).Bind()

hostCfg := agentworkflow.Config{DisableForwardIncomingMessages: true}
detector := agentworkflow.New(
    newFoundryAgent(endpoint, model, cred, "JailbreakDetector", detectorInstructions, mw),
    hostCfg,
)

return workflow.NewBuilder(userInput).
    AddEdge(userInput, inverter1).
    // …
    AddEdge(stringToChat, detector).
    AddEdge(detector, jailbreakSync).
    AddEdge(jailbreakSync, responder).
    AddEdge(responder, finalOutput).
    WithOutputFrom(finalOutput).
    Build()
```

`workflow.NewExecutor(...).Bind()` produces the deterministic nodes; `agentworkflow.New(agent, cfg)` produces the agent nodes; plain `AddEdge` joins them all.

## What to notice — agents need a TurnToken, and message contracts are typed

A hosted agent executor waits for a `workflow.TurnToken` before it takes its turn. That is why the intermediary executors send *two* things — their payload message **and** a turn token:

```go
func (stringToChatMessageExecutor) Handle(ctx *workflow.Context, text string) error {
    if err := ctx.SendMessage("", message.NewText(text)); err != nil {
        return err
    }
    emitEvents := true
    return ctx.SendMessage("", workflow.TurnToken{EmitEvents: &emitEvents})
}
```

The struct executors also carry `workflow.AttrSendsMessage[...]` marker fields (e.g. `AttrSendsMessage[*message.Message]` and `AttrSendsMessage[workflow.TurnToken]`). These declare, at the type level, which message types the executor emits, so the builder can type-check the graph at build time. Forget the token and the downstream agent simply never fires.

`JailbreakSync` sits between the two agents: it parses the detector's `JAILBREAK: DETECTED/SAFE` line, reformats it into a `SAFE:` or `JAILBREAK_DETECTED:` directive that matches the responder's instructions, then forwards it plus a token.

## How it maps to Azure AI Foundry

The two agent nodes call Azure AI Foundry (needs `az login` + `FOUNDRY_PROJECT_ENDPOINT`), while the guard rails around them stay deterministic and cheap. That mix — put your validation, parsing, and formatting in plain Go executors and reserve model calls for the two nodes that need judgment — is a practical shape for real pipelines, and it composes with `DisableForwardIncomingMessages: true` for strict per-node forwarding.

**Run it:** `go run ./tutorial/03-workflows/01-start-here/06_mixed_workflow_agents_and_executors`. The offline test builds the full graph with a fake credential and walks it edge by edge; the classification-parsing helpers are unit-tested directly. The live run is gated behind `AF_LIVE=1`.

---

Next: [07 · Writer ⇄ Critic Workflow (iterative refinement)](/blog/posts/maf-go-67-07-writer-critic-workflow.html)
