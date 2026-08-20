# DSPy in Production

*A compiled DSPy program is an artifact — you optimize it once, save it, and serve it — which turns the framework's compile step into an ordinary part of a build pipeline rather than something that runs on every request.*

The optimizer runs at build time, not request time. That single fact shapes how DSPy fits into production: you compile a program, save the result, and load and serve it like any other versioned artifact. This final post in the DSPy series covers persisting compiled programs, treating optimization as a build step, observability, and an honest account of where DSPy fits and where it does not.

## Compiled programs are artifacts you save and load

Optimization is expensive and deterministic enough to do offline. So you compile once, save the tuned program (its instructions and demonstrations), and load it in production without re-running the optimizer:

```python
# Build time
compiled = optimizer.compile(program, trainset=trainset)
compiled.save("rag_compiled.json")

# Serving time
program = RAG(my_retriever)
program.load("rag_compiled.json")
program(question="...")     # serves the optimized prompts, no optimizer involved
```

This is the crucial operational point: the compiled artifact captures the learned prompts, so serving is just running your program with those prompts — no optimizer, no extra cost beyond the normal model calls. Version these artifacts the way you version models and prompts elsewhere: store the compiled file with its metadata (which program, which model, which metric, what score), so you can roll back to a previous compile and know exactly what is in production. The compiled program *is* your prompt registry entry.

## Optimization is a build step

Because compiling is offline and produces a versioned artifact, it belongs in your build/CI pipeline, not your request path. The natural workflow mirrors the MLOps discipline from good AI engineering: on a change — new training data, a new model, a program edit — recompile, evaluate the new artifact against your held-out set, and gate promotion on the metric. A compile that does not beat the current production artifact does not ship. This makes DSPy fit cleanly into a governed release process: the optimizer is a build tool, `Evaluate` is the gate, and the compiled file is the deployable.

## Portability: the strategic payoff in production

The reason to adopt DSPy for a long-lived system is portability, and it shows up most in production. When a better or cheaper model arrives, you do not audit and rewrite prompts across your codebase — you point the compile at the new model and re-run it, and the optimizer regenerates the instructions and demonstrations that work best for that model on your metric. Your durable assets are the program and the metric; the model-specific prompts are regenerated. In a world where models change every few months, treating a model swap as a recompile-and-evaluate rather than a migration is a real operational advantage, and it compounds across every pipeline you run.

## Observability and serving concerns

In production, DSPy programs are ordinary LLM systems and need the same operational care as any other. Instrument them: DSPy exposes the calls it makes (its history), and it integrates with tracing so you can see, for each request, what each module was sent and returned — the end-to-end trace you need to debug a multi-step program. Cache identical model calls to cut cost and latency, both during the many repeated calls of compilation and in serving where inputs recur. Apply the usual reliability patterns around the model calls — timeouts, retries, fallbacks — since DSPy does not remove the fact that you are calling an external, sometimes-slow, sometimes-rate-limited model. And watch cost and quality in production the way you would any AI system, feeding regressions back into the training set and recompiling.

## Where DSPy fits — and where it doesn't

An honest close. DSPy is a strong fit when you have a task you can *measure*, a pipeline you will run at scale and evolve over time, and the intent to move across models or systematically improve quality. On multi-step systems — RAG, agents, classification chains — where hand-written prompts are most numerous and most brittle, its compile-the-prompts approach is a genuine step-change: prompt archaeology becomes a metric and a build step.

It is less compelling in a few cases. For a single throwaway prompt, the ceremony of signatures, metrics, and optimizers is overhead a good one-liner avoids. For tasks with no measurable notion of success, the optimizer has nothing to maximize, and DSPy's core value evaporates — you can still use its declarative modules, but you lose the compilation payoff. And DSPy asks for a real mindset shift and some upfront investment (building an eval set, writing a metric) that a quick experiment may not justify. The framework does not remove the need to think about your pipeline, your data, and your definition of good — it removes the need to hand-tune prompts, which is a different and, for serious systems, more valuable thing.

## The series in one line

Across this series the through-line has been consistent: stop writing prompts, start writing programs and metrics, and let the optimizer compile the prompts. Declare *what* each step does with signatures, choose *how* with modules, compose them into programs, define *good* with a metric, and let optimizers turn all of it into tuned, model-specific prompts you never hand-wrote — and in production, treat the compiled result as a versioned artifact that recompiles when the model changes. That is DSPy: prompting, made an optimization problem.

## Key takeaways

- Optimization runs at build time; a compiled program is a versioned artifact you `save` and `load`, so serving costs only the normal model calls — no optimizer at request time.
- Put compilation in CI: on new data, a new model, or a program change, recompile, evaluate against a held-out set, and gate promotion on the metric — the optimizer is a build tool, `Evaluate` the gate, the compiled file the deployable.
- Portability is the production payoff: a model swap is a recompile-and-evaluate, not a prompt rewrite, because your durable assets are the program and the metric.
- Treat DSPy programs as ordinary LLM systems operationally — trace them, cache repeated calls, wrap model calls in timeouts/retries/fallbacks, and feed production regressions back into the training set.
- DSPy fits measurable, scaled, evolving pipelines (especially multi-step RAG and agents); it's overkill for one-off prompts and loses its core value where success can't be measured — it removes prompt hand-tuning, not the need to design the pipeline and define good.

## Further reading

- [DSPy — official documentation](https://dspy.ai)
- [stanfordnlp/dspy on GitHub](https://github.com/stanfordnlp/dspy)
- [DSPy paper — Khattab et al., 2023](https://arxiv.org/abs/2310.03714)
