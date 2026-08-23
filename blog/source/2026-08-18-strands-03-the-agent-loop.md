# The Agent Loop

*Strands's agent loop is deliberately small: a prompt goes in, the model decides, tools run if needed, results feed back, and it repeats until the model is done. What makes it distinctive isn't the loop's shape — every agent has one — but that Strands exposes it plainly and lets the model drive it, with only three ingredients you provide.*

The last posts covered the model-driven *philosophy*; this one makes it concrete with the **agent loop** — the actual mechanism by which a Strands agent runs. It's simple by design, which is the point: three ingredients (model, system prompt, tools) and a loop the model drives. Understanding the loop is understanding how the model-driven approach becomes a running agent.

## The three ingredients

A Strands agent is defined by exactly three things, and their minimalism is deliberate:

- **A model** — the LLM that does the reasoning and drives the loop (model-agnostic; the models post covers providers).
- **A system prompt** — the agent's goal, guidance, and constraints. In a model-driven agent this is much of the "programming" (the last post), because it shapes how the model drives.
- **A set of tools** — the capabilities the model can invoke to act and observe (the tools post).

```python
# Illustrative shape — see the Strands docs for exact API.
from strands import Agent

agent = Agent(
    model="...",                       # the LLM
    system_prompt="You are a research assistant that ...",
    tools=[search, fetch_page, calculate],
)
result = agent("Find the population of the three largest EU cities.")
```

That's the whole agent: model, prompt, tools. There's no workflow graph to define, no orchestration DSL — because the *model* provides the orchestration by driving the loop. This minimalism is the model-driven philosophy made concrete: you supply the ingredients, the model does the cooking.

## The loop

Given those ingredients, the agent loop is straightforward, and Strands exposes it plainly:

```text
1. User prompt goes to the model (with the system prompt and available tools)
2. The model decides: call a tool, or return a final answer?
3. If a tool call → Strands runs the tool → the result feeds back to the model
4. The model observes the result and decides again (another tool? done?)
5. Repeat until the model returns a final answer
```

This is the standard think-act-observe loop (the ReAct pattern from the agent and RAG series), but with the model-driven emphasis: **the model decides at every step what to do next** — there's no developer-authored control flow choosing the path. The model looks at the goal, the tools, and what's happened so far, and decides: reason more, call this tool, or finish. Strands runs the tools the model asks for and feeds results back, and the loop continues until the model itself decides it's done.

Two things make this distinctively Strands. First, **the loop is exposed, not hidden** — you can observe each step (the model's decisions, the tool calls, the results), which matters because in a model-driven agent you supervise the loop rather than script it (the observability point). Second, **the model owns the control flow** — the branching, looping, and stopping are the model's decisions, not code you wrote. The loop is the same shape as any agent's; what's different is *who drives it* (the model) and *how visible it is* (fully).

## Why minimal ingredients are enough

It's worth appreciating *why* three ingredients suffice, because it's the model-driven bet in action. In a workflow-first framework, you'd additionally define the flow — but Strands doesn't need that, because the flow *emerges* from the model reasoning over the goal and tools:

- **The goal (prompt) tells the model what to achieve** — so it can plan toward it without a pre-written plan.
- **The tools tell the model what it can do** — so it can choose actions without a pre-written decision tree.
- **The model's reasoning supplies the rest** — the sequencing, the branching, the adaptation, the stopping — dynamically, per run.

So the "missing" workflow definition isn't missing — it's *delegated to the model*, generated fresh each run based on the actual situation rather than fixed in advance. This is why a capable model plus good tools plus a clear goal is enough: the model synthesizes the workflow on the fly. And it's why Strands stays minimal — adding orchestration scaffolding would only constrain the flow the model can already produce. The three ingredients are enough precisely because the model drives.

## The loop and its guardrails

The model driving the loop is powerful and needs bounding, so the loop comes with the reliability disciplines from across the blog (detailed in the production post):

- **Bound the iterations** — a max number of loop cycles, so a model that gets stuck (repeating tools, not converging) fails fast rather than looping forever and burning tokens.
- **Handle tool errors** — feed failures back so the model can adapt, and degrade gracefully when it can't.
- **Observe every step** — because the model drives dynamically, watching the loop (via the built-in observability) is how you understand and debug behavior you didn't script.
- **Shape behavior through the prompt** — since the prompt is the main lever on how the model drives, guidance in the prompt (when to stop, how to approach, what to avoid) is how you steer the loop without hard-coding it.

The recurring theme: model-driven autonomy is the strength, and the guardrails (bounded loop, error handling, observability, prompt guidance) are what keep it reliable. The loop is simple; using it well is about equipping and bounding it, not controlling its every step.

## The loop in one idea

The Strands agent loop is the model-driven approach in motion: three ingredients you supply (model, system prompt, tools) and a think-act-observe loop the *model* drives — deciding at each step to reason, call a tool, or finish — with Strands running the tools and exposing every step. Minimal ingredients suffice because the workflow is delegated to the model's reasoning rather than authored in code, generated fresh each run. Bound and observe the loop rather than scripting it. This is the concrete heart of Strands; the next posts detail the ingredients — tools first.

## Key takeaways

- A Strands agent is defined by exactly three ingredients — a model, a system prompt, and a set of tools — with no workflow graph or orchestration DSL, because the model provides the orchestration by driving the loop.
- The loop is the standard think-act-observe cycle (prompt → model decides → tool runs if called → result feeds back → repeat until done), but distinctively the *model* decides every step (owns the control flow) and the loop is fully exposed for observation.
- Three ingredients suffice because the workflow is delegated to the model: the goal (prompt) lets it plan, the tools tell it what it can do, and its reasoning supplies the sequencing/branching/stopping dynamically per run — so the "missing" workflow definition is generated by the model, not fixed in advance.
- Adding orchestration scaffolding would only constrain the flow a capable model can already produce, which is why Strands stays minimal — the model driving is what makes minimalism enough.
- The model-driven loop needs guardrails: bound iterations (fail fast, don't burn tokens), handle tool errors, observe every step (you supervise rather than script), and steer via the prompt — autonomy is the strength, guardrails keep it reliable.

## Further reading

- [The model-driven approach (previous post)](/blog/posts/strands-02-model-driven-approach.html)
- [Strands Agents documentation](https://strandsagents.com/)
- [Agentic RAG series — the think-act-observe (ReAct) loop](/blog/series/agentic-rag/)
