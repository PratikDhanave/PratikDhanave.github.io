# Collaborative Filtering

*The most powerful idea in recommendation is also the simplest to state: you can recommend things to someone based purely on the behavior of people like them, without knowing anything about the items themselves. Collaborative filtering turns "people who liked what you liked also liked X" into an algorithm, and it's the backbone of the whole field. This post covers how it works and why it's so effective — and where it breaks.*

The previous post named collaborative filtering as recommendation's foundational approach. This post goes deep. Its magic is that it needs *no* understanding of the items — no genres, no descriptions, just the interaction matrix of who engaged with what — and yet it produces strikingly good, often serendipitous recommendations. Understanding it is understanding the core of recommender systems.

## The core idea

**Collaborative filtering (CF)** recommends items to a user based on the preferences of *other* users, discovered from the pattern of interactions. The intuition is everyday: if you and I have liked many of the same things, then something *you* liked that I haven't seen yet is probably something I'll like too. It "collaborates" across users' behavior to filter the catalog.

The remarkable part: **CF uses only the interaction data** — the matrix of users × items with the interactions filled in. It doesn't need to know what the items *are* (no metadata, no content analysis). It finds patterns purely in *who interacted with what*. This is why CF is so widely applicable (it works for any domain where you have interactions, without domain-specific feature engineering) and why it can surface *serendipitous* recommendations — connections between items that share no obvious content similarity but that similar people happen to enjoy together. Content-based methods (next post) could never find that a jazz album and a specific novel go together; CF can, if the people who like one tend to like the other.

## Two flavors: user-based and item-based

CF comes in two symmetric forms, differing in what you compute similarity between:

- **User-based CF.** Find users *similar to you* (who interacted with similar items), then recommend items *they* liked that you haven't seen. "People like you liked X." The steps: compute similarity between users based on their interaction patterns, find your nearest neighbors, and aggregate what they liked.
- **Item-based CF.** Find items *similar to ones you liked* — where "similar" means *interacted-with by the same people*, not similar in content. "Because you liked A (and people who like A also like B), here's B." The steps: compute similarity between items based on which users interacted with both, then recommend items similar to a user's history.

**Item-based CF is often preferred in practice** for a practical reason: item-item similarities are more *stable* than user-user similarities (an item's audience changes slowly; a user's tastes and neighbors shift faster) and there are usually fewer items than users, so item-item similarities can be *precomputed* and cached, making serving fast. The famous "customers who bought this also bought that" is item-based CF. Both flavors express the same collaborative principle; they just pivot on users vs. items.

## How similarity is computed

At CF's heart is a **similarity measure** between users (or items) based on their interaction vectors. A user is represented by their row in the interaction matrix (which items they engaged with, and how much); similarity is how alike two such vectors are. Common measures:
- **Cosine similarity** — the angle between two interaction vectors (do they point the same way?), widely used.
- **Pearson correlation** — like cosine but accounting for differing rating scales (some users rate everything high).
- **Jaccard** — for pure binary interactions (overlap of sets of items).

Once you can measure similarity, recommendation is nearest-neighbor: find the most similar users/items and aggregate. This is why CF is sometimes called **memory-based** or **neighborhood-based** — it works directly from the interaction data by finding neighbors, without learning a compact model (contrast with matrix factorization, post 4, which *learns* latent factors). Neighborhood CF is intuitive and interpretable ("recommended because people similar to you liked it"), which is part of its enduring appeal.

## Why CF is so effective — and its limits

CF's strengths explain its dominance:
- **No item knowledge needed** — works from interactions alone, in any domain, with no feature engineering.
- **Serendipity** — finds non-obvious cross-category connections that content methods miss.
- **Gets better with scale** — more users and interactions mean richer patterns and better recommendations, a virtuous cycle for large platforms.

But CF has two well-known weaknesses, both rooted in its reliance on interaction data:
- **The cold-start problem** (next post) — CF is helpless for *new users* (no interactions, so no neighbors) and *new items* (no one has interacted with them, so they can't be recommended). This is CF's Achilles' heel, and the main reason content-based and hybrid methods exist.
- **Sparsity.** The interaction matrix is extremely sparse (any user has touched a tiny fraction of the catalog), so finding reliable overlaps between users can be hard, especially for less-active users or niche items. Sparsity weakens neighborhood similarity and motivates the latent-factor methods (post 4) that handle it better.

Additional practical issues include the **popularity bias** (CF tends to over-recommend already-popular items, since they have the most interactions) and scalability of naive neighborhood computation over huge matrices — problems that matrix factorization and modern methods address.

The takeaway: collaborative filtering is recommendation's foundational idea — recommend based on the behavior of similar users/items, using *only* the interaction matrix, with no item knowledge — coming in user-based and (usually-preferred, more stable) item-based flavors, powered by similarity measures over interaction vectors. It's remarkably effective and serendipitous, but it stumbles on cold start and sparsity, which is exactly what the next posts (content-based methods, then matrix factorization) address. CF is the backbone; the rest of the field is largely about shoring up its weaknesses and scaling it.

## Key takeaways

- **Collaborative filtering** recommends based on the behavior of *similar users/items* ("people who liked what you liked also liked X"), using **only the interaction matrix** — no item metadata or content — which makes it domain-agnostic and able to surface **serendipitous** cross-category connections content methods can't.
- Two symmetric flavors: **user-based** (find similar users, recommend what they liked) and **item-based** (find items co-liked by the same people); **item-based is often preferred** because item-item similarities are more stable and precomputable ("customers who bought this also bought that").
- CF is **neighborhood/memory-based**: represent users/items as interaction vectors, compute **similarity** (cosine, Pearson, Jaccard), find nearest neighbors, aggregate — intuitive and interpretable, working directly from data without learning a compact model.
- Strengths: no item knowledge needed, serendipity, and it improves with scale (more interactions → better patterns, a virtuous cycle for large platforms).
- Weaknesses rooted in its data reliance: the **cold-start problem** (helpless for new users/items — its Achilles' heel), **sparsity** (the matrix is mostly empty, weakening neighbor overlap), and **popularity bias** — which content-based (next) and matrix-factorization (post 4) methods address.

## Further reading

- [Collaborative filtering — overview](https://en.wikipedia.org/wiki/Collaborative_filtering)
- [Google — Recommendation Systems (collaborative filtering)](https://developers.google.com/machine-learning/recommendation)
