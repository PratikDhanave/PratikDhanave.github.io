# AG-UI Frontend Tools: The Server

*The mirror image of backend tools: the server hosts the agent but the tools live on the client, so the handler must forward tool calls instead of running them.*

---

## What this lesson demonstrates

Frontend tools invert where the work happens. The Foundry agent still runs on the server, but the tools it wants to call are implemented on the *client*. When the model requests one, the AG-UI handler streams that request to the connected client over SSE; the client executes it and streams the result back.

For that to work, the server must *not* auto-execute function tools. That is the whole lesson, and it comes down to a single flag.

## The real code

`newHostedAgent` builds the Foundry agent with `DisableFuncAutoCall: true`:

```go
func newHostedAgent(endpoint, model string, cred azcore.TokenCredential) *agent.Agent {
	return foundryprovider.NewAgent(
		endpoint,
		cred,
		foundryprovider.ModelDeployment(model),
		foundryprovider.AgentConfig{
			Instructions: "You are a helpful assistant.",
			Config: agent.Config{
				Name:                "AGUIAssistant",
				DisableFuncAutoCall: true, // client owns the tools, so don't auto-run them here
			},
		},
	)
}
```

Normally a provider attaches middleware that auto-executes function tools locally. `DisableFuncAutoCall: true` turns that middleware off. The model's tool request then flows out through the AG-UI handler to the client instead of being run server-side. `buildHandler` mounts the usual `aguiprovider.NewJSONHTTPHandler` at `/`.

## What to notice

- **The server registers no tools.** Notice `agent.Config` here has no `Tools` field set — the server doesn't own the implementations. It only needs to *not* swallow the calls, which is exactly what `DisableFuncAutoCall` guarantees.
- **The handler is identical to the earlier servers.** As with backend tools, the AG-UI wiring doesn't change; the behavior difference is entirely a property of the agent config. That symmetry is the point: one protocol, and where a tool runs is a config decision.
- **The offline test asserts the flag is set.** `main_test.go` builds the same agent with a fake credential and checks that `DisableFuncAutoCall` is on and the handler is non-nil — no server started, no network call. The live server binds `:8888` only under `AF_LIVE`.

## How it maps to the Microsoft Agent Framework Go SDK

`agent.Config.DisableFuncAutoCall` is the toggle that decides whether the framework runs function tools in-process or surfaces them as unresolved calls. Combined with `aguiprovider.NewJSONHTTPHandler`, an unresolved call becomes an AG-UI event the client fulfills — letting a server-hosted Foundry agent drive tools that only the front end can run (browser APIs, local state, user devices).

## Run it

`go run ./tutorial/02-agents/agui/step03_frontend_tools/server`, then in another terminal `go run ./tutorial/02-agents/agui/step03_frontend_tools/client`. Needs `az login` + `FOUNDRY_PROJECT_ENDPOINT` (+ `FOUNDRY_MODEL`). Offline tests run with `go test ./...`; the live bind skips without `AF_LIVE=1`.

---

Next: [AG-UI Human-in-the-Loop — The Server](/blog/posts/maf-go-90-human-in-loop-server.html)
