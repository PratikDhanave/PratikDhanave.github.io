# Online Evaluation and Feedback — Production Is the Real Test

*Offline evaluation tells you whether a change is safe to ship; online evaluation tells you whether it actually worked. No matter how good your eval set is, production always surprises you — real users send inputs you never imagined, and the gap between your offline scores and real-world quality is where LLM apps quietly fail. This post is about measuring quality on live traffic and turning user behavior into the feedback that makes the system improve.*

Post 4 built the offline gate. This post covers the other half of the loop (post 2): what happens *after* you deploy. The governing idea is that offline and online evaluation are complementary, not redundant — offline is controlled and repeatable but limited to inputs you thought of; online is messy and un-repeatable but reflects reality. You need both, and the bridge between them is a disciplined rollout and a feedback pipeline.

## The offline–online gap

Offline evals run on a curated set you built, so they can only measure the cases you *anticipated*. Production traffic is drawn from a different, wider, shifting distribution: users phrase things in ways you didn't predict, pursue use cases you didn't design for, and probe edges you never tested. The result is a persistent **offline–online gap** — a change that improves offline scores can still underperform live, and problems invisible offline appear immediately under real traffic.

This gap is not a failure of your eval set; it's intrinsic, and the correct response is to *close the loop* between the two:
- Production reveals the inputs reality actually sends.
- Those inputs — especially the ones the system handled badly — flow back into the offline eval set (post 2's backward arc), so next time they're anticipated.
- Over releases, the offline set converges toward the real distribution, shrinking the gap.

Treating online evaluation as the source of truth that continuously *corrects* your offline proxy is the healthy mental model. Offline tells you "this shouldn't regress"; online tells you "here's what you didn't know to test."

## Rolling out changes safely: experiments as evaluation

Because you can't fully predict a change's live effect, you deploy in a way that *measures* it rather than assuming it. This turns rollout itself into an evaluation method:
- **Canary / gradual rollout** — send the new prompt or model version to a small slice of traffic first, watch the online signals, and widen only if they hold. This bounds the blast radius of a bad change (post 3's instant rollback is the safety net).
- **A/B testing** — run the old and new versions side by side on comparable traffic and compare real outcomes. This is the gold standard for "is B actually better than A?" because it measures the thing you ultimately care about — user outcomes — under real conditions, controlling for everything an offline set can't. It's also how you avoid shipping a change that scores better offline but is worse for users.
- **Shadow / mirror testing** — run a candidate version on live traffic *without* showing its output to users, to compare behavior safely before any user sees it.

The discipline is to never treat "it passed offline evals" as "it's good in production." Offline passing earns a *controlled* rollout, and the rollout is where the real verdict is measured.

## Capturing feedback: explicit and implicit

Online evaluation needs quality signals from live traffic, and they come in two kinds — both valuable, with different trade-offs:

- **Explicit feedback** — users directly tell you: thumbs up/down, ratings, "regenerate," corrections, reports. It's high-signal and unambiguous but *sparse* (most users never rate) and biased (people rate when annoyed or delighted). Make it easy to give and treat it as precious.
- **Implicit feedback** — user *behavior* reveals quality without them stating it: did they copy the answer, accept the suggestion, immediately rephrase (a sign the answer missed), abandon the session, or follow up angrily? Implicit signals are abundant and unbiased by the act of rating, but noisier and need careful interpretation. At scale they're often the richer source.
- **Automated online quality checks** — run lightweight evaluators (rule-based checks, an LLM-judge on a sample) on live outputs to catch quality drops and safety issues in real time, not just in retrospect.

The payoff is a **feedback pipeline** that turns raw production behavior into action: aggregate the signals to spot quality trends and drift, route the bad cases into the eval set and into guardrail rules, and surface regressions fast enough to roll back. This is the engine of the "improve" stage (post 2) — without a feedback pipeline, production is write-only, and you learn nothing from the millions of real interactions you're accumulating. With one, every interaction makes the system a little better.

The takeaway: offline evaluation says a change is *safe to ship*; **online evaluation** says whether it *worked* — and because production traffic is a wider, shifting distribution than any curated set, there's an intrinsic **offline–online gap** that you close by flowing real (especially failed) production inputs back into the offline set. Since a change's live effect can't be fully predicted, deploy in ways that *measure* it: **canary/gradual rollout**, **A/B testing** (the gold standard for "is B actually better for users?"), and **shadow testing**. Capture quality from live traffic via **explicit feedback** (direct, high-signal, sparse/biased), **implicit feedback** (behavioral, abundant, noisier), and **automated online checks** — then build a **feedback pipeline** that routes bad cases into evals and guardrails, turning write-only production into the engine of continuous improvement.

## Key takeaways

- Offline evals only cover inputs you *anticipated*; production draws from a wider, shifting distribution, creating an intrinsic **offline–online gap** where offline-improving changes can still underperform live — closed by flowing real production failures back into the offline set (post 2), converging it toward reality.
- Offline and online are **complementary**: offline is controlled/repeatable but limited to known cases; online is messy/un-repeatable but reflects truth — offline says "shouldn't regress," online says "here's what you didn't test."
- Deploy to **measure, not assume**: **canary/gradual rollout** (bound the blast radius), **A/B testing** (gold standard for B-vs-A on real user outcomes), and **shadow testing** (run a candidate on live traffic without showing users). "Passed offline" earns a *controlled* rollout, not full release.
- Capture quality via **explicit feedback** (thumbs/ratings/corrections — high-signal but sparse and biased), **implicit feedback** (copy/accept/rephrase/abandon — abundant, unbiased-by-rating, noisier, often richer at scale), and **automated online checks** (rules/LLM-judge on live output).
- A **feedback pipeline** turns raw production behavior into action — spot drift, route bad cases into evals and guardrails, surface regressions fast — making production the engine of the "improve" stage instead of write-only.

## Further reading

- [A/B testing — comparing versions on live traffic](https://en.wikipedia.org/wiki/A/B_testing)
- [Reinforcement learning from human feedback — using human signals to improve models](https://en.wikipedia.org/wiki/Reinforcement_learning_from_human_feedback)
