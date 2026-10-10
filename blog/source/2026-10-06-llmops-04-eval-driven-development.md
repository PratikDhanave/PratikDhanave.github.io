# Eval-Driven Development — You Can't Ship What You Can't Measure

*The single practice that separates teams who improve their LLM apps from teams who just change them is evaluation. Without a trustworthy way to measure quality, every prompt tweak is a gamble — you fix one case, break two others, and never know. Eval-driven development makes the eval set the center of gravity: you build it before you optimize, you gate every change on it, and you treat it as the most valuable asset the project owns. This post is about building evaluation you can actually trust.*

Post 2 made offline evaluation the gate between develop and deploy. This post is how to build that gate. The hard truth underneath it: LLM output quality is fuzzy and non-deterministic (post 1), so "it looks good to me" doesn't scale and doesn't survive. Eval-driven development replaces vibes with a repeatable, graded measurement that tells you whether a change is actually an improvement.

## The eval set is the asset

The foundation of everything is a **curated evaluation set**: a collection of representative inputs paired with what good output looks like. This is the ground truth your whole loop runs on, and building a good one is the highest-leverage work in LLMOps:
- **Representative** — it should cover the real distribution of inputs: the common cases, the important edge cases, and crucially the *failure cases you've already hit in production* (post 2's backward flow). An eval set that only has easy cases tells you nothing.
- **Graded by difficulty and importance** — some cases are "must never get wrong" (safety, core use case); others are nice-to-have. Knowing which is which keeps you from trading a critical regression for a cosmetic win.
- **Living** — every real-world failure becomes a new eval case, so the set grows to encode everything the system has ever gotten wrong. This is what makes the loop have *memory*: a bug fixed and added to evals can't silently return.

A team's eval set is more valuable than any individual prompt, because prompts are cheap to change and the eval set is what tells you *which* change is better. Guard it, grow it, and version it like the asset it is.

## How to evaluate open-ended output

The awkward part: how do you *score* an open-ended answer when there's no single right string? There's a toolbox, and mature teams layer several:

- **Deterministic / rule-based checks** — the cheap, reliable first line. Does the output parse as valid JSON? Does it contain the required fields, stay under a length limit, avoid forbidden content, match a regex or a known answer for factual cases? Wherever correctness *can* be made exact, make it exact — it's fast, free, and non-flaky.
- **Reference-based metrics** — compare against a gold answer using similarity (semantic similarity via embeddings, or classic overlap metrics). Useful when there's a canonical answer, limited when there are many valid phrasings.
- **LLM-as-judge** — use a strong model to grade output against a rubric ("is this answer accurate, complete, and on-topic given this reference?"). This scales to the fuzzy qualities rules can't capture, but it must be used carefully: judges have biases (length, position, self-preference), so you calibrate the judge against human ratings, use clear rubrics, and spot-check it. A judge you haven't validated is just another opinion.
- **Human evaluation** — the ultimate ground truth, expensive and slow, so you spend it where it matters: calibrating the automated methods, auditing high-stakes cases, and sampling. The goal is to make human judgment *efficient*, not to do it on every case.

The practical pattern is a pyramid: cheap deterministic checks on everything, reference/judge metrics for quality, human review for calibration and high stakes. No single method is enough — rules miss nuance, judges have biases, humans don't scale — so you combine them.

## Making it drive development

Having evals is necessary; *using* them as the driver is the discipline:
- **Gate changes on the eval set.** Every prompt, model, or config change runs against the evals *before* it ships, and a change that regresses the must-pass cases doesn't merge. This is the mechanism that lets you iterate quickly without fear — you can try an aggressive prompt rewrite because the eval set will catch what it breaks.
- **Track scores over time, per version.** Tie eval results to the prompt configuration version (post 3) so you can see quality trending up or down across releases and attribute changes to specific versions.
- **Compare, don't just score.** The useful question is rarely "is this good?" but "is version B better than version A?" Run both against the same set and compare — relative comparison is more reliable than absolute scores and is exactly what you need to decide whether to ship.
- **Beware overfitting to the eval set.** If you only ever optimize against the same frozen set, you can tune to it while real quality stalls — the same trap as overfitting in ML. Keep growing the set with fresh production cases so it stays an honest proxy for reality.

The mindset shift is to treat quality as something you *measure and move*, not something you hope for. Teams that evaluate can answer "did this change help?" with evidence; teams that don't are editing a non-deterministic system in the dark, and it shows up as the mysterious quality drift that plagues unmeasured LLM apps.

The takeaway: evaluation is the practice that separates improving an LLM app from merely changing it, because quality is fuzzy and non-deterministic and "looks good to me" doesn't scale. The center of gravity is a **curated eval set** — representative (including real production failures), graded by importance, and *living* — which is more valuable than any prompt because it tells you which change is better and gives the loop memory. Score open-ended output with a **layered toolbox**: cheap **deterministic checks** wherever correctness can be exact, **reference-based metrics**, **LLM-as-judge** (calibrated against humans, watched for bias), and **human review** spent on calibration and high stakes. Then *drive* development with it: **gate every change on the evals**, track scores per version, **compare B vs A** rather than scoring in the abstract, and keep growing the set to avoid overfitting.

## Key takeaways

- Without trustworthy evaluation, every change is a gamble on a fuzzy, non-deterministic system — "looks good to me" doesn't scale; **eval-driven development** replaces vibes with repeatable, graded measurement.
- The **curated eval set** is the core asset: **representative** (common + edge + *real production failures*), **graded** by importance (must-never-fail vs. nice-to-have), and **living** (every failure becomes a case) — which gives the loop *memory*. It's worth more than any single prompt.
- Score open-ended output with a **layered toolbox**: **deterministic/rule-based** checks wherever correctness can be exact (cheap, non-flaky), **reference-based** similarity metrics, **LLM-as-judge** (scales to fuzzy quality but must be *calibrated against humans* and watched for length/position/self bias), and **human eval** (ground truth, spent on calibration + high stakes). No single method suffices.
- **Drive** development with evals: **gate** every prompt/model/config change before shipping (block regressions on must-pass cases), **track scores per version** (post 3), and **compare B vs A** on the same set rather than scoring absolutely.
- **Beware overfitting** to a frozen eval set — keep adding fresh production cases so it stays an honest proxy; teams that evaluate answer "did this help?" with evidence, the rest drift in the dark.

## Further reading

- [Evaluation of machine translation and text — metrics for generated text](https://en.wikipedia.org/wiki/Evaluation_of_machine_translation)
- [Test-driven development — the gate-every-change discipline evals borrow](https://en.wikipedia.org/wiki/Test-driven_development)
