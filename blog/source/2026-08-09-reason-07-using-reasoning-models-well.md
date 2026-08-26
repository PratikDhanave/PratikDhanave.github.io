# Using Reasoning Models Well

*The habits that made you good at prompting standard models can actively hurt you with reasoning models. "Let's think step by step" is redundant — even counterproductive — when the model already thinks natively. Few-shot examples can constrain reasoning that's better left free. The shift from standard to reasoning models isn't just picking a different model; it's unlearning some prompting reflexes and learning where deep thinking actually earns its cost.*

Reasoning models behave differently enough that using them well requires different practices. This post is the practical one: how prompting changes for reasoning models, when to reach for one versus a standard model, how they fit into agentic and tool-using systems, and the pitfalls to avoid. It translates the series' concepts into day-to-day guidance for building with these models.

## Prompting is different

The biggest surprise for people coming from standard models: **the prompting techniques you learned can be unnecessary or counterproductive with reasoning models.**

- **Don't tell it to think step by step.** Chain-of-thought prompting ("let's think step by step," "show your work") was essential for eliciting reasoning from *standard* models. A reasoning model already reasons natively — it does the step-by-step thinking automatically — so instructing it to is redundant, and over-specifying *how* to reason can constrain the model's own (often better) reasoning process. Let the model think its own way.
- **Few-shot examples can hurt.** With standard models, few-shot examples (showing worked examples in the prompt) often improve performance. With reasoning models, extensive few-shot examples can actually *degrade* results — they can anchor the model to the examples' reasoning patterns rather than letting it reason freshly, and reasoning models generally do well *zero-shot* with just a clear problem statement. Prefer clear, direct instructions over many examples.
- **Be clear about the goal, not the method.** The most effective prompting for reasoning models is to state the problem and desired outcome *clearly and completely* — give it the information and the objective — and let it figure out *how*. Specify constraints and what a good answer looks like; don't micromanage the reasoning steps. Clarity about *what* beats prescription about *how*.

The through-line: reasoning models want **a clear problem, not a reasoning recipe.** The prompting shift is from "guide the model's thinking" (needed for standard models) to "state the problem well and get out of the way" (better for reasoning models). Unlearning the step-by-step reflex is one of the most common adjustments.

## When to use a reasoning model

Reasoning models aren't a universal upgrade — they're the right tool for a *subset* of problems, and using them everywhere wastes cost and latency (the economics post). The decision:

