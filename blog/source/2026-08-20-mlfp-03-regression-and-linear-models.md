# Regression and Linear Models — The Workhorses You Should Understand First

*Before neural networks, the two models that still quietly run more of the world's predictions than anything else are linear and logistic regression. They are simple enough to understand completely, fast enough to train on anything, and interpretable enough to explain to a regulator — and understanding them teaches the mechanics (fitting, loss, gradient descent) that every more complex model shares. This post builds both from scratch and shows why "just use a linear model" is often the right answer.*

Post 1 defined supervised learning; this post builds its simplest, most important instances. Linear models are the "hello world" of ML, but dismissing them as toys is a mistake — they're a genuine production default, and crucially they're where you learn the universal pattern of *fitting a model by minimizing a loss*, which generalizes all the way up to training an LLM.

## Linear regression: fitting a line to predict a number

**Linear regression** predicts a continuous number (price, demand, temperature) as a weighted sum of the input features:

```
prediction = w₁·x₁ + w₂·x₂ + ... + wₙ·xₙ + b
```

Each feature gets a **weight** (`w`), there's a bias/intercept (`b`), and the prediction is their combination. "Training" means finding the weights that make the predictions fit the data best. "Best" is defined by a **loss function** — for regression, usually **mean squared error** (the average squared gap between predictions and true values) — and training is the search for the weights that *minimize* that loss.

Two things make this the foundational model:
- **It's interpretable.** Each weight says how much the prediction changes per unit of its feature — "each extra bedroom adds $40k" — so you can read the model, explain it, and sanity-check it. In regulated domains (credit, healthcare) this transparency is often legally required, which is why linear models remain in heavy production use.
- **It teaches the universal loop.** Define a model, define a loss measuring its error, and adjust parameters to reduce the loss. Every model in ML, up to and including LLMs, is this loop — linear regression just makes it visible.

## Gradient descent: how models actually learn

How do you *find* the loss-minimizing weights? For linear regression there's a closed-form formula, but the method that generalizes to everything else is **gradient descent**, and it's worth understanding because it's how essentially all modern ML trains:

- Start with random weights and compute the loss.
- Compute the **gradient** — the direction in which the loss increases fastest (the slope of the loss with respect to each weight).
- Take a small step in the *opposite* direction (downhill), scaled by a **learning rate**.
- Repeat until the loss stops decreasing.

It's the mental image of walking downhill in fog: feel the slope, step down, repeat, arrive at the bottom (the minimum-loss weights). The **learning rate** controls step size — too large and you overshoot and diverge, too small and training crawls — which is why it's the most important knob in ML training. This exact algorithm, scaled up with billions of parameters and automatic differentiation, is how neural networks and LLMs are trained. Learn it on linear regression and you understand training everywhere.

## Logistic regression: linear models for classification

Regression predicts numbers; **classification** predicts categories (spam/not-spam, fraud/legit, which-digit). **Logistic regression** adapts the linear model to classification with one change: it passes the linear combination through a **sigmoid** function that squashes any number into the range 0–1, interpreted as a **probability**.

```
probability = sigmoid(w₁·x₁ + ... + b)   →   a value between 0 and 1
```

So logistic regression outputs "70% likely to be fraud," and you threshold it (e.g. >0.5 → fraud) to get a decision. It's trained the same way — gradient descent minimizing a classification loss (cross-entropy) — and keeps the linear model's two virtues: it's fast and it's interpretable (each weight is the feature's influence on the odds). Despite the name "regression," it's the default *classification* algorithm, and like its cousin it's a legitimate production choice, not just a baseline.

Two notes that matter in practice: logistic regression draws a *linear* decision boundary, so it struggles when the classes aren't linearly separable (that's where trees and neural nets, posts 4 and beyond, come in) — but good feature engineering (post 2) often makes problems linearly separable, which is another reason features matter so much. And the **sigmoid** generalizes to the **softmax** for multi-class problems — the exact function at the output of a classifier neural network and in the final layer of an LLM choosing the next token. Again, the simple model teaches the mechanics of the complex one.

The throughline: **linear regression** predicts a number as a weighted sum of features, trained by minimizing a **loss** (mean squared error) — and it teaches the universal ML loop (model → loss → adjust parameters) plus **gradient descent** (step downhill along the loss gradient, scaled by the **learning rate**), which is how essentially all ML, including LLMs, is trained. **Logistic regression** adapts the linear model to classification via a **sigmoid** that outputs a probability, trained by minimizing cross-entropy — the default classification algorithm, and the direct ancestor of the softmax output in neural classifiers and LLMs. Both are **interpretable** and fast enough to be genuine production defaults, not just baselines — "just use a linear model" is often the correct, and most explainable, answer.

## Key takeaways

- **Linear regression** predicts a continuous value as a weighted sum of features (`w·x + b`), trained by minimizing a **loss** (typically **mean squared error**) — and it makes the universal ML loop visible: define a model, define a loss, adjust parameters to reduce it.
- **Gradient descent** is how that minimization (and nearly all modern ML training) works: compute the loss's **gradient**, step **downhill** scaled by the **learning rate** (the key knob — too big diverges, too small crawls), repeat — the same algorithm that trains neural networks and LLMs.
- **Logistic regression** adapts the linear model to **classification** by squashing the linear combination through a **sigmoid** into a 0–1 **probability**, thresholded into a decision; trained via cross-entropy, it's the default classifier.
- Both are **interpretable** (each weight is its feature's influence) and fast — genuine production defaults, often legally preferred in regulated domains, not mere baselines.
- Linear models draw **linear boundaries** (good feature engineering, post 2, often makes that enough); the **sigmoid → softmax** generalization is the exact output mechanism of neural classifiers and LLMs — the simple model teaches the complex one.

## Further reading

- [Linear regression — predicting a number from a weighted sum](https://en.wikipedia.org/wiki/Linear_regression)
- [Logistic regression — the linear model for classification](https://en.wikipedia.org/wiki/Logistic_regression)
