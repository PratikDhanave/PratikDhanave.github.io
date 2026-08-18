# Building an MCP Server from Scratch

*Everything in the series so far comes together here: a small but complete Model Context Protocol server, in Python, exposing a tool, a resource, and a prompt, runnable and testable in minutes.*

We have covered the mental model, the wire protocol, transports, and the three primitives. Now we build. This post walks through a complete, coherent Model Context Protocol (MCP) server in Python using the official SDK — a small "notes" service that lets a model add notes, read them back as resources, and offers a prompt to summarize them. It is deliberately simple enough to hold in your head and complete enough to run, inspect, and connect to a real host.

## Setup

The official Python SDK is the `mcp` package. Install it with the CLI extras so you get the development tooling too. Using `uv` (recommended):

```bash
uv add "mcp[cli]"
```

Or with pip:

```bash
pip install "mcp[cli]"
```

The `[cli]` extra brings the `mcp` command-line tool, which we will use to run and inspect the server.

## The server, end to end

Here is the full server in one file, `server.py`. It keeps notes in an in-memory dictionary so the example stays self-contained; in a real server this would be a database or an API. Read it once top to bottom — it exercises all three primitives.

```python
from mcp.server.fastmcp import FastMCP

mcp = FastMCP("notes")

# In-memory store: title -> body. Swap for a real database in production.
NOTES: dict[str, str] = {}


@mcp.tool()
def add_note(title: str, body: str) -> str:
    """Create or overwrite a note.

    Args:
        title: Short unique title for the note.
        body: The note's content.
    """
    if not title.strip():
        raise ValueError("title must not be empty")
    existed = title in NOTES
    NOTES[title] = body
    return f"{'Updated' if existed else 'Created'} note '{title}'."


@mcp.tool()
def list_notes() -> list[str]:
    """Return the titles of all notes."""
    return sorted(NOTES)


@mcp.resource("notes://{title}")
def read_note(title: str) -> str:
    """Read a note's body by title (read-only context)."""
    return NOTES.get(title, f"(no note titled '{title}')")


@mcp.prompt()
def summarize(title: str) -> str:
    """A prompt that asks the model to summarize a specific note."""
    body = NOTES.get(title, "")
    return (
        "Summarize the following note in one sentence, preserving any dates "
        f"or action items.\n\nTitle: {title}\n\n{body}"
    )


if __name__ == "__main__":
    mcp.run(transport="stdio")
```

A few things worth noticing about why this works:

- `add_note` and `list_notes` are **tools** — model-controlled actions. `add_note` has side effects (it mutates the store); `list_notes` is a harmless read. The decorator turns each function's type hints and docstring into the tool's input schema and description.
- `read_note` is a **resource** with a templated URI. Reading `notes://groceries` invokes `read_note("groceries")`. It is read-only context the host loads, not an action the model performs.
- `summarize` is a **prompt** — a user-invoked template. A host might surface it as a `/summarize` command; when chosen with a title, it returns a ready-to-send message.
- Raising `ValueError` on empty input gives the model a readable error instead of crashing the session.
- The final line selects the stdio transport, so this server runs as a subprocess of whatever host launches it.

That is a genuinely complete MCP server. There is no boilerplate for JSON-RPC, the handshake, or capability advertisement — the SDK handles all of it and advertises tools, resources, and prompts based on what you registered.

## Running and inspecting it

The fastest way to see your server work is the MCP Inspector, a development UI that connects to your server, lists its capabilities, and lets you call tools and read resources by hand. The SDK's CLI launches it:

```bash
mcp dev server.py
```

That starts your server and opens the Inspector against it. You can call `add_note` with a title and body, watch the result, then read `notes://<title>` and see the stored text — all without writing a client or involving a model. This is the tightest feedback loop you have while developing; use it before wiring the server into anything real.

To run the server as a host would (over stdio, no UI):

```bash
mcp run server.py
```

or simply `python server.py`, since the `__main__` block calls `mcp.run(...)`.

## Wiring it into a host

To use the server from an MCP-capable host, you register it in the host's server configuration. Conceptually, a host needs three things: how to launch the server (a command and its arguments), and a name to refer to it by. A typical configuration entry looks like this:

```json
{
  "mcpServers": {
    "notes": {
      "command": "python",
      "args": ["/absolute/path/to/server.py"]
    }
  }
}
```

The host spawns that command, runs the initialize handshake over stdio, discovers your `add_note`, `list_notes`, `read_note`, and `summarize` capabilities, and makes them available to the model and the user. From the host's side, your server is now just another set of tools and context — exactly the interchangeability MCP promised.

## Other languages

Python is not the only option. The project maintains official SDKs in several languages, including TypeScript and a Go SDK, that expose the same primitives with idiomatic APIs. If your ecosystem is Go or Node, you can build the identical "notes" server there and any MCP host will treat it the same — the protocol, not the language, is what the host depends on. Pick the SDK that matches the systems your server needs to reach.

## Key takeaways

- The official Python SDK (`mcp`, installed with the `[cli]` extra) lets you build a full server without touching JSON-RPC or the handshake — the SDK advertises capabilities from what you register.
- A coherent server combines primitives by control model: tools for actions (`add_note`), resources for read-only context (`read_note` via a templated URI), and a prompt for a user-invoked template (`summarize`).
- Raise ordinary exceptions for bad input; the SDK surfaces them to the model as readable errors instead of crashing the session.
- Develop against the MCP Inspector (`mcp dev server.py`) for a tight, model-free feedback loop, then run over stdio with `mcp run server.py`.
- Register a stdio server in a host by giving it a launch command and args; the host handles discovery. Official SDKs in other languages (TypeScript, Go) build the same server idiomatically.

## Further reading

- [Model Context Protocol — official site and docs](https://modelcontextprotocol.io)
- [MCP Python SDK](https://github.com/modelcontextprotocol/python-sdk)
- [MCP specification repository](https://github.com/modelcontextprotocol/modelcontextprotocol)
