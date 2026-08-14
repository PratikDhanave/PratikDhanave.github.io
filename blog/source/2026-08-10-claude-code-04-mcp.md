# MCP: Connecting Claude Code to Your Tools

*The Model Context Protocol lets Claude Code reach beyond your codebase — into your databases, issue trackers, docs, and services — through a standard, pluggable interface.*

Out of the box, Claude Code works with your files, shell, and git. But real work spans more than the repo: the ticket in your issue tracker, the schema in your database, the design in a doc, the error in your observability tool. The Model Context Protocol (MCP) is how Claude Code plugs into those systems through a common standard, so it can read and act on context that lives outside the codebase. This post is about what MCP is and how to use it with Claude Code sensibly.

## What MCP is

MCP is an open protocol — think of it as a universal adapter between AI applications and external tools/data. An **MCP server** exposes some capability (query this database, search these docs, create an issue) in a standard way; an **MCP client** (Claude Code, among others) connects to it and can then use those capabilities as tools. Because it's a standard, the same server works across any MCP-compatible client, and you can mix and match servers without custom integration each time.

The practical upshot for Claude Code: you can extend what it can *see and do* by connecting servers, without anyone writing a bespoke plugin. Want it to be able to query your Postgres, look up a Jira ticket, or read your team's Notion? Connect the corresponding MCP server.

## What MCP servers provide

MCP servers typically expose a few kinds of capability:

- **Tools** — actions the agent can invoke (run a query, create a ticket, call an API).
- **Resources** — data it can read (files, records, documents) as context.
- **Prompts** — reusable prompt templates the server offers.

For most Claude Code use, tools and resources are what you'll notice: they add new verbs and new context to what the agent can do.

## Connecting servers to Claude Code

You add MCP servers to Claude Code by configuring them (at user, project, or local scope — mirroring the config hierarchy from post 3). Servers can run locally (a process on your machine, e.g. talking to your local database) or be remote. A project-scoped server config, committed to the repo, means your whole team's Claude Code can use the same integrations — the same "make the good setup shareable" principle from post 3.

Common, high-value servers people connect: databases (query the schema and data directly), issue trackers and project tools, documentation/knowledge bases, browser automation, and cloud/provider APIs. The right set depends on where your work's context actually lives.

**The gotcha:** every MCP server you add expands what the agent can reach — which is the point, but also the risk. A server with write access to production, or broad read access to sensitive data, hands that reach to the agent. Add servers deliberately, scope their credentials to least privilege, and prefer read-only where you can.

## Security: treat servers as trust decisions

MCP is powerful precisely because it grants capability, so treat connecting a server as a security decision (this echoes the API Security and AI Security series):

- **Vet the server.** A third-party MCP server runs with whatever access you give it and sees the data that flows through it. Use ones you trust, and prefer official/first-party servers for sensitive systems.
- **Least privilege the credentials.** Give a database server a read-only, scoped account — not your admin connection string. The agent's blast radius equals the server's permissions.
- **Mind untrusted content.** Data pulled in via a server is untrusted input — a document or ticket the agent reads could carry a prompt injection (the AI Security series' indirect-injection lesson). Keep consequential actions gated (post 1 permissions).
- **Keep secrets out of committed config.** Connection strings and tokens belong in local/uncommitted settings or environment, not in a repo-committed server config (post 3).

## When to reach for MCP

MCP earns its keep when the context or action you need lives outside the codebase *and* you need it repeatedly. For a one-off, pasting a query result into the conversation is fine. But if you constantly need Claude Code to check tickets, inspect the database, or file issues, a connected server turns that from manual copy-paste into something the agent just does. The judgment call is the same as any integration: connect what you'll use often, keep the surface minimal, and don't wire up reach you don't need.

**The gotcha:** connecting a dozen servers "just in case" bloats the agent's tool surface (more choices, more ways to go wrong, more attack surface) without clear benefit. Start with the one or two integrations your work actually needs and add more when a real, repeated need appears.

## Key takeaways

- **MCP is a standard adapter** between Claude Code and external tools/data — connect servers to extend what the agent can see and do, without bespoke plugins.
- Servers expose **tools (actions), resources (data), and prompts**; the same server works across any MCP client.
- **Configure servers at user/project/local scope** (like other config); project-scoped, committed servers give the whole team the same integrations.
- **Treat every server as a trust and security decision** — vet it, least-privilege its credentials, treat pulled-in data as untrusted, and keep secrets out of committed config.
- **Connect what you'll use repeatedly**, keep the surface minimal, and prefer read-only for sensitive systems.

## Further reading

- [Model Context Protocol — official site & spec](https://modelcontextprotocol.io/) — what MCP is and how servers/clients work.
- [Claude Code — MCP documentation](https://docs.claude.com/en/docs/claude-code/mcp) — connecting and scoping servers in Claude Code.
- [Claude Code — settings](https://docs.claude.com/en/docs/claude-code/settings) — where server and permission config lives.
