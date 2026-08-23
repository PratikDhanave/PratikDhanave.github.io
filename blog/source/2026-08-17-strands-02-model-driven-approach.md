# The Model-Driven Approach

*The model-driven approach is not just how Strands works — it's a stance on where intelligence should live in an agent. Put it in the model's reasoning, not in developer-authored control flow. This post unpacks why that stance is increasingly the right one, and where it isn't.*

The last post named the model-driven approach as Strands's defining philosophy. This post goes deep on it, because it's the concept that everything else in Strands follows from — and it's a genuinely different way of thinking about agents than the workflow-first frameworks. Understanding *why* model-driven works (and its limits) is what lets you use Strands well rather than fighting its grain.

## The core stance: intelligence in the model, not the code

The model-driven approach makes a claim about *where the agent's intelligence should live*: in the **model's reasoning**, not in the **developer's control flow**. Consider what an agent has to do — understand a goal, plan an approach, decide which tools to use and when, adapt when things don't go as expected, and know when it's done. There are two places that intelligence can sit:

- **In the code** — the developer writes the plan as explicit control flow (do this, then that, if this branch here), and the model fills in narrow slots. The *code* is smart; the model is a component.
- **In the model** — the developer gives the model a goal and tools, and the *model* plans, decides, adapts, and finishes. The *model* is smart; the code is minimal scaffolding.

Strands bets on the second. The system prompt states the goal, the tools provide capabilities, and the model does the reasoning — deciding at each step what to do next. This is a deliberate philosophical position: **the model is now capable enough to be the planner, so let it plan.** The developer's job shifts from *authoring the workflow* to *equipping the model* (good prompt, good tools) and *observing and bounding* the loop.

## Why this ages well

The model-driven approach is a bet on a trajectory, and the trajectory is favorable, which is the strongest argument for it:

- **Models keep getting better at planning.** Each generation is more capable at multi-step reasoning, tool selection, and adaptation — exactly the things a hand-authored workflow substitutes for. So the value of developer-authored orchestration *decreases* as models improve, while the value of letting the model drive *increases*.
- **Hand-authored workflows can constrain a capable model.** A rigid workflow written for a weaker model may actively prevent a stronger model from using a better approach it could have found itself. The scaffolding that helped a weak model handicaps a strong one — the same "prompts written for an older model" problem from the cost playbook, at the workflow level.
- **Minimal scaffolding is less to maintain.** Elaborate orchestration is code to write, test, and update as requirements and models change; a model-driven agent's logic largely lives in the prompt and the model, which is less brittle over time.

So the model-driven approach isn't just simpler today — it's *positioned* for a world of increasingly capable models, where trusting the model's planning becomes more correct over time, not less. This is the deepest argument for Strands's design: it's built for where models are going, not just where they are.

## What the developer does instead

If the model drives, what's left for the developer? Plenty — the work shifts rather than disappears:

- **Craft the system prompt** — the goal, constraints, and guidance that shape how the model drives. In a model-driven agent, the prompt *is* much of the "programming," so it matters enormously (the prompt-engineering and cost-playbook lessons apply directly).
- **Provide good tools** — the capabilities the model draws on. Tool quality and clear descriptions determine what the model can do and how well it chooses (the tools post). Equipping the model well is the developer's leverage.
- **Observe the loop** — because the model drives dynamically, you *watch* what it does (which tools, in what order, why) rather than pre-scripting it — making observability essential, not optional (the observability post).
- **Bound and guardrail** — set limits (max iterations, budgets) and handle errors so the model's autonomy doesn't become unreliability (the production post).

The shift is from *directing* the agent to *equipping and supervising* it — like the difference between micromanaging and delegating to a capable person: you give them the goal, the tools, and the boundaries, then let them work and watch the results. That's the model-driven developer's role.

## Where model-driven has limits

Honesty requires the limits, because model-driven isn't universally right — it's a trade-off (the autonomy-vs-control tension):

- **When you need guaranteed structure**, model-driven is the wrong tool. If a process *must* follow specific steps in a specific order (a compliance flow, a regulated sequence, a human-approval gate that must always fire), you want explicit control (workflow-first, LangGraph) — you can't leave a mandatory sequence to the model's discretion.
- **When the model isn't capable enough** for the task's planning, letting it drive produces poor or erratic behavior; a more structured approach compensates. The model-driven bet assumes a *sufficiently capable* model.
- **When predictability matters more than flexibility** — model-driven agents are, by design, less predictable (the model decides), so for cases where you need repeatable, auditable, deterministic behavior, structure wins.

The practical framing: **model-driven for tasks that benefit from the model's own planning and tolerate its variability; structured/workflow-first for tasks needing guaranteed flow and predictability.** Strands is the former; it's an excellent fit when you want to trust a capable model, and a poor one when you need to *guarantee* a process. Many real systems mix both — a structured backbone with model-driven agents inside bounded steps (the composition pattern from the workflow series) — and Strands can be a model-driven component within a larger structure.

## The approach in one idea

The model-driven approach is the stance that an agent's intelligence belongs in the model's reasoning, not the developer's control flow — so you equip the model (prompt, tools), let it drive the loop, and observe and bound it rather than pre-scripting it. It ages well because models keep improving at planning, making minimal scaffolding increasingly sufficient and elaborate orchestration increasingly constraining. Its limit is when you need guaranteed structure or the model isn't capable enough. This philosophy is the soul of Strands, and every subsequent concept — the loop, tools, models, multi-agent — is an expression of it. The next post makes it concrete with the agent loop itself.

## Key takeaways

- The model-driven approach is a stance on where an agent's intelligence lives: in the model's reasoning (Strands) rather than in developer-authored control flow — the developer equips the model (prompt, tools) and the model plans, decides, adapts, and finishes.
- It ages well because it bets on a favorable trajectory: models keep improving at planning, so developer-authored orchestration's value decreases (and can constrain a capable model) while letting the model drive increases — it's built for where models are going.
- The developer's role shifts from directing to equipping and supervising: craft the system prompt (much of the "programming"), provide good tools, observe the dynamic loop (making observability essential), and bound/guardrail the autonomy.
- Its limits are real: use structured/workflow-first approaches when you need guaranteed step ordering (compliance, mandatory gates), when the model isn't capable enough to plan the task, or when predictability matters more than flexibility.
- Framing: model-driven for tasks that benefit from the model's planning and tolerate variability; structured for guaranteed flow and predictability — Strands is model-driven, and can also serve as a model-driven component inside a larger structured system.

## Further reading

- [What is Strands Agents? (previous post)](/blog/posts/strands-01-what-is-strands.html)
- [Strands Agents and the model-driven approach (AWS Open Source Blog)](https://aws.amazon.com/blogs/opensource/strands-agents-and-the-model-driven-approach/)
- [LangGraph, Concept by Concept — the workflow-first contrast](/blog/series/langgraph-concept-by-concept/)
