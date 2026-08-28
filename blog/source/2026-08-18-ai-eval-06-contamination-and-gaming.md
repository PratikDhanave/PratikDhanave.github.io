# Contamination, Gaming, and Goodhart's Law

*A benchmark score is trustworthy only if the model hasn't seen the answers and no one has optimized directly for the test. Both assumptions fail constantly. Training data contamination inflates scores by rewarding memorization; optimizing for a benchmark turns it from a measure into a target and destroys its meaning. This post is about the ways evaluation gets corrupted — and how to defend against them.*

The previous post covered how benchmarks are designed. This one covers how they're *broken* — sometimes accidentally, sometimes deliberately. The unifying principle is a law of measurement that predates AI by decades, and understanding it is the difference between numbers you can trust and numbers that are quietly lying to you.

## Data contamination

**Contamination** is when the test data has leaked into the model's training data. Because frontier models train on enormous web scrapes, and popular benchmarks are published *on the web*, the benchmark's questions and answers are very likely somewhere in the training corpus. When that happens, a high score may reflect **memorization, not capability** — the model has effectively seen the exam beforehand.

Contamination is insidious because it's usually invisible and unintentional. No one set out to cheat; the benchmark simply ended up in the crawl, along with the countless blog posts, GitHub repos, and papers that quote it. The result is scores that overstate real ability, and worse, that overstate it *unevenly* — a model contaminated on benchmark A but not B will look artificially strong on A, corrupting comparisons.

Detecting it is hard. Techniques exist — checking whether a model can complete a benchmark item verbatim from a partial prompt, comparing performance on the original test vs. a freshly-written equivalent, or looking for suspiciously low "perplexity" on test items — but none is definitive, and model providers rarely disclose their training data. The honest stance is to *assume* any well-known public benchmark is at least partly contaminated for any model trained after that benchmark was published, and to weight it accordingly.

## Goodhart's law: the deeper problem

Contamination is a special case of a more general trap, captured by **Goodhart's law**: *when a measure becomes a target, it ceases to be a good measure.* The moment a metric is something you optimize *toward* rather than merely observe, you start improving the metric in ways that don't improve the underlying thing it was meant to track.

In AI evaluation this shows up everywhere:

- **Benchmark optimization.** If a team tunes models specifically to score well on MMLU or a popular leaderboard — training on similar data, formatting for the benchmark's quirks — the score rises while general capability may not. The benchmark stops measuring capability and starts measuring "effort spent on this benchmark."
- **Overfitting to your own eval.** The same happens *internally*. Iterate against a fixed eval set long enough and you'll start (often unconsciously) tuning to its idiosyncrasies. The eval score climbs; real-world quality plateaus. Your own golden set can rot into a target you're gaming.
- **Proxy metrics gone wrong.** Optimize "response length" as a proxy for thoroughness and you get verbose padding. Optimize a single LLM-judge score and you may be optimizing the judge's *verbosity bias* (post 3) rather than quality.

Goodhart's law is not a bug to be fixed; it's a property of optimization. The defense is not to find an ungameable metric — none exists — but to *design your evaluation so gaming it is hard and detectable.*

## Defending against contamination and gaming

Several practices, used together, keep evaluation honest:

- **Held-out and private test sets.** The strongest defense: keep some evaluation data *secret*, never published and never sent anywhere it could be scraped or trained on. A private held-out set can't be contaminated because no one outside has seen it, and it can't be gamed because no one can optimize toward what they can't see. This is why serious evaluations reserve a private slice.
- **Fresh and dynamic benchmarks.** Continuously generate *new* test cases — questions written after the model's training cutoff, or procedurally generated variants — so there's nothing to have memorized. Live, rotating benchmarks (and human-preference arenas fed by ever-new prompts) resist contamination by construction.
- **Rotate and refresh your own eval set.** Don't iterate against the *exact* same cases forever. Periodically add new cases and retire stale ones so you're not overfitting to a frozen target. Keep a stable golden set for long-term comparison, but pair it with rotating cases that catch overfitting.
- **Separate development and test sets.** Borrow the oldest trick in machine learning: iterate against a *development* set, but measure final quality on a *test* set you touch rarely. If dev and test scores diverge, you're overfitting the dev set — a direct, measurable signal of Goodhart's law in action.
- **Use diverse, complementary metrics.** A single number is easy to game; a suite that measures genuinely different things (post 2) is much harder to satisfy dishonestly, because a cheat that inflates one metric usually shows up as a discrepancy in another.

## The mindset: treat every number as a claim to be checked

The through-line of this post is skepticism as a discipline. A benchmark score is not a fact about a model; it's a *claim* produced under conditions that may or may not have been honest. Before trusting one, ask: could the model have seen this data? Was the metric optimized toward, directly or indirectly? Is this the dev set I've been iterating on, or a genuine held-out test? Is one metric hiding a regression in another?

This isn't cynicism — it's the same rigor you'd apply to any experiment. The teams that ship reliable AI are the ones that treat their own evaluations adversarially, actively hunting for the ways their numbers might be lying, rather than celebrating a score and moving on. Contamination and Goodhart's law guarantee that some of your numbers *will* be misleading; the only question is whether you catch it before your users do.

## Key takeaways

- **Contamination** — benchmark data leaking into training data (near-inevitable for public benchmarks scraped from the web) — inflates scores by rewarding **memorization over capability**, and unevenly, corrupting model comparisons.
- Contamination is a special case of **Goodhart's law**: *when a measure becomes a target, it ceases to be a good measure* — optimizing toward a benchmark, or overfitting your own eval set, raises the score without raising real quality.
- Gaming happens even unintentionally: iterating against a fixed eval long enough tunes you to its quirks, and optimizing proxy metrics (length, a single judge score) optimizes the proxy's biases, not quality.
- Defend with **private held-out sets** (can't be contaminated or gamed if no one's seen them), **fresh/dynamic benchmarks** (nothing to memorize), **rotating your own cases**, and a **dev/test split** where divergence is a direct overfitting signal.
- Adopt a **skeptical mindset**: treat every score as a claim to verify — could the model have seen this? was the metric optimized toward? is this dev or held-out test? — and evaluate your own numbers adversarially before users expose the gaps.

## Further reading

- [Goodhart's law — overview](https://en.wikipedia.org/wiki/Goodhart%27s_law)
- [Holistic Evaluation of Language Models (HELM) — Liang et al., arXiv:2211.09110](https://arxiv.org/abs/2211.09110)
