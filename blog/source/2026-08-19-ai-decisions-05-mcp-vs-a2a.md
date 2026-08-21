# MCP vs A2A: Tools vs Agents

*The most common question about the two big agent protocols is which one to use — and the answer is almost always "both," because they solve different problems: MCP connects an agent to its tools, A2A connects an agent to other agents.*

The Model Context Protocol and the Agent2Agent protocol are frequently framed as competitors, and choosing between them is treated as an either/or. It isn't. They operate at different layers of an agentic system, and the useful decision is not "which one" but "which one for *this* connection." This fifth post in the AI Architecture Decisions series settles the distinction. (I've written full series on both — [MCP from Scratch](/blog/series/model-context-protocol-from-scratch/) and the [Agent2Agent Protocol](/blog/series/agent2agent-protocol-from-scratch/) — this is the chooser.)

## Two layers, not two competitors

The clean mental model:

- **MCP connects an agent to its tools and context** — the *vertical* link. A single agent reaching down to functions, data, and resources it uses to do its own work. A database, a code interpreter, a document: things an agent *uses*.
- **A2A connects an agent to other agents** — the *horizontal* link. An agent reaching across to peer agents it delegates work to. A specialist agent in another team or company: a collaborator an agent *works with*.

The one-line mnemonic: **MCP is how an agent uses tools; A2A is how an agent talks to agents.** A tool is a capability you invoke and control; an agent is an autonomous, opaque peer you delegate to and coordinate with. They are complementary layers of the same system, not two options for the same job.

## How to tell which a dependency is

When you have something your agent needs to interact with, ask what it *is*:

- Is it a **discrete capability you invoke and fully control** — a function, a query, a resource fetch, with no autonomy of its own? That's a **tool** → expose it via **MCP**.
- Is it an **autonomous system that reasons, has its own tools, and produces deliverables over a task lifecycle** — possibly owned by another team or vendor, whose internals you neither know nor want to know? That's an **agent** → connect via **A2A**.

Two more tells that resolve edge cases. If you'd need to know and manage its *internals* to use it, you're building a tool; if you deliberately do *not* want to know its internals and just want its results, you're delegating to an agent. And if the interaction is a quick synchronous call, MCP's shape fits; if it's long-running, interruptible work with its own progress and artifacts, A2A's task model fits.

## Why real systems use both

Because the two protocols address different layers, a mature system uses them together. Picture an orchestrating agent handling "plan and book a client offsite." It uses **MCP** to call tools — query the company calendar, look up the travel budget in a database, read the attendee list from a file. And it uses **A2A** to delegate to *other agents* — hand venue research to a specialist events agent, flights to a travel agent, catering to a vendor's agent — each of which is itself an autonomous system with its own tools.

The elegant part is that they nest. Each remote A2A agent can, internally, use its *own* MCP tools and delegate to its *own* downstream A2A agents — because A2A treats remote agents as opaque, the orchestrator neither knows nor cares how the events agent does its job. The boundary is clean: **tools within an agent (MCP), agents between (A2A).** That composition is how systems larger than any single agent get built.

## When you need only one

You won't always need both. If you're building a single self-contained agent that uses tools but doesn't collaborate with other autonomous agents, you need **MCP** and not A2A — most single-agent applications are here. Conversely, if you're exposing an existing agent for *other* organizations' agents to delegate to, or orchestrating across autonomous agents you don't own, you need **A2A** (and each agent still uses MCP internally for its own tools). The decision is per-connection: MCP for every agent-to-tool link, A2A for every agent-to-agent link, and most systems have more of the former than the latter.

## Pick this when

- **MCP** — for connecting an agent to a tool, data source, or resource it invokes and controls (the common case; nearly every agent needs it).
- **A2A** — for connecting an agent to another autonomous agent it delegates to, especially across teams or organizations, for long-running collaborative work.
- **Both** — for any multi-agent system: MCP for each agent's tools, A2A for the agent-to-agent delegation. This is the norm for anything beyond a single tool-using agent.
- **Neither as a rivalry** — never choose "MCP *or* A2A" for the same connection; they're different layers, and the question is always which layer a given dependency lives at.

## Key takeaways

- MCP and A2A are complementary layers, not competitors: MCP connects an agent to its tools/context (vertical), A2A connects an agent to other agents (horizontal).
- Tell which a dependency is by what it is: a discrete capability you invoke and control is a tool (MCP); an autonomous, opaque, task-lifecycle system is an agent (A2A).
- Real systems use both, and they nest cleanly — each A2A agent internally uses its own MCP tools and downstream A2A agents, because A2A treats remote agents as opaque.
- The rule: tools within an agent (MCP), agents between (A2A); decide per-connection, and most systems have more MCP links than A2A ones.
- Single tool-using agents need only MCP; cross-organization or multi-agent delegation needs A2A (with MCP still inside each agent) — never frame them as an either/or for one connection.

## Further reading

- [Model Context Protocol from Scratch series](/blog/series/model-context-protocol-from-scratch/)
- [Agent2Agent Protocol from Scratch series](/blog/series/agent2agent-protocol-from-scratch/)
- [The AI Production Roadmap series](/blog/series/the-ai-production-roadmap/)
