<!-- Markdown version for AI agents and readers. Canonical: https://pratikdhanave.com/blog/posts/fraud-04-scoring-thresholds-and-the-cost-of-errors.html -->

# Scoring, Thresholds, and the Cost of Errors — Where ML Meets the P&L

*A fraud model outputs a probability; the business needs a decision; and the line between them — the threshold — is where machine learning stops and economics begins. Set it by gut and you've made your most consequential business decision by vibes. This post builds the machinery that makes the error trade-off explicit: metrics that survive extreme imbalance, calibration that makes scores mean something, and thresholds derived from costs rather than from tradition.*

Post [1](/blog/posts/fraud-01-the-fraud-problem.html) established that false positives and false negatives cost in different currencies; posts [2](/blog/posts/fraud-02-rules-and-models.html)–[3](/blog/posts/fraud-03-features-and-feature-stores.html) built the scoring stack. This post decides what the score *does*.

## Metrics that survive 0.1% base rates

At fraud's base rates, most familiar metrics mislead. Accuracy is void (post 1). ROC-AUC — the default "is the model good?" number — deceives more subtly: with 1,000 legitimate transactions per fraud, a model can post 0.99 AUC while drowning every caught fraud in false positives, because ROC's false-positive *rate* denominates against the enormous negative class. The metrics that reflect reality denominate against *decisions*: **precision at a review capacity** (of the N riskiest transactions a day the team can examine, how many are fraud — post 7's queue economics in metric form), **recall at a fixed FP budget** (how much fraud is caught while declining no more than X% of good customers), and the **precision-recall curve** generally, which unlike ROC degrades visibly as base rates fall. The operational discipline: evaluate on *time-split* data (train past, test future — random splits leak the adversary's evolution, per post 1), and segment the metrics (by amount band, payment method, geography), because an aggregate number can hide a model that's excellent on small transactions and blind on exactly the large ones where FN cost concentrates.

## Calibration: making the score a probability

Threshold-by-cost (next section) only works if the score *means* something — specifically, if transactions scored 0.3 are actually fraudulent about 30% of the time. Most classifiers out of the box are discriminative but miscalibrated: the ranking is good, the absolute values aren't. The fixes are standard — post-hoc calibration (isotonic regression or Platt scaling on held-out data) — but fraud adds two twists: calibration **decays with drift** (the mapping from score to true probability shifts as the adversary moves — recalibration belongs in post 6's refresh cadence, and a calibration dashboard in post 8's monitoring), and calibration must be **conditional** on the segments that matter (a model calibrated overall can be miscalibrated at high amounts — which, again, is where the money is). Calibration is unglamorous and load-bearing: it's the difference between a threshold meaning "block above 60% fraud probability" and meaning "block above the number that felt right in 2024."

## Thresholds as cost minimization

With calibrated scores and named costs, the threshold stops being a dial and becomes a derivation. For a transaction of amount A: declining a fraud saves roughly A (plus fees and network standing — post 1); declining a legitimate customer costs the margin on A plus some estimate of future-relationship value; approving a fraud costs A-plus. The expected-cost-minimizing rule falls out: block when *p × cost-of-fraud > (1−p) × cost-of-false-positive* — which immediately yields the insight flat thresholds miss: **the optimal threshold moves with the amount** (and segment). A $5 transaction tolerates high fraud probability — the FP cost of blocking a real customer dwarfs the $5 at risk; a $5,000 transaction justifies action at low probability. Production systems encode this as threshold *schedules* over amount and segment, or equivalently score on expected cost directly. Two completions make it a system rather than a formula: **more than two outcomes** — between approve and decline sit step-up friction and human review (post 7), each with its own cost (friction's abandonment rate, review's unit cost) slotting into the same expected-cost frame, turning one threshold into a *ladder* of them; and **costs are owned, versioned inputs** — the FP-cost estimate embeds strategic judgments (how much is customer trust worth?) that belong to the business, reviewed and versioned like bill-08's metric definitions, so when the risk appetite changes, a parameter changes — not a model.

The takeaway: the score-to-decision layer is economics made explicit — **decision-denominated metrics** (precision at review capacity, recall at FP budget, PR curves) on time-split, segmented evaluations because ROC flatters at 0.1% base rates; **calibration** (maintained against drift, checked per segment) so scores are probabilities rather than rankings; and **thresholds derived from named costs** — moving with amount and segment, extended into a ladder across approve/friction/review/decline, with the cost parameters owned and versioned by the business. The threshold is the business logic; everything before it is estimation.

## Key takeaways

- At fraud base rates: accuracy is void, **ROC-AUC flatters** (FP rate denominates against a huge negative class) — use **precision@review-capacity, recall@FP-budget, PR curves**, on time-split and *segmented* evaluations.
- **Calibration makes thresholds meaningful** — post-hoc fit, recalibrated on drift cadence, verified per segment (especially high-amount, where miscalibration costs most).
- Thresholds are **cost derivations**: block when p·FN-cost exceeds (1−p)·FP-cost — so the optimal threshold *moves with amount and segment*; encode schedules, not constants.
- Between approve and decline sits the **ladder** (friction, review) — same expected-cost frame, more outcomes; and **costs are versioned business inputs**, so risk appetite changes parameters, not models.

## Further reading

- [Precision and recall — the decision-denominated metrics that survive imbalance](https://en.wikipedia.org/wiki/Precision_and_recall)
- [Receiver operating characteristic — and why it misleads at extreme base rates](https://en.wikipedia.org/wiki/Receiver_operating_characteristic)

---

Author: Pratik Dhanave (https://pratikdhanave.com) | Published: 2026-11-04
Canonical: https://pratikdhanave.com/blog/posts/fraud-04-scoring-thresholds-and-the-cost-of-errors.html
Attribution: please link the canonical URL when citing or quoting this post.
