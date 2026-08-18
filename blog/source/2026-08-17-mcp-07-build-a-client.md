# Building an MCP Client

*A server is only half the story; the client is what connects to it, discovers its capabilities, and turns a model's intent into real tool calls.*

In the last post we built a Model Context Protocol (MCP) server. Now we build the other side: a client that launches that server, completes the handshake, discovers its tools, and drives them from a language model. Most developers consume MCP through a ready-made host, but writing a client yourself is the clearest way to understand what a host actually does — and it is exactly what you need when you are embedding MCP into your own agent runtime. We will use the official Python SDK's client APIs and stay consistent with the "notes" server from the previous post.

## What a client does

A client's responsibilities are small and specific:

1. Connect to a server over a transport (here, launching it as a stdio subprocess).
2. Run the `initialize` handshake and send the `initialized` notification.
3. Discover capabilities — list tools, resources, and prompts.
4. Invoke them on behalf of the model — call tools, read resources, fetch prompts.
5. Clean up — close the session and the transport.

The SDK gives you a `ClientSession` that handles the JSON-RPC plumbing; you drive it with high-level calls.

## Connecting and discovering

Here is a minimal client that launches the notes server, initializes, lists tools, and calls one:

```python
import asyncio
from mcp import ClientSession, StdioServerParameters
from mcp.client.stdio import stdio_client

server = StdioServerParameters(
    command="python",
    args=["server.py"],
)

async def main():
    async with stdio_client(server) as (read, write):
        async with ClientSession(read, write) as session:
            await session.initialize()

            tools = await session.list_tools()
            print("tools:", [t.name for t in tools.tools])

            result = await session.call_tool(
                "add_note", {"title": "groceries", "body": "milk, eggs, coffee"}
            )
            print("add_note ->", result)

            note = await session.read_resource("notes://groceries")
            print("resource ->", note)

asyncio.run(main())
```

Walking through it:

- `stdio_client(server)` launches the server subprocess and yields a `read`/`write` pair — the raw transport streams.
- `ClientSession(read, write)` wraps those in a session that speaks JSON-RPC.
- `await session.initialize()` performs the handshake and capability negotiation; nothing else is valid before it returns.
- `session.list_tools()` returns the tools the server advertised, each with its name, description, and input schema.
- `session.call_tool(name, arguments)` invokes a tool and returns its result content.
- `session.read_resource(uri)` fetches a resource by URI.

Both `async with` blocks matter: they guarantee the session and the subprocess are torn down cleanly when you leave the block, even on error. This is the whole client lifecycle in a dozen lines.

## Bridging MCP tools to a language model

Listing and calling tools by hand is useful for testing, but the point of a client is to let a *model* decide which tools to call. That bridge has three moving parts: translate MCP tools into your model's tool format, run the model, and dispatch any tool calls it emits back through the session.

The translation step exists because each model provider expects tool definitions in its own shape, while MCP gives you a provider-neutral description. You map one to the other:

```python
def to_model_tool(mcp_tool):
    """Convert an MCP tool into a generic provider tool definition."""
    return {
        "name": mcp_tool.name,
        "description": mcp_tool.description or "",
        "parameters": mcp_tool.inputSchema,  # already JSON Schema
    }
```

Then the agent loop ties it together. The specifics of calling a model differ by vendor, so treat the model call below as a stand-in for whichever API you use:

```python
async def agent_turn(session, model, user_message):
    listed = await session.list_tools()
    model_tools = [to_model_tool(t) for t in listed.tools]

    messages = [{"role": "user", "content": user_message}]
    while True:
        response = model.complete(messages=messages, tools=model_tools)

        if response.tool_calls:
            for call in response.tool_calls:
                result = await session.call_tool(call.name, call.arguments)
                messages.append({
                    "role": "tool",
                    "tool_call_id": call.id,
                    "content": str(result),
                })
            continue  # let the model react to the tool results

        return response.text  # no tool calls left: final answer
```

The pattern is the important part, not the vendor details: list tools, hand their schemas to the model, and whenever the model asks to call a tool, dispatch it through `session.call_tool` and append the result so the model can continue. The loop ends when the model stops asking for tools and produces a final answer. This is precisely what a full MCP host does internally — you have just written the core of one.

## Talking to multiple servers

Real hosts connect to several servers at once — a notes server, a GitHub server, a database server. The pattern generalizes cleanly: open one `ClientSession` per server, keep them in a registry keyed by server name, and merge their tool lists (namespacing tool names by server so two servers can both have a `search` without colliding). When the model calls a namespaced tool, route it to the right session. Each session stays isolated, which is exactly why MCP uses one client per server.

## Errors, timeouts, and cleanup

Robust clients plan for servers that misbehave. Wrap `call_tool` so a tool error becomes feedback the model can act on rather than a crash, apply a timeout to calls so a hung server does not freeze the agent, and rely on the `async with` blocks to guarantee the subprocess is reaped when a session ends. If you manage sessions manually instead of with context managers, close them explicitly in a `finally` — a leaked server subprocess is the most common client bug.

## Key takeaways

- A client's job is to connect, initialize, discover, invoke, and clean up; the SDK's `ClientSession` handles the JSON-RPC underneath.
- Use `stdio_client` to launch a server and `ClientSession.initialize()` to complete the handshake before any other call; `async with` guarantees clean teardown.
- Discover with `list_tools`/`read_resource` and act with `call_tool`; MCP's `inputSchema` is JSON Schema, so it maps directly onto model tool definitions.
- The agent loop is: translate tools, run the model, dispatch its tool calls through the session, feed results back, repeat until it answers — this is the core of any MCP host.
- Support multiple servers with one session each, namespaced tool names, per-call timeouts, and error handling that turns failures into model-visible feedback.

## Further reading

- [Model Context Protocol — official site and docs](https://modelcontextprotocol.io)
- [MCP Python SDK](https://github.com/modelcontextprotocol/python-sdk)
- [MCP specification repository](https://github.com/modelcontextprotocol/modelcontextprotocol)
