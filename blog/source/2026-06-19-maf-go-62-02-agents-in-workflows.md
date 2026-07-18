# 02 · Agents in Workflows (a translation pipeline)

*This lesson teaches how to host real `agent.Agent`s as workflow executors and chain them into a sequential pipeline.*

---

## What this lesson demonstrates

The first workflow lesson wired plain `string -> string` functions. This one hosts **three translation agents** as executors and chains them:

```
"Hello World"  →  French  →  Spanish  →  English  →  (output)
```

Each agent translates the text it receives into its target language and returns *only* the translation, so the French output becomes the Spanish agent's input, and the Spanish output becomes the English agent's input — "Hello World" round-trips back to English. The same `agent.Agent` you called directly in `02-agents` now lives inside a graph; the graph, not your `main`, decides what runs next.

## An agent becomes an executor

`agentworkflow.New(agent, cfg)` wraps an agent as a workflow node, and the strict-pipeline flag is the detail that makes the chain behave.

```go
cfg := agentworkflow.Config{
    DisableForwardIncomingMessages: true,
}
french := agentworkflow.New(newTranslationAgent(endpoint, model, cred, "French"), cfg)
spanish := agentworkflow.New(newTranslationAgent(endpoint, model, cred, "Spanish"), cfg)
english := agentworkflow.New(newTranslationAgent(endpoint, model, cred, "English"), cfg)

return workflow.NewBuilder(french).
    AddEdge(french, spanish).
    AddEdge(spanish, english).
    WithOutputFrom(english).
    Build()
```

The agents are built with `foundryprovider.NewAgent`, each carrying an `Instructions` string like *"Translate the user's text to French. Return only the translation."* and a `Config.Name` matching the language.

## What to notice — the gotcha

`DisableForwardIncomingMessages: true` is the load-bearing setting. By default a hosting executor forwards the *incoming* messages downstream too, so later nodes would see the whole conversation. Disabling it makes each node forward **only its own output**, so Spanish translates the French text — not the original English — and English translates the Spanish. Flip this off and the pipeline stops being a pipeline.

The second detail is how a run advances. `RunStreaming` seeds the start node, then you must send a turn token:

```go
emitEvents := true
run.SendMessage(ctx, workflow.TurnToken{EmitEvents: &emitEvents})
```

A `TurnToken` advances the workflow one turn and, with `EmitEvents` set, asks the hosting executors to surface their streaming updates as workflow events. Only the designated output node (English) yields an `OutputEvent`, whose `Output` you type-assert to `*agent.ResponseUpdate` to print.

## How it maps to Azure AI Foundry

Each executor makes a real Foundry model call, so the program needs `az login` plus `FOUNDRY_PROJECT_ENDPOINT` (and `FOUNDRY_MODEL`). The bridge — `agentworkflow.New` returning a `workflow.ExecutorBinding` — is the SDK's answer to "how do I put an LLM-backed agent inside a deterministic graph?" Nothing about the agent changes; the binding just teaches the runner how to run it as a node.

**Run it:** `go run ./tutorial/03-workflows/01-start-here/02_agents_in_workflows`. The offline test builds the identical graph with a fake credential and asserts its wiring with no network; the live end-to-end run is gated behind `AF_LIVE=1`.

---

Next: [03 · Agent Workflow Patterns (sequential · concurrent · group chat)](/blog/posts/maf-go-63-03-agent-workflow-patterns.html)
