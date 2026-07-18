# Backend Tools

*How an AG-UI-hosted agent runs a server-side function tool while the thin client just streams the conversation.*

---

## What this lesson demonstrates

This builds on the AG-UI getting-started pair by giving the hosted agent a **backend tool** — a Go function that runs *server-side* whenever the model decides to call it. The lesson is a client+server pair: the server owns a `search_restaurants` tool; the client is a thin SSE front end that never runs the tool at all. When the model calls the tool, it executes on the server and the result folds back into the same streamed reply.

The point is the split of responsibility. The client speaks the AG-UI wire protocol and prints text deltas; the server holds the model *and* the tools.

## The server: a typed tool wired into the agent

The tool's input and output are ordinary structs, and `functool` derives the JSON schema from them so the model knows what to pass:

```go
func newSearchTool() tool.Tool {
    return functool.MustNew(functool.Config{
        Name:        "search_restaurants",
        Description: "Search for restaurants in a location.",
    }, searchRestaurants)
}
```

`searchRestaurants` is a pure Go function — `func(ctx, restaurantSearchRequest) (restaurantSearchResponse, error)` — with no framework or network dependency, so the offline test can call it directly and assert its behaviour (e.g. an empty/`"any"` cuisine defaults to Italian). The tool then goes into the Foundry agent via `agent.Config.Tools`, and the agent goes behind `aguiprovider.NewJSONHTTPHandler`, exactly as in the previous lesson.

## The client: still credential-free

```go
func newAGUIClient(url string) *agent.Agent {
    return aguiprovider.NewAgent(
        aguiSSEClient.NewClient(aguiSSEClient.Config{Endpoint: url}),
        aguiprovider.AgentConfig{},
    )
}
```

No tools, no credential — the client's only configuration is the endpoint URL. It calls `CreateSession` once and reuses that session across turns so the same thread ID (and therefore the server-side history and tool state) stays coherent. Each user turn streams to the server with `agent.Stream(true)`, and the client prints only the text deltas that arrive.

## What to notice / the gotcha

The tool round-trip is invisible to the client. When the model calls `search_restaurants`, the server runs it and continues the same run — the client never sees a tool-call event, only more text. That is deliberate: a backend tool is *server-owned*, so the front end stays dumb. Contrast this with the next lesson, where the tool lives on the client instead.

## How it maps to the Microsoft Agent Framework

This is the natural shape for tools that need server-side resources — a database, an internal API, secrets. The agent runs against Azure AI Foundry, the tool executes in your backend, and clients get the answer without ever touching either. Because the tool is just a `tool.Tool` in `agent.Config.Tools`, nothing about AG-UI changes how you author it — the transport and the tool are orthogonal.

## Run it

```bash
go run ./tutorial/02-agents/agui/step02_backend_tools/server   # terminal 1
go run ./tutorial/02-agents/agui/step02_backend_tools/client   # terminal 2
```

The tool logic and wiring build/test offline; the live run is gated behind `AF_LIVE=1` (server needs `az login` + `FOUNDRY_PROJECT_ENDPOINT`).

---

Next: [Frontend Tools](/blog/posts/maf-go-29-frontend-tools.html)
