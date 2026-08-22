# Effort Tuning, Budgets, and the max_tokens Trap

*Two more levers of control: how hard the model thinks, and how you bound what it spends. Both have measured sweet spots — and both have a trap that quietly wastes money. The sharpest is a cap that most people reach for first and that saves nothing at all: max_tokens.*

This post covers **effort/reasoning-depth tuning** (dialing how hard the model works) and **budgets, caps, and stopping conditions** (bounding a run). Both are about spending only what a task needs — but the controls behave differently than intuition suggests, and one popular cap is a trap. Figures are vendors' own directional numbers; verify on your workload.

## Effort tuning: the accuracy-vs-cost curve is often flat

Modern models expose an *effort* or reasoning-depth setting — how much the model "thinks" before answering. Anthropic's effort sweep is the best-documented instance of this lever, and the finding is encouraging: on many tasks, the **accuracy-vs-cost curve is nearly flat**, meaning you can turn effort *down* and lose little accuracy for real savings.

Its measured results: on four research and knowledge-work benchmarks, *low* effort gave up only 1–3 accuracy points for a third to half off the cost, and *medium* effort matched the default's accuracy at ~70–85% of the cost. So for a large class of tasks, you're paying for reasoning depth you don't need — the default effort is more than the task requires, and dialing it down is nearly free accuracy-wise. **But** on long-horizon coding, the curve was *steep* — a real tradeoff where lower effort meaningfully hurt. So the lever's value is task-dependent: flat (free savings) on many tasks, steep (real tradeoff) on the hardest.

The actionable practice: **sweep two or three effort levels on a sample of your own traffic** before doing anything more drastic (like adding a second model). Effort tuning is often a bigger, simpler win than model switching, and you find your curve by measuring. Two measurement cautions:

