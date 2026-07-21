# Protocols in Google ADK: MCP for Tools, A2A for Agents

*Two open protocols that let an agent reach outside its own process — one to borrow tools, one to call other agents as peers.*

---

Everything so far has kept an agent inside one process: its tools are functions you wrote, its sub-agents are objects you constructed. Real systems don't stay that small — you want your agent to use the GitHub server someone else built, or hand a sub-question to a specialist agent on another machine in another language. Google's [Agent Development Kit](https://google.github.io/adk-docs/) answers both with two open protocols: **MCP** (Model Context Protocol) connects your agent to external *tool servers*, and **A2A** (Agent-to-Agent) connects it to other *agents*. Think of MCP as "USB for tools" and A2A as "HTTP for agents."

| Protocol | Connects your agent to… | Direction |
|----------|-------------------------|-----------|
| **MCP** | external **tool servers** | agent → tools |
| **A2A** | other **agents** | agent ↔ agent |

## MCP — borrow tools from a server

An MCP **server** publishes tools; your agent connects as an MCP **client**, and those tools appear as if they were native. You don't write wrappers — the GitHub server, a filesystem server, a database server all become agent tools by connecting to them. In ADK this is a single toolset object mounted on the agent:

```python
# Python — connect to an MCP server over stdio and mount its tools
from google.adk.agents import LlmAgent
from google.adk.tools.mcp_tool.mcp_toolset import MCPToolset
from mcp import StdioServerParameters

toolset = MCPToolset(
    connection_params=StdioServerParameters(command="uvx", args=["mcp-server-fetch"]),
)
agent = LlmAgent(name="researcher", model="gemini-flash-latest", tools=[toolset])
```

```go
// Go — mcptoolset.New with an MCP transport (in-memory, stdio, or remote HTTP)
import (
    "google.golang.org/adk/v2/agent/llmagent"
    "google.golang.org/adk/v2/tool"
    "google.golang.org/adk/v2/tool/mcptoolset"
)

mcpToolSet, _ := mcptoolset.New(mcptoolset.Config{ /* Transport: ... */ })
agent := llmagent.New(llmagent.Config{
    Name:     "researcher",
    Model:    m,
    Toolsets: []tool.Toolset{mcpToolSet},
})
```

The Python `MCPToolset` takes a `StdioServerParameters` (spawn a local server) or an SSE/HTTP endpoint; the Go `mcptoolset` takes a transport — in-memory, stdio, or a `StreamableClientTransport` pointing at a remote URL. Either way the mounted server's tools show up in the agent's tool list, and the model calls them like any local function.

### An MCP server exposes three primitives, not just tools

Tools get the attention, but the MCP spec defines **three** server primitives, and a well-built server can advertise all three:

| Primitive | What it is | Who drives it | Analogy |
|-----------|-----------|---------------|---------|
| **Tools** | callable functions the agent may **invoke** (side effects) | model-controlled | a POST endpoint |
| **Resources** | readable **context** at a `uri` (a file, a DB row, a doc) | app-controlled | a GET endpoint |
| **Prompts** | reusable **prompt templates** offered by name | user-controlled | a slash-command |

**Resources** are readable context, not actions: the server lists them (each has a `uri` like `weather://stations`) and the client fetches one when it wants that context in view. Reading one should have no side effects — "load a document," not "run a query that charges money." **Prompts** are server-provided templates: instead of the client hard-coding "summarize this in three bullets," the server publishes a named `forecast_briefing` prompt and the client requests it, keeping the good prompt next to the server that knows the domain.

Your ADK agent can also *be* an MCP server, exposing its own tools, resources, and prompts to other clients — `FastMCP` with `@mcp.tool` / `@mcp.resource` / `@mcp.prompt` in Python, or `mcp.NewServer` with `AddTool` / `AddResource` / `AddPrompt` in Go.

## A2A — call another agent as a peer

Where MCP borrows *tools*, A2A borrows *judgment*. A remote agent exposes itself over HTTP via an **Agent Card**: a JSON manifest at a well-known URL describing its name, endpoint, and skills. Another agent fetches the card and calls a skill — even if the remote agent is written in a different language or framework. Discovery is "fetch the card"; invocation is "call a skill."

```python
# Python — expose an agent as an A2A server, and call a remote one
from google.adk.a2a.utils.agent_to_a2a import to_a2a
from google.adk.agents.remote_a2a_agent import RemoteA2aAgent

app = to_a2a(my_agent)  # ASGI app serving the AgentCard + JSON-RPC endpoint

weather = RemoteA2aAgent(
    name="weather",
    agent_card="http://host/.well-known/agent-card.json",
)
```

```go
// Go — build an AgentCard, serve it, and consume a remote one
agentCard := &a2a.AgentCard{
    Name:   "weather_agent",
    Skills: adka2a.BuildAgentSkills(agent),
    // URL, Version, capabilities...
}
remote, _ := remoteagent.NewA2A(remoteagent.A2AConfig{
    AgentCardProvider: remoteagent.NewAgentCardProvider(url),
})
```

The payoff: a `RemoteA2aAgent` behaves like any local sub-agent. You can drop it into a multi-agent tree and delegate to it exactly as you would to an in-process specialist — the network hop is invisible to your orchestration logic.

### What actually crosses the A2A boundary

It is tempting to picture A2A as "text in, text out." It carries far more. ADK's converters (`google.adk.a2a.converters`) translate the rich ADK event model into A2A messages and back, so three things you might expect to be lost survive the hop:

- **Reasoning / thought signatures.** A model's thinking parts and their opaque *thought signatures* are preserved. The `part_converter` stashes a part's `thought` flag and base64-encodes its `thought_signature` into the A2A part metadata, then decodes it on the far side — so a remote agent keeps reasoning coherently instead of restarting cold.
- **Long-running tool calls surface as task states.** A tool marked long-running (the human-in-the-loop pattern) doesn't block the wire. ADK emits a `TaskStatusUpdateEvent` and moves the task into `input_required` (or `auth_required` for credential requests). The client sees a *pausable task*, supplies the missing input later, and the task resumes.
- **Artifacts transfer.** Files an agent produces travel too. An after-agent interceptor loads each artifact from the artifact service and emits a `TaskArtifactUpdateEvent` carrying an A2A `Artifact`, so the caller receives the generated PDF or image — not just a sentence describing it.

Because all of this crosses a trust boundary, the security mindset still applies: a remote agent's thoughts, task states, and artifacts are *inputs you did not generate* — validate them before acting.

## Mental model: which protocol?

> Need a **capability** — search GitHub, read files, query a DB? Reach for **MCP** and borrow the tools. Need another **agent's judgment** — a specialist that reasons, not just a function? Reach for **A2A** and delegate to a peer.

Both are network protocols with external dependencies, which makes their *data model* the part worth internalizing first: an A2A Agent Card is just `{name, url, skills}` — a card is usable only if it has a name, an `http(s)` URL, and at least one named skill — and an MCP server descriptor is `{name, version}` plus its three primitive lists (tools, resources, prompts). Get those two shapes right and the SDK wiring is mechanical.

A third, still-emerging axis rounds out the picture: protocols that stream an agent's events to an interactive **front-end UI** — **AG-UI** (CopilotKit's agent-to-UI event protocol) and the nascent **A2UI** proposal. These are ecosystem efforts, not part of the core ADK surface — there is no `google.adk` AG-UI API to import today — but they complete the three directions: agent ↔ tools (MCP), agent ↔ agent (A2A), agent → UI (AG-UI / A2UI).

**Next in the series:** grounding an agent's answers in Google Search and your own documents with RAG.
