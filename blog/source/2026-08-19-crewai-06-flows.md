# Flows: Event-Driven Orchestration

*Crews give agents autonomy, which is powerful and unpredictable; Flows give you back deterministic control — an event-driven engine where you decide exactly what runs when, with crews slotted in only where autonomy is actually wanted.*

Crews are autonomous: you describe a team and it collaborates, with the LLM driving decisions. That's the right model when you *want* emergent behavior, but production often needs the opposite — precise, reliable, repeatable control over the sequence. CrewAI's answer is **Flows**: an event-driven orchestration layer where you, not the LLM, decide the control flow. This sixth post in the CrewAI series covers Flows and how they complement crews.

## What a Flow is

A Flow is a Python class that wraps your crews and direct LLM calls inside an event-driven execution engine. You write methods and decorate them to declare *when* they run; CrewAI handles the execution order, threads state between them, and can persist that state. The core decorators:

- **`@start()`** — marks an entry point that runs when the flow begins.
- **`@listen(...)`** — marks a method that runs *when another method completes*, receiving its output. This is how you chain steps.
- **`@router(...)`** — marks a branching point that decides which path to take next, enabling conditional flows.

```python
from crewai.flow.flow import Flow, start, listen

class ReportFlow(Flow):
    @start()
    def gather(self):
        return fetch_source_data()

    @listen(gather)
    def analyze(self, data):
        return analysis_crew.kickoff(inputs={"data": data})

    @listen(analyze)
    def publish(self, analysis):
        return save_report(analysis)
```

You declared the flow — gather, then analyze, then publish — explicitly. The engine runs it in that order, passing each step's output to the next. This is *deterministic* orchestration: the sequence is code you control, not a decision the LLM makes.

## Why Flows exist: control where crews are too autonomous

Crews trade control for autonomy, and sometimes that trade is wrong. If your workflow has a required sequence — fetch data, then run analysis, then validate, then publish — you don't want an autonomous crew *deciding* whether to skip validation; you want that step to run, every time, in that order. Flows give you exactly that: explicit, reliable control flow, with branching (`@router`) for real conditional logic and state threading so each step has what it needs.

This is the same control-vs-autonomy dial from the process post, lifted to a higher level. Within a crew, the process dials autonomy; across a whole workflow, Flows give you the deterministic-control end of the dial. When reliability and predictability matter — which in production they usually do — Flows are how you get them while still using agents.

## Crews inside Flows: the best of both

The key architectural pattern is that **Flows and crews compose** — a Flow can call crews as steps. You use the Flow for the deterministic backbone (the required sequence, the branching, the state) and drop a crew into the specific steps that genuinely benefit from autonomous, collaborative reasoning. In the example above, `analyze` runs a crew, while the surrounding fetch/publish are plain deterministic steps.

This composition is CrewAI's most powerful shape, and it resolves the whole autonomy tension. You don't have to choose between "fully autonomous crew" and "rigid pipeline." You build a deterministic Flow for the parts that must be reliable and repeatable, and reserve crew autonomy for the parts where letting agents figure it out actually adds value. Most robust production CrewAI systems are Flows orchestrating crews, not bare crews.

## State and persistence

Flows thread **state** between steps, so a later method can use what earlier ones produced — and that state can be **persisted**, which matters for long-running or resumable workflows. Persistence means a flow can survive interruptions and pick up where it left off, rather than restarting from scratch — important for workflows that span time, wait on external events, or must be durable. Designing what lives in the flow's state (and keeping it lean) is part of building a good flow, much like managing any workflow's context.

## Choosing: crew, flow, or both

The decision that this post enables:

- **A bare crew** — when the task is genuinely collaborative and you want the agents to figure out the approach, and predictability isn't critical.
- **A Flow** — when you need deterministic, reliable control over a sequence, branching, or resumable state, with plain LLM calls or logic as steps.
- **A Flow orchestrating crews** — the common production answer: a deterministic backbone with crew autonomy dropped into the steps that need it.

The instinct to reach for as you mature with CrewAI: default to a Flow for anything production-facing that has a required sequence, and use crews *within* it for the collaborative parts. That gives you reliability where you need it and autonomy where it helps — which is exactly the balance production systems want.

## Key takeaways

- A Flow is a Python class that wraps crews and LLM calls in an event-driven engine; you decorate methods with `@start` (entry), `@listen` (run when another completes), and `@router` (branch) to declare deterministic control flow.
- Flows exist to give back the control crews trade away: when a workflow has a required sequence or conditional logic, you want it to run reliably, not have an autonomous crew decide.
- Flows and crews compose — a Flow provides the deterministic backbone and calls crews for the specific steps that benefit from autonomous, collaborative reasoning; this is CrewAI's most powerful shape.
- Flows thread and can persist state, enabling long-running, resumable, durable workflows that survive interruptions.
- Choose a bare crew for genuinely collaborative, non-critical tasks; a Flow for deterministic control; and (usually, in production) a Flow orchestrating crews for reliability plus autonomy where each is warranted.

## Further reading

- [CrewAI documentation](https://docs.crewai.com)
- [crewAIInc/crewAI on GitHub](https://github.com/crewAIInc/crewAI)
- [CrewAI, Concept by Concept — start of the series](/blog/posts/crewai-01-what-is-crewai.html)