- **Test each level in a separate session.** Changing effort mid-session invalidates the cache (the caching post's warning) and distorts the comparison — so a multi-level config that looks cheaper than a single level can actually cost *more* due to cache invalidation. Compare levels in clean, separate sessions.
- **Re-run failures at higher effort.** Where outcomes are checkable (tests, a verifier), run *everything* at low effort and re-run only the *failures* at high effort. Anthropic measured ~the same pass rate (~93% vs 91.7%) at *half the cost* this way, even counting the wasted low-effort attempts. This requires a trustworthy failure signal and costs some latency on the failures, but it's a strong pattern: cheap-first, expensive-only-on-failure.

## Budgets, caps, and stopping conditions: three different jobs

AWS makes bounding a run its own question — GENCOST05 "how do you optimize agent workflows for cost?", with the practice "create stopping conditions to control long-running workflows" and the principle "design workflow boundaries … avoid scenarios where workflows consume excessive resources or continue beyond their useful purpose." The key insight from Anthropic's measurements is that **three controls that look similar actually do three different jobs** — and confusing them is where money is lost:

| Control | What it does | Saves money? |
|---|---|---|
| **Task budget** | Model sees a live token countdown and self-regulates | **Yes** — measured ~18% saving for ~2.7 points of pass rate; ~47% saving at the tightest budget |
| **`max_tokens`** | Caps one response, invisibly to the model | **No** — truncated turns are discarded *and still billed* |
| **Session / workspace spend limit** | Platform-enforced hard dollar stop | Backstop, not an optimizer |

The distinction is worth getting exactly right:

- **Task budget** genuinely saves, because the model *sees* the budget and adapts — it self-regulates to fit, trading a little accuracy for real savings (18% for ~2.7 pass-rate points; up to 47% at the tightest setting). This is the lever the model can actually respond to.
- **Session/workspace spend limits** are a *backstop* — a hard dollar stop that prevents catastrophe but doesn't *optimize* anything; it just stops the bleeding at a limit. Necessary as a safety net, not a cost-reduction tool.
- **`max_tokens`** is the trap — see below.

## The max_tokens trap

Here's the finding most likely to save you from a mistake, because `max_tokens` is the cap most people reach for *first*, and it **saves nothing**. Unlike a task budget, `max_tokens` caps a single response *invisibly to the model* — the model doesn't know about the limit and doesn't adapt; it just gets cut off. And critically, **a truncated turn is discarded and still billed** — you pay for the tokens generated up to the cap, get an unusable truncated result, and have to retry.

Anthropic's measured example makes the trap vivid: a 16,384-token cap ended ~15% of one model's attempts and a third of another's — and **none of those truncated attempts solved the task.** The cost per *solved* task was identical to using a much higher (64,000-token) cap, because the low cap just added wasted, billed, truncated attempts without saving anything. Setting `max_tokens` low feels like a cost control, but it doesn't reduce cost per solved task — it just breaks attempts you still pay for.

The correct practice inverts the intuition:

- **Set `max_tokens` high** (e.g. ~64,000 for agentic work) — high enough that it rarely truncates a genuine attempt. It's a safety limit against runaway generation, not a cost lever.
- **Treat `stop_reason: max_tokens` as a failure** — if a response hit the cap, it was truncated and (per the finding) probably didn't succeed; handle it as a failed attempt, not a result.
- **Economize with effort and task budgets instead** — the levers the model can actually *see* and respond to. Effort tuning and task budgets reduce cost per solved task; `max_tokens` doesn't.

The general principle: **cost controls the model can see (task budgets, effort) let it adapt and genuinely save; controls it can't see (`max_tokens`) just truncate billed work.** Reach for the ones the model can respond to.

## Using these levers well

- **Sweep effort on your own traffic** — 2–3 levels, in separate sessions (to avoid cache-invalidation distortion) — before adding models; the curve is often flat (free savings) on many tasks, steep on the hardest.
- **Re-run failures at higher effort** where outcomes are checkable — cheap-first, expensive-only-on-failure gave ~equal pass rate at half the cost.
- **Use task budgets to genuinely save** — the model sees and self-regulates (18–47% measured savings for modest accuracy cost).
- **Set `max_tokens` high and treat hitting it as failure** — it's a safety limit, not a cost lever; low caps waste billed, truncated attempts.
- **Keep session/workspace spend limits as a backstop** — a hard stop against catastrophe, not an optimizer.

Effort tuning and budgets are about spending what a task needs and no more — but only through the controls the model can actually respond to, and never through the `max_tokens` trap. The next post covers the last inference lever, capacity commitments, plus the cloud-infrastructure fundamentals underneath it all.

## Key takeaways

- Effort/reasoning-depth tuning often has a nearly flat accuracy-vs-cost curve: low effort gave up only 1–3 points for a third-to-half off, medium matched default accuracy at ~70–85% cost on research tasks — though long-horizon coding was a steep, real tradeoff; sweep 2–3 levels on your own traffic (in separate sessions to avoid cache-invalidation).
- Re-run failures at higher effort where outcomes are checkable: run everything low, re-run only failures high — measured ~equal pass rate at half the cost, counting wasted cheap attempts.
- Three bounding controls do three different jobs: task budget (model sees it and self-regulates — genuinely saves, 18–47% measured), `max_tokens` (caps a response invisibly — saves nothing), and session/workspace spend limits (a backstop, not an optimizer).
- The `max_tokens` trap: it's the cap people reach for first and it saves nothing — truncated turns are discarded and still billed, a low cap breaks attempts (none solved in the measured case) with cost-per-solved-task identical to a high cap; set it high (~64k for agents) and treat hitting it as a failure.
- General principle: cost controls the model can *see* (task budgets, effort) let it adapt and genuinely save; controls it can't see (`max_tokens`) just truncate billed work — economize with the former.

## Further reading

- [Model selection and prompt audits (previous post)](/blog/posts/aicostplay-04-model-selection-and-audits.html)
- [AWS Well-Architected Generative AI Lens — cost](https://docs.aws.amazon.com/wellarchitected/latest/generative-ai-lens/generative-ai-lens.html)
- [Reasoning models and test-time compute — the effort lever in depth](/blog/series/ai-cost-optimization/)
