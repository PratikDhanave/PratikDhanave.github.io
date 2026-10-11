# Trees and Ensembles — Why Gradient Boosting Still Wins on Tabular Data

*If you have a spreadsheet and a prediction to make, the state of the art is probably not a neural network — it's a gradient-boosted ensemble of decision trees. Decision trees are intuitive, handle messy real-world data gracefully, and when combined into ensembles become the most consistently winning approach to tabular machine learning. This post builds from a single tree to the ensembles that quietly power a huge fraction of production ML.*

Post 3 covered linear models, which draw straight boundaries. This post covers the other great classical family — tree-based models — which carve the feature space into regions and handle the nonlinear, interaction-heavy patterns that real tabular data is full of. Understanding why ensembles of trees dominate tabular problems is understanding where neural networks *aren't* the answer, which is a surprisingly large territory.

## The decision tree: learning a flowchart

A **decision tree** is exactly what it sounds like: a flowchart of yes/no questions on features that leads to a prediction. "Is income > $50k? → Is debt < $10k? → approve." The algorithm *learns* the questions and their order from data: at each node it picks the feature-and-threshold split that best separates the examples (most reduces impurity / increases information gain), recursively, until leaves are pure enough or a stopping rule hits.

Trees have real virtues that explain their staying power:
- **Interpretable** — you can read the path from root to leaf as a human-readable rule.
- **No scaling needed** — splits are threshold comparisons, so features on wildly different scales (age vs income) work without normalization, unlike linear models (post 3).
- **Handle nonlinearity and interactions** — a tree naturally captures "high income *and* low debt" interactions and nonlinear thresholds that a linear model misses.
- **Handle mixed and missing data** gracefully — numeric and categorical together, with sensible handling of gaps.

But a single tree has a fatal flaw: **it overfits** (post 5). Grown deep enough, it memorizes the training data — carving a region for every example — and generalizes poorly. A single tree is high-variance: small data changes produce wildly different trees. The fix is not one tree but *many*.

## Ensembles: many weak models beat one strong one

The central insight of tree-based ML is the **ensemble** — combine many models so their errors cancel and the whole is more accurate and stable than any part. Two strategies dominate, and the difference between them is worth knowing:

- **Bagging / Random Forests.** Train many trees *independently*, each on a random subset of the data and features, then average their predictions (or vote). Because each tree overfits *differently*, averaging cancels their individual errors, slashing variance. **Random forests** are this idea, and they're a superb default: robust, hard to misuse, little tuning, strong out-of-the-box accuracy. The trees are trained in parallel and independent.
- **Boosting / Gradient Boosting.** Train trees *sequentially*, each new tree correcting the errors the ensemble has made so far. The model focuses successive trees on the hardest, still-wrong examples, gradually assembling a strong predictor from many weak ones. **Gradient boosting** (and its famous implementations) is this idea, and when tuned it typically achieves the *highest* accuracy on tabular data of any method — which is why it wins competitions and runs countless production systems.

The trade-off: random forests are more forgiving and parallel; gradient boosting is more accurate but more sensitive to tuning and sequential. Both turn the overfitting-prone single tree into a reliable, high-performance model — the ensemble is what makes trees great.

## Why trees still beat deep learning on tabular data

Here's the fact that surprises people steeped in the deep-learning narrative: on **tabular** data — the structured rows-and-columns that run business (fraud, credit, churn, pricing, demand) — gradient-boosted trees generally *outperform* neural networks, and remain the pragmatic state of the art. The reasons are instructive:

- **Tabular features are already meaningful.** Deep learning's advantage is *learning representations* from raw signals (pixels, audio, text) where features aren't given. Tabular features are already engineered and meaningful (post 2), so there's less representation to learn, erasing deep learning's main edge.
- **Trees handle tabular quirks natively.** Mixed types, different scales, missing values, irrelevant features, and sharp thresholds — all common in tabular data — are exactly what trees handle gracefully and neural nets handle awkwardly.
- **They're efficient and robust.** Boosted trees train fast on a CPU, need less data and less tuning than a neural net, and are harder to break — a better engineering fit for most business problems.

The practical takeaway is a decision rule: for **unstructured** data (images, audio, text, where representation must be learned), reach for deep learning; for **tabular** data, reach for gradient-boosted trees first, and only consider neural nets if trees plateau. This is one of the most useful and least-known heuristics in applied ML — it saves enormous effort and usually produces the better model. And trees keep the classical virtues: faster, cheaper, and more interpretable than a deep net (feature importances come for free), which matters in exactly the regulated, high-stakes domains where tabular data lives.

The throughline: a **decision tree** learns a flowchart of feature splits — interpretable, scale-free, nonlinearity- and interaction-friendly, graceful with mixed/missing data — but a single tree **overfits** badly. **Ensembles** fix this: **random forests** (bagging — many independent trees averaged to cancel variance; robust, low-tuning default) and **gradient boosting** (sequential trees each correcting prior errors; highest tabular accuracy when tuned). And the key heuristic: on **tabular** data, gradient-boosted trees generally **beat neural networks** — because tabular features are already meaningful (less representation to learn), trees handle tabular quirks natively, and they're faster/cheaper/more interpretable — so reach for trees on structured data and save deep learning for unstructured signals.

## Key takeaways

- A **decision tree** learns a flowchart of feature splits (picking the most-separating split at each node); it's **interpretable**, needs **no scaling**, and natively handles **nonlinearity, interactions, and mixed/missing data** — but a single tree **overfits** (high variance).
- **Ensembles** combine many trees so errors cancel: **random forests** use **bagging** (many *independent* trees on random data/feature subsets, averaged — robust, parallel, low-tuning, great default); **gradient boosting** trains trees **sequentially**, each correcting prior errors (highest tabular accuracy when tuned, more tuning-sensitive).
- On **tabular data**, gradient-boosted trees generally **outperform neural networks** — because tabular features are already meaningful (deep learning's representation-learning edge doesn't apply), trees handle tabular quirks natively, and they're faster, cheaper, and more interpretable.
- The useful decision rule: **unstructured** data (images/audio/text) → deep learning (representation must be learned); **tabular** data → gradient-boosted trees first, neural nets only if trees plateau.
- Trees give **feature importances for free** and keep classical virtues (speed, low data/tuning needs, interpretability) — a strong fit for the regulated, high-stakes domains where tabular data lives.

## Further reading

- [Decision tree learning — learning flowcharts from data](https://en.wikipedia.org/wiki/Decision_tree_learning)
- [Random forest — bagging ensembles of trees](https://en.wikipedia.org/wiki/Random_forest)
