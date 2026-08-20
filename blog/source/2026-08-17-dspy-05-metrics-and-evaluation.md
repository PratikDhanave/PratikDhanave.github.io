# Metrics and Evaluation

*DSPy's optimizer improves whatever your metric rewards, which makes the metric the single most consequential thing you write — get it right and compilation makes your program better; get it wrong and it optimizes confidently toward the wrong target.*

Before you can let DSPy optimize a program, you have to tell it what "better" means. That is the job of the **metric** and the **evaluation** data. This fifth post in the DSPy series covers examples, metrics, and the `Evaluate` utility — and why the metric deserves more care than any prompt ever did, because it *is* the objective the optimizer maximizes.

## Examples: the data DSPy learns from

DSPy represents data as `dspy.Example` objects — labeled inputs and expected outputs for your task. You mark which fields are inputs with `.with_inputs(...)`:

```python
import dspy

trainset = [
    dspy.Example(question="What is our refund window?", answer="30 days").with_inputs("question"),
    dspy.Example(question="Do you ship internationally?", answer="Yes, to 40 countries").with_inputs("question"),
    # ... more examples
]
```

You typically split these into a training set (used by optimizers to bootstrap demonstrations) and a held-out development/validation set (used to measure quality honestly). As with any machine learning, the set that *reports* quality must be separate from the set the optimizer *learns* from, or you are measuring memorization of your own examples rather than capability. You do not need thousands — DSPy's optimizers work with modest data, sometimes tens to a few hundred examples — but they must be representative.

## Metrics: defining "good" as a function

A DSPy metric is just a Python function that takes an example and the program's prediction and returns a score — a boolean, a float, or a richer value:

```python
def exact_answer(example, prediction, trace=None):
    return example.answer.lower() in prediction.answer.lower()
```

That is the whole interface. Because it is ordinary Python, a metric can be anything you can compute: an exact or semantic match, an F1 over extracted fields, a check that the output validates against a schema, a numeric quality score — or an **LLM-as-judge**, where you use a DSPy module itself to score whether the prediction meets the criteria. For fuzzy, open-ended tasks the judge approach is often necessary, with the same caveat as everywhere: calibrate the judge against human labels so you are not optimizing toward the judge's biases.

The `trace` parameter is what lets a metric inspect the program's *internal steps* (not just the final output) — useful for agent and multi-hop programs where you want to reward good intermediate behavior, like selecting the right tool, and not only the final answer.

## The metric is the objective — treat it that way

Here is the sentence to internalize: **the optimizer maximizes exactly what the metric rewards, so the metric defines what your program becomes.** This is liberating and dangerous in equal measure. A metric that genuinely captures quality turns DSPy's optimization into real improvement. A metric with a loophole — one that a superficial answer can satisfy without being good — will be found and exploited, and you will get a program that scores well and performs badly.

So write the metric with the care you would give a specification. Ask what a *cheap* way to satisfy it would be, and whether that cheap way is actually acceptable. Guard against the obvious gaming: if "answer contains the keyword" can pass, a verbose non-answer stuffed with keywords will pass too. Where a single check is gameable, combine several (correctness *and* grounding *and* format). The effort you once spent hand-tuning prompts moves here, to defining good precisely — and it is better spent, because a good metric improves every future compile.

## Evaluate: measuring before and after

DSPy's `Evaluate` utility runs your program over a dataset with your metric and reports the aggregate score:

```python
evaluator = dspy.Evaluate(devset=devset, metric=exact_answer, num_threads=8)
score = evaluator(my_program)
print(score)
```

Use it constantly. Run it on your un-optimized program first to establish a baseline, then after optimization to measure the lift — the difference is the concrete value DSPy added, in the units of your metric. Run it whenever you change the program, the model, or the data, so a regression is a number you see rather than a surprise users report. This baseline-then-compare loop is the same discipline good AI evaluation demands everywhere; DSPy just builds it into the framework.

## Per-slice evaluation catches what averages hide

An aggregate score can rise while a critical subset regresses. If your task has meaningful slices — categories of question, user segments, difficulty levels — evaluate per slice, not just overall, so a compile that improves the average by breaking the hard cases is caught. This matters especially after optimization, because an optimizer chasing the aggregate metric has no reason to protect a slice you did not measure. What you want DSPy to preserve, you must put in the evaluation.

## Key takeaways

- DSPy data is `dspy.Example` objects with `.with_inputs(...)`, split into a train set (optimizers bootstrap from it) and a held-out dev set (reports quality honestly) — modest, representative data suffices.
- A metric is a plain function `(example, prediction, trace) -> score`; it can be exact/semantic match, schema validation, a numeric score, or a calibrated LLM-as-judge, and `trace` lets it reward good intermediate steps.
- The optimizer maximizes exactly what the metric rewards, so the metric *is* the objective — write it like a specification and guard against gameable loopholes by combining checks.
- Use `dspy.Evaluate` to measure a baseline before optimizing and the lift after; run it on every program, model, or data change so regressions are numbers, not surprises.
- Evaluate per slice, not just in aggregate — an optimizer chasing the average will sacrifice any slice you didn't measure.

## Further reading

- [DSPy — official documentation](https://dspy.ai)
- [DSPy metrics & evaluation — docs](https://dspy.ai)
- [DSPy paper — Khattab et al., 2023](https://arxiv.org/abs/2310.03714)
