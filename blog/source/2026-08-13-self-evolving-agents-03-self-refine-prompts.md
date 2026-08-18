# Self-Refining Prompts and Instructions

*The prompt is the agent's program, so an agent that can rewrite its own prompts is an agent that can rewrite its own behavior — and there are now principled ways to make that search work.*

If memory evolves the *context* an agent brings to a task, prompt evolution changes the *program* itself. The instructions that drive an agent are its most editable surface, and a growing body of work turns "prompt engineering" from a human craft into an automated search the system runs on itself. This post, the third in a series on self-evolving agents, covers three points on that spectrum: iterative self-refinement of a single output, declarative pipelines that optimize their own prompts, and evolutionary search over populations of prompts.

## Iterative self-refinement

The simplest form of prompt-driven improvement operates within a single task. [Self-Refine (Madaan et al., 2023)](https://arxiv.org/abs/2303.17651) uses one model in three alternating roles: generate an initial output, produce feedback on that output, then use the feedback to refine it — and repeat. No extra training, no labeled data, no separate critic model; the same LLM generates, critiques, and revises iteratively.

This is a genuine improvement loop, but notice what makes it work: the feedback step has to produce *specific, actionable* critique, not vague approval. "Make it better" does nothing; "the function ignores the empty-list case and the variable name `x` is unclear" does. When the task has structure the model can reliably assess — code that can be reasoned about, text with checkable properties — self-refinement helps. When the model cannot actually tell good from bad, iterating just adds confident churn. That caveat is the seam between this technique and its limits, which the next post examines head-on.

Self-Refine improves a single output at inference time. It is "self-evolving" in the light sense of the loop from the first post, but the improvement does not persist across tasks unless you capture it — which is where the next two approaches come in.

## Declarative pipelines that optimize their own prompts

Hand-written prompt strings are brittle: a lengthy template discovered by trial and error, fragile to model changes, and impossible to systematically improve. [DSPy (Khattab et al., 2023)](https://arxiv.org/abs/2310.03714) reframes the problem. Instead of writing prompts, you write a program out of declarative **modules** that describe *what* each step should do (its inputs and outputs), and you let a compiler figure out the *how* — the actual prompts, few-shot examples, and reasoning strategies — by optimizing against a metric on training data.

The shift is from prompt-as-string to prompt-as-parameter. The pipeline's prompts become things that are *learned* from examples and a metric, rather than authored and frozen. When you change the model or the task, you recompile rather than rewrite. This is prompt evolution disciplined into an optimization problem: define the structure and the objective, and let the system search the prompt space for you. It is the most production-friendly form of prompt self-improvement precisely because it is anchored to an explicit metric on real data — the trustworthy signal again.

## Evolutionary search over prompts

The most self-referential approach treats prompts as a population to evolve. [Promptbreeder (Fernando et al., 2023)](https://arxiv.org/abs/2309.16797) maintains a set of task-prompts and improves them with a genetic loop: mutate the prompts, evaluate each variant's fitness on a training set, keep the winners, and repeat. The twist that gives it its name is self-reference — the *mutation-prompts* that decide how to mutate the task-prompts are themselves evolved by the model over the run. The system is improving both its solutions and its own method of improving them.

Reported results show this kind of evolutionary search discovering prompts that outperform well-known hand-designed strategies on reasoning benchmarks. The mechanism is worth internalizing even if you never run the full algorithm: given a *fitness function you trust*, you can search prompt space far more thoroughly than human iteration ever will, and the search can improve its own operators. As always, the fitness function is load-bearing — evolution optimizes exactly what you measure, so a weak or gameable metric produces prompts that are good at scoring, not at the task.

## A spectrum, not three isolated tricks

These three sit on one axis at increasing scope and cost:

- **Self-Refine** — improve one output, now, within a task. Cheap, no persistence, needs the model to give real feedback.
- **DSPy** — optimize a pipeline's prompts against a metric on data. Persistent, systematic, needs a dataset and metric.
- **Promptbreeder** — evolve a population of prompts (and mutation operators) by fitness. Most thorough, most expensive, needs a reliable fitness signal.

Which you reach for depends on what you have. A one-shot quality bump with no training data: self-refinement. A pipeline you will run at scale and want to keep tuned: a DSPy-style declarative optimizer. A hard task where you can afford search and have a solid metric: evolutionary prompt search. All three share the same non-negotiable ingredient — a signal that actually tracks quality. Prompt self-improvement is real and often the highest-leverage evolution axis, but every method here is only as good as the evaluator behind it.

## Key takeaways

- The prompt is the agent's program, so evolving prompts evolves behavior — and prompt engineering is increasingly an automated search the system runs on itself.
- Self-Refine iterates generate → feedback → refine with one model and no training, but only helps when the feedback step produces specific, actionable critique the model can reliably give.
- DSPy turns prompts from hand-written strings into parameters optimized against a metric on data, making prompt improvement systematic and portable across models.
- Promptbreeder evolves a population of task-prompts by fitness and even evolves its own mutation-prompts, searching prompt space far beyond human iteration.
- All three depend on a trustworthy signal — a real critique, metric, or fitness function; evolution optimizes exactly what you measure, so a weak metric yields prompts that game the score.

## Further reading

- [Self-Refine: Iterative Refinement with Self-Feedback — Madaan et al., 2023](https://arxiv.org/abs/2303.17651)
- [DSPy: Compiling Declarative Language Model Calls into Self-Improving Pipelines — Khattab et al., 2023](https://arxiv.org/abs/2310.03714)
- [Promptbreeder: Self-Referential Self-Improvement via Prompt Evolution — Fernando et al., 2023](https://arxiv.org/abs/2309.16797)
