# Building a Credit Scorecard: From Raw Data to a Score
*How lenders turn application and bureau data into a single, defensible number — and why the interpretable scorecard still wins in regulated lending.*

A credit scorecard is one of the most durable artifacts in financial engineering. Decades after machine learning swept through every other corner of fintech, the humble points-based scorecard still decides who gets a loan, a card, or a line of credit at most regulated lenders. It survives not because it is the most accurate model you can build, but because it is the most *explainable* one that is still competitive. This post walks the full pipeline: how a scorecard is defined, engineered, fit, scaled, and validated — end to end.

## Start at the end: defining "bad"

Every supervised model needs a label, and for credit risk the label is a definition, not a given. You must decide what counts as a *bad* account. The industry-standard choice is a delinquency threshold: an account is bad if it reaches 90 or more days past due at any point during a fixed **performance window**. The window matters as much as the threshold. You observe an applicant's attributes at origination, then watch the account for a set period — commonly 12 to 24 months — to see whether it goes bad.

This creates two timelines. The **observation point** is when you snapshot the features (income, utilization, prior delinquencies). The **performance window** is the forward-looking period over which the outcome is measured. Getting these right avoids the two classic errors: an immature window that hasn't given bad loans time to sour, and target leakage from using any information dated after the observation point. Accounts that are neither clearly good nor bad — say, one or two payments late — are often carved out as **indeterminate** and excluded so the model learns from unambiguous outcomes.

## Assembling the modeling sample

With the target defined, you assemble a modeling table. Two sources dominate: **application data** captured at origination, and **bureau data** — a third party's record of an applicant's credit history and, retrospectively, performance outcomes. These join on the applicant to form one wide feature set. From there you split into training and holdout partitions, and you decide how to sample. Because defaults are rare — often single-digit percentages — many teams keep all bads and subsample goods, then carry a weight so population statistics stay honest.

Feature engineering here is deliberately conservative. Rather than throwing hundreds of raw columns at an optimizer, you craft a manageable set of candidate predictors with clear business meaning: credit utilization, months since last delinquency, number of recent inquiries, debt-to-income. Each will be transformed the same disciplined way.

## Weight of Evidence: the scorecard's signature move

The transformation that defines the classic scorecard is **Weight of Evidence (WOE)**. You bin each predictor into a handful of ranges (for continuous variables) or grouped categories, then replace every raw value with a single number describing how the odds of good-versus-bad shift inside that bin.

For a bin, WOE is the natural log of the ratio of the share of goods in that bin to the share of bads in that bin:

`WOE = ln( (goods_in_bin / total_goods) / (bads_in_bin / total_bads) )`

A positive WOE means the bin skews good; a negative WOE means it skews bad. This does three useful things at once. It puts every predictor on the same log-odds scale, it handles missing values gracefully (missing becomes its own bin), and it tames outliers because extreme raw values collapse into an edge bin. Analysts usually enforce a **monotonic** trend across bins — risk should move in one consistent direction as, say, utilization rises — which keeps the final scorecard intuitive and stable.

The companion statistic is **Information Value (IV)**, a single number summarizing how much a binned predictor separates goods from bads. It is the standard first-pass filter for deciding which features earn a place in the model.

## The logistic regression scorecard

The model itself is almost always **logistic regression** fit on the WOE-transformed features. Logistic regression models the log-odds of being bad as a linear combination of inputs. Because the inputs are already WOE values — themselves expressed in log-odds units — the whole model lives in one coherent, additive space. Each fitted coefficient tells you how strongly a predictor pushes the odds, and the sign should agree with the monotonic trend you built into the bins. A coefficient that flips sign is a red flag worth investigating before it reaches production.

## Scaling log-odds into points

A raw probability is awkward to communicate. The final step maps the model's log-odds output onto a friendly integer scale using two business parameters: a **base score** anchored to a reference odds level, and the **PDO** — Points to Double the Odds — which sets how many points correspond to a two-fold change in the good/bad odds. The scaling is linear: `points = offset + factor x log-odds`, where `factor = PDO / ln(2)` and the offset positions the base score. Because WOE keeps each feature additive, you can distribute the total across bins and publish a literal table — each attribute range earns a fixed number of points, and an applicant's score is just the sum plus a constant. That table *is* the scorecard.

