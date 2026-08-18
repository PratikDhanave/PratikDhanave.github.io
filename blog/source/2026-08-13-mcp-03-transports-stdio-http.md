# MCP Transports: stdio and Streamable HTTP

*The same JSON-RPC messages can travel down a subprocess pipe or across the network, and choosing the right transport is mostly a question of where your server lives and who it serves.*

The previous post looked at *what* the Model Context Protocol (MCP) sends: JSON-RPC requests, responses, and notifications. This post is about *how* those bytes get from client to server and back. MCP deliberately separates the message layer from the transport layer, which means the exact same messages work whether the server is a script on your laptop or a service in another data center. There are two standard transports — stdio and streamable HTTP — and knowing when to reach for each is most of the battle.

## Why transport is a separate concern

Keeping transport independent from the message format is a small design decision with large payoffs. Server and client code that builds and handles JSON-RPC messages does not care how they travel; you can move a server from local to remote by changing one line, not rewriting its logic. It also means the protocol can gain new transports over time without touching the semantics of tools, resources, and prompts. So think of transport as the envelope, not the letter.

## stdio: the local subprocess transport

The stdio transport is the workhorse for local, single-user servers. The model is simple and robust: the client launches the server as a child process and talks to it over the process's standard streams.

- The client writes JSON-RPC messages to the server's **stdin**.
- The server writes its replies to **stdout**.
- Messages are newline-delimited: exactly one JSON object per line, with no embedded raw newlines inside a message.
- **stderr** is reserved for logging. This is the rule that trips people up most: if a stdio server prints a stray `print()` to stdout, it corrupts the message stream. All diagnostics go to stderr.

Because the server is a subprocess of the client, its lifecycle is tied to the session — the client starts it on connect and lets it exit on close. There is no network, no port, no listening socket. Trust is inherited from the local user: the server runs with your permissions on your machine.

With the official Python SDK, choosing stdio is a single argument when you run the server:

```python
from mcp.server.fastmcp import FastMCP

mcp = FastMCP("notes")

# ... register tools/resources/prompts ...

if __name__ == "__main__":
    mcp.run(transport="stdio")
```

stdio is ideal for developer tools, editor integrations, and anything that wraps local resources like the filesystem or a local database. It is fast, has no auth ceremony, and is trivial to debug.

## Streamable HTTP: the remote transport

When a server needs to be reachable over a network — hosted centrally, shared by many users, or run in a different environment from the client — MCP uses the streamable HTTP transport.

The shape is: the client sends JSON-RPC messages to the server as HTTP POST requests to a single endpoint. For a plain request/response, the server answers in the HTTP response body. But some interactions are not a simple round trip — the server may need to stream multiple messages back (progress notifications during a long tool call, or server-initiated requests). For those, the server can respond with a stream, using Server-Sent Events (SSE) to push a sequence of messages to the client over one connection.

That single-endpoint, optionally-streaming design is why it is called *streamable* HTTP. It supersedes an earlier "HTTP+SSE" transport that used two separate endpoints; if you read older material referring to that split design, the streamable HTTP transport is its modern replacement, and new servers should prefer it.

Running an HTTP server with the Python SDK is, again, a transport choice:

```python
if __name__ == "__main__":
    mcp.run(transport="streamable-http")
```

Remote servers bring real infrastructure concerns that local ones do not: authentication, authorization, and origin validation. We treat those properly in the security post; for now, the key point is that the moment a server listens on the network, "trust the local user" stops being enough.

## Choosing a transport

The decision is usually straightforward:

- **Use stdio** when the server is local to the user and serves one client at a time — a CLI tool, an editor plugin's backend, a wrapper around local files or a local database. It is the default for desktop and developer tooling.
- **Use streamable HTTP** when the server is hosted, shared across users or machines, or must live in a different environment than the client — a company-wide knowledge server, a SaaS integration, anything multi-tenant.

A useful tie-breaker: if the server would need its own deployment, scaling, and authentication story anyway, it belongs on HTTP. If it can ride along as a subprocess of whatever launched it, stdio keeps things simple.

## Security implications, previewed

Transport choice changes your threat model. A stdio server runs as a local subprocess with the user's privileges — the risks are the risks of running any local program, and isolation means sandboxing that process. An HTTP server is exposed to the network, so it needs authenticated clients, authorization on every call, and validation of request origins to avoid being driven by pages or hosts you did not intend. These are not optional niceties for remote servers; they are the price of network reach. The final post in this series covers the concrete mechanisms. For now, internalize the rule: **stdio inherits local trust; HTTP must establish trust explicitly.**

## Key takeaways

- MCP separates the message layer (JSON-RPC) from the transport layer, so the same server logic works locally or remotely with a one-line change.
- stdio launches the server as a subprocess and exchanges newline-delimited JSON over stdin/stdout, with stderr reserved for logs — never write protocol output to stdout on stdio.
- Streamable HTTP targets remote and multi-user servers: JSON-RPC over HTTP POST to one endpoint, with optional SSE streaming for server-pushed messages; it supersedes the older two-endpoint HTTP+SSE transport.
- Choose stdio for local single-user tools and streamable HTTP for hosted or shared servers.
- Transport determines your security posture: stdio inherits local user trust, while HTTP requires explicit authentication, authorization, and origin checks.

## Further reading

- [Model Context Protocol — official site and docs](https://modelcontextprotocol.io)
- [MCP specification repository](https://github.com/modelcontextprotocol/modelcontextprotocol)
- [MCP Python SDK](https://github.com/modelcontextprotocol/python-sdk)
