# step10 · Agent as an MCP Tool

*How to publish an agent as a discoverable tool on a Model Context Protocol server so any MCP client can invoke it.*

---

## What this lesson demonstrates

Earlier lessons *called* the agent themselves. This one flips it: the same "Joker" agent is wrapped as a **tool** and served over MCP on stdio. Any MCP client — Claude Desktop, the MCP Inspector, or another agent — can then discover a `Joker` tool, call it with `{"query": "..."}`, and get a joke back. This is the step where one agent stops being a program you run and becomes a reusable capability for the whole ecosystem.

The mechanism is two wrappers applied in order, and getting the order right is the entire lesson.

## The core: two wrappers, in order

```go
func buildServer(a *agent.Agent) *mcp.Server {
    srv := mcp.NewServer(&mcp.Implementation{
        Name:    "agent-mcp-server",
        Version: "1.0.0",
    }, nil)

    mcptool.AddTool(srv, agenttool.New(a, agenttool.Config{}))
    return srv
}
```

`agenttool.New(a, …)` adapts the `*agent.Agent` into a `tool.FuncTool`: the tool's **name and description come straight from the agent**, and its input schema is a single required `query` string. `mcptool.AddTool(srv, …)` then registers that FuncTool on the MCP server, translating each incoming MCP tool call into an agent run and the agent's reply back into an MCP result.

## What to notice

- **The agent's identity is the public contract.** Because the tool name is `a.Name()`, the `Name: "Joker"` and `Description: "An agent that tells jokes."` set in `AgentConfig` are exactly what clients see when they list tools. Rename the agent and the tool renames.
- **Construction is separated from serving.** `newJoker(...)` builds the agent and `buildServer(a)` builds and registers the server, so the offline test can assemble the identical wiring and assert the published tool's shape — name, description, and an `object` input schema with a required `query` — without opening a transport.
- **Only `main` opens the transport.** `srv.Run(context.Background(), &mcp.StdioTransport{})` blocks until the client disconnects and speaks JSON-RPC over stdin/stdout — the part that actually needs a live model behind each call.

## How it maps to the SDK

`agenttool` and `mcptool` are the two SDK adapters that make composition work: `agenttool` turns an agent into a callable tool, and `mcptool` exposes any FuncTool over the standard MCP surface using the `modelcontextprotocol/go-sdk` server. Together they mean a Foundry-backed agent can be dropped into any MCP-aware host with no bespoke glue.

## Run it

```bash
go run ./tutorial/02-agents/agents/step10_as_mcp_tool
# or poke at it:
npx @modelcontextprotocol/inspector go run ./tutorial/02-agents/agents/step10_as_mcp_tool
```

The offline structural test runs anywhere; the running server needs `az login` + `FOUNDRY_PROJECT_ENDPOINT`, and the live path is gated behind `AF_LIVE=1`.

## Key takeaways

- **Two wrappers, applied in order, publish an agent as an MCP tool.** `agenttool.New(a, ...)` adapts the `*agent.Agent` into a `tool.FuncTool`; `mcptool.AddTool(srv, ...)` registers that FuncTool on the MCP server, translating each MCP tool call into an agent run.
- **The agent's identity is the public contract.** The tool name is `a.Name()`, so `Name: "Joker"` and its description are exactly what clients see when they list tools — rename the agent and the tool renames.
- **The published tool's input schema is a single required `query` string**, an `object` schema the offline structural test asserts without opening a transport.
- Only `main` opens the transport — `srv.Run(ctx, &mcp.StdioTransport{})` speaks JSON-RPC over stdin/stdout — which is the part that needs a live model behind each call.

## Further reading

- [mcp · Agent with tools from an MCP Server](/blog/posts/maf-go-32-agent-mcp-server.html) — the reverse direction: borrow tools *from* a remote MCP server.
- [12 · Agent as a Function Tool](/blog/posts/maf-go-22-as-function-tool.html) — the same `agenttool.New` adapter used for in-process delegation.
- [Model Context Protocol](https://modelcontextprotocol.io/) — the open protocol this lesson serves the agent over.

---

Next: [step11 · Using Images (multi-modality)](/blog/posts/maf-go-21-using-images.html)
