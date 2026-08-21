# Agents: Role, Goal, and Backstory

*A CrewAI agent is defined less by code than by three sentences — its role, goal, and backstory — and getting those right is the highest-leverage thing you do, because they are the prompt that shapes everything the agent does.*

The agent is CrewAI's fundamental unit, and its definition is deceptively simple: a role, a goal, and a backstory. Those three fields are not decoration — they are how you program the agent's behavior, because CrewAI turns them into the prompt that governs how it reasons and communicates. This second post in the CrewAI series covers agents and how to define them well.

## The role/goal/backstory model

An agent is an autonomous, LLM-powered worker characterized by three things:

- **Role** — who the agent is ("Senior Financial Analyst"). It sets the persona and the lens the agent brings.
- **Goal** — what the agent is trying to achieve ("produce accurate, sourced analysis of a company's filings"). It orients every decision the agent makes.
- **Backstory** — the context that shapes how the agent reasons and communicates ("a meticulous analyst with a decade in equity research who never states a number without a source"). It fills in tone, priorities, and behavioral tendencies.

```python
from crewai import Agent

analyst = Agent(
    role="Senior Financial Analyst",
    goal="Produce accurate, well-sourced analysis of a company's filings",
    backstory=(
        "A meticulous analyst with years in equity research. You never state "
        "a figure without citing its source, and you flag uncertainty plainly."
    ),
)
```

These fields are effectively the agent's system prompt, so treat them with the care you'd give any prompt: specific, honest, and aligned with what you actually want. A vague role ("Assistant") and goal ("help the user") produce vague behavior; a precise role, a concrete goal, and a backstory that encodes your real priorities produce an agent that behaves the way you intend. This is where most of an agent's quality is won.

## Why the backstory matters more than it looks

The backstory is the field newcomers under-use, and it's often the most impactful. Because it shapes *how* the agent reasons and communicates, it's where you encode the behavior you care about — rigor, concision, caution, a house style, a refusal to speculate. "You always verify before asserting and say 'I'm not certain' when the evidence is thin" in a backstory does more for reliability than a dozen instructions bolted on later. Think of role and goal as *what* the agent is for, and backstory as *how* it should go about it — and spend real effort on the how.

## Configuring the agent

Beyond the three defining fields, agents take configuration that controls their behavior and capabilities:

- **`llm`** — which model powers the agent. CrewAI is model-agnostic (via litellm), so you can point different agents at different models — a cheaper model for a simple role, a stronger one for hard reasoning, which is a direct cost lever (right-sizing the model to the task).
- **`tools`** — the capabilities the agent can use (covered in the tools post). An agent with the right tools can act; without them it can only reason and write.
- **`allow_delegation`** — whether the agent can hand work to other agents in the crew. Enabling delegation lets agents collaborate and ask each other for help; disabling it keeps an agent focused on its own task. This is a key knob for how much the crew behaves as a team versus a pipeline.
- **Other controls** — limits like max iterations and verbosity that bound how hard an agent tries and how much it narrates, useful for cost and debugging.

The important one to understand is `allow_delegation`, because it changes the crew's dynamics: with delegation on, an agent that hits something outside its expertise can route it to a better-suited teammate; with it off, each agent sticks to its lane. Choose deliberately based on whether you want genuine collaboration or a predictable division of labor.

## Right-size the model per agent

A practical point that ties agents to cost: because each agent can have its own `llm`, you don't have to run your whole crew on an expensive frontier model. Assign a small, cheap model to the straightforward roles (formatting, simple extraction, routing) and reserve the strong model for the roles that genuinely need deep reasoning. In a multi-agent system this per-agent model choice is one of the biggest cost levers available, and CrewAI makes it a one-line decision. The [AI Cost Optimization](/blog/series/ai-cost-optimization/) discipline — right-size the model to the task — applies directly at the agent level here.

## Agents are only half the story

An agent on its own does nothing — it needs *work* to do. In CrewAI, that work is a **task**, and the pairing of a well-defined agent with a well-defined task is what actually produces output. A common newcomer mistake is pouring all the specificity into the agent and leaving the task vague, or vice versa; they work together, and both need to be precise. The next post is about tasks — how to describe the work and its expected output so a good agent produces exactly what you need.

## Key takeaways

- A CrewAI agent is defined by three fields — role (who it is), goal (what it's for), and backstory (how it reasons and communicates) — which together form the agent's system prompt.
- Treat role/goal/backstory like any prompt: specific and honest; vague definitions produce vague behavior, and this is where most of an agent's quality is decided.
- The backstory is the under-used, high-impact field — encode the behavior you care about (rigor, concision, caution, house style) there.
- Configure agents with `llm` (model-agnostic — right-size per agent as a cost lever), `tools` (capabilities), and `allow_delegation` (whether agents collaborate vs stay in their lane).
- Agents need tasks to do anything; define both precisely — the agent-plus-task pairing is what produces output.

## Further reading

- [CrewAI documentation](https://docs.crewai.com)
- [AI Cost Optimization series](/blog/series/ai-cost-optimization/)
- [CrewAI, Concept by Concept — start of the series](/blog/posts/crewai-01-what-is-crewai.html)
