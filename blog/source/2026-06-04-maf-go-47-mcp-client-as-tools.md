# 09 · MCP Client as Tools (Foundry)

*This lesson teaches how a Foundry agent borrows tools from a remote MCP server and calls them as if they were local functions.*

---

## What this lesson demonstrates

An agent's tools don't have to be functions you wrote. The **Model Context Protocol (MCP)** lets a separate server process publish a catalogue of tools, and any MCP *client* can connect, list them, and use them. This lesson connects — over streamable HTTP — to Microsoft Learn's public MCP endpoint (`https://learn.microsoft.com/api/mcp`), pulls its whole tool catalogue, and wires that slice into a Foundry `DocsAgent`. To the model they look like ordinary tools; each call is proxied back over the wire to the remote server.

## The two-phase shape

The lesson deliberately splits the *networked* work from *building the agent*. `connectMCPTools` opens a client session and lists the remote tools; `newDocsAgent` just wires the returned slice into `agent.Config.Tools`.

```go
func connectMCPTools(ctx context.Context, endpoint string) (*mcp.ClientSession, []tool.Tool, error) {
	session, err := mcptool.Connect(ctx, &mcp.StreamableClientTransport{Endpoint: endpoint})
	if err != nil {
		return nil, nil, fmt.Errorf("connect to MCP server %q: %w", endpoint, err)
	}
	tools, err := mcptool.ListTools(ctx, session)
	if err != nil {
		_ = session.Close()
		return nil, nil, fmt.Errorf("list tools from MCP server %q: %w", endpoint, err)
	}
	return session, tools, nil
}
```

## What to notice / the gotcha

- **Remote tools are just `tool.Tool`s.** The MCP wrapper implements the same interface a local function tool does, so `agent.Config.Tools` doesn't care whether a tool came from your code or a remote server.
- **Own the session.** `connectMCPTools` returns the `*mcp.ClientSession`, and `main` `defer`s `session.Close()`. The session must outlive every tool call, since each call proxies through it — close it too early and the agent's tool calls fail.
- **Splitting fetch-from-build is what makes it testable offline.** Because `newDocsAgent` takes the tools as a parameter, the structural test constructs the identical agent with a fake credential and a fake `tool.FuncTool` stand-in — no server, no network.

## How it maps to the Agent Framework

This is the client half of MCP in the Go SDK: `mcptool.Connect` and `mcptool.ListTools` turn a remote server's `tools/list` response into agent-side `tool.Tool` values, and `foundryprovider.NewAgent` runs them against Azure AI Foundry. It is the inverse of "agent as an MCP tool" — here your agent *consumes* someone else's tools rather than exposing its own.

## Run it

```bash
go run ./tutorial/02-agents/providers/foundry/step09_mcp_client_as_tools
```

The live run needs `az login`, `FOUNDRY_PROJECT_ENDPOINT`, and outbound network to the Learn server. The structural test builds and passes offline; the networked path is gated behind `AF_LIVE=1`.

---

Next: [step10 · Images (multimodal input)](/blog/posts/maf-go-48-images.html)
