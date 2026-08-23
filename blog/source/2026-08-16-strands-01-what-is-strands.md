# What Is Strands Agents?

*Most agent frameworks ask you to design the workflow — the steps, the branches, the orchestration. Strands Agents, AWS's open-source SDK, makes the opposite bet: give the model a goal and tools, and let it drive. That model-driven philosophy is the whole point, and understanding it is understanding why Strands feels different from everything else.*

Strands Agents is an open-source agent SDK from AWS, built around a distinctive philosophy: the **model-driven approach**, where the LLM itself drives the agent loop rather than the developer hand-designing a workflow. This series covers Strands concept by concept; this first post establishes what it is, the model-driven bet that defines it, and how it contrasts with the workflow-first frameworks elsewhere in this blog's coverage. It's a framework whose identity is a *philosophy*, so start there.

## What Strands is

Strands Agents is an open-source SDK (Python and TypeScript) from AWS for building AI agents. You define an agent with three things — a **model**, a **system prompt**, and a set of **tools** — and the SDK runs the agent loop, letting the model reason and decide what to do. It's production-oriented (AWS uses it internally), model-agnostic (works across providers, not just AWS's), and includes built-in support for the Model Context Protocol (MCP), giving access to a large ecosystem of pre-built tools.

But the *what* matters less than the *how it thinks about agents*, because that's what sets Strands apart. Its defining choice is to keep the agent definition minimal — model, prompt, tools — and put the intelligence in the *model driving the loop*, not in developer-authored orchestration. That's the model-driven approach, and it's the lens for everything in this series.

## The model-driven approach

The central idea, and the reason Strands exists: **let the model drive the agent, rather than hard-coding the workflow.** In many agent frameworks, the developer designs the flow — this step, then that step, branch here, loop there — and the model fills in the pieces. Strands inverts this: you give the model a goal (system prompt), the capabilities to pursue it (tools), and let the *model* decide, at each step, whether to call a tool, keep reasoning, or return an answer. The developer defines *what the agent can do*; the model decides *what to do*.

This bet rests on a real trend: as models get more capable, they're increasingly good at *planning and deciding* on their own, so elaborate developer-authored orchestration becomes less necessary — and sometimes counterproductive, constraining a model that could plan better itself. Strands leans into that: trust the model to drive, keep the scaffolding minimal, and expose the loop so you can observe and control it without pre-scripting it. It's a deliberate wager that the model-driven approach ages *well* as models improve, whereas heavily hand-orchestrated frameworks may increasingly fight the model's own capabilities.

## Model-driven vs workflow-first

To place Strands, contrast it with the workflow-first end of the spectrum (which this blog covers in the LangGraph and other series):

- **Workflow-first** (e.g. graph-based orchestration) — the developer explicitly designs the flow: nodes, edges, state transitions, branches, loops. Maximum *control and predictability*; the model operates *within* a structure you define. Best when you need guaranteed sequencing, complex controllable flows, and determinism.
- **Model-driven** (Strands) — the developer defines the model, prompt, and tools; the *model* decides the flow dynamically. Maximum *simplicity and flexibility*; you trust the model's planning. Best when the task benefits from the model's own reasoning and you don't need to pre-script the path.

Neither is universally right — it's the autonomy-vs-control trade-off that runs through all agent design (and the [agent-framework comparison](/blog/posts/ai-decisions-02-agent-frameworks.html)). Strands sits firmly on the *autonomy* side: minimal scaffolding, model drives. If you've worked with workflow-first frameworks, Strands feels like removing the scaffolding and trusting the model — which is liberating when the model is capable enough and risky when it isn't (hence the reliability disciplines later in the series). Knowing where Strands sits on this spectrum is the key orientation.

## What Strands gives you

The pieces this series covers, all in service of the model-driven approach:

- **The agent loop** — model + system prompt + tools, with the model driving; the loop is exposed and observable, not hidden.
- **Tools** — Python functions (via decorators) the model can call, plus built-in tools and MCP support for a large tool ecosystem.
- **Model providers** — model-agnostic support across providers (Bedrock, Anthropic, and others), so the model is a swappable choice.
- **Multi-agent** — building systems of agents (agents as tools, and orchestration patterns) when one agent isn't enough.
- **Observability and production** — built-in observability (OpenTelemetry-based) and a production-oriented design, reflecting its AWS-internal-use origin.

These are deliberately lean — Strands doesn't give you a big orchestration DSL, because its philosophy is that you don't need one when the model drives. The framework is minimal on purpose.

## When to use Strands

Like any framework, it fits some situations better (the comparison series covers the broader choice):

- **Reach for Strands when** you want a minimal, model-driven agent framework that trusts the model to plan, when you value simplicity over elaborate orchestration, and when you're comfortable letting a capable model drive the loop. Its AWS origin and production focus make it a natural fit in AWS-centric environments, though it's model- and provider-agnostic.
- **Its philosophy shines** for agentic tasks where the model's own planning is an asset and pre-scripting the flow would only constrain it — exploratory, tool-using, reasoning-heavy tasks.
- **Consider workflow-first frameworks** (LangGraph) when you need explicit, controllable, stateful orchestration with guaranteed structure; **Pydantic AI** when type safety and structured outputs dominate; **CrewAI** for the multi-agent-team metaphor. Strands is the model-driven, minimal-scaffolding choice.

The through-line: Strands Agents is AWS's bet that the best agent framework gets *out of the model's way* — minimal definition, model drives, loop exposed. The next post goes deeper on that model-driven approach, which is the framework's soul.

## Key takeaways

- Strands Agents is AWS's open-source agent SDK (Python/TypeScript) built around the model-driven approach: define an agent with a model, system prompt, and tools, and the SDK runs a loop where the *model* decides what to do — production-oriented, model-agnostic, with built-in MCP support.
- Its defining bet is to let the model drive rather than hard-code the workflow: the developer defines what the agent *can* do (tools) and its goal (prompt), and the model decides what to do at each step — trusting the model's own planning.
- This wager ages with model capability: as models get better at planning, minimal scaffolding beats elaborate developer-authored orchestration that can constrain a capable model — whereas heavily hand-orchestrated frameworks may increasingly fight the model.
- Strands sits on the autonomy side of the autonomy-vs-control spectrum: model-driven (simplicity, flexibility, trust the model) versus workflow-first like LangGraph (control, predictability, explicit flow) — neither universally right.
- Choose Strands for minimal, model-driven agents where the model's planning is an asset (and you're comfortable trusting it); choose workflow-first for controllable stateful orchestration, Pydantic AI for type safety, or CrewAI for multi-agent teams.

## Further reading

- [Strands Agents documentation](https://strandsagents.com/)
- [Strands Agents and the model-driven approach (AWS Open Source Blog)](https://aws.amazon.com/blogs/opensource/strands-agents-and-the-model-driven-approach/)
- [AI Architecture Decisions: choosing an agent framework](/blog/posts/ai-decisions-02-agent-frameworks.html)
