# Intrinsic vs Post-Hoc — Two Paths to an Explainable Model

*There are exactly two ways to get an explainable model: build one that's transparent from the start, or build a black box and explain it afterward. These two paths — intrinsic interpretability and post-hoc explanation — define the entire field, and choosing between them is the first real decision in any project where understanding matters. This post lays out both, their trade-offs, and why the choice is less obvious than "just use the accurate model and explain it later."*

Post 1 introduced the accuracy-interpretability tension. This post gives the two strategic responses to it. Everything else in the series is an instance of one or the other: glass-box models (intrinsic) or the explanation techniques like LIME and SHAP (post-hoc). Knowing the distinction — and the serious argument for preferring intrinsic when you can — frames all the techniques to come.

## Intrinsic interpretability: transparent by design

The first path is to use a model that is **interpretable by construction** — a "glass box" whose reasoning you can read directly, with no separate explanation step:

- **Linear/logistic regression** (ML series, post 3) — the coefficients *are* the explanation: each tells you exactly how much each feature moves the prediction, in which direction. Fully transparent.
- **Short decision trees** — the path from root to leaf *is* a human-readable rule ("income > X and debt < Y → approve"). You can literally trace the decision.
- **Rule-based models and other simple forms** — generalized additive models, small rule lists, and similar, which trade some flexibility for the property that a human can follow their logic.

The appeal is strong: the explanation is *faithful* (it's not an approximation — it's the actual model), it's always available, and there's no risk of the explanation diverging from what the model really does. The cost is the accuracy ceiling from post 1 — these models may not capture complex patterns as well as a deep net. But that cost is often *smaller than assumed*: for many real problems, especially tabular ones, a well-engineered interpretable model (good features + logistic regression or a tuned small ensemble) matches a black box closely, so you get transparency nearly for free. The intrinsic path says: *reach for the transparent model first, and only accept opacity when the accuracy gain is real and worth it.*

## Post-hoc explanation: explain the black box afterward

The second path is to build the most accurate model you can — a black box — and then apply a *separate* technique to explain its behavior after the fact. This is **post-hoc interpretability**, and it's where most of the field's famous methods live:

- You train the opaque model for accuracy, then use explanation techniques — **feature importance** (post 3), **LIME** (post 4), **SHAP** (post 5), example-based methods (post 6) — to produce human-understandable accounts of *why* it predicts as it does.
- Most of these are **model-agnostic** (post 1): they treat the model as a black box, probing it with inputs and observing outputs, so they work on *any* model including deep nets and LLMs.

The appeal is that you don't sacrifice accuracy — you keep the best model *and* get explanations. This is why post-hoc methods dominate in practice: they let teams use powerful models while still answering "why?" And for genuinely complex domains (images, text, high-dimensional data) where interpretable models really can't compete, post-hoc explanation is the *only* option — you can't make a transparent model that matches a deep net on image recognition, so you build the deep net and explain it.

But post-hoc explanations carry a fundamental caveat that post 1 flagged: **they are approximations of the model, not the model itself.** A post-hoc explanation is a *second* model or procedure trying to describe the first, and it can be *unfaithful* — it can give a plausible, human-friendly story that doesn't actually match what the black box is doing. You can get an explanation that *looks* reasonable and is *wrong* about the model's true reasoning, which is worse than no explanation because it's confidently misleading. Post-hoc interpretability buys accuracy-plus-explanation, but the explanation comes with an asterisk you must never forget.

## Choosing between them — and the real debate

The choice between intrinsic and post-hoc is a genuine strategic decision, and there's a serious, often-overlooked argument for intrinsic:

- **Default toward intrinsic when stakes are high and an interpretable model is competitive.** For high-stakes decisions (credit, healthcare, criminal justice), a faithful explanation matters enormously, and a prominent view in the field (notably argued by Cynthia Rudin) is that for many such problems you should *use an inherently interpretable model rather than explain a black box* — because the post-hoc explanation might be unfaithful exactly where being wrong is most dangerous. The common assumption that you *must* sacrifice accuracy for interpretability is frequently false on tabular/structured data, so the "black box + explanation" approach is often a needless risk. This is the most important and most under-appreciated point in applied interpretability.
- **Use post-hoc when a black box is genuinely necessary** — complex, high-dimensional data (images, text, audio) where interpretable models can't compete, and you accept the faithfulness caveat and validate explanations carefully.
- **It's not strictly either/or** — you can use an intrinsic model as a baseline and benchmark (does the black box actually beat it enough to justify its opacity?), and you can apply post-hoc methods to interpretable models too.

The practical discipline that follows: *first ask whether you even need the black box.* Train an interpretable baseline; if it's close to the black box's accuracy, prefer it and get faithful explanations for free. Only when the black box's accuracy advantage is real and the problem truly demands it should you accept opacity — and then lean on post-hoc methods (posts 3–7) while remembering their explanations are fallible approximations (post 8). The two paths aren't equal defaults: intrinsic should be the first reach, post-hoc the considered fallback — the opposite of the common "build the fanciest model, explain it later" instinct.

The throughline: there are exactly two routes to an explainable model. **Intrinsic interpretability** uses models transparent *by construction* — linear/logistic regression (coefficients *are* the explanation), short decision trees (the path *is* a rule), rule-based/additive models — giving **faithful, always-available** explanations that can't diverge from the model, at an accuracy cost that's **often smaller than assumed** (especially on tabular data). **Post-hoc interpretability** builds a black box for accuracy then explains it afterward with (usually **model-agnostic**) techniques (feature importance, LIME, SHAP) — keeping the best model and the only option for complex domains like images/text, but its explanations are **approximations that can be unfaithful** (plausible yet wrong — confidently misleading). The real debate: for high-stakes problems where an interpretable model is competitive, **prefer intrinsic** rather than risk an unfaithful explanation of a black box (Rudin's argument) — so the discipline is *first ask whether you even need the black box*, making intrinsic the first reach and post-hoc the considered fallback.

## Key takeaways

- Two paths to an explainable model: **intrinsic** (transparent by construction) and **post-hoc** (build a black box, explain it afterward) — the strategic distinction underlying the whole field.
- **Intrinsic**: linear/logistic regression (coefficients *are* the explanation), short decision trees (root-to-leaf path *is* a readable rule), rule-based/additive models — explanations are **faithful** (the actual model, not an approximation) and always available; the accuracy cost is **often smaller than assumed**, especially on tabular data.
- **Post-hoc**: train the most accurate (opaque) model, then apply **model-agnostic** techniques (feature importance post 3, LIME post 4, SHAP post 5) to explain it — keeps accuracy and is the **only option for complex data** (images/text/audio), but explanations are **approximations that can be unfaithful** (plausible but wrong = confidently misleading).
- The key debate: for **high-stakes** decisions where an interpretable model is competitive, **prefer intrinsic** over explaining a black box (the accuracy sacrifice is often illusory on structured data, and an unfaithful explanation is most dangerous exactly where stakes are high — Rudin's argument).
- The discipline: **first ask whether you need the black box** — train an interpretable baseline; prefer it if close (faithful explanations for free); accept opacity only when its accuracy advantage is real, then use post-hoc methods while remembering they're **fallible approximations** (post 8). Intrinsic is the first reach, post-hoc the fallback — not "build the fanciest model and explain it later."

## Further reading

- [Explainable artificial intelligence — intrinsic and post-hoc approaches](https://en.wikipedia.org/wiki/Explainable_artificial_intelligence)
- [Decision tree learning — an intrinsically interpretable model](https://en.wikipedia.org/wiki/Decision_tree_learning)
