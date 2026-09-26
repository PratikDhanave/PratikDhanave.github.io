# The Two-Stage Architecture

*You cannot run your best, most expensive model on millions of items for every request — the latency and cost are impossible. The elegant, near-universal answer is to split recommendation into two stages: a cheap, fast net that narrows millions of items to a few hundred, followed by a precise, heavier model that ranks those few. This retrieve-then-rank structure is the single most important architectural pattern in production recommenders.*

Posts 2–4 covered the *approaches* to recommendation. This post covers the *architecture* that makes them work at scale in real time — the structural insight that shapes almost every production system. It's the answer to the scale problem named in post 1, and it's worth understanding deeply because the same pattern recurs across search, RAG, and ranking everywhere.

## The scale problem, restated

The constraint is stark: a catalog has *millions* of items, and a recommendation request must be served in *milliseconds*. Your best ranking model — a rich neural network scoring a user-item pair with many features — might take a millisecond or more *per item*. Run that on millions of items per request and you're at minutes of compute and enormous cost. It simply doesn't work to score the whole catalog with your best model on every request.

So you face a trade-off: a model good enough to rank precisely is too slow to run on everything; a model fast enough to run on everything isn't precise enough to produce the final order. The two-stage architecture resolves this by **using both** — a cheap model on everything, then an expensive model on the survivors.

## The two stages

**Stage 1: Candidate generation (retrieval).** From the millions of items, cheaply and quickly narrow to a few *hundred* plausible candidates.
- Optimizes for **recall and speed**: don't miss good items, and be fast enough to consider the whole catalog.
- Typically done with **embedding nearest-neighbor search** (post 4): represent the user and items as vectors and use fast approximate-nearest-neighbor (ANN) search to pull the closest items — sublinear, so it scales to millions. Often *several* candidate sources are combined (embedding retrieval, recently popular, from-your-history, etc.) to build a diverse candidate pool.
- The output is a shortlist of a few hundred — a huge reduction that makes the next stage tractable.

**Stage 2: Ranking.** Take those few hundred candidates and score each *precisely* with a heavier model, producing the final ordered list.
- Optimizes for **precision**: get the *order* right at the top, because that's what the user sees.
- Can afford a rich, expensive model (many features: user, item, context, cross-features; a deep network — post 6) because it runs on only a few hundred items, not millions.
- The output is the ranked list, ready for final shaping.

The division of labor is the whole point: **retrieval trades precision for the ability to scan everything cheaply; ranking trades scalability for precision on a shortlist.** Chained, you get both wide coverage and precise ordering — neither achievable alone.

## The pipeline, end to end

Real systems usually add a third step after ranking — **filtering and shaping** — before serving:

```
Sources                Candidate Gen        Ranking          Filtering          Serving
┌──────────────┐       ┌─────────────┐      ┌──────────┐     ┌──────────────┐   ┌────────────┐
│ Item Catalog │──────▶│             │      │          │     │              │   │            │
│ (millions)   │ pool  │ Candidate   │─────▶│ Ranking  │────▶│ Filtering +  │──▶│ Top-N      │
├──────────────┤       │ Gen         │short │ Model    │rank │ Rules        │top│ Results    │
│ User History │──────▶│ (M→hundreds)│ list │ (score   │list │ (dedupe,     │-N │ (to user)  │
│ interactions │signals│             │      │  each)   │     │ diversity,   │   │            │
└──────────────┘       └─────────────┘      └──────────┘     │ policy)      │   └────────────┘
                       retrieval:            precise:         └──────────────┘   recommendations
                       cheap, high-recall    order the few    shape before serving
```

> **▸ [Open the interactive diagram](/blog/handbook-diagrams/recommender-pipeline.html)** — pan, zoom, focus each stage, and switch views (retrieve vs. rank-and-shape); light/dark, self-contained.

**Filtering and business rules.** After ranking, before serving, systems apply:
- **Deduplication** — don't show near-duplicate items.
- **Diversity** — avoid a monotonous list of near-identical items (all the same genre/creator); deliberately mix it up so the list is useful and not a filter bubble (post 8).
- **Already-seen / freshness removal** — drop items the user just saw or already consumed.
- **Business and policy rules** — promotions, content policy, regional availability, and other constraints the pure model score doesn't capture.

This shaping step matters: the raw ranked list is rarely the right thing to serve directly. Real products need diversity, freshness, and policy compliance layered on top of relevance.

## Why this pattern is everywhere

The retrieve-then-rank split isn't unique to recommendation — it's a **general answer to the "too many candidates for the expensive model" problem**, and you've seen it elsewhere:
- **Search** — retrieve candidate documents (cheap inverted-index/vector lookup), then rerank the top ones with an expensive model.
- **RAG** — retrieve candidate chunks by embedding similarity, then a reranker (or the LLM itself) precisely orders/uses the top few.
- **Ads** — candidate ad selection, then precise ranking/auction.

They all face the identical constraint: you can't apply your best, most expensive model to millions of candidates per request, so you filter cheaply first (recall-oriented retrieval) and rank the survivors well (precision-oriented ranking). Recognizing this pattern lets you reason about recommender architecture the same way you reason about search and RAG — they're the same shape.

## Why two stages and not one (or three)

- **Not one** — a single model can't be both cheap-enough-for-millions and precise-enough-for-the-final-order; the objectives conflict.
- **Sometimes more** — very large systems add stages (e.g. a lightweight "pre-ranking" between retrieval and full ranking, or a final re-ranking for diversity), but the *principle* is the same: progressively narrow the set while progressively increasing per-item cost and precision. Two stages is the minimal, canonical form; extra stages are refinements of the same idea.

The takeaway: the two-stage architecture — **candidate generation** (millions → hundreds, cheap, high-recall, usually embedding ANN search) then **ranking** (hundreds → ordered, precise, heavy model), followed by **filtering/shaping** (dedupe, diversity, freshness, policy) — is how production recommenders serve relevant results over huge catalogs in milliseconds. It resolves the scale-vs-precision conflict by using a cheap model on everything and an expensive model on the survivors, and it's the same retrieve-then-rank pattern that powers search, RAG, and ads. This is the backbone every real recommender is built on.

## Key takeaways

- You **can't run your best model on millions of items per request** (latency/cost), and a model fast enough to scan everything isn't precise enough for the final order — so production recommenders split into **two stages** that use both.
- **Stage 1 — candidate generation/retrieval**: millions → a few hundred, optimizing **recall and speed**, typically via **embedding nearest-neighbor (ANN) search** (post 4), often combining several candidate sources into a diverse pool.
- **Stage 2 — ranking**: the few hundred → an ordered list, optimizing **precision**, affording a **rich, expensive model** (many features, deep network — post 6) because it only scores a shortlist.
- A **filtering/shaping** step usually follows ranking before serving: **deduplication, diversity, already-seen/freshness removal, and business/policy rules** — because the raw ranked list is rarely the right thing to serve.
- The **retrieve-then-rank** pattern is general — the same shape powers **search, RAG, and ads** — because they all face the identical "too many candidates for the expensive model" constraint: filter cheaply first, rank the survivors well.

## Further reading

- [Google — Recommendation Systems: retrieval, scoring, re-ranking](https://developers.google.com/machine-learning/recommendation)
- [Nearest neighbor search (ANN) — overview](https://en.wikipedia.org/wiki/Nearest_neighbor_search)
