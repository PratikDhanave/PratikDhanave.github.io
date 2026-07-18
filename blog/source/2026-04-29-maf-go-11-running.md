# step01 · Running an Agent (with middleware)

*How to wrap every agent run with a middleware — the standard hook for logging, tracing, and guardrails.*

---

## What this lesson demonstrates

This is the same Joker agent from `01_hello_agent`, but the run now passes through a **middleware** before it reaches the model. A middleware sees every request on the way in and every update on the way back, which makes it the natural place to attach cross-cutting behaviour — here a run-counting logger — without touching the agent's core logic.

The lesson wires a small `runLogger` into `agent.Config.Middlewares`. On each call it bumps a counter, prints the newest user prompt, and then hands the rest of the chain back untouched.

## The core code

A middleware is really just one function. `agent.MiddlewareFunc` adapts a plain function to the `agent.Middleware` interface, so the whole logger is a closure over a counter:

```go
func (rc *runCounter) run(
	next agent.RunFunc,
	ctx context.Context,
	messages []*message.Message,
	options ...agent.Option,
) iter.Seq2[*agent.ResponseUpdate, error] {
	rc.n++
	fmt.Printf("===== Run %d =====\n", rc.n)
	// Pass through: hand the rest of the chain back untouched.
	return next(ctx, messages, options...)
}
```

The middleware is attached in `newJoker(...)` via `Config{Middlewares: []agent.Middleware{mw}}`, and construction is factored out of `main` so the offline test can build the identical, middleware-wired agent with a fake credential.

## What to notice

- **The signature is the crux.** `next` is the rest of the chain — ultimately the model call. Returning `next(ctx, messages, options...)` unchanged makes this a transparent observer. To *transform* behaviour you wrap the returned iterator, edit `messages` before calling `next`, or short-circuit and yield your own updates.
- **State survives across runs.** The counter field is why the streaming call prints `Run 2` — the same middleware value handles both `RunText` calls. That is a subtle gotcha: if you hold mutable state in a middleware, it is shared across every run of that agent.
- **Wiring lives in `agent.Config`.** The middleware is not a call-site option; it is baked into the agent, so it applies uniformly.

## How it maps to Azure AI Foundry

The agent is built with `foundryprovider.NewAgent(...)` against a Foundry project endpoint using `foundryprovider.ModelDeployment(model)`. The middleware pattern is provider-agnostic — the same `agent.Middleware` interface wraps runs regardless of whether the model lives in Foundry, OpenAI, or elsewhere. This is exactly where you would slot a real OpenTelemetry span, a rate limiter, or a prompt guardrail in production.

## Run it

```bash
go run ./tutorial/02-agents/agents/step01_running
```

Most lessons build and test offline; the live model call is gated behind `AF_LIVE=1` (and needs `az login` plus a Foundry endpoint). Here `TestRunLogger_PassesThrough` exercises the middleware directly, asserting updates come back unchanged and the counter advances 1 → 2 — no network.

---

Next: [02 · Multi-Turn Conversation](/blog/posts/maf-go-12-multiturn-conversation.html)
