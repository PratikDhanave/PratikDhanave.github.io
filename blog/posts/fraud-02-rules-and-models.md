<!-- Markdown version for AI agents and readers. Canonical: https://pratikdhanave.com/blog/posts/fraud-02-rules-and-models.html -->

# Rules and Models — Why Fraud Systems Need Both

*Every few years someone declares rules dead — just let the model learn everything — and every production fraud team quietly keeps both, because rules and models are good at different, complementary things: rules deploy in minutes against the attack happening right now, encode hard policy exactly, and explain themselves completely; models find the subtle multidimensional patterns no human would write down. The engineering question isn't which — it's how the two compose into one decision.*

Post [1](/blog/posts/fraud-01-the-fraud-problem.html) framed fraud as a decision factory; this post builds its two decision engines and the composition layer between them.

## What rules are actually for

A fraud rule is an explicit predicate with a consequence: more than N cards from one device in an hour → block; shipping country mismatches card country AND amount exceeds X → review. Dismissed as legacy, rules survive because of four properties models can't match:

- **Reaction speed.** A new attack pattern spotted at 10 a.m. is a deployed rule by 10:20. The model's answer to the same attack is: collect labeled examples (weeks, per post 1's label delay), retrain, validate, ship. Rules are the immune system's fast response; nothing else in the stack closes the loop in minutes.
- **Policy exactness.** Some decisions are policy, not prediction: sanctioned-country blocks, regulatory limits, "never approve over $X without 3DS." Encoding policy in a model is asking a statistical system to approximate a rule you could state exactly — the worst of both worlds. Policy belongs in rules by definition ([RegTech](/blog/series/regtech-compliance-as-engineering/) supplies many of them).
- **Total explainability.** "Blocked: velocity rule 47, 6 cards / 1 device / 40 minutes" survives disputes, audits, and regulator questions verbatim. Post 8 returns to model explainability; rules simply don't have the problem.
- **Cold starts and blind spots.** New products, new markets, declined-traffic regions (post 1's censoring): places the model has no trustworthy data are places rules hold the line while data accrues.

Their known pathology is *accretion*: hundreds of rules, interactions nobody models, ancient rules firing on traffic that outgrew them. The counter-disciplines: every rule carries an owner, a measured FP/catch rate (shadow-evaluate rules exactly like models), and a review date — and rules that a model now dominates get retired. A rule engine without lifecycle management becomes sediment (the same debt grammar as ZDM's contract-phase: additions must schedule their own removals).

## What models are for, and which models

The model's job is the pattern space rules can't enumerate: subtle joint distributions over dozens-to-thousands of features (post 3), where fraud looks like a faint statistical signature rather than a stateable condition. The honest state of practice: **gradient-boosted trees remain the production workhorse** — tabular features are fraud's native representation, GBDTs handle them superbly, train fast enough for frequent refresh (post 6's cadence), and score within post 1's latency budget; **deep models earn their place at the embedding edges** — sequence models over event histories, learned representations of devices/emails/graphs feeding the tabular model as features — rather than replacing the stack; and ensembles of specialized models (per payment method, per attack family) beat one monolith often enough to keep the architecture modular. The selection pressure is post 1 throughout: frequent retraining beats marginal accuracy (the adversary moves), calibration matters (post 4's thresholds consume probabilities, not ranks), and scoring cost is a hard constraint.

## Composition: one decision from many voices

The composition layer is where the system's character lives. The convergent pattern: **policy rules first** (hard blocks and allows — non-negotiable, cheap, terminal); **model scores next** (one or several probabilities); **decision logic last** — combining scores, remaining rule signals, and cost thresholds (post 4) into approve / decline / escalate (friction or review — post 7). Three composition principles earn emphasis: **rules can overrule the model, with accounting** — every override is logged and measured, because override-rate-where-the-model-was-right is the metric that retires obsolete rules; **signals compose better than verdicts** — rules firing as *features into* the model ("velocity rule would have fired" as an input) often beats binary gating, letting the model learn when the rule's signal matters; and **the composition is itself versioned and testable** — the decision logic is production code with golden decisions (the bill-07 pattern: fixed scenario inputs, pinned expected outcomes, diffed on every change), because the subtlest fraud incidents are composition bugs — model fine, rules fine, the blend wrong.

The takeaway: rules and models are complements, not competitors — rules for **minutes-fast reaction, exact policy, total explainability, and blind-spot coverage** (with lifecycle discipline against accretion); models — GBDTs as the tabular workhorse, deep learning at the embedding edges — for the unstateable pattern space, selected under retraining-speed and latency pressure. The composition layer makes them one decision: policy first, scores next, cost-thresholded logic last, with overrides accounted, rule signals feeding the model as features, and the blend itself versioned and golden-tested — because the decision factory's output is the *composition*, and that's where it breaks.

## Key takeaways

- Rules earn their keep four ways: **10-minute deployment** against live attacks, **policy exactness**, **audit-grade explainability**, **cold-start/blind-spot coverage** — with owners, measured rates, and retirement dates against accretion.
- Models own the unstateable patterns: **GBDTs as the production workhorse** on tabular features, deep models as embedding feeders at the edges, modular ensembles over monoliths — selected for retrain speed, calibration, and latency.
- Composition: **policy → scores → cost-thresholded decision logic**, overrides logged and measured, rules-as-features over rules-as-gates where subtlety wins.
- The blend is **versioned, golden-tested production code** — composition bugs are the fraud incidents that happen while every component's metrics look fine.

## Further reading

- [Anomaly detection — the statistical frame fraud models inhabit](https://en.wikipedia.org/wiki/Anomaly_detection)
- [Gradient boosting — the tabular workhorse of production risk models](https://en.wikipedia.org/wiki/Gradient_boosting)

---

Author: Pratik Dhanave (https://pratikdhanave.com) | Published: 2026-11-02
Canonical: https://pratikdhanave.com/blog/posts/fraud-02-rules-and-models.html
Attribution: please link the canonical URL when citing or quoting this post.
