# Multi-Agent Systems

*One model-driven agent handles a lot, but some problems want a team — a specialist per subtask, or a coordinator delegating to workers. Strands builds multi-agent systems from the same minimal parts, most elegantly by making an agent a tool another agent can call, so the model-driven approach scales up without new machinery.*

A single agent has limits — too many tools, too broad a scope, or genuinely separable subtasks. **Multi-agent systems** address this by composing several agents. This post covers how Strands does multi-agent, centered on its most characteristic pattern (agents as tools), plus the orchestration patterns available, and — importantly — when multi-agent is worth it versus a single agent. It's the model-driven approach scaled from one agent to many.

## When one agent isn't enough

Before *how*, the *when*, because multi-agent adds complexity and is often reached for too early. A single model-driven agent is capable, and you should prefer it until a specific limit forces more:

- **Too many tools** — an agent with too many tools chooses poorly among them (the tool-selection reliability issue). Splitting capabilities across focused agents keeps each agent's tool set small and its choices reliable.
- **Separable subtasks with different expertise** — when a task decomposes into genuinely distinct sub-problems (research, then writing, then review), a specialist agent per sub-problem (with its own prompt and tools) can outperform one generalist juggling everything.
- **Scope too broad for one prompt** — when the guidance one agent needs is too much for a single coherent system prompt, splitting into focused agents keeps each prompt clear.

The discipline (echoing the CrewAI and multi-agent lessons): **prefer a single agent until a real limit forces multi-agent.** Multi-agent multiplies cost (more model calls), latency, and failure modes, so it must earn its place. When it does, Strands offers a few composition patterns.

## Agents as tools: the characteristic pattern

Strands's most elegant multi-agent pattern falls straight out of the model-driven design: **an agent can be a tool that another agent calls.** Because a Strands agent is invoked like a function and a tool is just a function, you can wrap an agent *as a tool* and give it to another agent:

```text
Coordinator agent
  tools: [ research_agent (as a tool), writer_agent (as a tool), calculator ]
    → the coordinator's model decides to call research_agent, then writer_agent,
      just as it would call any tool
```

This is beautifully consistent with everything prior: the coordinator is a normal model-driven agent, and the specialist agents are just tools in its toolset. The coordinator's model *drives* — deciding when to delegate to which sub-agent — exactly as it decides when to call any tool (the tools post). No new orchestration machinery is needed; multi-agent is *composition of agents through the tool interface*, and the model-driven loop handles the coordination. This is the model-driven approach scaling up: the coordinator model plans the delegation the same way a single agent plans tool use.

The benefits mirror the single-agent tool lessons: each specialist agent has a *focused* tool set and prompt (reliable, expert), and the coordinator sees them as a *few clear tools* (reliable delegation). It's the "few, well-described tools" discipline applied at the agent level — specialists as clean, described capabilities the coordinator draws on.

## Other orchestration patterns

Beyond agents-as-tools, Strands supports patterns for different multi-agent shapes (the framework provides primitives for these):

- **Hierarchical / coordinator-worker** — a coordinator delegates to worker agents (the agents-as-tools pattern above), suited to tasks that decompose into subtasks a lead assigns.
- **Sequential / pipeline** — agents in a chain, each handling a stage and passing to the next, for tasks with distinct ordered phases.
- **Swarm / collaborative** — multiple agents working together on a shared problem, for tasks benefiting from parallel or collaborative effort.
- **Graph-based** — for more explicit multi-agent orchestration where you want defined structure among agents.

The choice among these mirrors the single-vs-multi and autonomy-vs-control themes: agents-as-tools (coordinator delegates dynamically) is the most model-driven (the coordinator's model decides delegation), while more structured patterns (sequential, graph) add explicit control over how agents interact. Strands, true to its philosophy, makes the model-driven delegation (agents-as-tools) the natural default, with more structured patterns available when you need defined multi-agent flow — the same "structure where you need predictability, autonomy where you need flexibility" balance, now at the agent-composition level.

## Keeping multi-agent reliable (and worth it)

Multi-agent amplifies both capability and the failure modes, so the disciplines matter more:

- **Cost multiplies** — each agent is model calls, and a coordinator calling several sub-agents (each running its own loop) can be expensive; the cost-playbook levers (caching, model selection per agent, bounded loops) apply per agent, and you should measure whether the multi-agent system's results justify its multiplied cost.
- **Latency compounds** — sequential agent calls add up; parallelize where the pattern allows (swarm), and prefer a single agent when the latency of coordination isn't justified.
- **Failure modes multiply** — more agents mean more places to fail; bound each agent's loop, handle inter-agent errors, and observe the whole system (which agent did what) — observability matters even more with multiple model-driven agents.
- **Right-size each agent's model** — a coordinator and specialists may warrant *different* models (a capable coordinator, cheaper specialists for narrow tasks) — the model-selection lever applied per agent, cutting cost without cutting capability where it matters.

The overarching guidance: **multi-agent is powerful but earns its complexity only when a single agent genuinely can't do the job** — and when it does, keep each agent focused, right-size its model, bound its loop, and observe the whole. Strands makes composing agents natural (agents-as-tools), but naturalness isn't a reason to over-decompose; a well-equipped single agent beats a needlessly fragmented team. The next post covers observing and operating all of this — Strands's observability and production story.

## Key takeaways

- Prefer a single model-driven agent until a real limit forces multi-agent: too many tools (poor selection), separable subtasks needing different expertise, or scope too broad for one coherent prompt — because multi-agent multiplies cost, latency, and failure modes.
- Strands's characteristic pattern is agents-as-tools: because an agent is invoked like a function and a tool is a function, you wrap a specialist agent as a tool for a coordinator agent, whose model drives the delegation exactly as it drives any tool call — no new orchestration machinery.
- This is the model-driven approach scaled up: the coordinator plans delegation the way a single agent plans tool use, with specialists as focused, well-described capabilities — the "few well-described tools" discipline at the agent level.
- Other patterns (hierarchical/coordinator-worker, sequential/pipeline, swarm/collaborative, graph-based) suit different shapes; agents-as-tools is the most model-driven default, with structured patterns adding explicit control when you need defined multi-agent flow.
- Multi-agent amplifies capability and failure modes: cost and latency multiply (measure whether results justify them), failures multiply (bound loops, handle inter-agent errors, observe the whole), and right-size each agent's model (capable coordinator, cheaper specialists) — it earns its complexity only when a single agent genuinely can't do the job.

## Further reading

- [Model providers (previous post)](/blog/posts/strands-05-model-providers.html)
- [CrewAI, Concept by Concept — the multi-agent-team metaphor](/blog/series/crewai-concept-by-concept/)
- [Strands Agents documentation — multi-agent](https://strandsagents.com/)
