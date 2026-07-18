# 02 · Providers · Azure · OpenAI Responses

*Back the agent with Azure OpenAI's Responses API, and toggle whether conversation state lives on the server or locally.*

---

## What this lesson demonstrates

This lesson swaps the provider onto **Azure OpenAI's Responses API**. The agent contract is identical to the very first `hello_agent` lesson — instructions plus a model, `RunText`, `Collect` — but the constructor is `openaiprovider.NewResponsesAgent` and the client is an `openai.Client` pointed at your Azure OpenAI endpoint with an Azure token credential.

The interesting twist is that it builds the agent **twice** to show one knob: `DisableStoreOutput`. By default the Responses service stores conversation state server-side; set `DisableStoreOutput = true` (the API's `"store": false`) and Agent Framework keeps the chat history locally instead.

## One real excerpt

```go
func newJoker(client openai.Client, model string, disableStore bool, mw agent.Middleware) *agent.Agent {
    return openaiprovider.NewResponsesAgent(
        client,
        openaiprovider.AgentConfig{
            Model:              model,
            Instructions:       "You are good at telling jokes.",
            DisableStoreOutput: disableStore,
            Config: agent.Config{
                Name:        "Joker",
                Middlewares: []agent.Middleware{mw},
            },
        },
    )
}
```

`main` builds one agent with `disableStore=false` (server-side state) and a second with `true` (local history).

## What to notice — the gotcha

**`DisableStoreOutput` decides *who owns the conversation history*.** With the default (`false`), the Responses service persists conversation state on the server, and follow-up turns reference it by ID. Flip it to `true` and Agent Framework manages the history in-process instead — useful when you don't want the service retaining conversation state, or when you're stitching history together yourself. The two agents in the lesson are otherwise identical; only this one boolean differs.

The endpoint comes from `AZURE_OPENAI_ENDPOINT` and the deployment from `AZURE_OPENAI_DEPLOYMENT_NAME` (default `gpt-4o-mini` — remember that on Azure this is the *deployment* name). `newClient` builds the `openai.Client` with `option.WithBaseURL` and `azure.WithTokenCredential(cred)`; the credential is `DefaultAzureCredential`, lazy, so the offline test builds both agent variants with a fake credential and asserts their wiring with no network.

## How it maps to the Agent Framework

The Responses API is Azure OpenAI's stateful conversation surface, and `DisableStoreOutput` is the framework's clean handle on the server-side-vs-local-state tradeoff — a decision that would otherwise mean reaching into raw request parameters. Pairing this with the `openai_chat_completion` lesson gives you the full Azure OpenAI picture: `NewChatCompletionsAgent` for the stateless Chat Completions API, `NewResponsesAgent` for the stateful Responses API, both from the same `openaiprovider`, both exposing the identical `agent.Agent` interface.

## Run it

```bash
AZURE_OPENAI_ENDPOINT=https://<res>.openai.azure.com go run ./tutorial/02-agents/providers/azure/openai_responses
```

Live runs need `AZURE_OPENAI_ENDPOINT` and an Azure login (`az login`). The structural test runs offline with a fake credential and asserts both variants; live calls are gated behind `AF_LIVE=1`.

---

Next: [step01 · Basic Foundry Provider](/blog/posts/maf-go-39-basic.html)
