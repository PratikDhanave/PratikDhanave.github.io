# What Is the Model Context Protocol?

*A model is only as useful as the context and tools it can reach, and MCP is the open standard that lets any AI app plug into any tool through one interface instead of a hundred bespoke integrations.*

Large language models are strong reasoners trapped behind a narrow doorway: the text you hand them. To be useful on real work, a model needs to reach outside that doorway — into your files, your database, your issue tracker, your monitoring, your internal services. For the last few years, every team wired those connections up by hand, once per app and once per tool. The Model Context Protocol (MCP) exists to end that busywork by making the connection a standard.

This post is the opening of an eight-part series that builds MCP up from first principles. Here we cover what problem it solves, the pieces it defines, and how it differs from the tool-calling you may already be doing.

## The M×N integration problem

Say you have *M* AI applications — a chat assistant, an IDE agent, a customer-support bot — and *N* systems you want them to use — Postgres, GitHub, Google Drive, a payments API. If each app integrates each system directly, you are on the hook for *M × N* integrations. Every new tool means touching every app; every new app means re-implementing every tool. The glue code is duplicated, subtly inconsistent, and never quite finished.

MCP reframes this as *M + N*. Each application speaks MCP as a client. Each system is wrapped once as an MCP server. Any client can now talk to any server, because they share a protocol. Write a GitHub server once and every MCP-capable app can use it; make your app MCP-capable once and it can use every server anyone has written. The integration surface collapses from a grid to two lists.

That is the whole pitch, and it is the same pitch that made the Language Server Protocol reshape editor tooling: standardize the seam, and an ecosystem grows on both sides of it.

## The mental model: hosts, clients, servers

MCP has exactly three roles, and keeping them straight makes everything else easier.

- A **host** is the AI application the user interacts with — an IDE, a desktop assistant, an agent runtime. The host holds the model (or talks to one) and decides what context to gather and what actions to allow.
- A **client** lives inside the host and manages a single connection to a single server. If the host connects to three servers, it runs three clients. The one-client-per-server rule keeps sessions isolated: a misbehaving server cannot see or interfere with another server's connection.
- A **server** is a program that exposes capabilities — actions to take, data to read, templates to reuse — over the protocol. A server can be a tiny local script or a hosted network service.

The user talks to the host. The host, through its clients, talks to servers. Servers do the actual reaching-out to files, databases, and APIs. Nothing about MCP requires a particular model vendor or programming language; it is a wire contract, not a library.

## What a server exposes

A server offers three kinds of capability, and the difference between them is *who is in control*. We spend a full post on each later, but here is the shape:

- **Tools** are actions the *model* chooses to invoke — "create an issue," "run this query," "send an email." Tools can have side effects, so the host usually gates the dangerous ones behind user approval.
- **Resources** are read-only context the *application* decides to pull in — a file's contents, a database record, a documentation page — each addressed by a URI. Resources load knowledge into the model's context without the model having to "act."
- **Prompts** are reusable, parameterized templates the *user* invokes deliberately, often surfaced as slash-commands or menu items — "review this diff," "summarize this thread."

Tools are model-controlled, resources are application-controlled, prompts are user-controlled. That three-way split is the cleanest way to remember what belongs where.

## MCP versus plain tool calling

If you have used an LLM's function-calling feature, you already hand the model a list of tools and let it emit structured calls. So what does MCP add?

Function calling defines *how one app describes tools to one model in one request*. It says nothing about where those tools come from, how they are discovered, or how they are reused across applications. You still write the tool implementations into your app, redeploy to change them, and re-implement the same tool in the next app.

MCP standardizes the layer underneath: discovery (`tools/list`), invocation (`tools/call`), transport, and lifecycle. A server publishes its tools at runtime; the client discovers them and adapts them to whatever tool-calling format its model expects. The result is that tools become *shareable, swappable dependencies* rather than code baked into each app. Function calling is how the model asks to use a tool; MCP is how the tool got there and how any app can offer the same one.

Here is the flavor of a discovery exchange — a client asking a server what it can do, in the JSON-RPC style MCP uses:

```json
{
  "jsonrpc": "2.0",
  "id": 1,
  "method": "tools/list"
}
```

```json
{
  "jsonrpc": "2.0",
  "id": 1,
  "result": {
    "tools": [
      {
        "name": "create_issue",
        "description": "Open a new issue in a repository.",
        "inputSchema": {
          "type": "object",
          "properties": {
            "repo": { "type": "string" },
            "title": { "type": "string" },
            "body": { "type": "string" }
          },
          "required": ["repo", "title"]
        }
      }
    ]
  }
}
```

The client takes that schema, reshapes it into the format its model expects, and now the model can request a `create_issue` call — without anyone hardcoding the tool into the app.

## When MCP is worth it — and when it is not

MCP shines when the same capability should be reachable from more than one application, when you want third parties to extend your app without a code change, or when you want to swap a data source without touching model code. A shared "company knowledge" server that your IDE agent, your support bot, and your internal chat all consume is exactly the case MCP was built for.

It is overkill when you have a single app with a couple of tightly-coupled, in-process functions that will never be reused elsewhere. Wrapping those in a protocol adds a process boundary and a serialization step for no gain. Reach for MCP when the reuse or the extensibility is real, not reflexively.

## What the rest of the series covers

With the mental model in place, the next posts go deep: the wire protocol and connection lifecycle (JSON-RPC and the initialize handshake), the two transports (stdio and streamable HTTP), then a post each on tools, and on resources and prompts. After that we build a real server, build a client that drives it from a model, and finish with security and production concerns. By the end you will be able to write MCP servers and clients from scratch and reason about them soundly.

## Key takeaways

- MCP turns an *M × N* integration mess into *M + N*: wrap each system as a server once, make each app a client once, and any app can use any system.
- The three roles are host (the AI app), client (one per server connection, inside the host), and server (exposes capabilities).
- Servers expose tools (model-controlled actions), resources (app-controlled read-only context), and prompts (user-controlled templates).
- MCP is not a replacement for function calling — it standardizes discovery, invocation, transport, and lifecycle *underneath* it, making tools reusable across apps.
- Use MCP where reuse or third-party extensibility is real; skip it for a lone app's in-process helpers.

## Further reading

- [Model Context Protocol — official site and docs](https://modelcontextprotocol.io)
- [MCP specification repository](https://github.com/modelcontextprotocol/modelcontextprotocol)
- [MCP Python SDK](https://github.com/modelcontextprotocol/python-sdk)
