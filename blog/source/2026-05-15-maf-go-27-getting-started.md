# Getting Started

*How to take the same Foundry agent from earlier lessons and serve it over the AG-UI protocol so a separate client can drive it over HTTP+SSE.*

---

## What this lesson demonstrates

Every prior lesson called the agent **in-process**. This one changes only the *transport*. AG-UI (Agent-User Interaction) is a small HTTP + Server-Sent-Events protocol for driving an agent from a separate process — a browser, a CLI, another service. The lesson is a **client+server pair**: the server wraps a Foundry agent in an AG-UI handler; the client opens an SSE connection and streams the replies back token by token.

The important thing to notice is that the agent itself is **completely unchanged**. It is the ordinary `foundryprovider` assistant — instructions, model, name. Nothing in it knows it will be served over the wire.

## The server: one call adds the protocol

```go
func newHandler(a *agent.Agent) http.Handler {
    mux := http.NewServeMux()
    mux.Handle("/", aguiprovider.NewJSONHTTPHandler(a, aguiprovider.HandlerConfig{}))
    return mux
}
```

`aguiprovider.NewJSONHTTPHandler` returns a plain `http.Handler`. Each incoming POST becomes exactly one agent run, and the run's updates stream back to the caller as AG-UI SSE events. Mount it on a standard `http.ServeMux`, serve it with `http.ListenAndServe(":8888", ...)`, and the agent now speaks AG-UI.

## The client: no credential, just a URL

The client half is even smaller. There is **no Azure credential here** — the model lives on the server. The client builds an SSE client and wraps it with `aguiprovider.NewAgent`:

```go
client := aguiSSEClient.NewClient(aguiSSEClient.Config{Endpoint: endpoint})
return aguiprovider.NewAgent(client, aguiprovider.AgentConfig{})
```

From there the client presents the *same* `*agent.Agent` surface as any local agent: `CreateSession`, then `RunText(ctx, input, agent.WithSession(session), agent.Stream(true))`. That `RunText` returns a Go 1.23+ range-over-function iterator; each update carries the next chunk of text.

## What to notice / the gotcha

`CreateSession` performs **no network I/O** for this provider — it just pins a thread ID. The socket does not open until the first `RunText`. That is why the offline structural tests can construct the whole client and server wiring with a fake credential and never bind a port. On the server side, the handler only accepts POST; a `GET /` short-circuits with `405 Method Not Allowed` before the agent is ever invoked — the test leans on exactly that.

## How it maps to the Microsoft Agent Framework

AG-UI is the framework's front-door protocol. In an Azure AI Foundry deployment, the server binding to Foundry (via `foundryprovider`) can live in your cloud, while browsers or edge clients drive it over AG-UI without ever holding a model credential. The transport is layered on top of the agent, so any agent you have already built can be exposed this way with one handler call.

## Run it

```bash
go run ./tutorial/02-agents/agui/step01_getting_started/server   # terminal 1
go run ./tutorial/02-agents/agui/step01_getting_started/client   # terminal 2
```

Most of the wiring builds and tests offline; the live server run is gated behind `AF_LIVE=1` (needs `az login` + `FOUNDRY_PROJECT_ENDPOINT`).

---

Next: [Backend Tools](/blog/posts/maf-go-28-backend-tools.html)
