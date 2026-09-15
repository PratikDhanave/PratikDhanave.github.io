# step12 · Middleware (guardrail + logger)

*This lesson teaches a middleware chain where a guardrail can block a run before the model is ever called, chained ahead of a logger.*

---

## What this lesson demonstrates

A middleware is any value with a `Run` method (`agent.Middleware`). It wraps every run: it sees the incoming messages before they reach the model and every update on the way back. This lesson chains two. The **guardrail** inspects the messages and, if the request looks harmful, yields its *own* refusal and never calls `next` — the model is never invoked. The **logger** is a transparent pass-through that records the run, then returns `next(...)` unchanged. The guardrail is outermost, so a blocked request stops there — offline, with no network.

## Blocking vs. passing through is one branch

The crux of the whole lesson is a single decision inside the guardrail: yield your own update to short-circuit, or return `next(...)` to pass through.

```go
func (guardrailMiddleware) Run(next agent.RunFunc, ctx context.Context,
	messages []*message.Message, options ...agent.Option) iter.Seq2[*agent.ResponseUpdate, error] {
	for _, msg := range messages {
		if strings.Contains(strings.ToLower(msg.String()), "harmful") {
			return func(yield func(*agent.ResponseUpdate, error) bool) {
				yield(&agent.ResponseUpdate{Role: message.RoleAssistant, Contents: message.Contents{
					&message.TextContent{Text: "I can't help with harmful requests."},
				}}, nil)
			}
		}
	}
	return next(ctx, messages, options...) // safe → pass through
}
```

## What to notice / the gotcha

- **Order is wiring order.** `Middlewares: mws` is applied outermost-first, so `guardrailMiddleware{}` runs before the logger. Reverse them and the logger would fire (and log) even on requests the guardrail is about to block.
- **Two ways to be a middleware.** `guardrailMiddleware` is a struct implementing `agent.Middleware` directly. The stateful `runLogger` uses `agent.MiddlewareFunc` to adapt a method value — handy when the middleware needs to close over state (here, a run counter).
- **Short-circuiting needs no model.** Returning your own iterator instead of calling `next` is what makes the refusal free and offline — the first prompt in `main` never touches Foundry.

## How it maps to the Agent Framework

`agent.Middleware` is the Go SDK's standard extension point for logging, tracing, and guardrails, all threaded through the `iter.Seq2[*agent.ResponseUpdate, error]` streaming type. Because a middleware can emit its own updates, safety policy lives in the same chain as observability — a guardrail is just a middleware that sometimes declines to call the next layer.

## Run it

```bash
go run ./tutorial/02-agents/providers/foundry/step12_middleware
```

The first prompt is refused offline by the guardrail; only the second reaches the model and needs `az login` + `FOUNDRY_PROJECT_ENDPOINT`. The offline test drives each middleware with a fake `next` (proving the guardrail never calls it on a harmful message); the live call is gated behind `AF_LIVE=1`.

## Key takeaways

- A middleware is any value with a `Run` method (`agent.Middleware`); it sees the incoming messages before the model and every update on the way back.
- A guardrail short-circuits by yielding its own `ResponseUpdate` and never calling `next` — so a blocked request never touches the model, running entirely offline.
- Wiring order is outermost-first: putting the guardrail before the logger means blocked requests stop before the logger even fires.
- There are two ways to be a middleware — a struct implementing `agent.Middleware` directly, or `agent.MiddlewareFunc` to adapt a method value when the middleware must close over state (like a run counter).

## Further reading

- [step07 · Observability](/blog/posts/maf-go-46-observability.html) — tracing implemented as the same middleware hook
- [step13 · Plugins (grouping tools)](/blog/posts/maf-go-51-plugins.html) — the next lesson in this Foundry provider track

---

Next: [step13 · Plugins (grouping tools)](/blog/posts/maf-go-51-plugins.html)
