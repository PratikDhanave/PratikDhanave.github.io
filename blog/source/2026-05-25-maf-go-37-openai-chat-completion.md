# Azure · OpenAI Chat Completions

*The same agent primitive, wired to Azure OpenAI's Chat Completions API where the model name is your deployment name.*

---

## What this lesson demonstrates

This lesson backs the agent with **Azure OpenAI's Chat Completions API**. It uses the OpenAI Go SDK client pointed at an Azure OpenAI resource, wrapped by `openaiprovider.NewChatCompletionsAgent`. Where the `foundry_model` lesson used the generic `NewAgent` (Responses API), this one calls the *chat-completions* constructor explicitly — the same provider, a different endpoint shape underneath. The agent surface — `RunText`, `Collect`, `Stream` — is identical; only the construction and the deployment convention differ.

The lesson also runs the agent twice: once one-shot to completion, once with `agent.Stream(true)` to show incremental updates ranged over as a Go 1.23+ range-over-func iterator.

## One real excerpt

```go
func newJoker(endpoint, model string, cred azcore.TokenCredential) *agent.Agent {
    return openaiprovider.NewChatCompletionsAgent(
        openai.NewClient(
            option.WithBaseURL(endpoint),    // point the OpenAI client at Azure
            azure.WithTokenCredential(cred), // authenticate with an Azure token
        ),
        openaiprovider.AgentConfig{
            Model:        model, // on Azure this is the deployment name
            Instructions: "You are good at telling jokes.",
            Config: agent.Config{
                Name:        "Joker",
                Middlewares: []agent.Middleware{&runLogger{name: "Joker"}},
            },
        },
    )
}
```

## What to notice — the gotcha

**On Azure, the `Model` field is your *deployment name*, not a model ID.** When you deploy a model in the Azure portal you give the deployment a name, and that name — not `gpt-4o-mini` as a catalog identifier — is what you call. The lesson reads `AZURE_OPENAI_DEPLOYMENT_NAME`, falling back to `gpt-4o-mini` as the default deployment name; the endpoint comes from `AZURE_OPENAI_ENDPOINT` (e.g. `https://<resource>.openai.azure.com`).

Note this constructor uses `azure.WithTokenCredential(cred)` with the *default* scope — it does not pass the `ai.azure.com` scope that the `foundry_model` lesson needed. That's the difference between an Azure OpenAI resource and a Foundry model resource. The credential (`DefaultAzureCredential`, i.e. your `az login` session) is lazy, so the offline test builds the agent with a fake credential and asserts the middleware is wired without any network.

## How it maps to the Agent Framework

`openaiprovider` offers two constructors — `NewChatCompletionsAgent` and `NewResponsesAgent` — because Azure OpenAI exposes both the older Chat Completions API and the newer Responses API, and they have different request shapes. Choosing the right constructor is the entire provider decision; the `agent.Config` (name, instructions, middleware) is shared. This lets one codebase target Chat Completions for a legacy deployment and Responses for a newer one, with only the constructor line changing.

## Run it

```bash
go run ./tutorial/02-agents/providers/azure/openai_chat_completion
```

Live runs need `az login` plus `AZURE_OPENAI_ENDPOINT` (and optional `AZURE_OPENAI_DEPLOYMENT_NAME`). The structural test runs offline with a fake credential; live calls are gated behind `AF_LIVE=1`.

---

Next: [02 · Providers · Azure · OpenAI Responses](/blog/posts/maf-go-38-openai-responses.html)
