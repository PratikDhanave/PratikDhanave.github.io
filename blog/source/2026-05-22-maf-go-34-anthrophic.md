# providers · Anthropic (Claude)

*The same agent primitive as the Foundry lessons, backed by the Anthropic (Claude) provider instead of Azure AI Foundry.*

---

## What this lesson demonstrates

This lesson is a **provider swap**: the identical `agent.Agent` you built against Azure AI Foundry, now driven by Anthropic's Claude models through the SDK's `anthropicprovider`. You construct an `anthropic.Client`, hand it to `anthropicprovider.NewAgent` along with a model and instructions, and run it exactly like every other agent — `RunText(...).Collect()`, middleware, and all. Nothing above the provider line changes.

The point the lesson makes is that the agent contract is provider-agnostic. Only the construction differs: a different client, a different `NewAgent`, and a different credential convention.

## One real excerpt

Construction is factored into `newJoker` so the offline test can build the identical agent with a dummy key:

```go
const model = "claude-sonnet-4-5"

func newJoker(client anthropic.Client, model string, mw agent.Middleware) *agent.Agent {
    return anthropicprovider.NewAgent(
        client,
        anthropicprovider.AgentConfig{
            Model:        model,
            Instructions: "You are good at telling jokes.",
            Config: agent.Config{
                Name:        "Joker",
                Middlewares: []agent.Middleware{mw}, // for logging agent interactions
            },
        },
    )
}
```

In `main`, `anthropic.NewClient()` reads the key from the environment, and the agent runs a one-shot prompt.

## What to notice — the gotcha

**Credentials follow the Anthropic SDK's own convention, not Azure's.** `anthropic.NewClient()` reads `ANTHROPIC_API_KEY` from the environment — there is no Azure `TokenCredential` and no Foundry endpoint anywhere in this lesson. The client is lazy: it doesn't contact Anthropic until the agent makes its first request, which is why the structural test can build the whole agent with a throwaway key and assert its wiring (name + provider) without any network call.

The model constant is `claude-sonnet-4-5` — a current, active Anthropic model ID that mirrors the upstream example. Model IDs are provider-specific strings; a Foundry deployment name won't work here, and vice versa.

## How it maps to the Agent Framework

The Microsoft Agent Framework treats "which model answers" as a pluggable provider, so an agent written for Foundry can be re-pointed at Claude by changing three lines: the client, the `NewAgent` call, and the credential source. The `agent.Config` — name, middleware, instructions — is shared verbatim. That portability is the whole design goal: your orchestration, tools, and observability code don't care whether the tokens come from Azure AI Foundry or Anthropic. `a.ProviderName()` reports the provider so downstream code can tell them apart when it needs to.

## Run it

```bash
ANTHROPIC_API_KEY=sk-... go run ./tutorial/02-agents/providers/anthrophic
```

The structural test builds the agent with a dummy key and runs fully offline; the live call needs a real `ANTHROPIC_API_KEY` and is gated behind `AF_LIVE=1`.

## Key takeaways

- **The agent contract is provider-agnostic.** The identical `agent.Agent` you built against Foundry runs on Anthropic's Claude by changing three lines: the client, the `NewAgent` call, and the credential source. `agent.Config` — name, middleware, instructions — is shared verbatim.
- **Credentials follow the Anthropic SDK's own convention.** `anthropic.NewClient()` reads `ANTHROPIC_API_KEY` — no Azure `TokenCredential`, no Foundry endpoint. The client is lazy, so the structural test builds the whole agent with a throwaway key and no network.
- **Model IDs are provider-specific strings.** The constant is `claude-sonnet-4-5`; a Foundry deployment name won't work here and vice versa.
- `a.ProviderName()` reports the provider so downstream code can tell a Claude-backed agent from a Foundry-backed one.

## Further reading

- [providers/azure · Azure AI Project](/blog/posts/maf-go-35-ai-project.html) — the same swap pointed back at a Foundry project endpoint.
- [Azure · OpenAI Chat Completions](/blog/posts/maf-go-37-openai-chat-completion.html) — another provider swap, onto Azure OpenAI.
- [Microsoft Agent Framework Go SDK](https://github.com/microsoft/agent-framework-go) — the provider packages (`anthropicprovider`, `foundryprovider`, `openaiprovider`) this series wires.

---

Next: [providers/azure · Azure AI Project](/blog/posts/maf-go-35-ai-project.html)
