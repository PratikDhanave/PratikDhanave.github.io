# A2A and MCP Together

*The two protocols people keep pitting against each other are actually two halves of the same architecture — MCP gives an agent its tools, A2A gives it collaborators, and real systems need both.*

Throughout this series, one comparison has hovered in the background: how does the Agent2Agent protocol (A2A) relate to the Model Context Protocol (MCP)? They are frequently framed as competitors, and that framing is wrong. They solve different problems at different layers, and the most capable systems use them together. This final post in the series settles the distinction, shows how the two compose, and works through an architecture that combines them.

## Two layers, two problems

The clearest way to hold the distinction:

- **MCP connects an agent to its tools and context.** It is the *vertical* link — a single agent reaching down to functions, data, and resources it uses to do its own work. A weather tool, a database, a file: these are things an agent *uses*.
- **A2A connects an agent to other agents.** It is the *horizontal* link — an agent reaching across to peer agents it delegates work to. A translation agent, a scheduling agent, a specialist in another organization: these are collaborators an agent *works with*.

The mnemonic that sticks: MCP is how an agent uses *tools*; A2A is how an agent talks to *agents*. A tool is a capability you invoke and control; an agent is an autonomous, opaque peer you delegate to and coordinate with. Confusing the two leads to bad designs — wrapping a whole autonomous agent as if it were a single function, or treating a simple API call as if it needed full agent negotiation.

## Why you need both

Consider a realistic goal: "Plan and book a client offsite." No single agent should do all of this alone, and not all of the pieces are tools. An orchestrating agent might:

- use **MCP** to call *tools* — query the company calendar, look up the travel budget in a database, read the attendee list from a file;
- use **A2A** to delegate to *other agents* — hand venue research to a specialist events agent, hand flights to a travel agent, hand catering to a vendor's agent, each of which is itself an autonomous system with its own tools.

The tools are things the orchestrator invokes directly and controls. The agents are opaque collaborators it hands sub-goals to and coordinates via tasks. Strip out either protocol and the design breaks: without MCP the orchestrator cannot touch its own data and tools; without A2A it cannot leverage specialist agents it does not own and should not have to reimplement.

## How they compose in one architecture

Picture the orchestrating agent at the center:

```text
                 ┌─────────────────────────┐
                 │   Orchestrator agent    │
                 └──────────┬───────┬──────┘
                     MCP    │       │   A2A
             (tools/context)│       │(peer agents)
              ┌─────────────┘       └─────────────┐
              ▼                                    ▼
   ┌────────────────────┐             ┌──────────────────────────┐
   │  MCP servers        │            │  Remote A2A agents        │
   │  • calendar tool    │            │  • events agent           │
   │  • budget database  │            │  • travel agent           │
   │  • files/resources  │            │  • catering agent (vendor)│
   └────────────────────┘             └──────────────────────────┘
```

Downward, the orchestrator is an MCP *client* consuming tools and resources from MCP servers. Sideways, it is an A2A *client agent* delegating tasks to remote A2A agents. And here is the elegant part: each of those remote agents can, internally, be doing the same thing — using its *own* MCP servers for its tools and delegating to its *own* downstream A2A agents. A2A's opacity means the orchestrator neither knows nor cares how the events agent does its job; it just sees the Agent Card and the task lifecycle. The two protocols nest cleanly because each respects a clear boundary: MCP inside an agent, A2A between agents.

## Deciding which to reach for

When you are designing and unsure whether a dependency should be an MCP tool or an A2A agent, ask:

- Is it a **discrete capability you invoke and fully control** — a function, a query, a resource fetch? That is an **MCP tool**. It has no autonomy of its own; you call it and get a result.
- Is it an **autonomous system that reasons, has its own tools, and produces deliverables over a task lifecycle** — possibly owned by another team or vendor? That is an **A2A agent**. You delegate to it and coordinate, treating it as opaque.

Two more tells. If you would need to know and manage its *internals* to use it, it is a tool you are building; if you deliberately do *not* want to know its internals and just want its results, it is an agent you delegate to. And if the interaction is a quick, synchronous call, MCP fits; if it is long-running, interruptible work with its own progress and artifacts, A2A's task model fits.

## The bigger picture

MCP and A2A together sketch the shape of an interoperable agent ecosystem: agents that can reach any tool through a common standard *and* collaborate with any other agent through a common standard, across frameworks and organizations. Neither protocol is sufficient alone — an agent with tools but no peers is an island, and an agent with peers but no tools has nothing to contribute. Build with both: use MCP to give each agent its capabilities, use A2A to let agents form teams, and keep the boundary clean — tools within, agents between. That is how the pieces this series and the MCP series covered come together into systems larger than any single agent.

## Key takeaways

- MCP and A2A are complementary layers, not competitors: MCP connects an agent to its tools and context (vertical), A2A connects an agent to other agents (horizontal).
- The mnemonic: MCP is how an agent uses tools; A2A is how an agent talks to agents. Tools are invoked and controlled; agents are opaque peers you delegate to and coordinate.
- Real systems need both — an orchestrator uses MCP for its own data and functions and A2A to delegate sub-goals to specialist agents it does not own.
- The protocols nest cleanly: each remote A2A agent can internally use its own MCP tools and its own downstream A2A agents, because A2A's opacity hides internals behind the Agent Card and task lifecycle.
- To choose: a discrete capability you invoke and control is an MCP tool; an autonomous, opaque system with its own tools and a task lifecycle is an A2A agent — tools within, agents between.

## Further reading

- [A2A Protocol — official site](https://a2a-protocol.org)
- [Model Context Protocol](https://modelcontextprotocol.io)
- [Agent2Agent (A2A) on GitHub](https://github.com/a2aproject/A2A)
