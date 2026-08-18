# Self-Critique and Its Limits

*Asking a model to check its own work sounds like free improvement, but whether it actually helps depends entirely on where the feedback comes from — and getting this wrong is the most common way self-evolving agents fool themselves.*

Every technique so far has leaned on a feedback signal: reflection needs an outcome to reflect on, skills need verification, prompt search needs a fitness function. This post confronts the signal itself. Self-critique — a model evaluating and correcting its own output — is the most tempting feedback source because it is free and always available. It is also the most dangerous, because a model's confidence in its own correction is not the same as being correct. This fifth post in the series on self-evolving agents draws the line between self-critique that works and self-critique that quietly degrades your agent.

## The appeal of self-critique

The idea is seductive. You already have a capable model; why not have it grade its own homework? Ask it to critique its answer, then revise. No extra infrastructure, no human labels, no separate evaluator. When it works, it is the cheapest possible improvement loop, and several of the methods in this series use a version of it.

And it *does* work in specific conditions. Self-correction is effective when the critique step has access to something real: a test suite that runs, a compiler that rejects invalid code, a search that returns ground truth, a tool that reports an error. In those cases the model is not really grading itself — it is reading an external signal and reacting. That is legitimate and powerful. The trouble starts when the external signal is removed.

## The uncomfortable finding

[Huang et al. (2023), "Large Language Models Cannot Self-Correct Reasoning Yet"](https://arxiv.org/abs/2310.01798) studied *intrinsic* self-correction: a model attempting to fix its reasoning based solely on its own capabilities, with no external feedback. The finding is sobering. Without an external signal, models often fail to improve, and at times their performance *degrades* after self-correction. A model that had the right answer can talk itself out of it during a "correction" pass.

The reason is intuitive once stated. If a model could reliably tell its wrong answers from its right ones with no outside information, it would have produced the right answer in the first place. Intrinsic self-critique asks the model to have a skill it does not have — an oracle for its own errors. What often happens instead is that the critique pass introduces plausible-sounding second-guessing, and the revision moves away from a correct answer as easily as toward one.

This is the single most important caveat in the whole field of self-evolving agents: **a self-improvement loop with no real feedback signal is not improvement — it is drift.** Every impressive result in this series traces back to a genuine evaluator. Remove it and you are left with a model confidently rewriting itself in circles.

## What separates useful self-critique from noise

The practical distinction is the *grounding* of the critique. Ask of any self-critique step: what is the model actually checking against?

- **Grounded self-critique** (works): the model runs the code and reads the test results; queries a source and compares; calls a tool and sees the error; checks the output against an explicit rubric with verifiable criteria. The "self" is really an external signal the model interprets.
- **Ungrounded self-critique** (fails or drifts): the model is asked "is this correct?" with nothing to check against but its own judgment on a task where it cannot reliably judge. This is where performance degrades.

The design rule follows directly: **give the critic something real to check against.** Where a true external signal exists — tests, execution, retrieval, tools — self-critique is one of your best tools. Where none exists, do not manufacture false confidence by adding a critique pass; find or build a real signal instead, or keep a human in the loop.

## Techniques that add real signal

Several established methods work precisely because they smuggle in a signal beyond the model's bare judgment:

- **Execution and tests.** For anything expressible as code, running it is ground truth. A self-correction loop over a test suite is grounded and reliable.
- **Sampling and agreement.** Sampling several independent solutions and taking the majority answer exploits the fact that correct reasoning paths tend to agree more than incorrect ones do — an external-ish signal derived from consistency rather than the model's self-assessment.
- **Tool feedback.** A calculator, a database, a search engine, a type checker — any tool that can contradict the model provides grounding the model cannot fake.
- **Rubric-based critique.** A specific, checkable rubric ("does the response cite a source for each claim?") turns vague self-judgment into a series of concrete checks, which is far more reliable than "is this good?"
- **A separate, stronger evaluator.** A distinct critic — a different model, or the same model with tools the generator lacked — breaks the "grading your own homework" symmetry.

Notice the pattern: each replaces the model's opinion of itself with something harder to fool.

## Designing critique loops that help

When you build a self-critique step, three rules keep it honest. **Anchor it to a real signal** — never ship an ungrounded "are you sure?" pass and call it improvement. **Bound the iterations** — grounded loops still hit diminishing returns, and unbounded refinement wastes tokens and can wander; a small fixed cap is usually right. **Measure whether it actually helps** — run the agent with and without the critique step on a held-out set and confirm it improves the metric; if it does not, the loop is theater. That last rule is the through-line to the next post: you cannot trust *any* self-evolution mechanism, self-critique least of all, without a real evaluation to prove it earns its place.

## Key takeaways

- Self-critique is tempting because it is free, but its value depends entirely on whether the critique is grounded in a real external signal.
- Huang et al. found that *intrinsic* self-correction — fixing reasoning with no external feedback — often fails to help and can degrade performance, because the model has no reliable oracle for its own errors.
- The core caveat of self-evolving agents: an improvement loop with no real feedback signal is drift, not improvement.
- Grounded self-critique (tests, execution, tools, retrieval, explicit rubrics, a separate evaluator) works; ungrounded "is this correct?" self-judgment does not.
- Build critique loops that anchor to a real signal, bound their iterations, and are measured against a held-out set to prove they actually help.

## Further reading

- [Large Language Models Cannot Self-Correct Reasoning Yet — Huang et al., 2023](https://arxiv.org/abs/2310.01798)
- [Self-Refine: Iterative Refinement with Self-Feedback — Madaan et al., 2023](https://arxiv.org/abs/2303.17651)
- [Reflexion: Language Agents with Verbal Reinforcement Learning — Shinn et al., 2023](https://arxiv.org/abs/2303.11366)
