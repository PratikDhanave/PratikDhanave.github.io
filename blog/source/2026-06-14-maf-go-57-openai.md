# 02 · Providers · OpenAI

*The provider is the swappable back end: the same Joker agent, one-shot and streaming, now through the OpenAI API.*

---

## What this lesson demonstrates

Everything in module 01 ran on Azure AI Foundry. But an `agent.Agent` doesn't care *who* runs the model — that is the provider's job. This lesson rebuilds the exact same "Joker" agent, both one-shot and streaming, but through **`openaiprovider`** talking to the OpenAI API. Notice how little changes: the constructor and the credentials, and nothing else.

## The wiring

The agent is built from an `openai.Client` and an `openaiprovider.AgentConfig` that names the model directly:

```go
func newJoker(client openai.Client, model string, mw agent.Middleware) *agent.Agent {
	return openaiprovider.NewAgent(
		client,
		openaiprovider.AgentConfig{
			Model:        model,
			Instructions: "You are good at telling jokes.",
			Config: agent.Config{
				Name:        "Joker",
				Middlewares: []agent.Middleware{mw}, // wraps every run, for logging
			},
		},
	)
}
```

`main` runs the prompt twice — first `RunText(...).Collect()` to get the whole response at once, then the same call with `agent.Stream(true)` to range over incremental updates. The `defaultModel` is `gpt-4o-mini`.

## What to notice

- **A different credential convention.** OpenAI has *no* `azcore.TokenCredential`. Instead, `openai.NewClient()` reads `OPENAI_API_KEY` (and optional `OPENAI_BASE_URL`) from the environment — the OpenAI SDK's own default. `main` fails fast with a clear message if the key isn't set, rather than surfacing an opaque 401 mid-run.
- **`Model` lives in `AgentConfig`.** You name the model directly (`"gpt-4o-mini"`) rather than passing a Foundry `ModelDeployment(...)`.
- **Middleware is provider-agnostic too.** The `runLogger` — a transparent pass-through that counts runs and prints the prompt, then returns `next(...)` untouched — is the same middleware from `step01_running`, reused verbatim.
- **Construction is separated from `main`.** `newJoker(client, model, mw)` lets the offline test build the identical agent with a dummy-keyed client and assert `a.Name() == "Joker"` and `a.ProviderName() == "openai"` — with no network, since `openai.NewClient()` never dials out at construction.

## How it maps to the Microsoft Agent Framework

The provider is the whole portability story of the Agent Framework Go SDK. `openaiprovider.NewAgent(...)` returns the same `*agent.Agent` that `foundryprovider.NewAgent(...)` did — so `RunText`, `.Collect()`, and streaming are unchanged when you move a workload between OpenAI and Azure AI Foundry. Even swapping `NewAgent` for `NewChatCompletionsAgent` (Chat Completions instead of Responses) leaves your call sites and tests untouched.

## Run it

`OPENAI_API_KEY=sk-... go run ./tutorial/02-agents/providers/openai`. The offline test (wiring + middleware) needs no key; `TestOpenAI_Live` makes the real model call and is gated behind `AF_LIVE=1`.

---

Next: [step01 · File-Based Skills](/blog/posts/maf-go-58-file-based-skills.html)
