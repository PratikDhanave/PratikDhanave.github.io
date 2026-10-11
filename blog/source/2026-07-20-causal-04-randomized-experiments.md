# Randomized Experiments — The Gold Standard, and Your A/B Test

*The most reliable way to establish causation is almost embarrassingly simple: flip a coin to decide who gets the treatment. Randomization is the one technique that defeats confounding completely — including confounders you never thought of — which is why the randomized controlled trial is the gold standard of causal evidence and why the A/B test is the most powerful tool an engineer has. This post explains why randomization works its magic, and the many ways real experiments still go wrong.*

Post 3 named confounding the villain; this post is its definitive defeat. Randomized experiments — RCTs in science, A/B tests in product — achieve comparable groups *by construction* (post 2), making the causal effect directly estimable. Every engineer runs A/B tests; far fewer understand *why* they work and how they fail, which is exactly what makes or breaks their causal validity.

## Why randomization is magic

Recall the whole problem (posts 2–3): to estimate a causal effect you need treated and untreated groups that are comparable in every way except the treatment, and confounding — differences that affect both treatment and outcome — ruins that comparability. **Randomization** solves this at a stroke: if you assign treatment *by a random process* (a coin flip), then treatment assignment is, by construction, **unrelated to anything** — any characteristic of the units, measured or unmeasured, known or unknown.

This is the magic, and it's worth stating precisely: because assignment is random, the treated and untreated groups are, on average, **statistically identical in every respect** — same distribution of engagement, health, wealth, mood, and every confounder you never even considered. There's no systematic difference between the groups *except the treatment itself*, so any difference in outcomes must be *caused* by the treatment. The untreated group is a valid counterfactual for the treated group (post 2), the comparison is clean, and the causal effect is simply the difference in group averages.

The reason this is the *gold standard* is the phrase "known or unknown." Adjustment methods (post 6) can only handle confounders you've identified and measured; randomization handles **all** of them simultaneously, including ones nobody has ever thought of, *without needing to measure or even know about them.* That's a guarantee no observational method can match — randomization doesn't adjust for confounders, it makes confounding *impossible* by severing the link between assignment and everything else. This is why "did you randomize?" is the first question to ask of any causal claim.

## The A/B test is a randomized experiment

For engineers, the headline is that the **A/B test** — randomly showing version A to some users and version B to others, then comparing a metric — *is* a randomized experiment, and therefore a genuine causal tool. When you A/B test a feature and see higher retention in the treatment group, you can legitimately claim the feature *caused* the retention lift, because randomization guarantees the two groups were comparable. This is why A/B testing is the backbone of rigorous product development: it's the one routine engineering practice that produces real causal evidence, letting teams know whether a change *actually works* rather than guessing from correlations.

This also sharply distinguishes A/B tests from the correlational traps of post 1. "Users who adopted the feature retained better" (observational, confounded by engagement) is weak evidence; "users *randomly shown* the feature retained better" (experimental) is strong causal evidence. Same feature, same metric — the randomization is the entire difference. Understanding this is what separates teams who run A/B tests as rigorous experiments from teams who run them as dashboards.

## How real experiments still go wrong

Randomization is powerful but not foolproof — the *theory* is clean, the *practice* is full of ways to break the guarantee, and knowing them is essential:

- **Peeking / repeated testing.** Checking results repeatedly and stopping when they look significant inflates false positives dramatically — the statistics assume you decide the sample size in advance. "We saw significance on day 3 and shipped" is a classic way to ship noise. (This is the multiple-comparisons problem applied to time.)
- **Insufficient power.** Too small a sample can't detect a real effect, so a "no difference" result may just mean the test was underpowered — absence of evidence mistaken for evidence of absence. You must estimate the needed sample size up front.
- **Broken randomization.** If assignment isn't truly random (a bug sends certain users to one arm, or users self-select), confounding creeps back and the guarantee is void. The randomization must be *real* and *respected*.
- **Interference / spillover (SUTVA violations).** The framework assumes one unit's treatment doesn't affect another's outcome — but in social networks, marketplaces, and shared systems, it does (treating some users changes the experience of others, as in a two-sided marketplace). This breaks the clean comparison and needs special designs (cluster randomization).
- **Non-compliance and attrition.** Units assigned to treatment who don't actually take it, or who drop out differentially, muddy the analysis.
- **External validity.** An effect proven in your experimental population/time may not generalize to others — "it worked in the test" isn't "it works everywhere, forever."
- **You can't always randomize.** Ethics (can't randomize people to smoke), feasibility (can't randomize countries to a policy), or cost often rule out experiments — which is the entire reason observational methods (posts 6–7) exist.

The disciplined posture: randomization gives you the strongest causal evidence available *when done right*, so run A/B tests whenever you can, but respect the experimental discipline — fix the sample size in advance, don't peek, verify randomization, watch for interference, and be honest about power and generalization. A sloppy experiment can be *worse* than none, because it carries the authority of "we tested it" without the validity. The gold standard is only gold when the practice matches the theory.

The throughline: **randomization** defeats confounding completely — assigning treatment by a random process makes it **unrelated to everything** (every confounder, known or unknown, measured or not), so the treated and untreated groups are **statistically identical except the treatment**, the untreated group is a valid counterfactual, and the outcome difference *is* the causal effect. This is the **gold standard** because it handles **all** confounders at once *without measuring or knowing them* — a guarantee no observational method can match. For engineers, the **A/B test is a randomized experiment** and therefore a real causal tool: "users *randomly shown* X retained better" is strong causal evidence where "users who *chose* X" (confounded) is weak. But the clean theory breaks in practice via **peeking**, **insufficient power**, **broken randomization**, **interference/spillover**, **non-compliance/attrition**, and limited **external validity** — and you **can't always randomize** (ethics/feasibility/cost), which is why observational methods exist. Run experiments whenever possible, but respect the discipline — a sloppy experiment carries false authority.

## Key takeaways

- **Randomization** assigns treatment by a random process, making it **unrelated to every characteristic** (confounders measured *or unmeasured*, known *or unknown*) — so the treated and untreated groups are **statistically identical except the treatment**, making the outcome difference a clean **causal effect** (the untreated group is a valid counterfactual, post 2).
- It's the **gold standard** because it defeats **all confounders simultaneously without needing to measure or know them** — a guarantee adjustment methods (post 6, limited to *measured* confounders) can't match; "did you randomize?" is the first question of any causal claim.
- The **A/B test is a randomized experiment** and thus a genuine causal tool: "users *randomly shown* the feature retained better" is strong causal evidence, where the correlational "users who *adopted* it retained better" (confounded by engagement) is weak — the randomization is the entire difference.
- Real experiments still fail via **peeking/repeated testing** (inflates false positives — fix sample size in advance), **insufficient power** (can't detect real effects — absence of evidence ≠ evidence of absence), **broken randomization** (confounding returns), **interference/spillover** (one unit's treatment affects another — breaks the comparison in networks/marketplaces), **non-compliance/attrition**, and limited **external validity**.
- You **can't always randomize** (ethics, feasibility, cost) — the reason observational methods exist (posts 6–7); run experiments whenever possible but **respect the discipline**, because a sloppy experiment carries the false authority of "we tested it."

## Further reading

- [Randomized controlled trial — the gold-standard experiment](https://en.wikipedia.org/wiki/Randomized_controlled_trial)
- [Design of experiments — planning valid experiments](https://en.wikipedia.org/wiki/Design_of_experiments)
