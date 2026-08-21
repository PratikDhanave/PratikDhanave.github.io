# How to Make AI Architecture Decisions

*Most AI architecture debates are settled by hype, familiarity, or whoever spoke last — this series settles them by requirements and trade-offs, starting with the meta-framework that every specific decision reduces to.*

"Which agent framework?" "RAG or fine-tuning?" "Managed API or self-host?" These decisions get made badly all the time — by defaulting to whatever is trending, whatever the loudest engineer prefers, or whatever the last blog post recommended. This series is a set of honest decision guides for the AI architecture choices that matter, each grounded in durable trade-offs rather than transient feature lists. This first post is the meta-framework: the recurring axes that every specific decision comes down to, and how to use them.

## Decide against requirements, not hype

The single most important habit: start from *your requirements*, not from the options. The question is never "what is the best agent framework?" — it is "what does *my* system need, and which option best fits that?" The best tool for a well-funded team building a complex research agent is not the best tool for a solo developer shipping a support bot, and neither is decided by which framework has the most stars. Write down what you actually need before you compare anything, and most decisions get much easier.

There is no universally best option in any of the comparisons ahead. There are only options that fit particular requirements better or worse. A guide that declares a global winner is selling something; a useful guide tells you *which* to pick *when*.

## The recurring axes

Nearly every AI architecture decision is a weighting of the same handful of axes. Learn these and you can reason about choices this series doesn't even cover:

- **Cost** — build cost and, more importantly, recurring run cost (inference is an operating expense paid forever). The [AI Cost Optimization](/blog/series/ai-cost-optimization/) series is entirely about this axis.
- **Latency** — how fast must a response be? Interactive vs batch changes the answer dramatically.
- **Control** — how much do you need to own and customize? Data residency, on-prem requirements, and the need to modify behavior push toward more control (and more work).
- **Quality** — measured on *your* task, via evaluation, not vendor benchmarks.
- **Lock-in** — how hard is it to leave? Proprietary APIs and formats trade convenience now for switching cost later.
- **Operational burden** — how much do you have to run, monitor, and maintain? This is the most underestimated axis; every capability you self-host is a system you operate at 2 a.m.
- **Team skills** — the best architecture your team cannot operate is the wrong architecture. Fit the choice to who will run it.
- **Time to market** — how fast must you ship? Often dominates early and should.

Every comparison in this series is, underneath, a different weighting of these axes.

## The fixed-versus-marginal shape

A specific pattern recurs so often it deserves naming. Many decisions pit an option with **higher up-front/fixed cost but lower per-use cost** against one with **low setup but higher per-use cost**. Self-hosting vs managed APIs, fine-tuning vs prompting, RAG-indexing vs stuffing context — all share this shape. And they all have the same answer: **it depends on volume.** Low volume favors the low-setup option; high, steady volume favors the low-marginal option, because you pay the marginal cost enough times to amortize the fixed one. When you hit a decision of this shape, the real question is "at my volume, which side of the crossover am I on?"

## Measure, don't assume

Wherever quality is part of the decision — which it usually is — the honest input is *measurement on your task*, not a leaderboard or a vendor claim. Build a small evaluation set representative of your real workload and compare the candidates on it. Vendor benchmarks are a starting signal at best; they were not run on your data, your prompts, or your edge cases. The teams that make good AI decisions are the ones that can say "we tested both on our eval set and X won by this much," not "we heard X is better."

## Reversibility changes the calculus

Finally, weight decisions by how hard they are to undo. A reversible choice (which prompt, which managed model behind an interface) can be made quickly and changed later — don't agonize over it. An expensive-to-reverse choice (a fine-tuned model you'll depend on, a proprietary platform you'll build deeply into, a data architecture) deserves more analysis, because you'll live with it. A useful move throughout: keep the expensive-to-reverse parts *swappable* behind interfaces so a decision you got wrong stays cheap to change. The [AI Production Roadmap](/blog/series/the-ai-production-roadmap/) makes "keep the model swappable" a first-class principle for exactly this reason.

## How to use this series

Each remaining post takes one real decision — agent frameworks, model platforms, RAG vs fine-tuning, MCP vs A2A, managed vs self-hosted, vector storage — and works it through these axes, ending with a clear "pick this when" rather than a global winner. Read the one you face; the meta-framework here is what ties them together. And when you hit a decision this series doesn't cover, run it through the same axes: requirements first, weigh cost/latency/control/quality/lock-in/ops/skills/time, find the fixed-vs-marginal crossover if there is one, measure on your task, and keep the expensive parts swappable.

## Key takeaways

- Decide against your requirements, not hype: there is no universally best option, only options that fit particular needs better or worse.
- Nearly every AI decision weighs the same axes — cost (especially recurring), latency, control, quality, lock-in, operational burden, team skills, time to market.
- Many decisions have a fixed-vs-marginal shape (self-host vs managed, fine-tune vs prompt, index vs stuff context); the answer turns on your *volume* and where the crossover is.
- Base quality judgments on measurement on *your* task with a real eval set, not vendor benchmarks or leaderboards.
- Weight analysis by reversibility — decide reversible choices fast, analyze expensive-to-reverse ones carefully, and keep the costly parts swappable behind interfaces.

## Further reading

- [The AI Production Roadmap series](/blog/series/the-ai-production-roadmap/)
- [AI Cost Optimization series](/blog/series/ai-cost-optimization/)
- [Browse all course series](/blog/series/)
