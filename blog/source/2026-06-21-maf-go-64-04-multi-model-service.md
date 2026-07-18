# 04 · Multi-Model Service (a sequential agent workflow)

*This lesson teaches how to chain three role-specialised agents — researcher → fact_checker → reporter — into one sequential workflow and stream each stage.*

---

## What this lesson demonstrates

Where the pattern lesson swapped topologies, this one commits to the sequential shape and gives each agent a distinct job, so the pipeline reads like a small editorial team:

- **researcher** — drafts a concise three-paragraph overview of the topic, deliberately including one claim that ought to be fact-checked.
- **fact_checker** — reviews that essay and flags supported / questionable / false claims.
- **reporter** — writes the final one-paragraph summary using only the claims that survived.

All three share the same Foundry model but carry different `Instructions`. That role separation — same model, different prompt — is the entire idea.

## Building the agents, then the chain

```go
return []*agent.Agent{
    newAgent(
        "researcher",
        "Write a concise three-paragraph overview of the user's topic. Include one claim that should be fact checked.",
    ),
    newAgent(
        "fact_checker",
        "Review the prior essay. Identify supported, questionable, and false claims in concise bullets.",
    ),
    newAgent(
        "reporter",
        "Write a final single-paragraph summary using only claims that survived the fact check.",
    ),
}
```

The wiring is a single builder call:

```go
return agentworkflow.
    NewSequentialWorkflowBuilder(agents...).
    WithName(workflowName).
    Build()
```

`NewSequentialWorkflowBuilder(agents...)` turns the ordered slice into a graph — `agents[0]` (researcher) is the start executor, and it inserts an edge from each agent to the next, with the last agent's response as the workflow's output.

## What to notice — executor IDs are derived, not the name

The builder names each executor `"<agentName>_<agentID>"` (e.g. `researcher_<uuid>`), not just `researcher`. That is why the program prints the full executor ID as a section header (`===== researcher_… =====`) and why the offline test asserts on ID **prefixes** rather than exact matches. If you expect the plain agent name and it isn't there, this is the reason.

Running is the now-familiar two-step: `RunStreaming` seeds the workflow with the topic, then `SendMessage(ctx, workflow.TurnToken{EmitEvents: &true})` advances it and asks it to emit events. Each `OutputEvent` carries one agent update; the program prints a header the first time a new executor speaks, then streams that agent's text.

## How it maps to Azure AI Foundry

This is the canonical "assembly-line of specialists" pattern: several Foundry-backed agents, each an expert at one step, composed so one stage's output feeds the next. Because every stage is a real model call, the program needs `az login` + `FOUNDRY_PROJECT_ENDPOINT` (+ `FOUNDRY_MODEL`). The builder's `WithName` / `WithOutputFrom` / `WithIntermediateOutputFrom` options let you name the workflow and choose which stages surface as output — useful when you want the fact_checker's notes visible alongside the final summary.

**Run it:** `go run ./tutorial/03-workflows/01-start-here/04_multi_model_service`. The offline test builds the identical graph with a fake credential and walks the edges to assert the researcher → fact_checker → reporter chain; the live run is gated behind `AF_LIVE=1`.

---

Next: [05 · Subworkflows (composing workflows)](/blog/posts/maf-go-65-05-subworkflow.html)
