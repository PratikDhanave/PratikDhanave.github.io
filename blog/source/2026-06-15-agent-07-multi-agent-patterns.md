# Multi-Agent Patterns

*The instinct, once single agents work, is to build teams of them — a researcher agent, a writer agent, a critic agent, all collaborating like a little organization. It's an appealing vision, and sometimes exactly right. But multi-agent systems are also where a lot of complexity and cost hides, and the honest guidance is more restrained than the hype: use multiple agents when the problem genuinely calls for it, and prefer a single well-designed agent when it doesn't. Understanding the multi-agent patterns — and their real tradeoffs — is what lets you make that call well.*

**Multi-agent patterns** involve *multiple* agents (or agent-like components) working together on a task. This post covers what multi-agent systems are, the main patterns (orchestrator-workers, specialists, and others), when multi-agent helps versus hurts, and the significant tradeoffs. It's a pattern area with real value *and* real overhead, so the emphasis is on using it judiciously — a theme consistent with the whole series' "use the simplest thing that works."

## What multi-agent systems are

A **multi-agent system** uses *multiple* agents — each an LLM-driven agent, often with a distinct role — coordinated to accomplish a task together, rather than one agent doing everything. The idea and motivation:

- **Multiple agents with roles, collaborating.** Instead of a single agent, you have *several* — often *specialized* (a researcher, a coder, a critic, etc.) — that *coordinate* to accomplish the overall task, each handling part of it. It's like a team or organization of agents, dividing and combining work. Each agent has its own role, tools, and focus.
- **The appeal: division of labor and separation of concerns.** The motivation mirrors why *human* organizations divide labor: *specialization* (each agent focused on and good at its part), *separation of concerns* (each agent's context/task is focused, not cluttered with everything), and *parallelism* (agents working on different parts simultaneously). These can make a complex task more manageable than one agent doing it all. Division of labor is the core appeal.
- **It's a composition of agents.** A multi-agent system *composes* multiple agents (each itself an LLM + tools + loop) into a larger system, with some coordination mechanism connecting them. So the patterns are about *how agents are organized and coordinate* — the "org chart" of the agent system. Understanding multi-agent design is understanding these coordination structures.

Multi-agent systems use multiple coordinated (often specialized) agents to accomplish a task through division of labor, separation of concerns, and parallelism — a composition of agents with a coordination structure. The appeal is real (like organizational division of labor), but so are the costs (below). The main patterns describe how the agents are organized.

## Common multi-agent patterns

Several recurring patterns describe how multiple agents are organized and coordinate — the main ones:

- **Orchestrator-workers (manager-workers).** A central *orchestrator* agent breaks the task into sub-tasks and delegates them to *worker* agents, then combines their results. The orchestrator plans and coordinates (like a manager); the workers execute sub-tasks (often specialized). This is one of the most common and useful patterns — a coordinator directing specialized workers — and it maps naturally to decomposition (the planning post): decompose the task, delegate the pieces, integrate the results. It's the "manager delegating to a team" structure.
- **Specialist agents.** Different agents *specialized* for different roles or capabilities (a research agent, a coding agent, a writing agent, a review agent), each expert at its part, invoked as needed. Specialization lets each agent be focused and effective at its role (with role-appropriate tools, prompts, context). Often combined with an orchestrator that routes work to the right specialist. Specialization is a core multi-agent idea.
- **Pipeline/sequential.** Agents arranged in a *sequence*, each doing a stage and passing to the next (agent A's output → agent B → agent C) — like an assembly line. Useful when the task has clear sequential stages, each suited to a specialized agent. (Note: a fixed sequence is really more of a *workflow* — from post one — than a dynamic multi-agent system; the line blurs.)
- **Collaborative/debate.** Multiple agents *collaborate* or *debate* — e.g. agents proposing and critiquing each other's work, or debating to reach a better answer (a generator and a critic, or multiple agents cross-checking). This leverages multiple perspectives and mutual critique (connecting to reflection — one agent reflecting on another's output). It can improve quality through diverse perspectives and checking.

These patterns — orchestrator-workers (a coordinator directing specialized workers, the most common), specialist agents (role-specialized experts), pipeline (sequential stages), and collaborative/debate (multiple perspectives, mutual critique) — are the main ways to organize multiple agents. Orchestrator-workers with specialists is a particularly common and useful combination. But whether to use multi-agent at all is the crucial question.

## When multi-agent helps — and when it hurts

The most important guidance is *when* multi-agent systems genuinely help versus when a single agent is better — because multi-agent adds significant cost and complexity that isn't always worth it:

- **Multi-agent helps when the task genuinely has separable parts.** Multi-agent shines when the task *naturally decomposes* into fairly independent sub-tasks that benefit from specialization or parallelism — where dividing among focused agents genuinely helps (e.g. researching many things in parallel, or distinct specialized stages). If the work truly benefits from division of labor, multi-agent can outperform a single agent. Genuine separability is the key indicator.
- **Multi-agent helps with focused contexts.** A real benefit: each agent has its *own focused context*, avoiding one agent's context being cluttered with everything (which can degrade performance and hit context limits — the memory post). Splitting work across agents with focused contexts can help on tasks too big/varied for one agent's context. Context management is a legitimate multi-agent motivation.
- **But multi-agent adds major cost and complexity.** The downsides are significant: *more LLM calls* (each agent, plus coordination = more cost/latency), *coordination overhead* (agents must communicate/coordinate, which is itself complex and error-prone), *harder debugging* (many interacting agents = complex, non-deterministic behavior), and *compounding errors* (one agent's mistake propagates). Multi-agent multiplies the challenges of single agents. It's a big step up in complexity and cost.
- **Prefer a single agent when it suffices.** The honest, restrained guidance (echoed by practitioners): *don't* jump to multi-agent by default — a single well-designed agent (with good tools, memory, reflection) handles many tasks, and is simpler, cheaper, and more reliable than a multi-agent system. Use multi-agent when the task *genuinely needs* it (real separability, specialization, parallelism, context benefits), not because it sounds sophisticated. Multi-agent is powerful for the right problems and overkill (or harmful) for the wrong ones. Reach for it deliberately, not reflexively.

Multi-agent helps when a task genuinely has separable parts benefiting from specialization, parallelism, or focused contexts — but it adds major cost, coordination overhead, debugging difficulty, and error propagation, so prefer a single well-designed agent unless the task genuinely needs multi-agent. This "don't over-engineer" guidance mirrors the whole series' "use the simplest thing that works." The overhead is the crux to weigh.

## Making multi-agent work

When multi-agent *is* warranted, a few principles help make it work — and reinforce the judicious-use theme:

- **Clear roles and responsibilities.** Each agent should have a *clear, focused role* and scope — well-defined responsibilities, so agents don't overlap confusingly or leave gaps. Clear division of labor (like a good org) is essential; muddled roles cause chaos. Design the "org chart" deliberately.
- **Well-defined coordination/communication.** How agents *coordinate* (an orchestrator directing, agents passing results, a shared state/memory) must be *well-defined* — coordination is where multi-agent complexity concentrates, so a clear, structured coordination mechanism is crucial. Ad-hoc, unclear coordination is a major failure source. Structure the communication.
- **Manage the cost.** Because multi-agent multiplies LLM calls, be deliberate about cost — use the right model for each agent (cheaper models for simpler roles), avoid unnecessary agents, and watch the total cost/latency (which can balloon). The economics (test-time-compute cost, from the reasoning series) apply strongly to multi-agent. Don't let agent count run away.
- **Consider simpler alternatives first.** Before a multi-agent system, ask whether a *single agent* with good design, or a *workflow* (fixed structure, from post one), would do — often it would, more simply. Multi-agent should be a considered choice for genuinely complex, separable tasks, after simpler approaches are ruled out. Start simple, escalate to multi-agent only when needed. This is the recurring "simplest thing that works" discipline.

Multi-agent patterns — orchestrator-workers, specialists, pipelines, and collaborative/debate — organize multiple agents for tasks with separable parts benefiting from specialization, parallelism, or focused contexts. But they add major cost and complexity, so use them judiciously (clear roles, structured coordination, cost management) and prefer a single well-designed agent or workflow when it suffices. Next, the final post: building reliable agents and when *not* to use agents at all.

## Key takeaways

- A multi-agent system uses multiple coordinated (often specialized) agents to accomplish a task through division of labor, separation of concerns, and parallelism — a composition of agents (each an LLM + tools + loop) with a coordination structure, motivated like organizational division of labor.
- The main patterns are orchestrator-workers (a coordinator decomposes and delegates to specialized workers, then integrates — the most common and useful), specialist agents (role-specialized experts, often with an orchestrator routing to them), pipeline/sequential (assembly-line stages — though a fixed sequence is really a workflow), and collaborative/debate (multiple perspectives and mutual critique).
- Multi-agent helps when a task genuinely has *separable* parts benefiting from specialization or parallelism, and when splitting gives each agent a *focused context* (avoiding one agent's context being cluttered — a real benefit given context limits).
- But multi-agent adds major downsides: more LLM calls (cost/latency), coordination overhead (complex and error-prone), harder debugging (many interacting non-deterministic agents), and compounding errors (one agent's mistake propagates) — it multiplies single-agent challenges.
- Prefer a single well-designed agent (or even a workflow) unless the task genuinely needs multi-agent — don't reach for it reflexively because it sounds sophisticated — and when it is warranted, use clear roles, well-defined coordination, and deliberate cost management (the recurring "use the simplest thing that works" discipline).

## Further reading

- [A Survey on Large Language Model based Autonomous Agents — multi-agent systems (Wang et al., 2023)](https://arxiv.org/abs/2308.11432)
- [Reflection and self-correction (previous post)](/blog/posts/agent-06-reflection-and-self-correction.html)
- [smolagents, Concept by Concept — a framework with multi-agent support](/blog/series/smolagents-concept-by-concept/)
