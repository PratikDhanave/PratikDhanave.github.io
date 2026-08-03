# Supervised Fraud Detection with Imbalanced Data

*Why accuracy lies, how to train on a needle-in-a-haystack, and picking a threshold by the money it saves.*

Fraud detection is one of the few supervised learning problems where the thing you are trying to catch is genuinely rare. In a healthy payments stream, confirmed fraud might be one transaction in a thousand, sometimes one in ten thousand. That extreme class imbalance breaks most of the habits engineers bring from tidy, balanced classification tutorials. A model can be 99.9% accurate by predicting "legitimate" for every single transaction and still be completely worthless. This post is about the supervised angle only: you have labeled examples of past fraud and non-fraud, and you want a classifier that scores new transactions. Graph-based approaches and unsupervised anomaly detection are their own topics.

## The imbalance problem, stated plainly

When one class is 1000x larger than the other, a standard loss function is dominated by the majority. Gradient updates overwhelmingly reflect legitimate transactions, so the model learns the majority distribution well and the minority barely at all. The decision boundary drifts toward "everything is fine" because that is where the bulk of the error mass sits. Nothing is broken; the optimizer is doing exactly what you asked. You just asked the wrong question by treating both classes as equally important.

There are three broad families of fixes, and they are not mutually exclusive.

**Class weighting.** Tell the loss function that a misclassified fraud example costs far more than a misclassified legitimate one. Most libraries expose a `class_weight` parameter or a per-sample weight vector. This keeps your full dataset intact, changes nothing about the data pipeline, and directly reshapes the gradient. It is usually the first thing to try because it is cheap and reversible.

**Resampling.** Either undersample the majority (throw away legitimate examples until the ratio is manageable) or oversample the minority (duplicate or synthesize fraud examples). Undersampling is fast and often works well when you have millions of legitimate rows to spare, but you discard information. Oversampling keeps everything but risks overfitting to the handful of fraud patterns you happen to have.

**Cost-sensitive learning.** Bake the real-world asymmetry of errors directly into the objective, so the model optimizes expected cost rather than raw error count. This is the most principled option and connects naturally to threshold selection later.

## A caution about SMOTE

Synthetic oversampling techniques that interpolate new minority points between existing ones (the SMOTE family) are popular, and they are also the source of a lot of quietly broken pipelines. Two failures dominate.

First, **leakage through the resampling step.** If you synthesize new fraud examples and *then* split into train and validation, synthetic points derived from a real fraud row can land in both sets. Your validation score becomes optimistic fiction. Resampling must happen strictly inside the training fold, after the split, never before.

Second, **synthetic points in the wrong neighborhood.** Interpolating between two fraud examples assumes the space between them is also fraud. In tabular financial data with categorical fields, mixed scales, and sharp non-linear boundaries, that assumption often fails. You manufacture "fraud" examples that sit squarely inside legitimate territory, smearing the boundary you were trying to sharpen. For many fraud problems, a well-tuned class weight beats SMOTE and carries none of this baggage. Reach for synthesis only after you have measured that it helps on an honest, leakage-free validation set.

## Why accuracy is the wrong metric

Accuracy answers "what fraction of predictions were correct," which is meaningless when one answer is right 99.9% of the time by default. You need metrics that focus on the rare positive class.

- **Precision** is, of the transactions you flagged as fraud, how many actually were. Low precision means you are annoying good customers and drowning your review team in false alarms.
- **Recall** is, of all the actual fraud, how much you caught. Low recall means fraud is slipping through and costing money directly.
- **PR-AUC** (area under the precision-recall curve) summarizes the tradeoff across every threshold. Unlike ROC-AUC, it does not get flattered by the enormous true-negative count, so it is the honest single number for rare-event problems.
- **Recall at a fixed precision** ("what recall can I get while holding precision at 90%?") is often the metric the business actually cares about, because it maps to a review-team capacity you can staff.

ROC-AUC is not useless, but on extreme imbalance it can look impressive while the model is still practically unusable, because the false-positive rate is computed against a denominator of legitimate transactions so large that even many false positives barely move it. Prefer PR-AUC as your primary offline number.

