# Evaluating Recommenders

*A recommender that scores well offline can flop in production, and a metric that looks like success can quietly harm the product. Evaluating recommenders is genuinely hard: offline metrics only approximate real behavior, the only ground truth is a live A/B test, and the very act of recommending shapes the data you learn from next. This post covers offline metrics, online testing, the gap between them, and the feedback loops that make evaluation a moving target.*

The posts so far built recommenders. This one asks the harder question: *how do you know if a recommender is good?* Evaluation is where recommendation gets subtle, because the thing you can measure cheaply (offline accuracy) is not the thing you actually care about (real user value), and because a deployed recommender changes its own future data. Getting evaluation right is as important as the model.

## Offline evaluation: fast but approximate

**Offline evaluation** measures a model against historical interaction data — hold out some known interactions, predict them, and score the predictions. It's fast, cheap, and repeatable, so it's how you iterate during development. The metrics fall into families:
- **Ranking metrics** (the ones that matter most, since recommendation is ranking): **Precision@K** and **Recall@K** (of the top-K recommended, how many are relevant / of the relevant items, how many made the top-K), **NDCG** (normalized discounted cumulative gain — rewards putting relevant items *higher*, the standard ranking-quality metric), **MAP** (mean average precision), and **MRR** (mean reciprocal rank — how high the first relevant item is). These measure whether you put the right items at the top of a short list, which is what recommendation is.
- **Rating-prediction metrics** — RMSE/MAE, from the Netflix-Prize era of predicting explicit ratings. Less central now that most systems optimize implicit-feedback ranking rather than predicting star ratings, but still seen.
- **Beyond accuracy** — metrics for **diversity** (is the list varied?), **novelty** (are you showing non-obvious items?), **coverage** (what fraction of the catalog ever gets recommended?), and **serendipity**. These matter because a recommender optimized *only* for accuracy tends to be repetitive and popularity-biased (post 8) — accuracy alone is a trap.

The crucial limitation: **offline metrics are only a proxy.** They measure prediction on *past, logged* behavior — behavior that was itself shaped by the *old* recommender. They can't observe how users would react to your *new* recommendations, and they systematically miss things like whether you'd have surfaced good items the old system never showed (so no one could interact with them). Offline evaluation narrows the field of candidate models, but it can't crown a winner.

## Online evaluation: the real ground truth

The only way to truly measure a recommender is to **put it in front of real users** and observe real behavior — **online evaluation via A/B testing**:
- Split traffic: some users get the current recommender (control), some get the new one (treatment).
- Measure **real business/engagement metrics**: click-through rate, engagement, watch/read time, conversions, retention, revenue — the outcomes you actually care about.
- Compare with statistical rigor (significance, enough traffic and time to detect a real effect).

A/B testing is the **ground truth** because it measures what actually happens when real users meet your recommendations — including the effects offline evaluation is blind to. This is why mature recommendation teams run continuous A/B tests and treat online results as the real scoreboard, with offline metrics as a filter that decides *what's worth testing*.

## The offline-online gap

Here's a defining challenge of the field: **offline metrics and online results often disagree.** A model that wins offline can lose online, and vice versa. Why the gap?
- **Offline data is biased by the old recommender.** You only logged interactions with items the old system chose to *show*. Items it never surfaced have no interaction data, so offline evaluation can't credit a new model for surfacing them — even if users would love them. This **exposure bias** is the core reason offline and online diverge.
- **Offline can't measure real-time reaction.** How a user responds to a *genuinely new* set of recommendations (novelty, diversity, presentation) simply isn't in the historical data.
- **Proxy misalignment.** Offline accuracy isn't the business goal; a model can predict logged clicks well yet not improve retention or long-term satisfaction.

The practical consequence: use offline metrics to **narrow** candidates (cheap filtering of obviously-worse models), then use online A/B tests to **decide** (the real verdict). Trusting offline metrics alone is a classic and costly mistake — the numbers can look great while the product gets worse. Never ship on offline metrics alone.

## Feedback loops: evaluation on shifting ground

The deepest subtlety: **a deployed recommender shapes its own future training data.** It decides what users see; users can only interact with what they're shown; those interactions become the next round of training data. This creates **feedback loops** with real consequences:
- **Popularity bias amplification.** If the system recommends popular items, they get more interactions, which makes them look even *more* popular to the next model, which recommends them even more — a rich-get-richer loop that can crowd out the long tail.
- **Filter bubbles / narrowing** (post 8). Recommending similar-to-past items generates similar-to-past interactions, which reinforce the same recommendations, potentially narrowing what a user is ever exposed to.
- **Biased future evaluation.** Because the data is shaped by the current system, *future* offline evaluation is biased toward what the current system already does — the loop contaminates your measurements, not just your training.

Handling feedback loops is part of doing evaluation honestly:
- **Exploration.** Deliberately show some items the model is *uncertain* about (or new items) to gather unbiased data — the explore-vs-exploit trade-off (post 3). Without exploration, the system only ever learns about what it already recommends.
- **Watch beyond-accuracy and long-term metrics.** Track diversity, coverage, novelty, and *long-term* outcomes (retention, satisfaction), not just immediate clicks — because optimizing short-term engagement can degrade the product over time via these loops.
- **Debias where possible.** Techniques exist to correct for exposure/popularity bias in both training and evaluation, acknowledging that logged data is not a neutral sample.

The takeaway: evaluating recommenders means using **offline metrics** (ranking metrics like NDCG/Precision@K/Recall@K plus beyond-accuracy measures) to *narrow* candidates cheaply, then **online A/B testing** on real engagement/business metrics as the *ground truth* — because the two often disagree (the **offline-online gap**, driven by exposure bias and proxy misalignment). And it means reckoning with **feedback loops**: a recommender shapes its own data, amplifying popularity bias and narrowing exposure, which is why exploration, long-term/beyond-accuracy metrics, and debiasing are essential to evaluating honestly. Evaluation is not a one-time score; it's continuous measurement on ground that the system itself keeps shifting.

## Key takeaways

- **Offline evaluation** (against historical data) is fast and repeatable for iteration, scored with **ranking metrics** — **NDCG, Precision@K, Recall@K, MAP, MRR** (recommendation is ranking) — plus **beyond-accuracy** metrics (diversity, novelty, coverage, serendipity), because accuracy-only recommenders turn repetitive and popularity-biased.
- Offline metrics are only a **proxy**: they score prediction on *past* behavior shaped by the *old* recommender, can't observe reactions to genuinely new recommendations, and can't credit surfacing items the old system never showed.
- **Online A/B testing** is the **ground truth** — split traffic, measure real engagement/business outcomes (CTR, watch time, retention, revenue) with statistical rigor — because it captures what actually happens when real users meet the recommendations.
- The **offline-online gap** (models that win offline can lose online) is driven by **exposure bias** (you only logged interactions with shown items) and proxy misalignment — so use offline to **narrow**, online to **decide**; never ship on offline metrics alone.
- **Feedback loops** make evaluation a moving target: a recommender shapes its own future data, **amplifying popularity bias** and **narrowing exposure** (filter bubbles) and biasing future offline evaluation — countered with **exploration** (explore-vs-exploit), **long-term/beyond-accuracy** metrics, and **debiasing**.

## Further reading

- [Evaluation measures (information retrieval) — NDCG, MAP, precision/recall](https://en.wikipedia.org/wiki/Evaluation_measures_(information_retrieval))
- [A/B testing — overview](https://en.wikipedia.org/wiki/A/B_testing)
