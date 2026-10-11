# Differential Privacy in Practice — Training Models That Don't Memorize

*The theory of differential privacy is elegant; applying it to machine learning training is where it gets real. The key technique, DP-SGD, modifies the ordinary training loop so the resulting model carries a provable privacy guarantee — it demonstrably can't have memorized any individual's data too strongly. This post is about how differential privacy actually gets into a model, the knobs that control it, and the honest trade-offs that decide whether it's worth it.*

Post 3 defined differential privacy and its ε budget. This post applies it to the thing this series cares about — training ML models on sensitive data — turning the abstract guarantee into a concrete modification of gradient descent (ML series, post 3). It's where differential privacy stops being a statistics concept and becomes an ML engineering practice.

## DP-SGD: making the training loop private

Ordinary model training (the ML series' gradient descent) computes gradients from batches of data and steps the parameters to reduce loss. The problem for privacy: those gradients carry detailed information about the specific training examples, and the model can memorize them (post 2). **Differentially Private Stochastic Gradient Descent (DP-SGD)** modifies the loop to bound and mask each example's influence, with two changes:

- **Gradient clipping (per example).** Compute the gradient for each individual training example and *clip* its magnitude to a fixed maximum. This bounds how much any single example can influence the update — directly limiting the "sensitivity" (post 3) of training to any one person. No single outlier record can yank the model toward itself, which is exactly the lever memorization uses.
- **Noise addition.** Add calibrated random noise to the (clipped, aggregated) gradient before the parameter step. This is post 3's noise, applied to the learning signal: it obscures the contribution of any individual example within the batch, so the model's updates — and thus the final model — are provably insensitive to whether any one person was present.

The result is a model trained with a **provable differential-privacy guarantee**: you can state an ε (post 3) for the trained model, meaning it demonstrably can't have depended too much on any individual's data — which defeats membership inference and extraction (post 2) at the source. The guarantee is in the *model*, not bolted on afterward. Crucially, differential privacy *composes* (post 3), and training touches the data many times (every epoch, every batch), so the privacy cost accumulates across all those accesses — DP-SGD carefully *accounts* for the total ε spent over the whole training run. This accounting is what makes the final guarantee trustworthy and is a core part of the technique.

## The knobs and the cost

DP-SGD exposes the privacy-utility trade-off (post 3) as concrete training choices:

- **The privacy budget ε** — chosen up front: smaller ε means more noise and stronger privacy but a less accurate model. This is the primary dial.
- **The clipping threshold** — how tightly per-example gradients are bounded; too tight loses signal, too loose weakens the privacy.
- **The noise multiplier** — how much noise per step, which combines with the number of training steps (via composition) to determine the total ε.
- **Batch size and training length** — interact with the privacy accounting, since more data accesses spend more budget.

And the cost is real — this is the honest part practitioners must weigh:
- **Accuracy drops.** DP-SGD almost always produces a less accurate model than non-private training at a given budget, because the noise and clipping degrade the learning signal. The gap can be small or large depending on ε, the task, and especially the dataset size.
- **Small datasets and minorities suffer most.** Differential privacy's noise hurts more when there's less data to average over, and it can disproportionately degrade performance on *underrepresented groups* (whose patterns are rarer and thus more obscured by the privacy mechanism) — a genuine tension between privacy and fairness worth naming explicitly.
- **Compute overhead.** Per-example gradient clipping is more expensive than standard batched gradients, adding real training cost.
- **Choosing ε is hard.** There's no universal "private enough" value; ε is a policy decision balancing risk, utility, and context, and reasonable experts disagree on acceptable values.

## When (and whether) to use it

Given the cost, DP-SGD is not a default — it's a deliberate choice for specific situations:

- **Use it when the model will be exposed and the data is sensitive.** If you're releasing a model, offering query access via an API, or sharing a model trained on private data (medical, financial, personal), DP-SGD's guarantee is exactly the protection against the extraction/membership attacks (post 2) that exposure invites. The more public the model, the more the guarantee is worth.
- **Use it when you need to *prove* privacy** — for regulatory compliance or contractual assurance, a formal ε guarantee is something you can state and defend, unlike "we were careful." This provability is often the real reason to adopt it.
- **Weigh it carefully when accuracy is critical and data is limited** — on small or imbalanced datasets the accuracy cost (and the fairness impact) may be prohibitive, and a different privacy approach (federated learning, post 5; or strong access control plus not releasing the model) may fit better.

The broader practical point: differential privacy in ML is a *spectrum*, not a switch. You choose how much privacy to buy (ε) against how much accuracy you can spare, and you combine it with other techniques — famously, **federated learning with differential privacy** (post 5) trains across decentralized data *and* bounds each participant's influence, getting both "data never centralizes" and "the model can't memorize individuals." DP-SGD is the workhorse that puts a provable privacy guarantee *inside* a model, and knowing its knobs and its costs is what lets you decide, honestly, whether that guarantee is worth its price for your system.

The throughline: **DP-SGD** puts a provable privacy guarantee *inside* a trained model by modifying gradient descent with **per-example gradient clipping** (bound any one example's influence — the lever memorization uses) and **calibrated noise** on the aggregated gradient (obscure any individual's contribution), plus careful **privacy accounting** of the total ε spent across all data accesses (since DP composes and training touches data repeatedly). The result demonstrably can't depend too much on any individual, defeating membership inference/extraction (post 2) at the source. Its knobs (**ε**, clipping threshold, noise multiplier, batch/length) expose the **privacy-utility trade-off** as training choices, and the **cost is real**: accuracy drops (worst on **small datasets and underrepresented groups** — a privacy-fairness tension), compute overhead, and ε is a hard policy call. So use it deliberately — when the **model is exposed** and data sensitive, or when you must **prove** privacy — and combine it (e.g. **federated learning + DP**), treating privacy as a spectrum you price, not a switch.

## Key takeaways

- **DP-SGD** modifies training (gradient descent) to produce a model with a **provable differential-privacy guarantee**, via **per-example gradient clipping** (bound each example's influence — directly limiting the memorization lever) and **calibrated noise** on the aggregated gradient (mask any individual's contribution).
- Because DP **composes** and training accesses data many times (epochs/batches), DP-SGD **accounts** for the total **ε** spent across the whole run — this accounting is what makes the final guarantee trustworthy, and the guarantee lives *in the model*, defeating membership inference/extraction (post 2) at the source.
- Knobs expose the privacy-utility trade-off: **ε** (primary dial — smaller = more private, less accurate), **clipping threshold**, **noise multiplier**, and **batch size/training length** (interact with accounting).
- The **cost is real**: accuracy drops versus non-private training; the hit is **worst on small datasets and underrepresented groups** (a genuine **privacy-vs-fairness** tension); per-example clipping adds **compute**; and choosing **ε is a hard policy decision** with no universal "private enough."
- Use DP-SGD **deliberately**: when the **model is exposed** (released, API, shared) and the data is sensitive, or when you must **prove** privacy (compliance/contract); weigh it carefully when accuracy is critical and data limited — and **combine** it with other techniques (e.g. **federated learning + DP**, post 5), treating privacy as a priced spectrum, not a switch.

## Further reading

- [Differential privacy — the guarantee DP-SGD provides](https://en.wikipedia.org/wiki/Differential_privacy)
- [Stochastic gradient descent — the training loop DP-SGD modifies](https://en.wikipedia.org/wiki/Stochastic_gradient_descent)
