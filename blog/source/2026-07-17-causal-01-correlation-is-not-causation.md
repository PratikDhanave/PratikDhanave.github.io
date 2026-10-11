# Correlation Is Not Causation — Why Engineers Keep Getting This Wrong

*Every data-driven engineer knows the phrase "correlation is not causation," and almost everyone violates it anyway — in A/B test readouts, in metric dashboards, in ML models used to make decisions. The gap between "these move together" and "this causes that" is where enormous amounts of money and effort get wasted on changes that don't work. Causal inference is the discipline of crossing that gap rigorously, and this series builds it from first principles for people who build systems.*

This series fills a gap in the blog's data and ML coverage: machine learning is superb at *prediction* (what correlates with what) but silent on *causation* (what happens if I intervene) — and most real decisions are causal. It assumes the [machine learning foundations](/blog/series/machine-learning-from-first-principles/) and some comfort with data. Post 1 makes the problem vivid and precise, because you can't appreciate the machinery until you feel why the easy answer fails.

## The difference that changes everything

Two variables are **correlated** when they move together — when one is high, the other tends to be. Two variables are in a **causal** relationship when *changing one actually changes the other*. These are completely different claims, and the difference is the whole game:

- **Correlation answers:** "If I *observe* X, what should I expect for Y?" (prediction)
- **Causation answers:** "If I *intervene* and change X, what will happen to Y?" (decision)

Almost every decision is secretly causal. "Will adding this feature increase retention?" "Will this discount drive more purchases?" "Will this drug improve outcomes?" Each asks what happens *if we act* — a causal question — but we usually answer it with correlational data ("users who used the feature retained better"), which can be flatly, expensively wrong. The retention-feature users might have retained anyway because they were already your most engaged users; the feature caused nothing. Mistaking correlation for causation means shipping changes that don't work and claiming credit for outcomes you didn't cause — a failure mode endemic to data-driven teams.

## The three reasons correlation appears without causation

Correlation between X and Y can arise in several ways, and only one of them is "X causes Y." Knowing the alternatives is the core skill:

- **Reverse causation** — Y actually causes X, not the other way around. "Hospitals correlate with death, so hospitals are dangerous" — no, being sick causes both hospital visits and death. The arrow points the opposite way from the naive reading.
- **Confounding (the big one)** — a *third* variable causes both X and Y, creating a correlation between them with no direct causal link. Ice-cream sales correlate with drownings, but neither causes the other; *hot weather* causes both. Confounding is the single most important concept in the series (post 3), because it's the most common and most dangerous source of fake causal conclusions — and it's everywhere in observational data.
- **Selection effects and coincidence** — the correlation is an artifact of *how the data was collected* (you only sampled a biased subset) or pure chance (test enough variable pairs and some will correlate by luck — spurious correlation).

The practical lesson: when you see a correlation, "X causes Y" is only *one* of several explanations, and usually not the most likely one. The discipline of causal inference is systematically ruling out the alternatives — reverse causation, confounding, selection — until a causal claim is actually justified. Until you've done that, you have a pattern, not a cause.

## Why this is an engineering problem, not just a stats one

It's tempting to file this under "statistics" and move on, but causal confusion is deeply an *engineering and product* problem, because engineers constantly make causal claims from data:

- **A/B tests** are the engineer's main causal tool — and they're powerful *because* randomization solves the causal problem (post 4). But teams routinely undermine them (peeking, bad segmentation, ignoring interference) and, worse, make causal claims from *non-randomized* data ("users who did X converted more") as if it were an experiment. Knowing which analyses support causal claims and which don't is core data literacy.
- **ML models encode correlations, not causes** — a model predicting churn finds what *correlates* with churn, which is perfect for *flagging* at-risk users but can be actively misleading for *deciding what to do about it*. Acting on a model's correlational features (e.g. "users who contact support churn, so reduce support") can backfire catastrophically because the feature wasn't causal. Using predictive models to drive *interventions* is exactly where correlation-causation confusion bites hardest, and it's an increasingly common mistake as ML is wired into decisions.
- **Metrics and dashboards** invite causal stories ("retention went up after we shipped the redesign, so the redesign worked") that ignore everything else that changed. Observational "before/after" is one of the weakest forms of causal evidence.

The through-line of the series is that answering "what happens if we act?" requires more than data — it requires *reasoning about the data-generating process* and either controlling it (experiments) or carefully modeling it (causal inference on observational data). This post establishes the stakes; the rest build the tools: the potential-outcomes way of defining causal effects precisely (post 2), confounding and why it's the central villain (post 3), randomized experiments as the gold standard (post 4), causal graphs for reasoning about it (post 5), and the observational and natural-experiment methods for when you can't randomize (posts 6–7). Engineers who internalize this stop shipping changes that "the data supported" and don't work — and start knowing the difference between a pattern and a cause.

The throughline: **correlation** ("these move together" — answers *if I observe X, expect Y*, prediction) is categorically different from **causation** ("changing X changes Y" — answers *if I intervene on X, what happens to Y*, decision), and almost every real decision is secretly causal yet usually answered with correlational data — which is expensively wrong. A correlation between X and Y has several explanations beyond "X causes Y": **reverse causation**, **confounding** (a third variable causing both — the central villain, post 3), and **selection/coincidence** — so a causal claim is only justified after systematically ruling these out. This is an **engineering problem**: A/B tests work *because* randomization solves causality while non-randomized "users who did X" claims don't; **ML encodes correlations not causes**, so acting on a predictive model's features for *interventions* backfires; and before/after dashboards invite weak causal stories. The series builds the tools to answer "what happens if we act?" rigorously.

## Key takeaways

- **Correlation** (X and Y move together → answers "if I *observe* X, expect Y", prediction) is categorically different from **causation** (changing X changes Y → answers "if I *intervene* on X, what happens to Y", decision) — and almost every decision ("will this feature/discount/drug work?") is secretly **causal** yet usually answered with correlational data, which can be flatly wrong.
- A correlation between X and Y has several explanations besides "X causes Y": **reverse causation** (Y causes X), **confounding** (a third variable causes both — the most common and dangerous, post 3), and **selection effects/coincidence** — so "X causes Y" is only one hypothesis, usually not the likeliest; causal inference systematically *rules out the alternatives*.
- This is an **engineering/product** problem: **A/B tests** are causal *because* randomization (post 4), but teams make causal claims from **non-randomized** data as if it were an experiment.
- **ML models encode correlations, not causes** — great for *flagging* (churn prediction) but misleading for *deciding what to do* (acting on correlational features for interventions backfires) — the fastest-growing version of this mistake as ML drives decisions.
- The series builds the tools to answer "**what happens if we act?**" rigorously: potential outcomes (post 2), confounding (post 3), randomized experiments (post 4), causal graphs (post 5), and observational/natural-experiment methods (posts 6–7) — turning "the data supported it" into actually knowing a cause.

## Further reading

- [Causal inference — the discipline of identifying causes](https://en.wikipedia.org/wiki/Causal_inference)
- [Correlation does not imply causation — the core caution](https://en.wikipedia.org/wiki/Correlation_does_not_imply_causation)
