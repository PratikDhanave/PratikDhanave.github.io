# Evaluating Models — Accuracy Is the Metric That Lies

*The most dangerous number in machine learning is accuracy, because it's the one everyone reaches for and the one that most often misleads. A fraud model that's 99.9% accurate by never catching any fraud is useless and common. Choosing the right evaluation metric — and understanding what each one hides — is the difference between a model that looks good and a model that works. This post is about measuring models honestly.*

Post 5 established *where* to measure (held-out data); this post is about *what* to measure. Evaluation is where ML meets the real objective, and the recurring lesson is that the metric encodes what you actually care about — pick the wrong metric and you'll optimize the wrong thing, confidently. This matters as much for LLM evaluation as for a credit model.

## Why accuracy lies: the imbalance trap

**Accuracy** — the fraction of predictions that are correct — is the intuitive default and the classic trap, because it's meaningless on **imbalanced** data. If 99.9% of transactions are legitimate, a model that predicts "legitimate" for everything scores 99.9% accuracy while catching *zero* fraud. The accuracy is excellent; the model is worthless. Since most high-value ML problems *are* imbalanced (fraud, disease, churn, defects are rare), accuracy is misleading exactly where it matters most.

The fix is to look at *what kind* of errors the model makes, via the **confusion matrix** — the four outcomes of a binary classifier:
- **True positives** (correctly flagged fraud), **true negatives** (correctly passed legit),
- **False positives** (flagged legit as fraud — a false alarm), **false negatives** (missed real fraud).

Every meaningful classification metric is built from these four numbers, because they distinguish the two very different ways a model can be wrong — and those two errors usually have very different costs.

## Precision, recall, and the trade-off that matters

From the confusion matrix come the two metrics you actually need:

- **Precision** — of the things the model flagged, how many were right? (TP / all flagged). High precision means few false alarms.
- **Recall** — of the things that were actually positive, how many did the model catch? (TP / all actual positives). High recall means few misses.

These trade off against each other, and *which matters more is a business decision, not a statistical one*:
- For **fraud or cancer screening**, missing a real case (false negative) is catastrophic, so you favor **recall** — catch them all, tolerate false alarms.
- For **spam filtering or a recommendation**, a false alarm (flagging a real email as spam) is costly and annoying, so you favor **precision** — only flag when sure.

You tune this balance by moving the decision threshold (post 3's 0.5 cutoff), trading precision for recall along a curve. The **F1 score** (harmonic mean of precision and recall) summarizes the balance in one number when you need a single metric, and the **ROC / AUC** and **precision-recall curves** show performance across all thresholds at once. The key discipline: *name the costly error for your problem, then choose the metric that tracks it* — don't default to accuracy.

## Regression metrics, and evaluating beyond a single number

For **regression** (predicting numbers, post 3), the metrics measure how far off the predictions are:
- **Mean Absolute Error (MAE)** — average absolute gap, in the target's units, easy to interpret.
- **Mean Squared Error (MSE) / RMSE** — squares the gaps, so large errors are penalized disproportionately — use it when big misses are especially bad.
- **R²** — the fraction of variance the model explains, a scale-free "how much better than predicting the average."

The choice again encodes what you care about: MAE treats all errors proportionally; RMSE punishes outliers. There is no universal "best" metric, only the one that matches your cost of being wrong.

Two broader disciplines complete honest evaluation:
- **Evaluate on segments, not just the average.** A model with great overall metrics can be terrible for a subgroup — this is both a quality and a *fairness* issue (post 2's representativeness). Break performance down by segment (demographics, regions, input types) to catch the failures the aggregate hides. This is directly how bias is detected in practice.
- **Match the metric to the real objective.** The ultimate evaluation isn't an offline metric at all but the business/user outcome — which is why production ML uses online tests (A/B testing) as ground truth, and why an offline metric is only ever a *proxy* for what you actually want. A model that improves your offline F1 but hurts the real outcome has optimized the proxy, not the goal (Goodhart's law in action).

The throughline: **accuracy lies** on imbalanced data (the 99.9%-accurate fraud model that catches nothing), so evaluate via the **confusion matrix** and its two real metrics — **precision** (few false alarms) and **recall** (few misses) — whose trade-off is a *business* decision (favor recall for fraud/cancer, precision for spam), summarized by **F1** or shown across thresholds by **ROC/AUC**. For regression, pick **MAE** (proportional), **RMSE** (punishes big misses), or **R²** by what your cost-of-error demands. Above all: **evaluate by segment** (the average hides subgroup failure — how bias is caught) and remember every offline metric is a **proxy** for the real objective (Goodhart's law) — so name the costly error and the true goal, and measure *those*, never defaulting to accuracy.

## Key takeaways

- **Accuracy misleads** on imbalanced data (a model predicting "all legit" scores 99.9% and catches zero fraud) — and most valuable problems (fraud, disease, churn) are imbalanced, so accuracy fails exactly where it matters.
- Use the **confusion matrix** (true/false positives/negatives) and its metrics: **precision** (of flagged, how many right — few false alarms) and **recall** (of actual positives, how many caught — few misses); their **trade-off is a business decision** (recall for fraud/cancer, precision for spam), summarized by **F1**, shown across thresholds by **ROC/AUC** and precision-recall curves.
- For **regression**, choose by cost-of-error: **MAE** (proportional, interpretable), **MSE/RMSE** (punishes large misses), **R²** (variance explained) — no universal best metric.
- **Evaluate by segment**, not just the average — strong aggregate metrics can hide terrible subgroup performance, which is both a quality and a **fairness/bias** issue (how bias is detected in practice).
- Every offline metric is a **proxy** for the real objective (**Goodhart's law**: optimizing the proxy can hurt the goal) — so name the costly error and the true business/user outcome, measure those, and treat online A/B tests as ground truth.

## Further reading

- [Precision and recall — the metrics accuracy hides](https://en.wikipedia.org/wiki/Precision_and_recall)
- [Cross-validation (statistics) — robust held-out evaluation](https://en.wikipedia.org/wiki/Cross-validation_(statistics))
