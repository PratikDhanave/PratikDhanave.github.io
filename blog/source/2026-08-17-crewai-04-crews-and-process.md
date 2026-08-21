# Crews and Process

*Agents and tasks are the pieces; the crew is what assembles them into a working team, and its process — sequential or hierarchical — decides whether they run like an assembly line or a delegating manager.*

A crew brings agents and tasks together and runs them. The one decision that most shapes how a crew behaves is its **process** — the execution strategy that determines who does what, in what order, and whether a manager coordinates. This fourth post in the CrewAI series covers assembling crews and choosing a process.

## Assembling a crew

A crew is agents plus tasks plus a process:

```python
from crewai import Crew, Process

crew = Crew(
    agents=[researcher, analyst, writer],
    tasks=[research_task, analysis_task, writing_task],
    process=Process.sequential,
)
result = crew.kickoff(inputs={"industry": "fintech"})
```

`kickoff()` runs the crew and returns the result (with runtime inputs filling any `{placeholders}` in the tasks). The `process` is the strategy for *how* those tasks get executed across those agents — and it's the choice that changes everything about the crew's dynamics.

## Sequential: the assembly line

The **sequential** process runs tasks in order, each task's output flowing as context into the next. Research → analyze → write: the researcher's findings feed the analyst, whose analysis feeds the writer. It's the simplest, most predictable process — a clear pipeline where you know exactly what runs when.

Sequential is the right default for most crews. It's easy to reason about, easy to debug (you can see each step's output), and maps onto the many workflows that really are a pipeline of stages. Reach for something more elaborate only when your problem genuinely isn't a straight line.

## Hierarchical: a manager delegates

The **hierarchical** process introduces a **manager** agent that coordinates the others. Instead of a fixed order, the manager decides how to delegate tasks to worker agents, reviews their output, and drives toward the goal — much like a team lead assigning work and integrating results. CrewAI can use a manager agent (or a manager LLM you specify) to run this coordination.

Hierarchical suits problems where the right sequence isn't known up front, or where a coordinator adds value by deciding who handles what and validating results. The trade is cost and predictability: the manager is extra LLM calls and reasoning, and because it decides dynamically, the flow is less deterministic than sequential. Use hierarchical when the coordination is genuinely worth it — a complex job where an intelligent delegator beats a fixed pipeline — not as a default.

## Consensual and beyond

CrewAI also describes a **consensual** process, where agents collaborate more democratically (for example, weighing in on decisions) rather than following a fixed order or a single manager. Treat process types as a spectrum from fully deterministic (sequential) to more autonomous and collaborative (hierarchical, consensual): the more autonomy you give the crew, the more adaptive it can be *and* the less predictable and more expensive it becomes. Pick the least-autonomous process that meets your need — determinism is a feature, and you give it up only when the problem demands adaptivity.

## Process is the autonomy dial

The unifying idea: the process is a dial between control and autonomy. **Sequential** is maximum control — you defined the order, it runs it. **Hierarchical** hands the ordering to a manager agent — more adaptive, less predictable, more costly. More autonomous processes trade your control for the crew's ability to figure things out. Where you set that dial should follow the task: a well-understood pipeline wants sequential; a genuinely open-ended coordination problem might justify hierarchical. And this dial is exactly why CrewAI added **Flows** — when you want deterministic orchestration *around* your crews rather than within them, Flows give you explicit control at a higher level, which the Flows post covers.

## Crews and the complexity caveat

Because a crew makes it trivial to add another agent and another task, it's worth restating the discipline: more agents and a more autonomous process multiply cost and reduce reliability (end-to-end success roughly `pⁿ` over `n` steps). A three-agent sequential crew is often the sweet spot for genuinely multi-step collaborative work; a ten-agent hierarchical crew for a task a single well-prompted agent could handle is the anti-pattern. Design the crew to be as small and as deterministic as the problem allows, and let extra agents or extra autonomy earn their place with measured results — the [AI Production Roadmap](/blog/series/the-ai-production-roadmap/) principle, applied to crew design.

## Key takeaways

- A crew is agents + tasks + a process, run with `kickoff()`; the process is the decision that most shapes the crew's behavior.
- Sequential runs tasks in order with each output feeding the next (an assembly-line pipeline) — the simplest, most predictable, and the right default for most crews.
- Hierarchical adds a manager agent that dynamically delegates to workers and reviews results — more adaptive for open-ended coordination, but more costly and less deterministic.
- Process is an autonomy dial from deterministic (sequential) to autonomous/collaborative (hierarchical, consensual); pick the least-autonomous process that meets the need, since determinism is a feature.
- Keep crews small and as deterministic as the problem allows — more agents and more autonomy multiply cost and cut reliability (≈ pⁿ); use Flows when you want deterministic orchestration around crews.

## Further reading

- [CrewAI documentation](https://docs.crewai.com)
- [The AI Production Roadmap series](/blog/series/the-ai-production-roadmap/)
- [CrewAI, Concept by Concept — start of the series](/blog/posts/crewai-01-what-is-crewai.html)
