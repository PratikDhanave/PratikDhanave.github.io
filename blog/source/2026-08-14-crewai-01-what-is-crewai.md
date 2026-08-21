# What Is CrewAI?

*CrewAI takes the most intuitive metaphor for multi-agent AI — a team of specialists with roles collaborating on a job — and makes it the programming model, which is both its great strength and the thing to be disciplined about.*

Of the popular agent frameworks, CrewAI is the one with the most human metaphor: you assemble a *crew* of agents, each with a role, and give them work, the way you'd staff a project. That high-level, role-based model makes CrewAI fast to pick up and expressive for collaborative workflows. This series builds CrewAI up concept by concept; this first post covers what it is, its philosophy, and when its approach fits.

## The core metaphor: a crew of specialists

CrewAI's organizing idea is that multi-agent AI should mirror how human teams work. You define **agents** — each an LLM-powered worker with a *role* ("Senior Researcher"), a *goal*, and a *backstory* that shapes how it reasons and communicates. You define **tasks** — specific assignments with expected outputs. And you assemble them into a **crew** that executes the tasks according to a **process** (in order, or with a manager delegating). The mental model is a small team: specialists with defined roles, each handed work, collaborating toward an outcome.

This is the highest-level, most opinionated abstraction among the major frameworks. Where LangGraph asks you to draw an explicit control-flow graph, CrewAI asks you to describe *who's on the team and what they should do*, and handles the orchestration. That trade — convenience and speed over low-level control — is CrewAI's defining characteristic, and the [agent-framework comparison](/blog/posts/ai-decisions-02-agent-frameworks.html) elsewhere on this blog places it precisely on that spectrum.

## Crews and Flows: two execution models

Modern CrewAI has two complementary ways to run agents, and understanding the split early prevents a lot of confusion:

- **Crews** are the autonomous, collaborative model — agents with roles work through tasks, with the LLM driving decisions. Best when you want emergent collaboration and are comfortable with the agents having latitude.
- **Flows** are the event-driven, *deterministic* orchestration model — a Python class where you decorate methods with `@start`, `@listen`, and `@router` to control execution order, thread state, and persist it. Best when you need precise, reliable control over the sequence, and you can even run Crews *inside* Flows.

The useful framing: Crews give you agent autonomy; Flows give you deterministic control; and real systems combine them — a Flow orchestrating the overall process, with Crews handling the parts that genuinely need collaborative reasoning. Later posts cover each in depth; know now that CrewAI is not just "autonomous crews," it's crews *and* structured flows.

## Model-agnostic and standalone

Two practical facts shape adoption. CrewAI is **model-agnostic** — through its litellm integration it works with essentially every major provider (OpenAI, Anthropic, Gemini, Bedrock, Azure, Groq, and local models via Ollama), so you're not tied to one vendor and can keep the model swappable, exactly as good architecture demands. And it is **standalone** — a lean framework in its own right, not a layer on top of another agent library. That independence keeps it focused and reduces the dependency surface, which matters when you're deciding what to build a system on.

## A first crew

The smallest CrewAI program shows the shape — agents, a task, a crew, and `kickoff()`:

```python
from crewai import Agent, Task, Crew, Process

researcher = Agent(
    role="Market Researcher",
    goal="Find and summarize the key trends in a given industry",
    backstory="A meticulous analyst who values sources and concision.",
)

research = Task(
    description="Research the top trends in {industry} for this quarter.",
    expected_output="A concise bullet list of 5 trends, each with a source.",
    agent=researcher,
)

crew = Crew(agents=[researcher], tasks=[research], process=Process.sequential)
result = crew.kickoff(inputs={"industry": "fintech"})
```

Notice what you *didn't* write: no control-flow graph, no manual orchestration. You described a specialist and its assignment, and the crew ran it. Add more agents and tasks and CrewAI coordinates them according to the process — that's the productivity CrewAI is designed for.

## When CrewAI fits — and the discipline it needs

CrewAI shines when your problem maps naturally onto a *team of roles* collaborating — research-then-write-then-review, or a set of specialists each owning a piece of a larger job — and you want to get from idea to a working multi-agent system fast. Its role/goal/backstory model is genuinely good at expressing that, and Flows add the deterministic control for the parts that need it.

The discipline it needs is the same caveat that governs all agent frameworks: **most tasks need far less agentic machinery than the framework makes it easy to add.** Because CrewAI makes spinning up a five-agent crew trivial, it's tempting to build a crew where a single well-engineered call would do better, cheaper, and more reliably — end-to-end reliability drops roughly as `pⁿ` over `n` steps and cost scales with agent count. The [AI Production Roadmap](/blog/series/the-ai-production-roadmap/) rule holds: prefer the simplest architecture that meets the requirement, and let multi-agent complexity earn its keep. CrewAI's ease is a feature; treat it as a reason to be *more* deliberate about when a crew is actually warranted, not less.

## Where the series goes

From here we go concept by concept: agents (role, goal, backstory), tasks (describing work and its expected output), crews and process types (sequential, hierarchical), tools (giving agents capabilities), Flows (event-driven deterministic orchestration), memory and collaboration, and running CrewAI in production. By the end you'll be able to build role-based multi-agent systems in CrewAI — and know when to reach for a crew, a flow, or just a single call.

## Key takeaways

- CrewAI models multi-agent AI as a team of specialists: agents with a role, goal, and backstory work through tasks, assembled into a crew that runs them by a process.
- It's the highest-level, most opinionated of the major frameworks — you describe the team and the work, and it handles orchestration, trading low-level control for speed and expressiveness.
- Two execution models: Crews (autonomous, collaborative) and Flows (event-driven, deterministic via `@start`/`@listen`/`@router`); real systems combine them (Flows orchestrating, Crews for collaborative parts).
- It's model-agnostic (via litellm — keep the model swappable) and standalone (lean, not built on another agent library).
- CrewAI fits problems that map onto a team of roles and gets you to a working system fast — but its ease makes it critical to apply the "simplest architecture wins" discipline (reliability ≈ pⁿ) and use a crew only when it earns its keep.

## Further reading

- [CrewAI documentation](https://docs.crewai.com)
- [crewAIInc/crewAI on GitHub](https://github.com/crewAIInc/crewAI)
- [Choosing an Agent Framework (MAF vs LangGraph vs ADK vs CrewAI)](/blog/posts/ai-decisions-02-agent-frameworks.html)
