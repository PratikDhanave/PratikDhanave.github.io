# Optimizers: Letting DSPy Write Your Prompts

*This is the payoff of the whole framework: you hand an optimizer your program, your metric, and some examples, and it searches for the instructions and demonstrations that make the program measurably better — the prompts you never had to write.*

Everything so far has been setup: signatures declare the what, modules choose the how, programs compose them, and metrics define good. The **optimizer** is where it pays off. An optimizer takes your program, your metric, and a training set, and *compiles* the program — searching over prompt instructions and few-shot demonstrations to maximize the metric. This sixth post in the DSPy series covers how compilation works and which optimizer to reach for.

## What compilation actually does

When you compile a program, the optimizer improves two kinds of "parameters" in your modules, without ever touching the model's weights:

- **Few-shot demonstrations.** It runs your program on training examples, keeps the runs that satisfy your metric, and turns those successful runs into few-shot examples embedded in each module's prompt. This is *bootstrapping*: the program generates its own demonstrations from data, and only the ones that worked are kept.
- **Instructions.** It proposes alternative wordings of each module's instruction (the signature's docstring), tries them, and keeps what scores best.

The compile call looks like this:

```python
import dspy

optimizer = dspy.MIPROv2(metric=my_metric)
compiled = optimizer.compile(my_program, trainset=trainset)

compiled(question="...")     # the optimized program
```

`compiled` is a new version of your program with tuned prompts. Nothing about your *code* changed — the signatures, modules, and `forward` are identical — only the compiled instructions and demonstrations behind them improved. That is the compiler analogy made concrete: same source, better generated output.

## The optimizer ladder

DSPy offers several optimizers at increasing cost and sophistication. Climb the ladder as your data and needs grow rather than starting at the top:

- **BootstrapFewShot** — the starting point. It bootstraps few-shot demonstrations from your training data. Fast, works on small data, and often a meaningful lift over the un-optimized program. Start here.
- **BootstrapFewShotWithRandomSearch** — runs bootstrapping several times with random search over the generated demonstrations and keeps the best program. More compute, better results, still demonstration-focused.
- **MIPROv2** — optimizes *both* instructions and few-shot demonstrations jointly, using Bayesian optimization to search the combined space: it proposes candidate instructions grounded in the task, bootstraps demonstration candidates, and searches for the best combination. Reach for it when you have a couple hundred examples and want instructions and demos tuned together.
- **COPRO** — focuses on optimizing the instruction wording when demonstrations are not the lever you need.
- **GEPA** — a reflective optimizer suited to multi-objective problems, multi-module pipelines, or cases where MIPROv2 has plateaued and you can afford more search.

There are further optimizers (including approaches that combine prompt optimization with model fine-tuning), but this ladder covers the common path: bootstrap demos first, add instruction optimization when you have the data, and escalate to reflective search when simpler optimizers stall.

## Bootstrapping is the key idea

The concept worth dwelling on is bootstrapping, because it is what makes DSPy's optimization self-improving. Rather than you hand-writing few-shot examples, the program *runs itself* on training inputs, the metric judges which runs succeeded, and the successful trajectories become the demonstrations. For a multi-step program, this even captures good *intermediate* behavior — the demonstrations show each sub-module what a successful step looks like in context. The program teaches itself from its own best runs, filtered by your metric. This is why the metric quality from the previous post is load-bearing: the optimizer keeps exactly the runs the metric approves, so a weak metric bootstraps weak demonstrations.

## Compile cost and how to manage it

Optimization is not free — it runs your program many times over the training set, and instruction-proposal optimizers make additional model calls to generate and test candidates. A few practices keep it affordable: start with the cheap optimizer (BootstrapFewShot) and only climb the ladder if the metric says you need to; use a smaller training subset while iterating and a larger one for the final compile; and cache aggressively, since DSPy can reuse identical calls across the search. Because compilation is a build-time cost paid to produce a better program, it is usually well worth it — but treat it like a build step you run deliberately, not on every request.

## Recompile, don't rewrite

The property that makes optimizers strategically valuable is portability. When you swap the underlying model — a new release, a cheaper option, a different provider — you do not rewrite prompts. You *recompile*: run the optimizer again against the new model, and it finds the instructions and demonstrations that work best for *that* model on your metric. The hand-tuned-prompt world treats a model change as a migration; DSPy treats it as a build. This is the clearest argument for the whole approach: your investment is in the program and the metric, both of which survive a model change, while the model-specific prompts are regenerated on demand.

## Key takeaways

- An optimizer compiles your program — searching over instruction wordings and few-shot demonstrations to maximize your metric — without touching model weights; your code is unchanged, only the generated prompts improve.
- Compilation tunes two things: bootstrapped demonstrations (successful runs the metric approved, turned into few-shot examples) and proposed instructions.
- Climb the optimizer ladder as data grows: BootstrapFewShot → BootstrapFewShotWithRandomSearch → MIPROv2 (joint instruction+demo Bayesian search) → COPRO (instruction-only) / GEPA (reflective, multi-objective).
- Bootstrapping is the self-improving core: the program generates its own demonstrations from data, filtered by the metric — so a weak metric yields weak demonstrations.
- Manage compile cost (start cheap, subset while iterating, cache), and treat model swaps as a *recompile*, not a rewrite — your program and metric survive the change while model-specific prompts are regenerated.

## Further reading

- [DSPy optimizers — official docs](https://github.com/stanfordnlp/dspy/blob/main/docs/docs/learn/optimization/optimizers.md)
- [DSPy — official documentation](https://dspy.ai)
- [DSPy paper — Khattab et al., 2023](https://arxiv.org/abs/2310.03714)
