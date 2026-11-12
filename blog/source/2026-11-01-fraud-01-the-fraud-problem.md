# The Fraud Problem — Adversarial, Asymmetric, and Allergic to Textbook ML

*Fraud detection looks like a classification problem and behaves like nothing else in machine learning: the adversary adapts to your model, the classes are wildly imbalanced, the labels arrive months late, your own decisions censor the data you learn from, and both kinds of error cost real money in different currencies. This series builds fraud and risk systems from first principles — and this opening post is about why the textbook assumptions fail, because every architecture decision downstream flows from these five inversions.*

Fraud sits at the intersection this blog has circled from several sides — [ML foundations](/blog/series/machine-learning-from-first-principles/), [RegTech compliance](/blog/series/regtech-compliance-as-engineering/) (which covers the AML/KYC *regulatory* layer; this series covers the *decision systems*), and the [fintech handbook](/blog/series/the-fintech-engineering-handbook/)'s money rails that fraud rides in on.

## Five ways fraud breaks the textbook

- **The adversary adapts.** In ordinary ML the world is indifferent to your model; in fraud the world studies it. Every deployed defense changes attacker behavior — block a pattern and they probe for the boundary, A/B-testing your model with stolen cards. The consequence is foundational: **model performance decays by design**, not by accident, and the system must be built around continuous adaptation (post 6) rather than periodic refreshes. Your test set from last quarter describes an adversary that no longer exists.
- **Base rates are tiny and the costs are asymmetric.** Fraud is a fraction of a percent of traffic, so accuracy is meaningless (approve everything: 99.9% accurate) and even precision/recall needs care (post 4). Worse, the error costs differ in kind: a **false negative** costs the fraud amount plus fees plus (at volume) your standing with card networks; a **false positive** costs a blocked legitimate customer — lost revenue now, lost lifetime value later, and the quiet reputational tax of "my card never works here." These aren't the same currency, and the exchange rate between them is a *business* decision the system must expose, not bury in a threshold (post 4).
- **Labels arrive late and lie a little.** Ground truth is a chargeback that lands 30–90 days after the transaction — and some fraud is never reported, some chargebacks aren't fraud ("friendly fraud" is a customer disputing a purchase they made). Training data is therefore always months stale against an adversary that moved weeks ago, and partially mislabeled besides (post 5's whole subject).
- **Your decisions censor your data.** The transactions you decline produce *no outcome label* — you never learn whether they were actually fraud. Train naively on approved-only data and the model learns the fraud that got past you, not the fraud that exists; meanwhile the region you decline hardest is exactly where you're blindest. This selective-labels problem (post 5) quietly bends every metric computed on observed outcomes.
- **Milliseconds, in the payment path.** The decision runs synchronously inside authorization — tens of milliseconds of budget, at peak traffic, with the answer irrevocable at approval time. Whatever sophistication the system has must fit that budget (post 8), which shapes feature engineering (post 3) more than any modeling preference.

## The shape of the solution

These inversions dictate the architecture the series builds: **rules and models as complements** (post 2 — rules for the sharp, explainable, fast-deploy edges; models for the subtle patterns), **features as the real IP** (post 3 — velocities, graphs, and histories computed identically offline and online, where most production fraud-ML failure actually lives), **threshold-and-cost machinery** that keeps the error trade visible to the business (post 4), **label pipelines** that handle delay, censoring, and noise honestly (post 5), **adaptation loops** against drift both natural and adversarial (post 6), **humans in the loop** — review queues and friction ladders, because the best answer is often "make them prove it" rather than yes/no (post 7), and **production operation** under latency, explainability, and regulatory constraints (post 8). The through-theme: fraud systems are not models — they're *decision factories* where the model is one input among rules, features, costs, humans, and feedback, and treating the model as the system is the field's most reliable beginner mistake.

The takeaway: fraud inverts the textbook five ways — an adversary that adapts to the model, vanishing base rates with asymmetric error currencies, labels that arrive late and partly wrong, decisions that censor their own training data, and a milliseconds budget in the money path. The answer isn't a better classifier; it's a **decision system**: rules beside models, feature infrastructure as the core asset, explicit cost machinery, honest label handling, continuous adaptation, human review, and production discipline — the map this series walks.

## Key takeaways

- **The adversary studies the model**: decay is by design; the test set describes a dead adversary; adaptation is architecture, not maintenance.
- **Tiny base rates, asymmetric costs**: accuracy is void; FN and FP cost in *different currencies*, and that exchange rate is a business decision to surface, not a threshold to bury.
- **Labels are late, partial, and noisy** (chargebacks at 30–90 days, unreported fraud, friendly fraud) — training data trails the adversary by months.
- **Selective labels**: declined transactions never get outcomes — naive training learns only the fraud that got past you, and you're blindest where you block hardest.
- Fraud systems are **decision factories** — model + rules + features + costs + humans + feedback — with the model as one component, under a real-time budget.

## Further reading

- [Credit card fraud — the adversarial domain itself](https://en.wikipedia.org/wiki/Credit_card_fraud)
- [Card-not-present transaction — where modern fraud concentrated](https://en.wikipedia.org/wiki/Card-not-present_transaction)
