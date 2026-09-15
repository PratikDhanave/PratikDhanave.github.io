# providers/azure · Azure AI Project

*Point the same agent at an Azure AI Foundry project endpoint using the project Responses API mode.*

---

## What this lesson demonstrates

This lesson wires an agent to an **Azure AI Foundry project** — not a bare model deployment, but a Foundry *project endpoint* addressed through the project Responses API. You give `foundryprovider.NewAgent` three things: the project endpoint, a `TokenCredential`, and a `ModelDeployment` target naming the deployed model. The provider derives the project's OpenAI-compatible base URL (`…/openai/v1/`) from the endpoint and talks to it. From there the agent is identical to every other lesson.

The distinguishing detail is the *mode selector*. `foundryprovider.ModelDeployment(model)` tells the provider to treat the endpoint as a project endpoint and use project Responses API mode, rather than a plain chat-completions endpoint.

## One real excerpt

Construction is factored out of `main` so the offline test can build the same agent with a fake credential:

```go
func newJoker(endpoint, model string, cred azcore.TokenCredential, mw agent.Middleware) *agent.Agent {
    return foundryprovider.NewAgent(
        endpoint,
        cred,
        foundryprovider.ModelDeployment(model), // project Responses API mode
        foundryprovider.AgentConfig{
            Instructions: "You are good at telling jokes.",
            Config: agent.Config{
                Name:        "Joker",
                Middlewares: []agent.Middleware{mw},
            },
        },
    )
}
```

## What to notice — the gotcha

**`ModelDeployment(model)` is the mode switch, and it changes how the endpoint is interpreted.** Pass it and the endpoint is treated as a Foundry *project* endpoint, from which the provider builds the OpenAI-compatible base URL itself. Get the target wrong and you'll point a project-mode agent at a non-project URL (or vice versa) and requests will fail in confusing ways. The endpoint, model, and credential all come from the repo's own `internal/demo` helper (`Endpoint()`, `Model()`, `Credential()`), which follows the standard Foundry env-var convention — `FOUNDRY_PROJECT_ENDPOINT` and `FOUNDRY_MODEL`.

The credential is lazy: `demo.Credential()` builds a `TokenCredential` that doesn't call Azure until the first request, so the structural test builds the whole agent with a fake credential and a dummy endpoint and asserts its wiring with no network.

## How it maps to the Agent Framework

This is the canonical "run against my Foundry project" path. In Azure AI Foundry, a *project* is the unit that groups deployed models, connections, and settings; addressing the project endpoint (rather than a raw model URL) is what lets Foundry apply project-level configuration. The provider hides the base-URL derivation and authentication scope entirely — you supply the project endpoint and a deployment name, and the same `RunText`/`Collect` surface works unchanged. The `ModelDeployment` target is the one knob that distinguishes this from the other Azure provider lessons in the series.

## Run it

```bash
go run ./tutorial/02-agents/providers/azure/ai_project
```

Live runs need `az login` plus `FOUNDRY_PROJECT_ENDPOINT` (and `FOUNDRY_MODEL`). The structural test runs offline with a fake credential; live calls are gated behind `AF_LIVE=1`.

## Key takeaways

- **`ModelDeployment(model)` is the mode switch.** Pass it and `foundryprovider.NewAgent` treats the endpoint as a Foundry *project* endpoint, deriving the OpenAI-compatible base URL (`…/openai/v1/`) itself and using project Responses API mode.
- **Get the target right or requests fail confusingly.** Pointing a project-mode agent at a non-project URL (or vice versa) is the classic mistake; endpoint, model, and credential all come from `internal/demo` using the standard `FOUNDRY_PROJECT_ENDPOINT` / `FOUNDRY_MODEL` convention.
- **The credential is lazy**, so the structural test builds the whole agent with a fake credential and a dummy endpoint and asserts its wiring with no network.
- A *project* is the Foundry unit that groups deployed models, connections, and settings; addressing the project endpoint is what lets Foundry apply project-level configuration.

## Further reading

- [Azure · OpenAI Chat Completions](/blog/posts/maf-go-37-openai-chat-completion.html) — the Azure OpenAI resource path, contrasted with the project path here.
- [step01 · Basic Foundry Provider](/blog/posts/maf-go-39-basic.html) — the same three-input wiring with `ServerAgent` mode also explained.
- [providers · Anthropic (Claude)](/blog/posts/maf-go-34-anthrophic.html) — the non-Azure end of the provider-swap spectrum.

---

Next: [Azure · Foundry Model](/blog/posts/maf-go-36-foundry-model.html)
