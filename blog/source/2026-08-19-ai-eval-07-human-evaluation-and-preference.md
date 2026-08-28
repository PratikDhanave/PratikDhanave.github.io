# Human Evaluation and Preference

*Automated metrics and LLM judges are scalable proxies for the thing that actually matters: whether a human finds the output good. Human evaluation is the ground truth those proxies are calibrated against — and getting it right is its own discipline, full of subtle traps around agreement, bias, and how you ask the question. This post is about doing human eval well, and about how human preference became the signal that trains models themselves.*

Every metric in this series is ultimately trying to approximate human judgment. Sometimes you have to go to the source. Human evaluation is slower and more expensive than everything we've covered, but it's the anchor: the thing you use to validate your automated evals, to make final calls on high-stakes quality, and — increasingly — to *train* models directly. This post covers how to run it rigorously and why it underlies modern model development.

## When you need humans

Automated evaluation is the default because it's fast and cheap. Reach for humans when automation isn't enough:

- **Validating your automated evals.** As post 3 stressed, an LLM judge is only trustworthy once you've checked it against human grades. Humans are the calibration standard for your cheaper instruments.
- **Subjective and nuanced quality.** Helpfulness, tone, tact, cultural appropriateness, "would I actually use this answer" — qualities that resist formalization are where human judgment still clearly beats proxies.
- **High-stakes decisions.** Before a major launch or a model swap, human review of a sample catches failures automated metrics miss.
- **Novel tasks with no established metric.** When you're doing something new, humans define what good means before you can build an automated proxy for it.

The goal is not to human-evaluate everything — that doesn't scale — but to use humans where their judgment is *load-bearing*, and to amortize it through automation everywhere else.

## Agreement: the first hard problem

The moment you have more than one human rater, you discover they disagree — and how you handle that disagreement determines whether your human eval means anything. Two people grading the same summary will often give different scores, because quality is genuinely subjective and because instructions are always somewhat ambiguous.

**Inter-annotator agreement** measures how much your raters actually agree, and it's the health check for your whole human-eval process. Crucially, you measure it with a statistic that corrects for chance — **Cohen's kappa** (two raters) or **Fleiss' kappa** (more) — not raw agreement percentage, because two raters guessing randomly on a yes/no task agree 50% of the time by luck alone. Kappa subtracts that chance baseline.

Low agreement is a *diagnosis*, not just a number: it usually means your **rubric is ambiguous**, not that your raters are bad. The fix is to tighten the instructions — clearer criteria, concrete examples of each score level, edge-case guidance — and re-measure. High agreement means your notion of "good" is well-defined enough to be measured consistently; low agreement means it isn't, and any score built on it is unreliable. Agreement is thus both a quality gate on your process and a forcing function to make "good" precise.

## Designing human evaluation that works

The way you ask determines the quality of the answer. Well-run human evaluation borrows the same discipline as LLM judging (unsurprisingly, since judges imitate humans):

- **Prefer comparison over rating.** "Which of these two is better?" yields more consistent data than "rate this 1–7," for the same reason it does with LLM judges: relative judgments are more stable than absolute ones. Absolute rating scales drift between people and over time.
- **Write a concrete rubric with examples.** Vague instructions ("rate the quality") produce low agreement. Specific criteria plus anchor examples for each level align raters and raise agreement.
- **Randomize and blind.** Randomize the order of options and hide which system produced which output, so raters aren't biased by position or by knowing "this is the new model." The same position and halo biases that afflict LLM judges afflict people.
- **Use multiple raters and aggregate.** Several raters per item, combined (majority vote or averaging), smooths individual noise and idiosyncrasy — and lets you compute agreement.
- **Watch rater quality and fatigue.** Attention flags over long sessions; include occasional gold-standard items with known answers to catch raters who've stopped reading, and keep tasks short enough to sustain care.

## From evaluation to arenas

Human *comparison*, done at scale, becomes a ranking system. **Chatbot Arena** popularized this: real users submit prompts, get two anonymous model responses, and vote for the better one. Aggregating millions of these pairwise votes with an **Elo-style rating** (the system used to rank chess players) produces a live leaderboard grounded entirely in human preference on real, ever-changing prompts.

This design is quietly powerful. It resists contamination (prompts are fresh and user-generated), it measures what users actually prefer rather than an academic proxy, and being pairwise it inherits the stability of comparison over absolute scoring. Its limits are the limits of preference itself: humans can prefer confident, verbose, or flattering answers over more correct ones, so arena rank measures *preference*, which is related to but not identical with *correctness* — the same fluency-vs-truth caveat, now at population scale.

## Preference as a training signal

The deepest connection is that human preference doesn't just *evaluate* models — it *trains* them. Modern alignment (RLHF and its relatives) works by collecting exactly the pairwise human comparisons described above — "which response is better?" — and using them to teach the model to produce more-preferred outputs. The evaluation data *is* the training data.

This closes a loop that reframes the whole series: the same pairwise-comparison methodology serves as your quality measurement *and* as the fuel for improving the model, and the two are continuous. It also raises the stakes on doing human evaluation well — biases in how you collect preferences don't just skew a report, they get *baked into model behavior* (a model trained on length-biased preferences learns to be verbose). Rigorous human evaluation, then, isn't only about grading what exists; it's about shaping what the model becomes. Which is the strongest possible argument for taking its methodology — agreement, blinding, comparison, clear rubrics — seriously.

## Key takeaways

- **Human evaluation is the ground truth** that automated metrics and LLM judges approximate — use it to *validate* your cheaper instruments, judge subjective/nuanced quality, make high-stakes calls, and define "good" for novel tasks.
- **Inter-annotator agreement** (measured with chance-corrected **Cohen's/Fleiss' kappa**, not raw percentage) is the health check on human eval; low agreement usually means an **ambiguous rubric**, not bad raters — tighten instructions and re-measure.
- Design for reliability: **prefer pairwise comparison** over absolute rating, write concrete rubrics with anchor examples, **randomize and blind**, use multiple raters, and guard against fatigue with gold-standard checks.
- Human comparison at scale becomes an **arena** (Chatbot Arena + Elo): fresh, contamination-resistant, and grounded in real preference — but it measures *preference*, which tracks but isn't identical to correctness.
- **Human preference is also the training signal** behind RLHF-style alignment — the same pairwise data both evaluates and improves models — so biases in how you collect preferences get baked into model behavior, making rigorous methodology doubly important.

## Further reading

- [Judging LLM-as-a-Judge with MT-Bench and Chatbot Arena — Zheng et al., arXiv:2306.05685](https://arxiv.org/abs/2306.05685)
- [Chatbot Arena: An Open Platform for Evaluating LLMs — Chiang et al., arXiv:2403.04132](https://arxiv.org/abs/2403.04132)
