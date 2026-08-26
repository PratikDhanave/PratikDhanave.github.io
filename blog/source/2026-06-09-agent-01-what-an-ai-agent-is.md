# What an AI Agent Is

*"Agent" has become one of the most overused and least precise words in AI — applied to everything from a chatbot with a system prompt to a fully autonomous system that writes and ships code. Cutting through the hype requires a clear definition: an agent is a system where an LLM decides its own actions in a loop, using tools, until a goal is met. That one distinction — the model choosing what to do next, rather than following a fixed script — is what separates a genuine agent from a workflow, and it's where both the power and the difficulty come from.*

This series is a **framework-agnostic** guide to **AI agent design patterns** — the recurring architectural patterns for building agents with LLMs, independent of any specific framework. (The blog has framework-specific series too — LangGraph, Microsoft Agent Framework, Google ADK, smolagents — this one is about the *patterns* beneath them all.) This first post defines what an agent actually is, distinguishes agentic from non-agentic systems, covers the core components, and — crucially — when to use agents and when not to. It sets the foundation for the patterns that follow.

## What an agent is

An **AI agent** (in the LLM sense) is a system where an **LLM decides its own actions in a loop** to accomplish a goal — rather than following a fixed, pre-programmed sequence. The defining characteristic:

- **The model directs the control flow.** In an agent, the LLM *decides what to do next* — which action to take, which tool to use, whether the goal is met — dynamically, based on the situation. The *model* drives the flow of the program, not a fixed script the developer wrote. This is the essence of "agentic": the LLM is in the driver's seat, choosing its path. (Anthropic's framing captures this well — agents are systems where the LLM dynamically directs its own processes and tool use.)
- **It operates in a loop.** An agent works by *iterating*: it takes an action, observes the result, decides the next action, and repeats — continuing until the goal is achieved (or it gives up/hits a limit). This loop (covered in depth next post) is the agent's core mechanism: repeated cycles of deciding and acting, rather than a single response. The loop is what lets an agent tackle multi-step tasks.
- **It uses tools to act.** Agents *act on the world* through **tools** — functions/capabilities the LLM can invoke (search, run code, call APIs, read/write data). Tools are how the agent does things beyond generating text (the tool-use post). Without tools, an LLM can only talk; with tools, an agent can *act*.

So an AI agent is an LLM that, in a loop, decides and takes actions (via tools) to accomplish a goal — with the *model* directing the control flow. This "model decides its own actions" property is the crux of what makes something an agent, and it's what distinguishes agents from fixed workflows. That distinction is worth dwelling on, because it clarifies a lot of confused "agent" talk.

## Agentic vs non-agentic

The key distinction — and a source of much confusion — is between **agentic** systems (the model decides the flow) and **non-agentic** ones (a fixed flow), often framed as *agents vs workflows*:

- **Workflows: fixed, predefined flow.** A *workflow* uses LLMs within a *predetermined* sequence of steps that the developer defined — e.g. "summarize this, then classify it, then route it." The LLM does tasks *within* a fixed structure, but the *flow* is fixed in code, not decided by the model. Workflows are *not* agents (in the strict sense) — the control flow is predetermined. Many useful "LLM applications" are actually workflows.
- **Agents: the model decides the flow.** An *agent*, by contrast, lets the *LLM decide* the steps dynamically — what to do, in what order, when to stop — based on the situation, not a fixed script. The flow *emerges* from the model's decisions. This dynamic, model-directed control is what makes it an agent. The difference is *who decides the sequence*: the developer (workflow) or the model (agent).
- **It's a spectrum, and "agent" is overused.** In practice, systems range from fully fixed (workflows) to fully autonomous (agents), with much in between (fixed flows with some dynamic steps). And "agent" is applied loosely to *all* of these (and to simple chatbots), causing confusion. The useful precise sense is: *the more the LLM dynamically directs the flow and tool use, the more agentic it is*. Being clear about where a system sits on this spectrum cuts through the hype.

The agentic/non-agentic (agent/workflow) distinction — *does the model decide the flow, or is it fixed?* — is the clarifying lens for "agent" talk. It matters practically because the two have very different tradeoffs (below): agents are more flexible but less predictable, workflows more reliable but rigid. Knowing which you're building (and which you *need*) is a key early decision.

## The components of an agent

Beyond the loop, agents are built from a few core components — which map to the rest of the series:

- **The LLM (the "brain").** The language model that reasons and *decides* — the core that drives the agent's decisions. Its capability (especially reasoning — the reasoning-models series) largely determines the agent's capability. The LLM is what makes the agent's dynamic decision-making possible.
- **Tools (the "hands").** The actions the agent can take — functions/APIs it can invoke to do things and get information (search, code execution, data access, etc.). Tools extend the agent beyond text into acting on the world (the tool-use post). An agent's capabilities are bounded by its tools.
- **The loop (the "control").** The iterative cycle of decide → act → observe → repeat that lets the agent work through multi-step tasks (the core-loop post). This is the engine that turns single LLM decisions into sustained goal-pursuit.
- **Memory (the "state").** How the agent remembers — the context of the current task (short-term) and, sometimes, information across tasks (long-term). Memory lets the agent maintain state and learn across steps (the memory post). Without memory, each step is isolated.
- **(Often) planning and reflection.** More sophisticated agents *plan* (decompose the task — the planning post) and *reflect* (evaluate and correct themselves — the reflection post). These add capability for complex tasks.

