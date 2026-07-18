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

---

Next: [My upstream Microsoft Agent Framework Go contributions](/agent-framework/)
