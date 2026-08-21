# Choosing an Agent Framework: MAF vs LangGraph vs ADK vs CrewAI

*Four popular agent frameworks, four genuinely different philosophies — and the right choice is decided less by features than by how much control you want, how your team thinks, and what you're actually building.*

The agent-framework question generates more heat than almost any other AI decision, usually because people compare feature checklists instead of philosophies. Microsoft Agent Framework, LangGraph, Google's ADK, and CrewAI are not four flavors of the same thing — they embody different stances on how agents should be built. This second post in the AI Architecture Decisions series compares them on the axes that actually determine fit. (I've written deep series on several of these; this is the chooser.)

## Four philosophies, not four feature sets

The most useful way to see these frameworks is by their core abstraction and the control it gives you:

- **LangGraph** models an agent as an explicit **graph** — nodes and edges with shared state and checkpointing. You draw the control flow. Maximum control and transparency over what happens when, at the cost of more to author. Best when you need precise, inspectable, stateful control of complex flows. (See [LangGraph, Concept by Concept](/blog/series/langgraph-concept-by-concept/).)
- **Microsoft Agent Framework** is an enterprise-oriented framework for building agents and workflows with first-class tooling, integration, and governance leanings. Strong fit when you're in the Microsoft/Azure ecosystem or need enterprise integration and support. (See [Microsoft Agent Framework Go, Every Lesson](/blog/series/microsoft-agent-framework-go-every-lesson/).)
- **Google ADK** is Google's Agent Development Kit — agents, tools, sessions, and multi-agent composition, with strong ties to the Google/Vertex ecosystem and protocol interop (A2A). Natural when you're on Google Cloud or want that interoperability. (See [Google ADK, Concept by Concept](/blog/series/google-adk-concept-by-concept/).)
- **CrewAI** organizes work around **roles and crews** — you define agents with roles, assign tasks, and let a crew collaborate. The highest-level, most opinionated abstraction: fast to express role-based multi-agent workflows, less low-level control. Best when your problem maps cleanly onto "a team of specialists with roles."

Notice the spectrum from *low-level control* (LangGraph: you wire the graph) to *high-level convenience* (CrewAI: you assign roles). MAF and ADK sit in between, weighted by ecosystem. That spectrum, not a feature grid, is the real decision.

## The deciding questions

Work through these against the axes from the first post:

**How much control do you need over the flow?** If you need to see and shape every step — branching, loops, human-in-the-loop checkpoints, precise state — LangGraph's explicit graph rewards you. If you'd rather express intent at a high level and let the framework handle orchestration, CrewAI's roles-and-tasks model is faster. Control and convenience trade off directly here.

**What ecosystem are you in?** This often dominates. On Azure, MAF's integration and support are a real advantage; on Google Cloud, ADK's Vertex ties and A2A interop are. Fighting your cloud's native framework to use a "better" one usually costs more than it's worth unless you have a specific reason.

**How complex is the agentic logic?** Simple, role-based collaboration ("researcher hands to writer hands to reviewer") maps cleanly onto CrewAI. Complex, stateful, branching workflows with strict control needs favor LangGraph. Over-powered frameworks add ceremony for simple tasks; under-powered ones fight you on complex ones.

**Team skills and speed.** CrewAI's high-level model gets a team to a working multi-agent prototype fastest. LangGraph asks more up front but pays back in control. MAF/ADK reward existing ecosystem familiarity.

## The caveat that outranks the choice

Two things matter more than which of these you pick, and both come from elsewhere in this library. First, **most tasks need far less agentic machinery than teams reach for** — reliability drops roughly as `pⁿ` over `n` steps and cost scales with agent count, so the [AI Production Roadmap](/blog/series/the-ai-production-roadmap/) rule holds: prefer the simplest architecture that works, and a single well-engineered call often beats a multi-agent crew. Choose a framework only after you've confirmed you actually need agents.

Second, **keep the framework swappable.** Agent frameworks are young and moving fast; welding your whole system to one framework's abstractions is the lock-in axis biting. Keep your tools, prompts, and business logic separable from the orchestration framework so switching later is a rewrite of the glue, not the system.

## Pick this when

- **LangGraph** — you need precise, inspectable, stateful control over complex or branching flows, and you're willing to author the graph.
- **Microsoft Agent Framework** — you're in the Microsoft/Azure ecosystem or need enterprise integration, tooling, and support.
- **Google ADK** — you're on Google Cloud/Vertex or want strong protocol interop (A2A) and Google-ecosystem ties.
- **CrewAI** — your problem is naturally role-based multi-agent collaboration and you want the fastest path from idea to a working crew.
- **None yet** — you haven't confirmed the task actually needs agents; start with a single call and add a framework only when a single agent provably can't do it.

## Key takeaways

- These four frameworks embody different philosophies on a control-vs-convenience spectrum: LangGraph (explicit graph, max control) → MAF/ADK (ecosystem-weighted middle) → CrewAI (roles-and-crews, high-level convenience).
- The deciding questions are how much flow control you need, which cloud ecosystem you're in (often dominant), how complex the agentic logic is, and team skills/speed — not a feature checklist.
- LangGraph for complex stateful control; MAF for Azure/enterprise; ADK for Google Cloud/interop; CrewAI for fast role-based multi-agent work.
- Two things outrank the choice: confirm you actually need agents (simplest architecture wins; reliability ≈ pⁿ), and keep the framework swappable since the space is young and lock-in is real.
- There's no global winner — match the framework's philosophy and ecosystem to your requirements, and measure on your task.

## Further reading

- [LangGraph, Concept by Concept](/blog/series/langgraph-concept-by-concept/)
- [Microsoft Agent Framework Go, Every Lesson](/blog/series/microsoft-agent-framework-go-every-lesson/)
- [Google ADK, Concept by Concept](/blog/series/google-adk-concept-by-concept/)
