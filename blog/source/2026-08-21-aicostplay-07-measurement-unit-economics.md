# Measurement and Unit Economics

*Every lever in this playbook shares one precondition: you have to measure. The vendor percentages are directional signposts, not promises — the only number that governs your bill is the one from your own workload. Measurement, and the right unit of measurement, is what turns a list of tactics into an actual reduction.*

The levers so far are only as good as your ability to *measure* their effect, and to measure the *right thing*. This post covers the measurement discipline that underlies the whole playbook: why you measure on your own workload, what unit to measure (unit economics, not raw spend), and a consolidated ranking of the levers by measured impact. It's the meta-lever — the one that makes all the others real.

## Measure on your own workload

The single most important caveat, repeated by the vendors themselves and throughout this playbook: **every quoted percentage is the vendor's own measured or advertised figure on the vendor's own benchmark — directional, not a guarantee.** Anthropic states this explicitly about its own numbers, and it applies equally to AWS, Google, and Microsoft figures. They tell you a lever *can* help and roughly how much; they do *not* tell you what it'll do on *your* traffic.

Why the gap? Because the effect of every lever depends on your specific workload:

- **Caching savings depend on your cache hit rate**, which depends on how much stable prefix your prompts share — a vendor's 90% assumes a workload structured for it.
- **Model-selection savings depend on your task mix** — the frontier model is cheaper per task on some tasks, the mid-tier on others (the model-selection post), so "which is cheaper" is a fact about *your* tasks.
- **Effort-tuning savings depend on where your tasks sit on the accuracy-vs-cost curve** — flat for some, steep for others.
- **Commitment savings depend on how predictable your baseload is** — worthless if you over-commit.

So the vendor numbers are *signposts* — they tell you which levers are worth investigating and their rough ceiling — but the number that governs your bill is the one you measure on your own workload. **The practice: for each lever, measure before and after on a representative sample of your real traffic, and trust that number over any published percentage.** This isn't a disclaimer to skip past; it's the core discipline. A lever that saves 90% on a vendor benchmark and 5% on your workload is a 5% lever *for you*, and only measurement tells you which.

## Measure the right unit: unit economics, not raw spend

The second measurement lesson is *what* to measure. Raw total spend is a poor optimization target, because it moves with volume — spend can rise while efficiency improves (you're serving more), or fall while efficiency worsens (you're serving less). The right target is **unit economics**: cost per unit of value delivered — cost per completed task, per request, per resolved ticket, per customer, per whatever unit represents value in your application.

Unit economics is the right lens for several reasons that recur through the playbook:

- **It's the metric model selection is decided on** — cost per *completed task*, not per token (the model-selection post). Per-token price is a component; cost-per-task is the outcome.
- **It normalizes for volume** — cost per task tells you whether you're getting *more efficient*, independent of how much you're serving, so you can tell optimization from volume change.
- **It connects cost to value** — Google's "align spending with business value" principle made measurable. Cost per unit of value is what tells you whether spend is *justified*, not just whether it's *lower*.
- **It exposes the tail** — measuring cost per task (not average) surfaces that a few expensive tasks carry most of the spend (the tail from the model-selection post), which raw totals hide.

The practice: **define your value unit and measure cost per unit, not just total spend.** Then every lever's success is measured as "did cost per completed task go down (at held quality)?" — which is the number that actually matters, normalized for volume and tied to value. Optimizing total spend can mislead; optimizing unit economics is optimizing the real thing.

## The levers, ranked by measured impact

Consolidating the playbook, here are the inference levers ranked by the size of effect the vendors have measured — a quick reference for where to look first:

```text
1. Prompt caching        — largest lever; up to ~90% on long prompts, multi-fold on agent loops
2. Batch processing      — flat ~50% off, universal across providers, for deferrable work
3. Token hygiene         — trims input/output; compounds with caching (~83% → ~88%)
4. Prompt auditing       — ~36% waste from stale instructions on existing codebases (most under-known)
5. Model selection       — cost per completed task, priced on the tail not the median
6. Effort tuning         — often flat curve; a third-to-half off for 1–3 points on many tasks
7. Budgets / stopping    — task budgets save (18–47%); max_tokens does NOT (the trap)
8. Capacity commitments  — lower rate for predictable baseload (e.g. ~26% on longer terms)
```

Two things to read from this ranking. First, **the biggest levers are largely free** — caching and batching require no quality tradeoff, so they're where to start; you get the largest savings before touching anything that trades accuracy. Second, **the order is by *measured* effect, but your order may differ** — if your workload isn't agentic, caching may matter less; if you have an old codebase, prompt auditing (ranked 4th generally) might be your *biggest* win. So use the ranking to know what exists and its rough ceiling, then *measure on your workload* to find *your* order. The ranking is the map; measurement is your position on it.

## The measurement discipline in practice

Pulling it together into a workflow:

- **Instrument cost per value unit** — measure cost per completed task/request/ticket, not just total spend, so you optimize the right, volume-normalized, value-tied number (and it exposes the tail).
- **Measure each lever before/after on a representative sample** — trust your measured number over any vendor percentage, because every lever's effect is workload-dependent.
- **Start with the free levers** — caching and batching (no quality tradeoff) first, then token hygiene and prompt auditing, before levers that trade accuracy (effort, budgets, model downgrades).
- **Find your own lever order** — the general ranking is a starting map; your workload's characteristics (agentic or not, old codebase or new, steady or spiky) determine which levers matter most for you.
- **Re-measure over time** — models change (re-audit prompts, re-sweep effort), workloads change, and prices change, so measurement is continuous, not one-time (the "monitor and optimize over time" principle).

Measurement is the meta-lever: it's what turns the vendor percentages from marketing into engineering, tells you which levers actually pay on your workload, and — through unit economics — keeps you optimizing the number that matters. The final post covers the layer beyond core inference: AI developer-tooling spend and the provider landscape.

## Key takeaways

- Every vendor percentage is a directional figure on the vendor's own benchmark, not a guarantee — the effect of each lever depends on your workload (cache hit rate, task mix, effort curve, baseload predictability), so measure before/after on a representative sample of your real traffic and trust that number.
- Measure the right unit: unit economics (cost per completed task/request/ticket) not raw total spend, because it's the metric model selection is decided on, normalizes for volume, ties cost to business value, and exposes the tail that averages hide.
- The inference levers ranked by measured impact: prompt caching (largest), batch (~50% flat), token hygiene, prompt auditing, model selection, effort tuning, budgets/stopping (task budgets yes, max_tokens no), capacity commitments.
- The biggest levers (caching, batching) are largely free (no quality tradeoff), so start there — but the general ranking is a map, and your workload determines your order (prompt auditing may be your biggest win on an old codebase; caching matters less if you're not agentic).
- Measurement is the meta-lever: instrument cost per value unit, measure each lever on your workload, start with the free levers, find your own lever order, and re-measure continuously as models, workloads, and prices change.

## Further reading

- [Capacity commitments and cloud fundamentals (previous post)](/blog/posts/aicostplay-06-commitments-and-cloud.html)
- [Observability Engineering — measuring and unit economics](/blog/series/observability-engineering/)
- [FinOps Foundation](https://www.finops.org/)