```
   LABELED TRANSACTIONS ─┐
                         ├─▶ [ REBALANCE ] ─▶ [ TRAIN ]
   FEATURE VECTORS ──────┘   class weights    classifier
                                                  │
                                                  ▼
   COST MATRIX ───────────────────────▶ [ CALIBRATE + THRESHOLD ]
   (FP cost vs FN cost)                          │
                                                 ▼
                                    fraud score ─▶ APPROVE / REVIEW / BLOCK
```

> **▸ [Open the interactive diagram](/blog/diagrams/finai-supervised-fraud-imbalanced-data.html)** — labeled data and features flow through rebalancing and training, then a cost matrix drives calibration and the threshold behind the final approve/review/block decision.

## Choosing the threshold by money, not by 0.5

A classifier outputs a score; a decision needs a cutoff. The default 0.5 is arbitrary and almost always wrong for fraud. The right cutoff comes from the asymmetric cost of the two mistakes.

A **false negative** (missed fraud) costs you the transaction amount plus chargeback fees and operational overhead. A **false positive** (a good transaction blocked or sent to review) costs you a review analyst's time, a moment of customer friction, and some probability of losing that customer. These are rarely equal. Blocking a genuine large purchase might cost tens of dollars in goodwill; missing a fraudulent one might cost hundreds directly.

Write the expected cost at threshold *t* as roughly:

```
cost(t) = (FN count at t) x cost_FN + (FP count at t) x cost_FP
```

Sweep *t* across your validation scores, compute the expected cost at each, and pick the threshold that minimizes it. Because fraud amounts vary wildly, it is often better to weight each error by the actual transaction value rather than counting incidents equally, so a missed thousand-dollar fraud pulls the threshold harder than a missed five-dollar one. This turns threshold selection from a guess into an optimization against a number your finance team recognizes.

Many production systems use two thresholds, not one: below the lower cutoff, approve automatically; above the upper cutoff, block outright; in between, route to human review. That three-way policy lets you keep automated precision high while giving marginal cases to analysts.

## Calibration matters if you act on the probability

If your downstream logic multiplies the fraud probability by the transaction amount to get an expected loss, that probability needs to *mean* something. A model that says 0.9 should be wrong about one time in ten. Many classifiers, especially boosted trees, output scores that rank well but are poorly calibrated as probabilities. Fit a calibration step (isotonic regression or Platt scaling) on a held-out set so that a stated 0.9 corresponds to real-world 90% fraud odds. Rank-only use cases can skip this; expected-cost decisioning cannot.

## Label latency and leakage: the traps unique to fraud

Two data problems will quietly wreck a fraud model no matter how good your algorithm is.

**Label latency.** You often do not know a transaction was fraudulent until a chargeback arrives weeks later. So recent data has *incomplete* labels: transactions currently marked "legitimate" may simply not have been disputed yet. If you train on last month's data as if its labels were final, you teach the model that some real fraud is legitimate. Always leave a maturation window between the end of your training period and today, long enough for most chargebacks to have landed.

**Target leakage.** Fraud pipelines are full of features that only exist *because* fraud was already suspected: an account-status flag flipped by the fraud team, a manual-review outcome, a post-hoc risk note. Include any of these and your offline metrics will be spectacular and your production performance dismal, because at scoring time those features are empty or reflect a decision that has not happened yet. Audit every feature for the question: would this value be available, unchanged, at the exact moment I need to score a live transaction? If not, drop it.

## Putting it together

A dependable supervised fraud model is less about the fanciest architecture and more about respecting the shape of the problem. Handle imbalance with class weights before reaching for synthesis. Measure with PR-AUC and recall-at-precision, never raw accuracy. Choose your operating threshold by minimizing expected monetary cost, and calibrate the score if you plan to act on the probability itself. Guard against label latency and target leakage, because those two will fool you long before your loss function does. Get those fundamentals right and the model earns its keep.
