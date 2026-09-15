# AG-UI State Management: The Server

*The final lesson: a recipe agent whose JSON replies are turned into trackable state snapshots by a middleware, so the client can render the recipe as it evolves.*

---

## What this lesson demonstrates

State management is about giving the client something structured to track, not just a stream of text. The server hosts a recipe agent instructed to answer with a JSON recipe object. A *state-snapshot middleware* watches every update flowing back from the model; whenever a reply parses as a JSON object, it emits an extra update — a `DataContent` snapshot — *before* passing the original text through unchanged. The AG-UI client reads that snapshot to track the recipe as evolving state.

This is the capstone of the series and the 91st and last lesson.

## The real code

The middleware yields a base64-encoded JSON snapshot ahead of the original update:

```go
var snapshot any
if json.Unmarshal([]byte(trimmed), &snapshot) == nil {
	encoded := base64.StdEncoding.EncodeToString([]byte(trimmed))
	if !yield(&agent.ResponseUpdate{
		Role:     update.Role,
		Contents: message.Contents{&message.DataContent{MediaType: "application/json", Data: encoded}},
	}, nil) {
		return
	}
}
```

`stateSnapshotMiddleware` returns an `agent.MiddlewareFunc` that ranges over the wrapped `next(ctx, messages, opts...)` iterator. For each `*message.TextContent` that starts with `{` and parses as JSON, it emits the `DataContent` snapshot, then yields the original update. `newRecipeAgent` wires it in via `agent.Config{Middlewares: []agent.Middleware{stateSnapshotMiddleware()}}`, and `newHandler` serves the agent with the usual `aguiprovider.NewJSONHTTPHandler`.

## What to notice

- **State lives in middleware, not the handler.** The AG-UI handler is unchanged from the getting-started server; the entire feature is one `agent.Middleware` that intercepts the update stream. It is pure — a function of `next` with no network — which is why the offline test can drive it with a fake run and assert the snapshot it emits.
- **The snapshot precedes the text.** The middleware yields the `DataContent` first, then the original update. The client gets structured state to render *and* the human-readable reply, in that order.
- **The instructions are the contract.** `recipeInstructions` tells the model to reply with a specific JSON shape (`title`, `ingredients`, `steps`, `skill_level`, …). The middleware keys entirely off that JSON parsing — no shape means no snapshot.

## How it maps to the Microsoft Agent Framework Go SDK

`agent.Middleware` / `agent.MiddlewareFunc` let you wrap an agent's run and rewrite its update stream; `message.DataContent` carries typed, non-text payloads over the wire. Composed with `aguiprovider.NewJSONHTTPHandler`, they let a Foundry agent stream structured application state alongside its prose — the foundation for UIs that render live, evolving objects rather than a chat log.

## Run it

`go run ./tutorial/02-agents/agui/step05_state_management/server`, then connect the matching AG-UI client. Needs `az login` + `FOUNDRY_PROJECT_ENDPOINT` (+ `FOUNDRY_MODEL`). Offline tests run with `go test ./...`; the live bind skips without `AF_LIVE=1`.

That closes out all 91 lessons of the series.

The reason the snapshot is emitted *before* the original text, rather than after, is ordering: the client receives structured state it can render first, then the human-readable prose that accompanies it. Because the middleware only acts when a `*message.TextContent` starts with `{` and parses as JSON, a reply that is plain prose flows through untouched — the feature never corrupts a non-JSON turn. And because the whole thing is an `agent.Middleware` rather than handler code, it composes: you can stack it with other middlewares (logging, guardrails) on the same agent without any of them knowing about the others.

## Key takeaways

- State management means handing the client something *structured* to track, not just a stream of text — here, a recipe object the agent is instructed to emit as JSON.
- A state-snapshot middleware watches every update from the model and, whenever a reply parses as a JSON object, emits a base64-encoded `DataContent` snapshot *before* yielding the original text unchanged.
- The entire feature is one `agent.Middleware`; the AG-UI handler is identical to the getting-started server, which is why the middleware is pure and can be driven by a fake run in an offline test.
- The model instructions are the contract: `recipeInstructions` fixes the JSON shape, and the middleware keys entirely off that parse — no shape means no snapshot.

## Further reading

- [Human-in-the-loop server](/blog/posts/maf-go-90-human-in-loop-server.html) — the preceding AG-UI lesson.
- [Frontend tools server](/blog/posts/maf-go-89-frontend-tools-server.html) — another AG-UI capability in the same series.
- [microsoft/agent-framework-go](https://github.com/microsoft/agent-framework-go) — the `agent.Middleware`, `message.DataContent`, and `aguiprovider` APIs used here.

---

Next: [My upstream Microsoft Agent Framework Go contributions](/agent-framework/)
