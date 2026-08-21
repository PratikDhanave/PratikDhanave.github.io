# Tasks: Describing the Work

*An agent is a capability; a task is the assignment — and the two fields that define a task, its description and its expected output, are where you turn "a smart agent" into "the specific result I need."*

If an agent is *who* does the work, a task is *what* the work is. Tasks are how you translate a goal into a concrete, checkable assignment, and the discipline of describing them well — especially their expected output — is what makes a crew produce what you actually wanted rather than something plausible-but-off. This third post in the CrewAI series covers tasks.

## What a task is

A task is a specific assignment given to an agent, defined primarily by two fields:

- **`description`** — what to do, in detail. This is the instruction the agent acts on.
- **`expected_output`** — what a good result looks like. This tells the agent (and you) what "done" means.

```python
from crewai import Task

research = Task(
    description=(
        "Research the top regulatory changes affecting {industry} this year. "
        "Focus on changes that take effect within 12 months."
    ),
    expected_output=(
        "A markdown list of 3-5 changes. For each: the rule, its effective date, "
        "and one sentence on its impact. Cite a source for each."
    ),
    agent=researcher,
)
```

The task is assigned to an agent (`agent=`), or in a hierarchical crew left for the manager to delegate. A crew is fundamentally a set of these tasks, executed in an order determined by its process.

## expected_output is the field that decides quality

The single most important habit with CrewAI tasks: **write a precise `expected_output`.** Because LLM agents will happily produce *something*, the difference between a useful result and a vague one is usually how clearly you specified what the output should be. "A summary" gets you an unpredictable blob; "a markdown list of exactly 5 items, each under 20 words, with a source URL" gets you something consistent and usable downstream.

`expected_output` does double duty. It steers the agent toward the right shape, and it gives you a checkable definition of done — a specification you can evaluate against. Treat it the way you'd treat an API response schema: the more precisely you define the shape, the more reliably you get it. This is the task-level version of the constrained-output discipline that runs through good AI engineering.

## Passing data in and structuring data out

Tasks aren't static text. Two mechanisms make them dynamic and reliable:

- **Inputs.** Descriptions can use `{placeholders}` filled at runtime via `crew.kickoff(inputs={...})`, so the same task template runs on different data — `{industry}` above becomes "fintech" or "healthcare" per run.
- **Structured output.** When you need machine-readable results rather than prose, a task can produce structured output — for example a Pydantic model — so downstream code gets typed, validated data instead of parsing free text. This is the reliable way to chain a task's result into subsequent tasks or into your own code, and it's far better than asking for JSON in the description and hoping.

Structured output is worth reaching for whenever a task's result feeds something automated. It turns "the agent usually returns roughly the right shape" into "the result is a validated object," which is the difference between a demo and a system.

## Context: tasks building on tasks

Tasks in a crew rarely stand alone — later tasks build on earlier ones. CrewAI lets a task receive the output of previous tasks as **context**, so a "write the report" task can consume the "research the topic" task's findings. This is how a sequential crew forms a pipeline: research → analyze → write, each task grounded in the last. Designing that context flow deliberately — which prior outputs each task needs — is part of designing a good crew, and it keeps each agent focused on its step with exactly the inputs it requires rather than the whole history.

## Task design principles

A few habits separate crews that work from crews that flail:

- **One clear job per task.** A task that tries to do three things gets a muddled result; split it. Narrow tasks are easier for an agent to nail and easier for you to evaluate.
- **Specify the output precisely.** As above — the `expected_output` is your lever on consistency and your definition of done.
- **Match the task to the agent.** A task's demands should fit the assigned agent's role and tools; a research task for a "writer" agent with no search tool will struggle.
- **Use structured output when the result is consumed by code.** Prose for humans, typed objects for pipelines.

Get these right and the crew's behavior becomes predictable; get them wrong and you'll be debugging vague outputs with no clear notion of what "correct" even was.

## Key takeaways

- A task is a specific assignment defined by a `description` (what to do) and an `expected_output` (what a good result looks like), assigned to an agent.
- `expected_output` is the highest-leverage field — precise output specs turn unpredictable blobs into consistent, usable, evaluable results; treat it like a response schema.
- Pass runtime data via `{placeholders}` filled by `crew.kickoff(inputs=...)`, and use structured output (e.g. Pydantic) when results feed code, rather than asking for JSON and hoping.
- Tasks build on each other via context — a task can consume prior tasks' outputs — which is how a sequential crew forms a research → analyze → write pipeline.
- Design tasks with one clear job each, precise outputs, a good agent-task match, and structured output where results are machine-consumed.

## Further reading

- [CrewAI documentation](https://docs.crewai.com)
- [CrewAI, Concept by Concept — start of the series](/blog/posts/crewai-01-what-is-crewai.html)
- [Context Engineering series](/blog/series/context-engineering/)
