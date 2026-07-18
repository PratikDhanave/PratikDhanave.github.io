# mcp · Agent with tools from an MCP Server

*How to borrow tools from a remote Model Context Protocol server and hand them to a Foundry agent as ordinary tools.*

---

## What this lesson demonstrates

An agent's tools don't have to be Go functions you wrote. The **Model Context Protocol (MCP)** lets a server publish a catalog of tools that any agent can discover and call over HTTP. Here the lesson connects to Microsoft Learn's public MCP server, lists the tools it exposes, and hands them to a Foundry agent — so the model can search the Microsoft docs without a single search function being implemented locally.

## The one networked step

`connectLearnTools` is the *only* function that touches the network. It opens a streamable-HTTP session and turns each remote tool into an ordinary `tool.Tool`:

```go
session, err := mcptool.Connect(ctx, &mcp.StreamableClientTransport{
    Endpoint: learnServerEndpoint(),
})
if err != nil {
    return nil, nil, fmt.Errorf("connect to MCP server: %w", err)
}
tools, err := mcptool.ListTools(ctx, session)
```

`mcptool.Connect` performs the real HTTP handshake against `https://learn.microsoft.com/api/mcp`, and `ListTools` issues the catalog request. It returns the tools *and* the live `*mcp.ClientSession` so the caller can close it.

## Wiring the borrowed tools into the agent

From the agent's point of view these remote tools are indistinguishable from local function tools — they just go into `agent.Config.Tools`:

```go
foundryprovider.AgentConfig{
    Instructions: "You are a helpful assistant that can help with microsoft documentation questions.",
    Config: agent.Config{
        Name:  "DocsAgent",
        Tools: tools, // borrowed from the Microsoft Learn MCP server
    },
}
```

Note that `newDocsAgent` takes the tools as a **parameter** rather than fetching them. That deliberate separation — networked `connectLearnTools` on one side, pure `newDocsAgent` on the other — is what lets the offline test build the identical agent with fake tools and never open a connection.

## What to notice / the gotcha

Two things. First, **close the session**: `mcptool.Connect` returns a live session that the tools keep calling back into for the life of the run, so `main` does `defer session.Close()` — drop it and the tool calls have nothing to talk to. Second, tools arrive **at runtime, over the wire**, so the catalog depends on what the server advertises that day (e.g. `microsoft_docs_search`, `microsoft_code_sample_search`). The pure helpers `learnServerEndpoint()` and `toolNames()` have no I/O, so they're pinned by direct unit tests.

## How it maps to the Microsoft Agent Framework

MCP is the framework's answer to tool reuse across processes and vendors. Instead of re-implementing "search the docs," you point a Foundry agent at any MCP server — Microsoft Learn here, but equally your own internal tool server — and `mcptool` adapts its catalog into `tool.Tool` values the model can call. The agent runs against Azure AI Foundry; the tools live wherever the MCP server does; the wiring is one `Connect` + `ListTools` + `agent.Config.Tools`.

## Run it

```bash
go run ./tutorial/02-agents/mcp/agent_mcp_server
```

The agent wiring and pure helpers test offline; the live path (real MCP server + real model) needs `az login`, `FOUNDRY_PROJECT_ENDPOINT`, network access, and is gated behind `AF_LIVE=1`.

---

Next: [providers · A2A (Agent2Agent)](/blog/posts/maf-go-33-a2a.html)
