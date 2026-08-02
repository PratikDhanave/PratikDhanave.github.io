# Anomaly Detection for Fraud: Isolation Forests and Autoencoders
*When fraud labels are scarce or the attack is brand new, unsupervised anomaly detection buys you a signal before you ever have a training set.*

Supervised fraud models are wonderful when you can feed them thousands of confirmed fraud cases. The problem is that confirmed fraud is exactly what you tend not to have. Labels arrive weeks late and incomplete, and by the time a chargeback settles the fraudster has already moved on to a pattern your labeled history has never seen. Unsupervised anomaly detection sidesteps the label bottleneck entirely. Instead of learning "what fraud looks like," it learns "what normal looks like" and flags whatever deviates — which is what lets it catch a novel attack on its first appearance, before a single analyst has tagged it.

This post walks through three workhorse methods — isolation forests, autoencoders, and one-class SVMs — then the parts nobody warns you about: turning a raw score into a decision without labels, the false-positive burden, and fusing an unsupervised score with a supervised model instead of choosing between them.

## The core assumption, and where it bites

Every unsupervised detector rests on one bet: fraud is rare and structurally different from the bulk of your traffic. When that holds, anomalies genuinely sit in the sparse corners of your feature space. When it fails — when fraud has grown common, or deliberately mimics ordinary behavior — an anomaly score measures "unusual," not "fraudulent," and those are not the same thing. A customer's first international purchase is unusual and perfectly legitimate. That gap is the source of nearly every false positive you will fight.

## Isolation forests: fraud is easy to isolate

The isolation forest starts from a simple observation. If you repeatedly split your data on random features at random thresholds, points far from the crowd get cut off in just a few splits, while points buried inside a dense cluster take many more. So the *number of splits needed to isolate a point* is itself an anomaly signal: shallow isolation depth means anomalous, deep means normal.

You build many random trees, each on a small subsample, record how deep each point sits averaged across the forest, and normalize that depth into a score between 0 and 1. Scores near 1 are strongly anomalous; scores around 0.5 are indistinguishable from normal.

```
        ISOLATION DEPTH: ANOMALY vs NORMAL

  feature space                 random split tree
  ...............               depth
  ...:::::::....                  1  o------ split ------
  ..:::::::::::.                  2   |         normal
  ..::::::[N]::.                  3   |  o----- point sits
  ..:::::::::::.                  4   |  |      deep inside
  ...:::::::::..                  5   |  |      the cluster
  ...........[A]                     ===> deep  => low score

                                  1  o-- split --o [A]
  [A] anomaly, far out            2               ===> shallow
  [N] normal, in the cluster              => few splits => HIGH score
```

> **▸ [Open the interactive diagram](/blog/diagrams/finai-anomaly-detection-fraud.html)** — Unsupervised fraud dataflow: unlabeled transactions become features, two detectors (isolation forest, autoencoder) score them, the scores blend, then route to a supervised model as a feature and to a review queue as a novelty fallback.

Isolation forests are the default first reach for tabular fraud data: fast, scalable to millions of rows, and forgiving about feature scaling. Their weakness is that axis-aligned random cuts struggle with anomalies defined by a *combination* of features rather than an extreme in any single one — a transaction whose amount is normal and whose merchant is normal but whose amount-for-that-merchant is bizarre.

## Autoencoders: anomaly as reconstruction error

An autoencoder is a neural network trained to copy its input to its output through a narrow bottleneck. Because the middle layer is too small to memorize everything, the network is forced to learn a compressed representation of the *dominant* patterns. Train it only on traffic you believe is mostly legitimate, and it becomes very good at reconstructing normal transactions and very bad at reconstructing anything structurally unlike them.

The anomaly score is the **reconstruction error**: feed a transaction in, measure how far the output drifts from the input. Normal transactions pass through cleanly with low error; a fraudulent pattern the network never internalized comes out mangled, and that large error is your flag. This is powerful precisely where isolation forests are weak — the autoencoder learns nonlinear interactions among features, so it can notice that a plausible-looking combination is one the legitimate population never actually produces.

