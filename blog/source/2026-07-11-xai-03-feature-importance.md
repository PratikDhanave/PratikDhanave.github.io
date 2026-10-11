# Feature Importance — What the Model Pays Attention To

*The most basic and most used interpretability question is also the most useful: which features actually matter to this model? Feature importance answers it, giving a ranked list of the inputs that drive a model's predictions — the first thing to compute when you want to understand, debug, or trust any model. This post covers the main ways to measure it, the traps that make naive importance misleading, and why permutation importance is the reliable default.*

Posts 1–2 framed interpretability and the intrinsic/post-hoc choice. This post covers the workhorse *global* technique (post 1): feature importance, which summarizes a model's overall behavior by ranking its inputs. It's where most interpretability work starts, and getting it right (and knowing its limits) prevents a surprising number of wrong conclusions.

## What feature importance tells you

**Feature importance** assigns each input feature a score reflecting how much it contributes to the model's predictions, producing a ranked list: this feature matters a lot, that one barely at all. It answers the *global* question "what does the model rely on overall?" and it's valuable for several immediate reasons:

- **Sanity-checking.** If a model predicting loan default rates "favorite color" as its top feature, something is wrong — feature importance catches models learning nonsense or leaking data. Conversely, if the important features match domain intuition, it builds trust.
- **Debugging and leakage detection.** A suspiciously dominant feature often signals **data leakage** (a feature that secretly encodes the answer — e.g. "account closed date" predicting churn). Feature importance is the fastest way to spot it, and leakage is one of the most common silent ML failures (ML series, post 5).
- **Feature selection and simplification.** Low-importance features can often be dropped, simplifying the model without hurting accuracy.
- **Communication.** "The model's decisions are driven mostly by income, debt, and payment history" is an explanation stakeholders and regulators can understand.

It's usually the *first* interpretability analysis to run on any model, because the ranked list of what-matters is both easy to produce and immediately informative.

## How it's measured — and why the obvious ways mislead

There are several ways to compute feature importance, and the naive ones have real traps:

- **Model-specific importances (use with caution).** Many models expose built-in importances — a linear model's coefficients, a tree ensemble's "impurity-based" importance (how much each feature reduced error across the trees). These are convenient but **misleading in specific ways**: tree impurity importance is *biased toward high-cardinality features* (features with many distinct values look important just because they offer more split points), and coefficients can mislead if features aren't scaled or are correlated. Built-in importances are a quick first look, not a trustworthy final answer.
- **Permutation importance (the reliable default).** The robust, model-agnostic approach: measure how much the model's *performance drops* when you randomly **shuffle** one feature's values. The logic is clean — if scrambling a feature badly hurts accuracy, the model relied on it heavily; if shuffling it changes nothing, the model wasn't using it. Permutation importance works on *any* model (post 1's model-agnostic virtue), directly measures *predictive* reliance, and avoids the cardinality bias of impurity importance. It's the recommended default for a trustworthy global importance ranking.
- **SHAP-based importance** (post 5) — aggregating SHAP values across the dataset gives a theoretically grounded global importance that also connects to *local* explanations; often the best when you can afford it.

The practical guidance: don't trust built-in impurity importances uncritically; prefer **permutation importance** for a reliable global ranking, and SHAP when you want rigor and local-global consistency.

## The traps that make even good importance misleading

Feature importance is useful but genuinely easy to misread, and three traps cause most of the errors:

- **Correlated features split and hide importance.** If two features are correlated (say, two measures of income), the model may use them interchangeably, so importance gets *split* between them — each looks only moderately important when *together* they're crucial. Worse, permutation importance can *understate* a feature's importance when a correlated twin can substitute for it. Correlated features systematically distort importance rankings, and ignoring this leads to dropping features that actually matter.
- **Importance is not causation.** This is the big one (connecting to the [causal inference](/blog/series/causal-inference-for-engineers/) series): "feature X is important to the model" means the model *uses* X to predict, **not** that X *causes* the outcome or that *changing* X would change anything. A model may lean heavily on a feature that's merely correlated with the outcome via a confounder. Reading feature importance as a causal story — "income is important, so raising income would prevent default" — is a classic and costly error. Importance describes the *model*, not the *world*.
- **Global importance hides local and interaction effects.** A feature can be unimportant on average but *decisive* for a subset of cases, or matter only in *combination* with another feature — nuances a single global ranking erases. This is exactly why you also need *local* explanations (posts 4–6) that explain individual predictions, not just the global summary.

Held with these caveats, feature importance is the indispensable first step of interpretability: compute a reliable ranking (permutation or SHAP), use it to sanity-check and debug the model and detect leakage, and communicate what the model relies on — while never mistaking "the model uses this" for "this causes the outcome," and always remembering that correlated features and local effects can make the global picture lie. It tells you *what the model pays attention to*, which is the foundation, but not the whole story — the local methods in the next posts fill in *why a particular prediction* came out as it did.

The throughline: **feature importance** ranks which inputs drive a model's predictions — the first and most useful interpretability analysis, great for **sanity-checking**, **leakage detection**, **feature selection**, and **communication**. But measurement matters: **model-specific** importances (tree impurity, coefficients) are convenient yet **biased** (impurity favors high-cardinality features), so prefer **permutation importance** (shuffle a feature, measure the accuracy drop — model-agnostic, measures true predictive reliance, the reliable default) or **SHAP-based** importance (rigorous, local-global consistent). Three traps make even good importance mislead: **correlated features** split/hide importance, **importance is not causation** (it describes the *model* using a feature, not that the feature *causes* the outcome or that changing it would help — the costly error linking to causal inference), and **global importance hides local/interaction effects** (motivating the local methods of posts 4–6). Indispensable foundation, but not the whole story.

## Key takeaways

- **Feature importance** ranks how much each input drives predictions — the usual *first* interpretability step — valuable for **sanity-checking** (catch nonsense top features), **leakage detection** (a suspiciously dominant feature often secretly encodes the answer), **feature selection**, and **communication** to stakeholders/regulators.
- Measure it well: **model-specific** importances (tree **impurity** importance, linear **coefficients**) are convenient but **biased** (impurity favors high-cardinality features; coefficients mislead if unscaled/correlated) — a quick look, not a final answer.
- Prefer **permutation importance** (shuffle one feature's values, measure the performance drop — if it hurts, the model relied on it): **model-agnostic**, measures true *predictive* reliance, avoids cardinality bias — the reliable default; or **SHAP-based** importance (post 5) for rigor and local-global consistency.
- Three traps: **correlated features** split/hide importance (two income measures each look moderate when together they're crucial; permutation can *understate* a feature whose twin substitutes), **importance ≠ causation** (it means the model *uses* the feature, not that it *causes* the outcome or that changing it helps — the costly misread, see causal inference series), and **global importance hides local/interaction effects** (a feature decisive for a subset or only in combination — motivating local methods, posts 4–6).
- Held with these caveats, feature importance is the **indispensable foundation** of interpretability (compute a reliable ranking, debug/detect leakage/communicate) — telling you *what the model attends to*, but never *why a specific prediction* happened (local methods) and never a *causal* claim about the world.

## Further reading

- [Explainable artificial intelligence — global feature attribution](https://en.wikipedia.org/wiki/Explainable_artificial_intelligence)
- [Random forest — and the bias of impurity-based importance](https://en.wikipedia.org/wiki/Random_forest)