```
   SOURCES          ENCODE            MODEL        SCALE        CONSUME
 +-----------+   +-------------+                              +-----------+
 |Application|-->| WOE Encoding|--WOE vectors--+              | Scorecard |
 |   Data    |   | (binned)    |               |              |   Score   |
 +-----------+   +-------------+               v          +-->+-----------+
 +-----------+          ^              +-------------+     |
 |  Bureau   |--history-+          +-->| Logistic Fit|--log-odds
 |   Data    |--delinq--+          |   | (coeffs)    |--> Scale to
 +-----------+          v          |   +-------------+    Points (PDO)
                 +-------------+    |                      |
                 |Define Target|---+  (bad flag)          +-->+-----------+
                 | 90+ DPD win |                          scored |Validation|
                 +-------------+                          holdout|  Report  |
                                                          ------>+-----------+
```

> **▸ [Open the interactive diagram](/blog/diagrams/finai-credit-scorecard-from-data-to-score.html)** — the end-to-end scorecard data flow, from application and bureau sources through WOE encoding and logistic fitting to a scaled score and validation report.

## Validating discrimination and calibration

A scorecard earns trust through evidence, measured on a holdout sample the model never saw. Two questions matter. First, **discrimination**: can the model rank a random bad above a random good? The **Kolmogorov-Smirnov (KS)** statistic captures the maximum separation between the cumulative good and bad distributions across score bands, while **Gini** (equivalently, the **AUC** of the ROC curve, since Gini = 2·AUC − 1) summarizes ranking power in one number. Higher is better, and both are reported per score band so you can see where separation concentrates.

Second, **calibration**: do the predicted default rates match reality? A model can rank perfectly yet still be miscalibrated, quoting a 3% default probability where 6% actually default. You check this by bucketing applicants by predicted risk and plotting predicted against observed default rates — a well-calibrated scorecard tracks the diagonal. Calibration is what makes a score usable for pricing and provisioning, not just approve/decline.

## Why interpretability still wins

Gradient-boosted trees and neural nets often edge out a scorecard on raw discrimination. Yet regulated lenders keep choosing the scorecard, and the reason is governance, not nostalgia. Fair-lending law demands that a lender explain an adverse decision with specific reasons; an additive points table produces those reasons for free, since each attribute's contribution is right there. Model-risk teams can inspect every coefficient, challenge every bin, and reproduce every score by hand. The monotonic WOE bins make the model's behavior predictable at the edges of the data, and the whole artifact is stable enough to monitor for drift over years.

The lesson generalizes beyond credit: in high-stakes, regulated decisions, a model you can defend line by line often beats a marginally sharper one you cannot. The scorecard endures because it was engineered, from its first design choice to its last validation chart, to be explained.

## Key takeaways

- The label is a definition, not a given: "bad" is typically 90+ days past due within a fixed performance window (12–24 months), observed forward from an origination snapshot, with ambiguous accounts carved out as indeterminate. Getting the two timelines right avoids an immature window and target leakage.
- Weight of Evidence puts every predictor onto one log-odds scale — `ln((goods_in_bin/total_goods)/(bads_in_bin/total_bads))` — which handles missing values as their own bin, tames outliers into edge bins, and (with enforced monotonicity) keeps the model intuitive; Information Value is the first-pass filter for which features earn a place.
- The model is logistic regression on WOE features, so inputs and coefficients live in the same additive log-odds space, and a coefficient whose sign flips against its monotonic bin trend is a red flag to investigate before production.
- Scaling to points is linear — `points = offset + factor × log-odds`, `factor = PDO/ln(2)` — and because WOE keeps features additive, the total distributes across bins into a literal points table: that table *is* the scorecard.
- Validate on holdout for both discrimination (KS, Gini/AUC) and calibration (predicted vs. observed default rates); a model can rank perfectly and still be miscalibrated, and calibration is what makes a score usable for pricing and provisioning.

## Further reading

- [Weight of Evidence and Information Value](/blog/posts/finai-weight-of-evidence-iv-binning.html) — the binning step at the heart of the scorecard, in depth.
- [Explaining credit decisions: SHAP and reason codes](/blog/posts/finai-credit-explainability-shap-reason-codes.html) — turning a score into the legally required adverse-action reasons.
- [Reject inference: modeling the applicants you declined](/blog/posts/finai-reject-inference-credit-scoring.html) — correcting the sample-selection bias baked into scorecard training data.