The costs are the usual neural-network costs: you need data and compute to train, the result is harder to explain to a risk committee than a tree, and it is sensitive to contamination — if too much fraud sneaks into the training set, the network learns to reconstruct fraud too, and your signal quietly erodes.

## One-class SVM: drawing a boundary around normal

A one-class SVM takes a third angle. Rather than scoring depth or reconstruction, it draws a tight boundary enclosing the bulk of the normal data in a transformed feature space; anything outside that frontier is flagged, and the distance past it is the score. The kernel trick captures subtle nonlinear boundaries, but it scales poorly and is fussy about parameters, so teams usually reserve it for smaller, well-scaled problems. It completes the mental map: depth-based, error-based, and boundary-based are the three families you will keep meeting under different names.

## Scoring and thresholding without labels

Every method above emits a continuous score. Turning that into a "review this" decision is where unsupervised detection actually earns its keep — and where it is hardest, because you have no labels to tune a threshold against.

The honest, capacity-driven approach is to threshold on the score *distribution*, not on an absolute value. Decide how many cases your review team can work per day, express that as a percentile — say the top 0.5% most anomalous transactions — and set the cutoff there. Your threshold becomes a budget, not a guess about what score "means fraud," and you recompute the percentile on a rolling window so the queue stays roughly constant as behavior drifts.

Whatever small pool of confirmed labels you do have should not train the detector; it should *evaluate* the threshold. Because fraud is rare, accuracy is useless — a detector that flags nothing is 99.5% accurate. Watch precision at your chosen cutoff, recall against the frauds you did eventually confirm, and above all the alert volume the threshold implies. Move the cutoff and watch that curve, rather than chasing a mythical "correct" score.

## The false-positive burden

Here is the number that governs the whole system. Suppose fraud is 0.2% of transactions and your detector is a strong 95% accurate in both directions. Out of 100,000 transactions, 200 are fraud — you catch 190. But 5% of the 99,800 legitimate transactions also trip the alarm: 4,990 false alarms. Your review queue is over 5,000 cases to find 190 real ones, a precision under 4%. That is not a modeling failure; it is the base-rate reality of rare events, and it is why "just lower the threshold to catch more fraud" is almost always the wrong instinct. The unsupervised score does not decide anything on its own — it *prioritizes a scarce review resource*, and must be judged as a ranking of where to spend attention, not as a verdict.

## Combining unsupervised scores with supervised models

The mature pattern is not either/or. The two approaches fail in opposite places, so run them together.

The most durable move is to treat the anomaly score as **just another feature** feeding your supervised model. Trained on the labels you do have, that model learns *when* an unusual transaction is actually worth worrying about — discounting the harmless first international purchase while still weighting genuinely suspicious novelty. You get the supervised model's precision on known fraud plus a standing input that reacts to strangeness it was never trained on.

The complementary move is to keep the unsupervised detector as a **fallback for novel attacks**. A supervised model is, by construction, blind to fraud absent from its training labels; a brand-new attack scores low because it resembles nothing the model was taught to fear. The anomaly detector has no such blind spot — novelty is exactly what it measures. Route high-anomaly, low-supervised-score transactions to human review as a dedicated catch-all, and that queue becomes an early-warning system: the frauds you find there are the seed labels for the next retrain, closing the loop from "we have never seen this" to "now we have a supervised signal for it."

## Practical guidance

Start with an isolation forest — it is the fastest path to a working signal on tabular data and asks almost nothing of you. Reach for an autoencoder when fraud hides in feature *interactions* rather than univariate extremes, and guard its training set against contamination. Threshold on your team's review capacity as a percentile, not on a magic score, and recompute it on a rolling window. Never sell the output as a fraud verdict; sell it as a prioritized queue, measured by precision and volume at your operating point rather than by accuracy. Then fold the score into your supervised stack as a feature and keep the raw detector alive as a novelty tripwire. Labels will always lag the fraudsters. Unsupervised anomaly detection is how you keep a signal in the window before they arrive.
