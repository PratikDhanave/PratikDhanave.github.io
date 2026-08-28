# LLM-as-a-Judge

*When there's no reference answer and no rule to check, you can ask a strong model to grade the output — LLM-as-a-judge. It's the technique that made open-ended evaluation practical at scale, and it's also a minefield: judges have systematic biases, can be gamed, and agree with humans only when you design the grading carefully. Used well it's indispensable; used naively it produces confident numbers that mean nothing.*

The previous post ran out of road at open-ended tasks: for a summary, an explanation, a chatbot reply, there's no reference to match and no regex to fire. The dominant modern answer is to use *another LLM as the evaluator* — the "LLM-as-a-judge" pattern. This post covers how it works, why it's powerful, and the biases that will wreck it if you don't design around them.

## The idea

An LLM judge is a model prompted to *evaluate* an output rather than produce one. You give it the input, the response (or two responses), and a rubric, and ask it to score or choose. Because a capable model *understands* language, it can assess qualities that surface metrics can't: coherence, helpfulness, whether an answer actually addresses the question, tone, reasoning quality. It approximates human judgment at a fraction of the cost and time — you can grade thousands of open-ended outputs in minutes.

There are two main modes, and the difference matters more than people expect:

- **Pointwise (scoring)** — the judge rates a single response, e.g. 1–5 on helpfulness, or pass/fail against a rubric. Simple, but absolute scores are noisy: models are inconsistent about what "4 out of 5" means from one call to the next.
- **Pairwise (comparison)** — the judge sees two responses (A vs B) and picks the better one. This is generally **more reliable**, because relative judgments ("which is better?") are easier and more stable than absolute ones ("how good, on a scale?"). Pairwise comparison is the backbone of preference evaluation and of arena-style rankings.

## Why it works — and the catch

The research that popularized this — the *Judging LLM-as-a-Judge* work behind MT-Bench and Chatbot Arena — found that strong judge models agree with human preferences at roughly the rate humans agree *with each other*, which is a strikingly good result. That's the promise: a scalable, cheap stand-in for human evaluation on open-ended tasks.

The catch is that this only holds when the grading is designed carefully. A judge is still a language model, which means it inherits language-model failure modes and adds a few of its own. Treat its output as ground truth without accounting for these and you get numbers that look rigorous and are quietly wrong.

## The biases you must design around

LLM judges have *systematic*, repeatable biases — not random noise, but consistent tilts that skew results in one direction:

- **Position bias** — the judge tends to favor the response shown *first* (or sometimes second), regardless of quality. This is the most notorious one. The fix: **run each pairwise comparison both ways** (A-then-B and B-then-A) and only count a win if the judge picks the same response in both orders; ties/flips are thrown out or counted as ties.
- **Verbosity bias** — judges systematically prefer *longer*, more elaborate answers even when a concise one is better or equally correct. Length reads as thoroughness. Guard against it with rubrics that explicitly value concision and by checking whether your "winner" is just consistently wordier.
- **Self-preference bias** — a judge tends to rate outputs from its *own model family* more highly. If you generate with GPT-family and judge with the same, expect an inflated score. Prefer a judge from a *different* family than the system under test, or at least be aware of the tilt.
- **Sycophancy and formatting halo** — confident tone, authoritative phrasing, nice markdown, and citations (even fabricated ones) can all inflate scores. The judge, like a human, is swayed by presentation. This is the same "fluency ≠ correctness" trap from post 1, now inside your evaluator.

None of these are dealbreakers. They're *known* biases, which means you can control for them. The teams that get value from LLM judges are the ones that treat these as first-class design constraints, not footnotes.

## Designing a judge that works

A reliable judge is mostly a matter of disciplined prompt and protocol design:

- **Give a concrete rubric, not "rate this."** Specify the exact criteria (accuracy, relevance, completeness, safety) and what each score level means. Vague prompts produce vague, unstable scores; specific rubrics produce reproducible ones.
- **Ask for reasoning before the verdict.** Having the judge explain *why* before giving a score improves quality and gives you an audit trail — you can read the rationale and catch when the judge misunderstood the task. (It also lets you spot when it's being swayed by length or tone.)
- **Prefer pairwise, and randomize + swap order.** Comparisons beat absolute scores; swapping order neutralizes position bias.
- **Use a strong, different-family judge**, and consider a *panel* — several judges voting — for high-stakes evals, which reduces any single model's idiosyncrasies.
- **Constrain the output format** (a JSON verdict) so scores are machine-parseable and consistent.

## Validate the judge itself

The step almost everyone skips: **the judge is a measurement instrument, so calibrate it against ground truth.** Take a sample of outputs, have *humans* grade them, then check how well the LLM judge's verdicts agree with the humans (using an agreement statistic like Cohen's kappa, not raw accuracy, so chance agreement is accounted for). If agreement is high, you can trust the judge to scale; if it's low, your judge is measuring something other than what you intended, and any downstream number built on it is fiction.

This closes the loop: you use humans to validate the judge on a small sample, then use the validated judge to evaluate at scale. The judge doesn't *replace* human evaluation — it *amortizes* it. And you should re-validate whenever the task or the judge model changes, because a judge calibrated for one domain can silently drift on another. An LLM judge you've never checked against humans is not an eval; it's a vibe with a number attached.

## Key takeaways

- **LLM-as-a-judge** uses a capable model to grade open-ended outputs, assessing qualities (coherence, helpfulness, faithfulness) that surface metrics can't — cheaply and at scale.
- **Pairwise comparison beats pointwise scoring**: "which is better?" is more stable than "how good, 1–5?", which is why comparisons underpin preference and arena-style evaluation.
- Judges have **systematic biases** — position (favoring order), verbosity (favoring length), self-preference (favoring their own family), and susceptibility to confident tone/formatting — that are repeatable and must be designed around, not ignored.
- Control them with **order-swapping** (count a win only if it holds both ways), **concise-favoring rubrics**, a **different-family judge** (or a voting panel), and **rubric-plus-reasoning** prompts that produce reproducible, auditable verdicts.
- Treat the **judge as an instrument and calibrate it**: validate its verdicts against human grades on a sample (using agreement statistics like kappa), and re-validate when the task or model changes — an unvalidated judge is not an evaluation.

## Further reading

- [Judging LLM-as-a-Judge with MT-Bench and Chatbot Arena — Zheng et al., arXiv:2306.05685](https://arxiv.org/abs/2306.05685)
- [Chatbot Arena: An Open Platform for Evaluating LLMs — Chiang et al., arXiv:2403.04132](https://arxiv.org/abs/2403.04132)