- **Use a reasoning model for hard, multi-step problems.** Complex math, hard coding and debugging, multi-step logic, planning, careful multi-factor analysis, problems where getting it right requires working through steps — this is where reasoning models excel and their cost is justified. If a problem genuinely needs thinking, use a model that thinks.
- **Use a standard model for simple, fast, high-volume tasks.** Factual answers, simple classification, summarization, formatting, straightforward conversation, latency-sensitive interactions — here a standard model is faster, cheaper, and just as good (there's little to reason through). Reaching for reasoning is waste.
- **Consider a hybrid / routing approach.** Many real systems *route*: use a fast standard model for most traffic and escalate to a reasoning model for the hard cases (detected by difficulty, low confidence, or task type). This gives reasoning's accuracy where needed without paying for it everywhere — often the best overall design.

The judgment is the same as the economics dial: match the tool to the problem's difficulty and stakes. A good default is to *start* with a standard model and escalate to reasoning when the problem is hard enough to warrant it — rather than defaulting to reasoning and paying its cost on everything.

## Reasoning models in agents and tool use

Reasoning models are especially valuable in **agentic** systems — where a model plans, uses tools, and executes multi-step tasks — because those tasks are exactly the multi-step reasoning reasoning models are good at:

- **Planning benefits from reasoning.** Agentic tasks require decomposing a goal into steps, deciding what to do, and adapting as results come in — multi-step reasoning where a reasoning model's deliberation and self-correction help substantially. Reasoning models make better planners.
- **Tool use interleaves with thinking.** Modern reasoning models can reason *about* when and how to use tools — deciding which tool, interpreting results, deciding next steps — integrating thinking with action. This makes them strong at agentic loops (reason → act → observe → reason). The agent-design series covers these patterns in depth; reasoning models are a natural fit for the "plan and adapt" core.
- **But mind cost and latency in loops.** An agent that calls a reasoning model at every step, each thinking extensively, can be slow and expensive — the per-step cost multiplied across many steps. Use reasoning where the step genuinely needs it (hard planning/decisions) and lighter models for routine steps; don't make every agent step a deep-reasoning call by default.

So reasoning models and agents are complementary: agents need multi-step reasoning, and reasoning models provide it. But the economics compound in loops, so deploy reasoning selectively within an agent — deep thinking for the hard decisions, cheaper models for the routine.

## Pitfalls and practices

A grab-bag of practical guidance for building with reasoning models well:

- **Don't over-prompt.** Avoid stacking step-by-step instructions, many few-shot examples, and rigid reasoning templates onto a reasoning model — they can hurt. Clear problem statement, clear goal, relevant context.
- **Set reasoning effort deliberately.** Use the effort dial (economics post) to match thinking to the problem — don't max it out by default (wasteful and slow) or leave it minimal on problems that need thinking. Tune per task type.
- **Watch cost and latency in production.** Reasoning tokens and agentic loops multiply cost; monitor token usage and response times, and route by difficulty rather than paying reasoning prices on all traffic.
- **Don't rely on the visible reasoning as ground truth.** The chain of thought is the model's working, not a guaranteed-faithful explanation of *why* it answered as it did (the next post covers faithfulness) — useful for insight and debugging, but don't treat it as a verified audit trail.
- **Verify outputs for critical uses.** Reasoning improves accuracy but doesn't guarantee correctness — for high-stakes outputs, still verify (tests for code, checks for math, review for decisions). Consider pairing with inference-time verification (best-of-N with a checker) where correctness is critical.
- **Give it the information it needs.** Reasoning can't compensate for missing context — a reasoning model reasoning over incomplete information still gets things wrong. Supply the relevant facts, constraints, and data; reasoning amplifies good input, it doesn't replace it.

Using reasoning models well means unlearning some standard-model prompting habits (don't over-prompt or force step-by-step), matching the model to the problem (reasoning for hard multi-step work, standard models for simple/fast tasks, routing between them), leveraging them in agentic planning while watching loop costs, and remembering that reasoning improves but doesn't guarantee correctness. The final post covers the limits and frontier — what reasoning models still can't do, and where the field is heading.

## Key takeaways

- Prompting is different: don't tell a reasoning model to "think step by step" (it reasons natively — the instruction is redundant and can constrain it), avoid heavy few-shot examples (they can anchor and degrade reasoning; these models do well zero-shot), and state the problem and goal clearly rather than prescribing the reasoning method — clarity about *what* beats prescription about *how*.
- Match the model to the problem: use reasoning models for hard, multi-step work (complex math/coding, logic, planning, careful analysis) where their cost is justified, and standard models for simple/fast/high-volume/latency-sensitive tasks — often routing traffic, defaulting to a standard model and escalating to reasoning for hard cases.
- Reasoning models are a natural fit for agentic systems (planning, tool use, multi-step execution are exactly the reasoning they're good at), but per-step reasoning cost compounds across agent loops — deploy deep reasoning selectively for hard decisions and lighter models for routine steps.
- Key pitfalls: don't over-prompt, set reasoning effort deliberately (neither max-by-default nor too low for hard problems), monitor cost/latency and route by difficulty in production, don't treat the visible chain of thought as a faithful audit trail, and still verify outputs for critical uses.
- Reasoning amplifies good input but doesn't replace it or guarantee correctness — supply the needed context/facts/constraints, and pair with verification (tests, checkers, best-of-N) where correctness is critical.

## Further reading

- [DeepSeek-R1 — reasoning model behavior and usage](https://arxiv.org/abs/2501.12948)
- [The economics of thinking (previous post)](/blog/posts/reason-06-economics-and-tradeoffs.html)
- [LangGraph, Concept by Concept — reasoning models as agent planners](/blog/series/langgraph-concept-by-concept/)
