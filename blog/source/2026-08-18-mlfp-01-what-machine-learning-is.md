# What Machine Learning Is — Programs That Learn from Data

*Most of this blog's AI content sits on top of machine learning without ever defining it. This series fixes that from the ground up: before transformers and LLMs, before fine-tuning and RAG, there is the plain idea of a program that improves at a task by learning patterns from data instead of being explicitly told the rules. Understanding that idea — and its three core flavors — is the foundation everything else in modern AI is built on.*

This series is for engineers fluent in the LLM world who never built the classical-ML floor underneath it. It's the companion to the applied series (fine-tuning, inference, evaluation): here we start at the beginning — what learning from data actually means, the kinds of problems it solves, and the vocabulary (features, models, training, generalization) that the rest of AI assumes you already have. Post 1 defines the whole field.

## The shift: from rules to examples

Traditional programming is *rules in, answers out*: you write explicit logic (`if income > X and debt < Y then approve`) and the program applies it. This works when you can state the rules. It fails when you can't — nobody can write the explicit rules that distinguish a cat from a dog in a photo, or flag a fraudulent transaction among millions of legitimate ones, because the "rules" are too numerous, too fuzzy, and too entangled for a human to enumerate.

**Machine learning** inverts the arrangement: *examples in, rules out*. Instead of writing the logic, you show the system many examples of inputs paired with correct outputs, and an algorithm **learns** the patterns that map one to the other. You don't program the rule for "fraud"; you show the system thousands of transactions labeled fraud/not-fraud, and it infers a rule. The classic definition: a program *learns* from experience (data) if its performance at a task improves with more experience. The deliverable of that learning is a **model** — a mathematical function, with parameters tuned by the data, that maps new inputs to predicted outputs.

This is why ML took over: for a huge class of problems — perception, language, prediction, recommendation — it is far easier to *collect examples* than to *write rules*, and the learned rules are better than any a human could hand-code. Every LLM is this idea at enormous scale: not programmed to write, but trained on text until it learned the patterns.

## The vocabulary you need

A few terms recur through all of ML, and pinning them down now makes everything later clearer:

- **Features** — the input variables the model sees (a transaction's amount, time, location; a pixel's values; a word's embedding). Choosing and shaping features (post 2) is much of the real work.
- **Label / target** — the correct output for an example, in problems where you have it (fraud/not-fraud, the house's price). Learning *with* labels vs *without* is the great divide (below).
- **Model** — the function that maps features to a prediction, defined by **parameters** (the numbers learned from data). "Training a model" means finding the parameter values that make its predictions fit the data.
- **Training** — the process of adjusting parameters to minimize error on the training examples, usually by optimizing a **loss function** (a measure of how wrong the predictions are).
- **Inference / prediction** — using the trained model on *new*, unseen inputs. This is the whole point: a model is only useful if it works on data it wasn't trained on — which is **generalization** (post 5), the central obsession of the field.

Keep one distinction above all: a model that memorizes its training data is worthless; a model that *generalizes* to new data is valuable. Everything in ML — evaluation, regularization, the train/test split — exists to chase generalization.

## The three kinds of learning

Machine learning divides into three paradigms by *what signal the algorithm learns from*, and knowing which one a problem is is the first modeling decision:

- **Supervised learning** — learn from *labeled* examples (input → correct output). This is the workhorse: classification (predict a category — spam/not-spam, which digit) and regression (predict a number — price, temperature). Most practical ML, and most of this series (posts 3–4), is supervised, because labeled data makes the learning signal clear and strong.
- **Unsupervised learning** — learn from *unlabeled* data, finding structure without being told the answer: clustering (group similar items — customer segments), dimensionality reduction (compress features while keeping signal), anomaly detection. You use it when you have lots of data but no labels, and you want to discover what's in it (post 7).
- **Reinforcement learning** — learn from *interaction and reward*: an agent takes actions in an environment and learns a policy that maximizes cumulative reward, with no labeled "right answer," only feedback. This is how game-playing and robotic-control systems learn, and it's the backbone of RLHF — important enough to get [its own series](/blog/series/reinforcement-learning-from-first-principles/).

A useful fourth category, **self-supervised learning**, powers modern LLMs: the data labels itself (predict the next word from the preceding words), giving supervised-style learning on unlabeled text at massive scale. It's why foundation models exist — the internet became a labeled dataset for free.

The throughline: ML is the move from *writing rules* to *learning them from examples*, producing a **model** (a parameterized function) whose only real goal is to **generalize** to new data. It splits by learning signal into **supervised** (labeled examples — classification/regression, the workhorse), **unsupervised** (unlabeled — find structure), and **reinforcement** (interaction and reward), with **self-supervised** learning (data labeling itself) powering today's foundation models. This is the floor the entire AI stack stands on, and the rest of the series builds it up one concept at a time.

## Key takeaways

- **Machine learning** inverts traditional programming — *examples in, rules out* instead of *rules in, answers out* — learning the input→output mapping from data when the rules are too numerous/fuzzy to hand-code (fraud, perception, language).
- The learned artifact is a **model**: a parameterized mathematical function; **training** tunes its parameters to minimize a **loss function** on examples, and **inference** applies it to new inputs.
- The field's central obsession is **generalization** — a model that memorizes training data is worthless; one that performs on *unseen* data is valuable — and nearly every ML technique exists to chase it.
- Core vocabulary: **features** (inputs), **label/target** (correct output), **parameters** (the numbers learned), **loss** (how wrong), **training** vs **inference**.
- Three paradigms by learning signal: **supervised** (labeled examples → classification/regression, the workhorse), **unsupervised** (unlabeled → clustering, dimensionality reduction, anomaly detection), **reinforcement** (interaction + reward) — plus **self-supervised** (data labels itself, e.g. next-word prediction) which powers modern LLMs.

## Further reading

- [Machine learning — the field and its paradigms](https://en.wikipedia.org/wiki/Machine_learning)
- [Supervised learning — learning from labeled examples](https://en.wikipedia.org/wiki/Supervised_learning)
