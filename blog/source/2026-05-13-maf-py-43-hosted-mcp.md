# Hosted Mcp

*Point an agent at a remote MCP server and let Foundry do the calling — you describe the server once, the service discovers and invokes its tools for you.*

---

## What this lesson demonstrates

A hosted MCP tool aims the agent at a remote Model Context Protocol server — here the Microsoft Learn docs server — and lets the *Foundry service* connect and call it. Your process never opens a socket to the MCP server. You describe the server once with `client.get_mcp_tool(name=..., url=...)`, hand it to the agent, and Foundry discovers, invokes, and streams that server's tools back through the run.

## The code

The tool describes a remote server; nothing connects until `agent.run()`:

```python
learn_mcp = client.get_mcp_tool(
    name="Microsoft Learn MCP",
    url="https://learn.microsoft.com/api/mcp",
    approval_mode="never_require",
)
return Agent(
    client=client,
    name="MicrosoftLearnAgent",
    instructions="You answer questions by searching Microsoft Learn content only.",
    tools=[learn_mcp],
)
```

## What to notice

- **Build it from the client, not a bare class.** `client.get_mcp_tool(name=, url=)` — the `FoundryChatClient` owns the connection, so the MCP call runs server-side.
- **`approval_mode` gates execution.** `"never_require"` auto-runs, which is fine for read-only docs search. `"always_require"` pauses and surfaces `result.user_input_requests` so a human can approve — the same approval flow as guarded `@tool` functions.
- **Auth travels in headers.** Pass secrets via `headers={"Authorization": "Bearer ..."}` for servers that need it; omit entirely for open servers like Microsoft Learn.
- **You can attach several.** `tools=[learn, github]`, each with its own `approval_mode` and `headers`.

## The gotcha

The agent is used as an async context manager — `async with build_agent() as agent:` — and `approval_mode` choice matters. `"never_require"` is only safe for read-only servers; swap to `"always_require"` for any write-capable server (GitHub, payments) so a human gates side effects before Foundry executes them.

## How it maps to MAF and Foundry

Earlier lessons ran a *local* MCP client from your Python process. Hosted MCP inverts that: MAF hands Foundry the server description, and the service dials the MCP endpoint, negotiates its tools, and invokes them on your behalf. The model sees those remote tools as if they were native, and you get their results back in the response without managing a connection.

## Run it

```bash
uv run tutorial/02-agents/tools/07_hosted_mcp.py
```

Needs Foundry credentials (`az login`, `FOUNDRY_PROJECT_ENDPOINT`, `FOUNDRY_MODEL`). Success is a summary sourced from the Microsoft Learn MCP server.

---

Next: [Control Flow](/blog/posts/maf-py-44-control-flow.html)
