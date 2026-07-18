# providers/gemini · The Same Agent, Backed by Google Gemini

*How swapping in the Gemini provider changes the constructor and credential — and nothing else about your agent.*

---

## What this lesson demonstrates

This is the "Joker" agent from lesson 01 — same instructions, same `RunText`, same `Collect`, same streaming and middleware — but its model now lives behind the **Google Gemini API** instead of Azure AI Foundry. The whole point is a *provider swap*: the `agent.Agent` surface you program against is identical, and only two things change. The **constructor** becomes `geminiprovider.NewAgent`, and the **credential** becomes a `*genai.Client` holding a Gemini API key rather than an Azure `TokenCredential`.

## The wiring

The Gemini-backed agent is built from a `genai.Client` plus a `geminiprovider.AgentConfig`:

```go
func newJoker(client *genai.Client, model string, mw agent.Middleware) *agent.Agent {
	return geminiprovider.NewAgent(
		client,
		geminiprovider.AgentConfig{
			Model:        model,
			Instructions: "You are good at telling jokes.",
			Config: agent.Config{
				Name:        "Joker",
				Middlewares: []agent.Middleware{mw},
			},
		},
	)
}
```

The client itself is built with `genai.NewClient(ctx, &genai.ClientConfig{APIKey: apiKey, Backend: genai.BackendGeminiAPI})`. The model defaults to `gemini-2.5-flash` (override with `GEMINI_MODEL`), and the API key comes from `GEMINI_API_KEY`.

## What to notice

- **Auth is an API key, not a token.** There is no `az login`. The credential lives *inside* the `genai.Client`, and because `newClient` uses `BackendGeminiAPI` with an explicit `APIKey`, construction does no credential detection and no network call. The client is inert until you actually run the agent — which is exactly why the offline test can build it with a dummy key.
- **Everything downstream is unchanged.** `a.Name()`, `RunText(...).Collect()`, `agent.Stream(true)`, and the `runLogger` middleware are the same `agent.Agent` API you already know. Portability across model hosts is the value the provider abstraction buys you.
- **Construction is separated from `main`.** `newJoker(client, model, mw)` exists so the offline test constructs the *identical* agent and asserts its wiring (`a.Name() == "Joker"`) without a key or a network.

## How it maps to the Microsoft Agent Framework

The Agent Framework Go SDK treats a *provider* as the swappable back end that turns "instructions + a message" into a model call. `foundryprovider`, `openaiprovider`, and `geminiprovider` all return the same `*agent.Agent`. That means your prompt logic, tool wiring, middleware, and streaming code are provider-agnostic: moving a workload from Azure AI Foundry to Gemini is a constructor-and-credential edit, not a rewrite.

## Run it

`GEMINI_API_KEY=... go run ./tutorial/02-agents/providers/gemini` (get a key from Google AI Studio). Most lessons build and test offline; the live model call is gated behind `AF_LIVE=1`, so `go run ./...` and the structural tests stay green with no key.

---

Next: [github-copilot · A Local-CLI Provider](/blog/posts/maf-go-56-github-copilot.html)
