# Reject Inference: Modeling the Applicants You Declined
*Why a scorecard trained only on funded loans quietly overstates its own accuracy, and the inference techniques that pull the declined population back into view.*

Every credit model has a blind spot baked into its training data. You only observe repayment behavior for applicants you approved and funded. The applicants you declined never got a loan, so you never learned whether they would have paid it back. When you sit down to retrain, the only rows with a known good/bad label are the ones your previous policy already blessed. The model learns the world as your acceptance rule shaped it, not the world as it actually is.

This is a textbook case of sample selection bias, and it is more dangerous than it looks because the model still validates beautifully. It scores well on held-out accepts because accepts are exactly what it saw. Reject inference is the family of techniques that tries to reconstruct the missing outcomes for the declined population so the retrained model reflects the full through-the-door applicant flow, not just the survivors.

## Why the bias is not harmless

The intuition that "we rejected them because they were risky, so ignoring them is conservative" is wrong in a subtle way. Rejection is driven by the *old* model plus overlays, cutoffs, and manual rules. Those decisions were correlated with the features you now want to model. If a variable like short employment tenure was heavily used in the old cutoff, then almost everyone with short tenure was rejected, and your accepted sample has almost no short-tenure examples. The new model cannot see the true relationship between tenure and default in that region because the data was censored there.

The practical symptoms are predictable. The model overstates its discriminatory power on the accept-only sample. It is poorly calibrated near the cutoff, which is precisely where marginal lending decisions get made and where a point of accuracy is worth the most money. And it drifts as soon as you loosen policy, because the newly approved marginal applicants live in a feature region the model never trained on.

## The core workflow

Reject inference is not a single algorithm; it is a disciplined loop. Fit a base model on the accepts, use it to reason about the rejects, fold inferred outcomes back into the training set, refit, and then prove the result actually helped before you trust it.

```
                 REJECT INFERENCE PIPELINE

  [Accepts]                (observed good / bad outcomes)
     |
     v
  [Base Model] --------> [Score Rejects]   (fit on accepts,
     ^                        |             then apply to declines)
     |                        v
     |                   [Infer Outcomes]   (assign proxy good/bad
     |                        |              or fractional weight)
     |                        v
     |                   [Combine Set]      (accepts + inferred rejects)
     |                        |
     |                        v
     |                   [Refit Model]      (train on augmented data)
     |                        |
     |                        v
     |                   [Validate Lift]    (held-out accepts, KS / AUC,
     |                        |              calibration near cutoff)
     |          no lift       v
     +----------------- [ Revert ]          (keep the base model;
        (inference hurt)                     never ship a worse model)
```

> **▸ [Open the interactive diagram](/blog/diagrams/finai-reject-inference-credit-scoring.html)** — Reject-inference workflow: fit on accepts, infer the declined outcomes, refit on the augmented set, and revert if held-out lift is negative.

## The four techniques worth knowing

**Hard cutoff (reclassification).** Score every reject with the base model and assign it a definite good or bad label by comparing its predicted probability to a threshold. Rejects above the bad-rate cutoff become "bad," the rest become "good," and everything goes into the refit at full weight. It is the simplest method and the easiest to abuse. Because the labels come straight from the base model, hard cutoff tends to reinforce whatever the base model already believed. Use it as a baseline, not a destination, and expect it to overstate confidence.

**Parceling.** A more honest cousin of the hard cutoff. Instead of forcing a binary label, you bucket the rejects by their predicted score band and assign good/bad status *randomly within each band*, in proportion to the observed bad rate of accepts in that same band (usually inflated by a factor, since rejects are riskier than accepts at equal score). This preserves the fact that a score of, say, 0.3 means roughly a 30% chance of going bad rather than a hard verdict. Parceling injects realistic noise and avoids the false certainty of reclassification.

**Augmentation (reweighting).** This method reframes the problem as one of missing data rather than missing labels. You model the probability that an applicant was *accepted* given their features, then up-weight the accepts that resemble rejects so they stand in for the unobserved declined population. An accept who looks like a typical reject counts for more; an accept in a region densely populated by accepts counts for less. The appeal is that you never fabricate an outcome. The catch is that it only works where accepts and rejects overlap in feature space. In regions where you rejected essentially everyone, there is no analogous accept to borrow strength from, and reweighting cannot manufacture information that was never collected.

**Fuzzy augmentation (fractional parceling).** Rather than committing each reject to one class, you enter each reject into the training set *twice*: once as a "good" with weight equal to its inferred probability of being good, and once as a "bad" with the complementary weight. A reject scored at 0.7 bad contributes 0.7 of a bad row and 0.3 of a good row. This spreads each declined applicant's uncertainty across both classes instead of pretending you know which one they are, and it usually behaves better than a hard cutoff while being simpler to implement than a full accept/reject propensity model.

## The assumption you cannot escape

Every one of these methods leans on the same load-bearing assumption: that once you condition on the features you actually recorded, rejection carries no *additional* information about the outcome. In missing-data language, the outcomes are missing at random given the observed covariates. If a loan officer rejected someone for a reason that never made it into your feature set, that information is gone, and no inference method can recover it. Reject inference interpolates into the gaps between your observed data; it cannot extrapolate into regions where you have no signal at all.

This is why reject inference helps most when your rejection was driven mainly by scored, recorded variables, and helps least when it was driven by judgment, external data, or policy overlays you did not log. Be honest about which world you live in before you trust the inferred labels.

## Validating that inference actually helped

The dangerous failure mode is a model that *feels* more complete because you fed it the whole through-the-door population, but is actually worse because you injected fabricated labels built from the base model's own biases. Never assume inference helped. Prove it.

Reserve a held-out slice of your *accepts* that neither the base model nor the refit ever saw, and compare the two models on it using rank-ordering metrics such as KS or AUC, and — more importantly — calibration in the score bands near your cutoff. If the augmented model does not clearly beat the base model there, revert. That revert branch is not a formality; it is the whole safety net. A reject-inference pipeline that cannot fall back to the base model is a pipeline that ships regressions.

Two more checks pay for themselves. Track the acceptance-rate region: the inferred model should improve most where the old policy was loosest, since that is where accepts and rejects overlap and inference has real footing. And run a swap-set analysis by simulating the new cutoff and asking which applicants the two models disagree on — the "swap-ins" you would now approve and the "swap-outs" you would now decline. If the swapped population's expected bad rate looks worse than the customers it replaces, the inference has not bought you anything, however pretty the aggregate metrics.

## Practical guidance

Treat reject inference as a governed, reversible experiment rather than a data-cleaning step. Start with a well-calibrated base model, because every downstream method inherits its errors. Prefer the softer methods — parceling, fuzzy augmentation, or reweighting — over a hard cutoff, since fabricating confident labels is the fastest way to fool yourself. Document the missingness assumption and the exact weight or proxy assigned to each inferred row, so an auditor can reconstruct what you did and why. And keep the base model on the shelf, ready to reclaim, until held-out evidence says the augmented one earns its place. The applicants you declined are not noise to be ignored; they are the part of the picture your data politely hid from you, and modeling them well is what separates a scorecard that measures your old policy from one that can safely change it.
