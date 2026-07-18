# Frontend Tools

*How the server-hosted agent can call a tool that actually runs on the client, and the one flag that makes it work.*

---

## What this lesson demonstrates

This is the mirror image of the backend-tools lesson. Here the tool lives on the **client**, not the server. The client advertises a tool (`get_user_location`) to the AG-UI server on every run; when the model decides to call it, the server does *not* execute it — it streams the tool call back down to the client, which runs the Go function locally and returns the result. This is how a UI lends the agent a capability only the client has: GPS, the DOM, the logged-in user's session, a local file picker.

The lesson is a client+server pair, and the load-bearing detail is a single server flag.

## The server: don't auto-run the tool

```go
foundryprovider.AgentConfig{
    Instructions: "You are a helpful assistant.",
    Config: agent.Config{
        Name:                "AGUIAssistant",
        DisableFuncAutoCall: true, // client owns the tools, so don't auto-run them here
    },
}
```

Normally the provider attaches middleware that auto-executes function tools server-side. `DisableFuncAutoCall: true` turns that off. Now when the model asks for a tool, the AG-UI handler forwards the request to the client instead of trying to run it. The server itself registers *no* tool — it only hosts the model.

## The client: the tool runs here

```go
func newFrontendTool() tool.Tool {
    return functool.MustNew(functool.Config{
        Name:        "get_user_location",
        Description: "Get the user's current location from GPS.",
    }, func(ctx context.Context, in struct{}) (string, error) {
        return "Amsterdam, Netherlands (52.37°N, 4.90°E)", nil
    })
}
```

The handler is a closure that runs *in this process* — that is the whole point. The tool is registered via `agent.Config.Tools` on the AG-UI-backed agent, so its name, description, and schema are advertised to the server on every run. Ask "Where am I?" and the model calls `get_user_location`, which executes right here on the client.

## What to notice / the gotcha

Both halves must agree. If the server forgets `DisableFuncAutoCall: true`, it will try to run a tool it doesn't own and the call fails; if the client forgets to register the tool, the model never sees it. The tool round-trip itself is handled transparently by the provider middleware — the client's streaming loop is identical to earlier lessons; the local execution happens under the hood.

## How it maps to the Microsoft Agent Framework

Frontend tools are how the framework keeps client-only context out of the server. The model, hosted against Azure AI Foundry, can reason about "where the user is" without the server ever knowing the user's coordinates — the client answers that call and returns only what it chooses to. It is the same `functool` + `agent.Config.Tools` authoring you already know; only *which side* holds the handler, plus the server's opt-out flag, differs.

## Run it

```bash
go run ./tutorial/02-agents/agui/step03_frontend_tools/server   # terminal 1
go run ./tutorial/02-agents/agui/step03_frontend_tools/client   # terminal 2
```

The tool and agent wiring build/test offline against a dummy endpoint; the live run is gated behind `AF_LIVE=1`.

---

Next: [Human In Loop](/blog/posts/maf-go-30-human-in-loop.html)
