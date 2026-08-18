# MCP Resources and Prompts

*Tools let a model act, but resources and prompts are how a Model Context Protocol server feeds it the right context and gives users repeatable ways to invoke it.*

Tools get the attention, but a Model Context Protocol (MCP) server has two other primitives that are just as important for building something usable: resources and prompts. Resources supply read-only context; prompts supply reusable, parameterized templates. Their defining trait is *who is in control*, and understanding that is the fastest way to know which one you need. This post covers both, how they appear on the wire, how to define them with the Python SDK, and how to choose between a resource, a tool, and a prompt.

## The control model, revisited

MCP's three primitives map cleanly onto three controllers:

- **Tools are model-controlled.** The model decides when to call them, mid-reasoning.
- **Resources are application-controlled.** The host application decides which ones to pull into the model's context.
- **Prompts are user-controlled.** The user deliberately invokes them, often by name.

Keep that triad in mind and most "should this be a tool or a resource?" questions answer themselves. If the model should decide to *do* it, it is a tool. If the app should decide to *load* it, it is a resource. If the user should *pick* it, it is a prompt.

## Resources: read-only context by URI

A resource is a piece of context a server makes available for reading — a file's contents, a database record, a wiki page, the output of a report. Each resource is identified by a URI, and the scheme is yours to design: `file:///project/README.md`, `db://customers/42`, `notes://groceries`. The URI is the stable handle a client uses to fetch it.

Two methods cover the basics. `resources/list` enumerates what is available:

```json
{ "jsonrpc": "2.0", "id": 5, "method": "resources/list" }
```

```json
{
  "jsonrpc": "2.0",
  "id": 5,
  "result": {
    "resources": [
      { "uri": "notes://groceries", "name": "Groceries", "mimeType": "text/plain" }
    ]
  }
}
```

And `resources/read` fetches the contents of one by URI:

```json
{ "jsonrpc": "2.0", "id": 6, "method": "resources/read",
  "params": { "uri": "notes://groceries" } }
```

The crucial design point is that resources are *application-controlled*. The server offers them; the host decides which to actually load into context. In practice a host might show resources to the user as attachable context ("add this file to the chat"), or a client might select them programmatically. The model does not silently vacuum up every resource — that keeps context windows focused and gives the app control over what the model sees.

### Resource templates

Enumerating every possible resource is impractical when the space is large (every file in a repo, every row in a table). Resource *templates* solve this with parameterized URIs — a pattern with placeholders that expands to concrete resources on demand. A template like `file:///project/{path}` says "any project file is readable," without listing them all up front.

With the Python SDK, a templated resource is a decorated function whose URI carries parameters that map to its arguments:

```python
from mcp.server.fastmcp import FastMCP

mcp = FastMCP("notes")

@mcp.resource("notes://{title}")
def get_note(title: str) -> str:
    """Return the body of a note by title."""
    return NOTES.get(title, "")
```

Reading `notes://groceries` calls `get_note("groceries")`. Templates turn a potentially infinite resource space into a compact, discoverable contract.

### Updates and subscriptions

Resources are not always static. A server can advertise that a resource may change and support subscriptions, notifying the client when the underlying data updates so it can re-read. This is optional and negotiated via capabilities, but it is what lets, say, a "current build status" resource stay live rather than going stale the moment it is read. Reach for it only when freshness genuinely matters; most resources are fine read-on-demand.

## Prompts: reusable, user-invoked templates

A prompt is a named, parameterized message template the server offers — a canned, high-quality way to ask the model to do a common task. Because prompts are *user-controlled*, hosts usually surface them as explicit affordances: slash-commands, a menu, buttons. The user picks "Code Review," supplies a couple of arguments, and the server returns a well-crafted message (or messages) to send to the model.

The methods mirror the others. `prompts/list` enumerates available prompts and their arguments; `prompts/get` renders one with supplied arguments and returns the resulting messages.

With the Python SDK, a prompt is a decorated function that returns the text (or structured messages) to send:

```python
@mcp.prompt()
def code_review(language: str, code: str) -> str:
    """A prompt to review a snippet of code."""
    return (
        f"You are a senior {language} engineer. Review the following code for "
        f"correctness, clarity, and security. Be specific and constructive.\n\n"
        f"```{language}\n{code}\n```"
    )
```

The value here is consistency and reuse: the careful wording of a good review prompt lives in one place, is offered by the server, and any host can present it to users. Prompts let a server ship expertise, not just capability.

## Choosing between a resource, a tool, and a prompt

When you are unsure which primitive fits, work through the control question:

- Is it **read-only context** the app should be able to load? Make it a **resource**. (Reading a file, fetching a record.)
- Is it an **action with effects** the model should decide to take? Make it a **tool**. (Writing a file, sending a message, running a query that changes state.)
- Is it a **repeatable request pattern** a user should invoke by name? Make it a **prompt**. (A review template, a summarize-this template.)

Edge cases resolve the same way. "Search the docs" is usually a *tool* (the model decides to call it and passes a query), while "the docs page at this URI" is a *resource* (the app loads it). "Summarize this thread" as a one-click user action is a *prompt*; the summarization logic it triggers might itself use tools and resources. The primitives compose — a prompt can reference resources, a tool can return data you later expose as a resource — but each one still has a natural home defined by who is in control.

## Key takeaways

- MCP's three primitives split by controller: tools are model-controlled, resources are application-controlled, prompts are user-controlled.
- Resources are read-only context addressed by URIs; `resources/list` and `resources/read` handle discovery and fetching, and the host — not the model — decides what to load.
- Resource templates use parameterized URIs to expose large or dynamic spaces without listing every item; subscriptions keep changing resources fresh when needed.
- Prompts are reusable, parameterized templates users invoke by name (often as slash-commands); they let a server ship expertise, not just capability.
- To choose a primitive, ask who should be in control: app-loads-context → resource, model-takes-action → tool, user-invokes-pattern → prompt.

## Further reading

- [Model Context Protocol — official site and docs](https://modelcontextprotocol.io)
- [MCP Python SDK](https://github.com/modelcontextprotocol/python-sdk)
- [MCP specification repository](https://github.com/modelcontextprotocol/modelcontextprotocol)
