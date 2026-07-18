# AG-UI Backend Tools: The Server

*Same AG-UI transport as the getting-started server, but now the hosted agent carries a tool the model can call server-side while it answers.*

---

## What this lesson demonstrates

A *backend tool* runs on the server. The agent lives behind the AG-UI HTTP handler; when the model decides to call `search_restaurants`, the framework executes it right there in the server process and feeds the result back into the run. The client never sees the tool — it just streams the conversation, including whatever the tool produced.

The tool itself is an ordinary Go function with typed input and output. `functool` derives the JSON input schema from the request struct, so the model knows exactly what to pass.

## The real code

`searchRestaurants` is the pure handler, and `newSearchTool` wraps it as a framework `tool.Tool`:

```go
func newSearchTool() tool.Tool {
	return functool.MustNew(functool.Config{
		Name:        "search_restaurants",
		Description: "Search for restaurants in a location.",
	}, searchRestaurants)
}
```

`newAgent` then attaches it via `agent.Config{Tools: tools}` on a `foundryprovider.NewAgent`, with instructions `"You are a helpful assistant with access to restaurant information."`. `newHandler` wraps that agent in `aguiprovider.NewJSONHTTPHandler(a, aguiprovider.HandlerConfig{})` — the same handler as the getting-started server. The tool is the only thing that changed.

## What to notice

- **The handler is unchanged from lesson 87.** Adding a backend tool is purely an agent-side concern. `HandlerConfig{}` stays empty; you attach the tool to `agent.Config{Tools: ...}` and the AG-UI layer forwards its effects automatically.
- **The handler auto-executes the tool.** Unlike the frontend-tools lesson coming next, there is no `DisableFuncAutoCall` here — the model's call runs on the server, and only the finished text streams to the client.
- **The pure handler is directly testable.** `searchRestaurants(ctx, in)` has no framework or network dependency, so the offline test calls it straight (asserting the empty/`"any"` cuisine defaults to Italian) and separately asserts the agent + handler wiring with a fake credential — no port bound, no model called.

## How it maps to the Microsoft Agent Framework Go SDK

`functool.MustNew` pairs a name and description with a typed Go handler and builds the input schema; `agent.Config.Tools` registers it on the Foundry agent; `aguiprovider.NewJSONHTTPHandler` serves the whole thing over AG-UI. A server-side capability becomes available to a remote UI without the UI knowing the tool exists.

## Run it

`go run ./tutorial/02-agents/agui/step02_backend_tools/server`, then point the AG-UI client at `http://localhost:8888`. Needs `az login` + `FOUNDRY_PROJECT_ENDPOINT` (+ `FOUNDRY_MODEL`). Offline tests run with `go test ./...`; the live bind skips without `AF_LIVE=1`.

---

Next: [AG-UI Frontend Tools — The Server](/blog/posts/maf-go-89-frontend-tools-server.html)
