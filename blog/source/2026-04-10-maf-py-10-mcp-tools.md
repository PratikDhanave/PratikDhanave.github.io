# Mcp Tools

*Borrowing tools from an external MCP server instead of writing them yourself.*

---

## What it demonstrates

In the previous lesson a tool was a local Python function. The Model Context Protocol (MCP) lets an agent borrow tools from an **external** server — a filesystem server, a GitHub server, your own — over a standard protocol. You don't write the tool; you connect to a server that provides it. There are three transports for the same idea:

- `MCPStdioTool(name, command, args=[...])` — launch a local server process, talk over stdio
- `MCPStreamableHTTPTool(name, url)` — connect to a running HTTP MCP server
- `MCPWebsocketTool(name, url)` — same, over a websocket

## The code

```python
filesystem = MCPStdioTool(
    name="filesystem",
    command="npx",
    args=["-y", "@modelcontextprotocol/server-filesystem", os.getcwd()],
)
return Agent(
    client=client,
    name="FilesAgent",
    instructions="You can inspect the working directory using your filesystem tools.",
    tools=[filesystem],
)
```

The MCP tool object is a **connection**, so you enter it before use: `async with agent.mcp_tools[0]:` performs the handshake and loads the server's tool catalog, then `await agent.run(...)` can call the remote tools.

## The gotcha

The MCP tool is a connection, not a value — you must `async with mcp:` before the agent can call it, or the remote catalog is never loaded. Passing it in `tools=[...]` merges its remote tools alongside any local `@tool` functions; the agent tracks it in `agent.mcp_tools`. This example's stdio server also needs Node/`npx` on PATH and network access the first time to fetch the package.

## Azure / MAF mapping

The reasoning model behind the agent is `FoundryChatClient` on Azure AI Foundry with `AzureCliCredential`. Construction is offline; only the `async with` block and `run()` touch the network. MCP is provider-agnostic — the same server works no matter which chat client drives the agent.

## Run it

`uv run tutorial/02-agents/02_mcp_tools.py` — needs Foundry creds plus `npx`. It worked if the agent lists the cwd files and summarizes the project.

---

Next: [Context And Memory](/blog/posts/maf-py-11-context-and-memory.html)
