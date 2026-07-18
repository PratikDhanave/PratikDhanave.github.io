# Azure · Foundry Model

*Reach a Foundry-hosted model through the OpenAI-compatible Responses API by configuring a plain openai.Client with three request options.*

---

## What this lesson demonstrates

A model deployed in Microsoft Foundry exposes an **OpenAI-compatible endpoint**. That means you don't need a Foundry-specific client at all — you reach it with the generic `openaiprovider`, pointing a plain `openai.Client` at the Foundry endpoint. The "it's a Foundry model" detail lives entirely in how the client is configured; everything the agent does afterward is provider-agnostic.

The bridge is three request options: `option.WithBaseURL(endpoint)` says *where* to send requests, `azure.WithTokenCredential(cred, scopes)` says *how* to authenticate, and the scope `https://ai.azure.com/.default` says which Foundry token scope to request.

## One real excerpt

```go
const azureAIResourceScope = "https://ai.azure.com/.default"

func newJoker(endpoint, model string, cred azcore.TokenCredential) *agent.Agent {
    client := openai.NewClient(
        option.WithBaseURL(endpoint),
        azure.WithTokenCredential(
            cred,
            azure.WithTokenCredentialScopes([]string{azureAIResourceScope}),
        ),
    )
    return openaiprovider.NewAgent(client, jokerConfig(model))
}
```

`jokerConfig(model)` assembles the `openaiprovider.AgentConfig` — model, instructions, and a `runLogger` middleware wired into `agent.Config.Middlewares`.

## What to notice — the gotcha

**The token scope is the easy thing to get wrong.** A Foundry model deployment needs `https://ai.azure.com/.default`, which is *not* the plain Azure OpenAI scope (`https://cognitiveservices.azure.com/.default`). That's why the scope is passed explicitly to `azure.WithTokenCredential` instead of relying on the default — a token minted for the wrong scope authenticates fine but gets rejected at the Foundry resource.

Everything Foundry-specific is confined to those three options on the `openai.Client`. The agent built on top (`openaiprovider.NewAgent`) is the same generic provider you'd use against OpenAI directly. The offline test builds this agent with a fake credential and a dummy endpoint and asserts the logging middleware is present — construction touches no network because the credential is lazy.

## How it maps to the Agent Framework

This lesson shows the framework's OpenAI-compatibility strategy in action: because Foundry speaks the OpenAI wire protocol, the SDK reuses `openaiprovider` rather than shipping a bespoke Foundry client for this path. You get the full agent surface — `RunText`, `Collect`, streaming via `agent.Stream(true)`, middleware — for free. The contrast with the `ai_project` lesson is instructive: that one uses `foundryprovider` in project Responses mode; this one uses the generic OpenAI provider against a Foundry model endpoint. Both reach Azure AI Foundry; they differ in which client and endpoint shape they target.

## Run it

```bash
go run ./tutorial/02-agents/providers/azure/foundry_model
```

Live runs need `az login` plus `FOUNDRY_PROJECT_ENDPOINT` (and optional `FOUNDRY_MODEL`). The structural test runs offline with a fake credential; live calls are gated behind `AF_LIVE=1`.

---

Next: [Azure · OpenAI Chat Completions](/blog/posts/maf-go-37-openai-chat-completion.html)
