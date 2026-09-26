# The Recommendation Problem

*Every time a streaming service suggests what to watch, a shop shows "you might also like," or a feed decides what you see next, a recommender system is at work. Behind that simple experience is one of the most economically important and technically rich problems in applied machine learning: from a catalog of millions, pick the handful a specific person will want, right now. This series builds recommender systems from the ground up.*

Recommender systems are quietly among the highest-impact ML systems in the world — they drive a large share of engagement and revenue at the companies that run them. Yet the core problem is easy to state and hard to solve: match people to items at massive scale, personally, in milliseconds. This opening post frames the problem, the main approaches, and the two-stage architecture that structures almost every real recommender — the map for the series.

## The problem, stated plainly

A recommender system answers: **given a user (and context), which items from a large catalog should we show them?** The catalog might be millions of products, videos, songs, or articles; the user has tastes you must infer; and you have to pick a short, ordered list they'll actually want — fast enough to serve in real time.

What makes it genuinely hard:
- **Scale.** Catalogs are huge (millions of items) and users are many (millions). You can't score every item for every user on every request naively — that's the constraint that shapes the whole architecture.
- **Personalization.** The "best" items differ per person; there's no single right answer, only right-for-this-user. You must infer individual taste from limited signals.
- **Sparse signals.** Any given user has interacted with a tiny fraction of the catalog, so you're predicting preferences from very incomplete data.
- **Cold start.** New users (no history) and new items (no interactions) have little signal, yet still need good recommendations.
- **Real-time.** Recommendations must be served in milliseconds, so heavy computation has to be structured carefully.

The economic stakes make solving this worthwhile: better recommendations directly drive engagement, retention, and revenue, which is why recommender systems get enormous investment and are central infrastructure at consumer-scale companies.

## The core signal: interactions

The raw material of recommendation is **user-item interactions** — the record of who engaged with what. These come in two flavors:
- **Explicit feedback** — ratings, likes, thumbs up/down. Clear signal, but sparse (most people rarely rate).
- **Implicit feedback** — clicks, views, watch time, purchases, dwell. Abundant but noisy (a click isn't a guarantee of liking; a non-click isn't a guarantee of disliking). Most modern systems lean heavily on implicit feedback because there's so much more of it.

From this interaction data, a recommender learns patterns — what tends to go with what, who resembles whom — and turns them into predictions of what a user will want. The central bet of recommendation is that **past behavior (yours and others') predicts future preference**, and the whole field is about extracting that signal well from sparse, noisy interaction data.

## The main approaches

There are a few foundational strategies, each a post in this series:
- **Collaborative filtering** (post 2) — recommend based on the behavior of *similar users* (or *similar items*): "people who liked what you liked also liked X." It uses only the interaction matrix, needs no knowledge of the items themselves, and is the backbone of recommendation.
- **Content-based filtering** (post 3) — recommend items *similar in content* to what a user already liked (same genre, similar attributes). Uses item features, and helps with the cold-start problem collaborative filtering struggles with.
- **Matrix factorization and embeddings** (post 4) — learn compact *latent* representations of users and items so their compatibility is a simple computation; the technique that powered the modern era (famously, the Netflix Prize).
- **Deep learning approaches** (post 6) — neural models (two-tower retrieval, neural ranking) that incorporate rich features and power today's large-scale systems.

Real systems combine these (a **hybrid**), because each has strengths and weaknesses — collaborative filtering is powerful but cold-starts poorly; content-based handles new items but can be narrow. The art is blending them.

## The two-stage architecture

Here's the structural insight that shapes almost every production recommender, and the reason the scale problem is tractable: **you don't score the whole catalog for every request. You do it in two stages.**

1. **Candidate generation (retrieval).** From the *millions* of items, cheaply and quickly narrow to a few *hundred* plausible candidates. This stage optimizes for *recall* (don't miss good items) and *speed* — it must be fast because it considers the whole catalog.
2. **Ranking.** Take those few hundred candidates and score them *precisely* with a heavier model, producing the ordered final list. This stage optimizes for *precision* — it can afford a more expensive model because it only runs on a shortlist.

This retrieve-then-rank split (detailed in post 5, with an interactive diagram) is what makes real-time recommendation over huge catalogs possible: a cheap wide net followed by an expensive precise ranking. It mirrors patterns you've seen elsewhere (retrieval then reranking in RAG, candidate-then-rank in search) — because they all face the same scale problem: you can't apply your best, most expensive model to millions of items per request, so you filter cheaply first, then rank the survivors well.

## What this series covers

The series builds up the field:
- The foundational approaches: **collaborative filtering** (2), **content-based + cold start** (3), **matrix factorization + embeddings** (4).
- The **two-stage architecture** (5) that structures production systems.
- **Deep learning recommenders** (6) — two-tower retrieval and neural ranking.
- **Evaluation** (7) — offline metrics, online A/B testing, the offline-online gap, and feedback loops.
- **Production recommenders** (8) — serving, freshness, cold start, filter bubbles, and building one.

The mental model to carry: recommendation is the problem of matching people to items from a huge catalog, personally and in real time, learned from sparse interaction data — solved by a family of approaches (collaborative, content-based, matrix factorization, deep learning) arranged in a two-stage retrieve-then-rank architecture. Everything ahead fills in that picture.

## Key takeaways

- A recommender system answers **"given a user and context, which items from a large catalog should we show?"** — hard because of scale (millions of items/users), personalization (no single right answer), sparse signals, cold start, and real-time latency; and economically pivotal (engagement, retention, revenue).
- The raw material is **user-item interactions** — **explicit** feedback (ratings/likes: clear but sparse) and **implicit** feedback (clicks/views/purchases: abundant but noisy, and what modern systems lean on) — resting on the bet that **past behavior predicts future preference**.
- The main approaches: **collaborative filtering** (similar users/items, interaction-only), **content-based** (item-feature similarity, helps cold start), **matrix factorization/embeddings** (latent factors, the Netflix-Prize era), and **deep learning** (two-tower, neural ranking) — real systems **hybridize** them.
- The structural key is the **two-stage architecture**: **candidate generation/retrieval** (millions → hundreds, cheap + high-recall + fast) then **ranking** (hundreds → ordered, precise + heavier) — because you can't apply your best model to millions of items per request.
- Recommendation = matching people to items from a huge catalog, personally and in real time, from sparse interaction data, via a family of approaches arranged retrieve-then-rank.

## Further reading

- [Recommender system — overview](https://en.wikipedia.org/wiki/Recommender_system)
- [Google — Recommendation Systems (ML crash course)](https://developers.google.com/machine-learning/recommendation)
