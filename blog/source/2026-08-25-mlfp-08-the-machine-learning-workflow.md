# The Machine Learning Workflow — From Problem to Production

*Knowing the algorithms is maybe 20% of doing machine learning. The other 80% is the workflow around them: framing the problem, preparing the data, iterating honestly, and getting a model into production where it keeps working. This closing post assembles the series into the end-to-end process real ML follows — and names the places where projects actually fail, which are almost never the algorithm.*

Posts 1–7 built the pieces — learning, data, features, models, generalization, evaluation. This post is how they fit into a repeatable process, and how classical ML connects to the modern AI stack this blog mostly covers. The theme: ML is an *empirical, iterative engineering discipline*, and treating it as a one-shot "train a model" step is the surest way to fail.

## The workflow, end to end

A real ML project is a loop, not a line, and most of it isn't modeling:

1. **Frame the problem.** Turn a business goal into an ML problem: what's predicted, is it classification/regression (post 1), what would a *useful* result look like, and — critically — what's the metric that reflects success (post 6)? Many ML projects fail here, by solving a crisply-defined problem that doesn't match the real need. Also ask whether ML is even the right tool; often a rule or a query suffices.
2. **Get and prepare the data.** Collect, clean, and understand the data; engineer features (post 2). This is the largest, least glamorous, most decisive phase — and where quality is won or lost.
3. **Split the data.** Train/validation/test (post 5) *before* any modeling, so your evaluation stays honest and leakage-free.
4. **Build a baseline.** Train a simple model first (linear/logistic, post 3, or a trivial heuristic). The baseline tells you whether ML helps at all and gives every later model something to beat. Skipping the baseline is how teams celebrate a complex model that's barely better than "predict the average."
5. **Iterate.** Try better features, better models (trees/ensembles, post 4), tuning — measuring each honestly on validation data, diagnosing overfitting vs underfitting (post 5), and letting the evidence (not the hype) pick the model. Most gains come from *features and data*, not fancier algorithms.
6. **Evaluate for real.** Final test-set evaluation with the right metric, broken down by segment for quality and fairness (post 6). Decide, on evidence, whether it's good enough to ship.
7. **Deploy and monitor.** Put the model into production and *watch it* — because models decay (next section).

The shape to internalize: modeling is a small, late step in a process dominated by problem-framing and data work, and the whole thing is a *loop* driven by honest measurement.

## Deployment and the thing nobody warns you about: decay

Getting a model to good test accuracy is not the finish line — production is, and production has a failure mode that offline work never shows: **models degrade over time**. The world the model learned changes — customer behavior shifts, fraud tactics evolve, an upstream data source changes format — and the model's accuracy silently decays. This is **concept drift** (and data drift), and it means a deployed model is not a shipped artifact but a *maintained* one:

- **Monitor in production** — track the model's performance and its input distributions, so you detect drift before users do. A model that's quietly wrong looks exactly like one that's right until you measure.
- **Retrain on fresh data** — on a schedule or when drift triggers it, so the model stays matched to the current world.
- **Watch the data pipeline** — in practice, most production ML incidents are *data* problems (a feature's meaning changed, a source broke) rather than model problems, so the pipeline feeding the model needs as much monitoring as the model.

This is the bridge from classical ML to the **MLOps / LLMOps** discipline this blog covers elsewhere ([LLMOps in Practice](/blog/series/llmops-in-practice/), [The AI Production Roadmap](/blog/series/the-ai-production-roadmap/)): the practices for deploying, monitoring, and maintaining models in production. The lesson is identical whether the model is a logistic regression or an LLM — *shipping is the start of the model's life, not the end.*

## Where this sits in the modern AI world

To close the series, it's worth placing classical ML relative to the deep-learning and LLM world that dominates attention:

- **Classical ML is not obsolete — it's the right tool for a huge class of problems.** For tabular business data (post 4), for problems needing interpretability and regulatory defensibility (post 3), for small data, and where cost and latency matter, classical ML (especially gradient-boosted trees and linear models) is often the *better* choice than a neural network. A great deal of the world's production ML is still classical, and knowing when *not* to reach for deep learning is a mark of experience.
- **The foundations are universal.** Every concept here — features, loss, gradient descent, generalization, overfitting, the train/test split, evaluation metrics, the workflow, drift — applies directly to deep learning and LLMs. Fine-tuning a model is the training loop from post 3; LLM evaluation is the metric discipline from post 6; benchmark contamination is the leakage of post 5; model drift hits LLMs too. The deep-learning stack this blog covers is these foundations, scaled up and specialized.
- **Understanding the floor makes you better upstairs.** Engineers who skip classical ML and start at LLMs tend to misunderstand *why* things work and fail — they over-reach for deep learning, under-invest in data, mis-evaluate, and are surprised by drift. The foundations are what turn using ML libraries into understanding ML.

The throughline: doing ML is mostly the **workflow**, not the algorithm — **frame the problem** (and its metric; check if ML is even needed), **prepare data and features** (the biggest, most decisive phase), **split before modeling**, **build a baseline**, **iterate with honest measurement** (most gains from data/features, not fancier models), **evaluate for real** (right metric, by segment), and **deploy and monitor**. Production's hidden failure mode is **model decay / concept drift** — models are *maintained*, not shipped-and-forgotten, which bridges to **MLOps/LLMOps**. And classical ML remains the right tool for tabular, interpretable, small-data, and cost-sensitive problems, while its foundations — loss, gradient descent, generalization, evaluation, drift — are *universal*, underpinning the entire deep-learning and LLM stack. Learn the floor and everything upstairs makes sense.

## Key takeaways

- ML is ~80% **workflow**, ~20% algorithm: **frame the problem** (define the success metric; confirm ML is the right tool), **prepare data + features** (largest, most decisive phase), **split before modeling** (leakage-free), **build a baseline** (so you know ML helps and have something to beat), **iterate with honest validation measurement**, **evaluate for real** (right metric, by segment), **deploy and monitor**.
- Most gains come from **features and data**, not fancier algorithms; most projects that fail do so at **problem-framing** or **data**, almost never at the algorithm.
- Production's hidden failure mode is **model decay / concept drift** — the world changes and accuracy silently degrades — so a deployed model is **maintained, not shipped**: monitor performance and input distributions, retrain on fresh data, and watch the data pipeline (most incidents are *data* problems). This is the bridge to **MLOps/LLMOps**.
- **Classical ML isn't obsolete** — it's often the *better* choice for tabular, interpretability-required, small-data, and cost/latency-sensitive problems (gradient-boosted trees, linear models); knowing when *not* to use deep learning is a mark of experience.
- The foundations here — **features, loss, gradient descent, generalization, overfitting, train/test split, evaluation metrics, drift** — are **universal**, underpinning deep learning and LLMs (fine-tuning is the training loop; LLM eval is the metric discipline; benchmark contamination is leakage); learning the floor makes everything upstairs comprehensible.

## Further reading

- [Machine learning — the field these foundations compose](https://en.wikipedia.org/wiki/Machine_learning)
- [Training, validation, and test data sets — the workflow's backbone](https://en.wikipedia.org/wiki/Training,_validation,_and_test_data_sets)
