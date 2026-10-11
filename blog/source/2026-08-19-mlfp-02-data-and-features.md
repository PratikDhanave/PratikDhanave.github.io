# Data and Features — Where Machine Learning Is Really Won

*The glamorous part of machine learning is the model; the decisive part is the data and the features. A mediocre model on great features beats a great model on poor ones, almost every time — which is why experienced practitioners spend most of their effort here and almost none picking algorithms. This post is about the unglamorous, high-leverage work of turning raw data into the features a model can actually learn from.*

Post 1 said ML learns a mapping from features to outputs. This post is about the left side of that mapping — because the features you feed a model determine the ceiling on what it can learn. The guiding truth of applied ML: *garbage in, garbage out* is not a cliché here, it's the dominant factor, and feature work is where real-world ML projects succeed or fail.

## Data: quantity, quality, and representativeness

A model learns only what's in its data, so three properties of the data govern what's possible:

- **Quantity.** More data generally means better models, because the algorithm has more examples to find the real pattern rather than noise. Modern deep learning's power comes largely from scale — but for classical ML, often a few thousand good examples suffice, and more *bad* data doesn't help.
- **Quality.** Errors, missing values, mislabeled examples, and inconsistencies all become patterns the model dutifully learns. Cleaning data — handling missing values, fixing errors, removing duplicates — is typically the largest chunk of a real ML project, and skipping it quietly poisons everything downstream.
- **Representativeness.** The data must reflect the real distribution the model will face. A model trained on one population, season, or geography fails on another — this is the root of both poor accuracy and *bias*: if the training data under-represents a group, the model serves that group worse. Representativeness is a correctness *and* a fairness issue.

The practical discipline is to interrogate the data before modeling: where did it come from, what does it cover, what's missing, how is it labeled, and does it match where the model will run. Most model failures trace back to a data problem the team didn't look for.

## Features: the model's vocabulary

A **feature** is an input variable the model uses to make a prediction. **Feature engineering** is the craft of creating, transforming, and selecting features so the signal in the data is in a form the model can exploit. It matters because models don't see the world — they see *features*, so the features define what the model can possibly know:

- **Representation.** Raw data is rarely model-ready. Categories become numbers (one-hot or target encoding), text becomes vectors (embeddings), dates become day-of-week/season, and continuous values are often scaled. A phone number is useless as a number but its area code might be a feature.
- **Derivation.** The most valuable features are often *constructed*: from a timestamp, derive "hour of day" and "is weekend"; from a transaction history, derive "average spend last 30 days" and "time since last purchase." These encode domain knowledge the raw data only implies, and they're frequently what makes a model work.
- **Scaling and normalization.** Many algorithms are sensitive to the *scale* of features (a feature ranging 0–1,000,000 can swamp one ranging 0–1), so normalizing features to comparable ranges is routine and often necessary for the model to learn well.
- **Selection.** More features isn't better — irrelevant or redundant features add noise and overfitting risk (post 5). Selecting the features that carry signal, and dropping the rest, improves both performance and interpretability.

Feature engineering is where domain expertise enters ML: knowing *which* derived quantities matter for fraud, or churn, or pricing is a human insight the model can't discover from scratch (at least in classical ML). This is why the same algorithm, in the hands of someone who understands the domain, produces a far better model.

## The deep-learning caveat — and why features still matter

There's an important twist: deep learning (and modern LLMs) *learn their own features*. A neural network on raw pixels or raw text discovers useful internal representations through its layers, reducing the need for manual feature engineering — this **representation learning** is a big reason deep learning displaced hand-crafted features for perception and language. It's tempting to conclude feature engineering is obsolete.

It isn't, for two reasons. First, for the vast amount of real-world ML on *tabular* data (the spreadsheets that run businesses — fraud, credit, churn, demand), classical models with good feature engineering remain the practical state of the art, and gradient-boosted trees on well-engineered features routinely beat neural nets. Second, even in the deep-learning world, *data* quality and representativeness matter as much as ever — and curation, labeling, and the shaping of training data are feature engineering's spiritual successor (the entire "data-centric AI" movement is this point). The lesson generalizes: the model learns from what you give it, so what you give it — raw data quality and the features derived from it — is the highest-leverage place to spend effort, whatever the model.

The throughline: ML is won on the *input* side. The **data** must be sufficient, clean, and *representative* (representativeness is both an accuracy and a fairness issue — unrepresentative data is the root of bias), and most real projects spend their largest effort on data cleaning. **Features** are the model's vocabulary — it sees features, not the world — so **feature engineering** (representation, derivation of domain-informed quantities, scaling, selection) sets the ceiling on what the model can learn, and is where domain expertise enters. Deep learning *learns* features (representation learning), which is why it won perception and language and why classical feature engineering is less central there — but data quality and curation still dominate, and for tabular business data, good features plus a simple model still win. Spend your effort on the inputs.

## Key takeaways

- A model learns only what's in its data, so data **quantity** (more good data helps), **quality** (errors/missing/mislabeled become learned patterns — cleaning is usually the biggest task), and **representativeness** (must match the deployment distribution — the root of both poor accuracy *and* bias) govern what's possible.
- A **feature** is an input variable; **feature engineering** shapes raw data into model-usable signal via **representation** (categories/text/dates → numbers/vectors), **derivation** (domain-informed quantities like "avg spend last 30 days" — often what makes a model work), **scaling/normalization**, and **selection** (fewer, signal-carrying features beat many noisy ones).
- Features are where **domain expertise** enters classical ML — the same algorithm produces a far better model in the hands of someone who knows which derived quantities matter.
- **Deep learning learns its own features** (representation learning), reducing manual feature engineering for perception/language — but for **tabular** business data, good features + a simple model (e.g. gradient-boosted trees) still beat neural nets.
- Either way, the **input side wins ML**: data quality/representativeness and feature/data curation (the "data-centric AI" point) are the highest-leverage place to spend effort — *garbage in, garbage out* is the dominant factor, not a cliché.

## Further reading

- [Feature engineering — creating and shaping model inputs](https://en.wikipedia.org/wiki/Feature_engineering)
- [Feature (machine learning) — what a feature is](https://en.wikipedia.org/wiki/Feature_(machine_learning))