```text
   Agent = LLM (brain) + Tools (hands) + Loop (control) + Memory (state)
           [+ planning, reflection for harder tasks]
   The LLM decides, in the loop, which tools to use, using memory, until the goal is met.
```

These components — LLM, tools, loop, memory (plus planning and reflection) — are the building blocks of agents, and the series covers each as a design-pattern area. Understanding an agent as this composition (a deciding LLM, acting via tools, in a loop, with memory) frames the patterns that follow. But before building agents, the most important question is *whether* to.

## When to use agents (and when not to)

A crucial, often-skipped point: **agents are not always the right choice** — their flexibility comes at the cost of reliability, cost, and complexity, so use them judiciously:

- **Agents' tradeoff: flexibility vs predictability.** Because the model decides the flow, agents are *flexible* (they can handle open-ended, varied tasks a fixed workflow can't) — but *less predictable and reliable* (the model might do the wrong thing, loop, or fail in unexpected ways), *more expensive* (many LLM calls in the loop), and *harder to debug* (dynamic, non-deterministic flow). Flexibility and unpredictability are two sides of the same coin. This tradeoff governs when agents fit.
- **Use the simplest thing that works.** A key principle (emphasized by practitioners like Anthropic): *don't* reach for an agent when something simpler suffices. Often a single LLM call, a bit of retrieval (RAG), or a fixed *workflow* solves the problem more reliably and cheaply than an agent. Use agents only when the task genuinely *needs* the dynamic flexibility — and prefer workflows or simpler approaches otherwise. Complexity should be justified by need.
- **Agents fit open-ended, multi-step, unpredictable tasks.** Agents are worth their cost when the task is *open-ended* (the steps can't be predetermined), *multi-step*, and *varied* enough that a fixed flow can't handle it — where you genuinely need the model to *decide* the path dynamically. Coding assistants tackling varied problems, research tasks, and open-ended problem-solving are good fits. If you *can* predetermine the steps, a workflow is usually better.
- **The final post returns to this.** Building *reliable* agents (and knowing when *not* to use them) is hard enough that the series closes on it. For now, the key mindset: agents are a powerful but costly and less-reliable tool — use them when their flexibility is genuinely needed, not by default. Reaching for an agent when a workflow would do is a common, expensive mistake.

An AI agent is an LLM that decides its own actions in a loop, using tools, to accomplish a goal — with the *model* directing the flow (the agentic/workflow distinction) — built from an LLM, tools, a loop, and memory. Crucially, agents trade reliability and cost for flexibility, so use them only when that flexibility is genuinely needed (not by default). Next: the core agent loop — the fundamental reason-act-observe cycle at an agent's heart.

## Key takeaways

- An AI agent is a system where an LLM *decides its own actions in a loop* (using tools) to accomplish a goal — the defining property is that the *model directs the control flow* (chooses what to do next dynamically), rather than following a fixed developer-written script.
- The key distinction is agentic vs non-agentic (agents vs workflows): a workflow uses LLMs within a *predetermined* flow (the developer decides the steps — not a true agent), while an agent lets the *model* decide the steps dynamically; it's a spectrum, and "agent" is widely overused, so the precise sense is "the more the LLM dynamically directs the flow, the more agentic."
- Agents are built from core components: the LLM (the deciding "brain"), tools (the "hands" that act on the world), the loop (decide → act → observe → repeat control), and memory (state) — plus planning and reflection for harder tasks — each a design-pattern area the series covers.
- Agents trade predictability, cost, and debuggability for flexibility: because the model decides the flow, they handle open-ended varied tasks a fixed workflow can't, but they're less reliable, more expensive (many LLM calls), and harder to debug — flexibility and unpredictability are two sides of the same coin.
- Use the simplest thing that works — often a single LLM call, RAG, or a fixed workflow is more reliable and cheaper — and reach for agents only when the task is genuinely open-ended, multi-step, and unpredictable enough to *need* dynamic, model-directed flow; reaching for an agent by default when a workflow would do is a common, costly mistake.

## Further reading

- [A Survey on Large Language Model based Autonomous Agents (Wang et al., 2023)](https://arxiv.org/abs/2308.11432)
- [Intelligent agent (Wikipedia)](https://en.wikipedia.org/wiki/Intelligent_agent)
- [LangGraph, Concept by Concept — a framework-specific agent series](/blog/series/langgraph-concept-by-concept/)
