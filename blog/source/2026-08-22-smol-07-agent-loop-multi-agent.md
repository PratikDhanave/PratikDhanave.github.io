# The Agent Loop and Multi-Agent Systems

*Underneath the code-agent magic is a simple, readable loop — the kind of loop smolagents's minimalism lets you actually understand. And when one agent isn't enough, the same minimal parts compose into multi-agent systems, where a manager agent's code calls other agents as if they were tools.*

The previous posts covered code agents, security, tools, and models. This one covers the **agent loop** that runs it all (the multi-step loop at smolagents's core) and **multi-agent systems** (composing agents when one isn't enough). Both showcase smolagents's minimalism — the loop is simple enough to understand fully, and multi-agent falls out of the same parts rather than needing new machinery.

## The multi-step agent loop

At smolagents's core is a **multi-step agent loop** — the mechanism that drives an agent through repeated think-act-observe cycles until it reaches an answer. For a code agent, each step is: the model writes code (the action), the framework executes it (safely, sandboxed — the security post), the result is observed, and the model decides the next step. It's the standard ReAct-style loop (from the agent and RAG series), specialized so the action is code:

```text
1. Model writes code (its action) given the task, tools, and prior steps
2. Framework executes the code in a sandbox → captures the result/output
3. Result is fed back to the model as observation
4. Model decides: write more code (another step) or return the final answer
5. Repeat until the model produces a final answer (or a step limit is hit)
```

What's notable, consistent with smolagents's whole ethos, is that this loop is **small and readable** — the minimalism (from the first post) means you can actually read the loop's implementation and understand exactly what your agent does at each step. There's no deep abstraction hiding the control flow; the multi-step loop is legible, which is both a learning benefit (you see how agents really work) and a debugging benefit (you can reason about the loop directly). The loop is the beating heart, and smolagents deliberately keeps it simple enough to hold in your head.

As with every agent loop, it needs the usual guardrails (the reliability disciplines from across the blog): **bound the number of steps** so an agent that doesn't converge stops rather than looping forever, handle execution errors (feed them back so the model can fix its code — a natural fit, since the model can debug its own code from the error), and observe the steps. The self-correcting angle is nice here: when the model's code errors, the error goes back to the model, which can *fix the code* in the next step — code agents can debug themselves in a way JSON tool-calling agents can't as naturally.

## Multi-agent: the same parts, composed

When one agent isn't enough (too many tools, separable subtasks, scope too broad — the same triggers as always), smolagents composes **multiple agents**, and true to its minimalism, this reuses the existing parts rather than adding new machinery. The pattern: a **manager agent** can call other agents as if they were tools — the same agents-as-tools idea seen in the Strands series, and a natural fit for code agents specifically:

```text
Manager (code) agent
  can call: [ search_tool, a managed web-research agent, a managed writer agent ]
    → the manager's CODE calls the sub-agents like functions:
        research = web_research_agent("find X")
        draft = writer_agent(research)
```

Because a code agent's actions are code, and a sub-agent can be exposed as something the code calls (a "managed agent"), multi-agent composition is just the manager's code calling sub-agents like any other tool/function. This is elegant for the same reason it is in Strands — no new orchestration layer, multi-agent is composition through the (code) calling interface — and it's especially natural in a code agent, where the manager can call sub-agents *within code*, looping over them, combining their results, and composing them just like tools (the code-action advantage applied to agents). A manager code agent orchestrating sub-agents in code is the code-agent idea scaled to a team.

## When multi-agent is worth it

The same discipline as always applies, and it's worth restating because minimalism makes composition *easy*, which can tempt over-decomposition:

- **Prefer a single agent until a real limit forces multi-agent** — multi-agent multiplies cost (more model calls, each writing code), latency, and failure modes. A capable single code agent handles a lot, especially given code actions' efficiency.
- **Use it for genuine separation** — distinct subtasks with different tools/expertise, or a scope too broad for one agent — where specialist sub-agents genuinely help.
- **Keep each agent focused** — a manager with a few clear sub-agents (and each sub-agent with a focused toolset), so both delegation and each agent's own tool selection stay reliable.
- **Right-size each agent's model** — a capable manager, possibly cheaper/smaller (or local) models for narrower sub-agents (the model-selection lever per agent, plus smolagents's open/local support making per-agent model choice flexible).

The guidance mirrors the whole agent-framework landscape: multi-agent is powerful but earns its complexity, and smolagents making composition easy (via code calling sub-agents) is a reason to compose *cleanly when needed*, not to fragment reflexively. A well-equipped single code agent beats a needlessly split team.

## The loop and multi-agent, minimally

The mental model: smolagents runs a **simple, readable multi-step loop** (write code → execute safely → observe → repeat) that its minimalism lets you fully understand, and **multi-agent composition** falls out of the same parts (a manager code agent calls sub-agents like tools, in code). Both reflect the library's ethos — keep it small, make the mechanism legible, reuse the same parts rather than adding machinery. The self-correcting code loop (the model fixes its own erroring code) and the natural code-based agent composition are advantages specific to the code-agent approach. Bound and observe the loop, compose multi-agent only when a single agent can't cope, and right-size each agent's model. The final post covers when smolagents is the right choice overall.

## Key takeaways

- smolagents runs a multi-step agent loop (write code → execute in sandbox → observe result → decide next step → repeat until done), the standard ReAct-style loop specialized so the action is code — and its minimalism keeps the loop small and readable, a learning and debugging benefit.
- Code agents can self-correct in the loop: when the model's code errors, the error feeds back and the model can fix its own code next step — a natural debugging ability JSON tool-calling agents lack.
- Multi-agent reuses the same parts: a manager agent calls sub-agents ("managed agents") as if they were tools, and because a code agent's actions are code, the manager's code calls sub-agents like functions (looping, composing) — no new orchestration machinery, especially natural for code agents.
- The usual discipline applies: prefer a single agent until a real limit forces multi-agent (it multiplies cost/latency/failures), use it for genuine separation, keep each agent focused, and right-size each agent's model (aided by smolagents's open/local flexibility).
- Both the loop and multi-agent reflect smolagents's ethos — small, legible, reuse the same parts — with self-correcting code loops and natural code-based agent composition as code-agent-specific advantages; bound and observe the loop, and compose cleanly only when needed.

## Further reading

- [Models (previous post)](/blog/posts/smol-06-models.html)
- [Strands Agents: multi-agent — the agents-as-tools pattern](/blog/posts/strands-06-multi-agent.html)
- [smolagents documentation](https://huggingface.co/docs/smolagents/index)
