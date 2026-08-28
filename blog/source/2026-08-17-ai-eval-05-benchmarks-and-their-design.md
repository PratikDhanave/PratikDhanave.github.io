# Benchmarks and How They're Designed

*The scores that dominate model announcements — MMLU, GSM8K, HumanEval, and the rest — are benchmarks: standardized public tests that let the whole field compare models on common ground. They've driven enormous progress, but a benchmark is only as good as its design, and a number without understanding of what it measures is easy to misread. Knowing how benchmarks are built, and what makes a good one, is how you read a leaderboard critically instead of credulously.*

The previous posts built *your* evaluation for *your* task. This one steps back to the public benchmarks the whole field uses. They serve a different purpose than your bespoke evals — comparison across models rather than fitness for your use case — and they come with their own design principles and pitfalls. Understanding them makes you a better consumer of the numbers everyone quotes.

## What a benchmark is for

A **benchmark** is a fixed, standardized dataset plus a scoring method, published so that anyone can run it against any model and get comparable numbers. Its job is *comparison on common ground*: it lets the field say "model X scores 88 and model Y scores 84 on this test," and lets progress be tracked over years. Benchmarks created the shared yardsticks that made LLM progress legible and competitive.

They come in a few shapes. **Knowledge and reasoning** benchmarks like MMLU test breadth across many subjects with multiple-choice questions. **Task-specific** ones target a capability — GSM8K for grade-school math, HumanEval for code (scored by running the code against tests). **Aggregate suites** like HELM and BIG-bench bundle many tasks to give a holistic, multi-dimensional picture rather than a single score. And **arena-style** evaluation (Chatbot Arena) ranks models by human pairwise preferences on open-ended prompts, using an Elo-like system — a living benchmark rather than a fixed dataset.

## The critical distinction: benchmarks vs. your evals

The single most important thing to internalize: **a benchmark measures general capability; it does not measure fitness for your task.** A model topping MMLU may be worse at *your* customer-support domain than a lower-ranked one, because MMLU tests broad academic knowledge, not your product's needs.

So benchmarks and the bespoke evals from earlier posts answer different questions:

- **Benchmarks** — "how capable is this model in general, relative to others?" Use them to *shortlist* models and track the field.
- **Your evals** — "how well does this model do *my* task?" Use them to *choose and tune* what you ship.

Benchmarks narrow the field; your evals make the decision. Choosing a model on benchmark rank alone is one of the most common and expensive mistakes in applied AI — the leaderboard is a starting point, not a verdict.

## What makes a good benchmark

Not all benchmarks are equally trustworthy. Good ones share design properties worth checking before you weight a score heavily:

- **Construct validity** — it actually measures what it claims. A "reasoning" benchmark that can be aced by pattern-matching surface features isn't measuring reasoning. This is the hardest and most important property, and the easiest to get subtly wrong.
- **Discriminative power** — it separates models. If everything scores 95%, the benchmark is *saturated* and no longer informative; it has stopped doing its job (see below).
- **Difficulty and headroom** — hard enough that there's room to improve, so it stays useful as models get better.
- **Contamination resistance** — the test data shouldn't be trivially present in training data, or the score measures memorization rather than capability (the whole subject of the next post).
- **Clear, reproducible scoring** — an unambiguous, automatable metric so different evaluators get the same number. Even MMLU results vary between harnesses because of prompt-formatting and answer-extraction differences, which is why reported numbers must state *how* they were measured.
- **Adequate size and coverage** — enough items, spanning enough of the target skill, that the score is stable and representative.

## Saturation: benchmarks wear out

Benchmarks have a lifespan. When models approach the ceiling — everyone scoring in the high 90s — the benchmark **saturates** and stops discriminating. Worse, the remaining few percent are often the benchmark's own *errors and ambiguities*, so pushing the score higher measures noise, not capability. This is why the field constantly retires old benchmarks and builds harder ones: as models mastered earlier tests, successively more demanding benchmarks (harder reasoning, expert-level questions, adversarially-filtered items) were created to restore headroom.

The practical consequence: **a near-perfect score on a well-known benchmark often means the benchmark is exhausted, not that the model is perfect.** When you see 97% on a familiar test, the interesting question is what the model gets *wrong* and whether those failures are real deficiencies or dataset flaws — and whether a fresher, harder benchmark tells a different story.

## Reading a leaderboard critically

Putting it together, a disciplined way to read benchmark numbers:

- **Ask what the benchmark actually tests**, and whether that resembles your use case. General knowledge ≠ your domain.
- **Check how it was measured** — few-shot vs zero-shot, prompt format, whether chain-of-thought was allowed. The same model and benchmark yield different numbers under different protocols, so cross-source comparisons are often apples-to-oranges.
- **Watch for saturation** — a crowded top of the leaderboard means the benchmark has lost resolution.
- **Consider contamination** — was the test likely in training data? (Next post.)
- **Never let a benchmark rank substitute for your own eval.** It shortlists; it doesn't decide.

Benchmarks are one of the field's great tools — they made progress measurable and competitive. But they're instruments with known limits, not oracles. Read them as a capable, skeptical engineer: understand what each measures, how it was scored, and where it's worn out, and always confirm on your own task before you ship.

## Key takeaways

- A **benchmark** is a fixed public dataset plus a scoring method, built for **comparison on common ground** — knowledge suites (MMLU), task-specific tests (GSM8K, HumanEval), aggregate suites (HELM, BIG-bench), and arena-style human-preference rankings.
- Benchmarks measure **general capability, not fitness for your task** — they shortlist models and track the field, but your own evals make the shipping decision; choosing on benchmark rank alone is a classic, costly mistake.
- Good benchmarks have **construct validity** (measure what they claim), discriminative power, difficulty/headroom, contamination resistance, reproducible scoring, and adequate coverage.
- Benchmarks **saturate**: as models approach the ceiling they stop discriminating, and the last few percent are often dataset errors — a near-perfect score usually means the benchmark is exhausted, not the model perfect.
- **Read leaderboards critically**: check what's actually tested, how it was measured (few-shot, prompt format, CoT), whether it's saturated or contaminated, and always validate on your own task before deciding.

## Further reading

- [Beyond the Imitation Game (BIG-bench) — Srivastava et al., arXiv:2206.04615](https://arxiv.org/abs/2206.04615)
- [HellaSwag: Can a Machine Really Finish Your Sentence? — Zellers et al., arXiv:1905.07830](https://arxiv.org/abs/1905.07830)
