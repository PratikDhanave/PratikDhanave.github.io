# AG-UI Getting Started: The Server

*The client half streams events over SSE; this is the process on the other end of the wire — a Foundry agent wrapped in an HTTP handler that speaks AG-UI.*

---

## What this lesson demonstrates

AG-UI is a small HTTP+SSE protocol for driving an agent from a UI or another process. Instead of calling the agent in-process — the way every earlier lesson did — you wrap it in an HTTP handler and serve it over a socket. A matching AG-UI client then POSTs messages and streams the run's events back.

The load-bearing idea is that *nothing about the agent changes*. It is exactly the Foundry assistant from the earlier lessons — `foundryprovider.NewAgent` with `ModelDeployment(model)` and `Instructions: "You are a helpful assistant."`. Only the transport is new.

## The real code

The whole "make an agent speak AG-UI" step is one call. `newHandler` wraps the agent and mounts it at `/`:

```go
func newHandler(a *agent.Agent) http.Handler {
	mux := http.NewServeMux()
	mux.Handle("/", aguiprovider.NewJSONHTTPHandler(a, aguiprovider.HandlerConfig{}))
	return mux
}
```

`aguiprovider.NewJSONHTTPHandler` turns each incoming POST into one agent run and streams that run's updates back as AG-UI SSE events. The returned `http.Handler` is exactly what an `*http.Server` serves — `main` just hands it to `http.ListenAndServe(addr, handler)` on `:8888`.

## What to notice

- **The agent is factored out of `main`.** `newAGUIAgent(endpoint, model, cred)` builds the Foundry agent independently of the HTTP wiring. That is deliberate: the offline `main_test.go` constructs the identical agent with a fake credential and asserts its wiring — no network, no socket. The live server is gated behind `AF_LIVE`.
- **`HandlerConfig{}` is empty here.** The default configuration is enough for a plain assistant; later lessons (frontend tools, human-in-the-loop, state) add behavior on the agent side, not by changing the handler.
- **`serverURL` is a shared contract.** The server prints `http://localhost:8888` and the matching client dials the same address via `AGUI_SERVER_URL`. This pairing is why the getting-started lesson ships as two programs.

## How it maps to the Microsoft Agent Framework Go SDK

`foundryprovider.NewAgent` gives you an `*agent.Agent` backed by an Azure AI Foundry model; `aguiprovider.NewJSONHTTPHandler` adapts that agent into a standard `http.Handler`. Between them, an in-process agent becomes a network service any AG-UI-aware front end can drive — with the model living entirely server-side.

## Run it

`go run ./tutorial/02-agents/agui/step01_getting_started/server`, then start the matching client in another terminal. Needs `az login` + `FOUNDRY_PROJECT_ENDPOINT` (+ `FOUNDRY_MODEL`). Offline tests run with `go test ./...`; the live bind skips without `AF_LIVE=1`.

---

Next: [AG-UI Backend Tools — The Server](/blog/posts/maf-go-88-backend-tools-server.html)
