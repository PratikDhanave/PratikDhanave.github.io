# Learning to Rank — When Machine Learning Takes Over Relevance

*BM25 ranks by a fixed formula, but real search engines have hundreds of relevance signals — freshness, popularity, personalization, link quality, and dozens of text features — and no human can hand-tune how to weigh them all. Learning to rank hands that job to machine learning: train a model on examples of good and bad rankings, and let it discover the optimal combination of signals. This post is where search ranking becomes a machine-learning problem, and the bridge to the neural retrieval behind modern AI.*

Posts 4–5 covered formula-based ranking (BM25) and how to measure it. This post is the next evolution: using ML (from the [Machine Learning from First Principles](/blog/series/machine-learning-from-first-principles/) series) to *learn* the ranking function from data. It's how large-scale search actually ranks today, and it leads directly into the neural and embedding-based retrieval this blog covers elsewhere.

## Why hand-tuned ranking hits a wall

BM25 (post 4) is one strong signal, but production relevance depends on many signals at once:
- **Text relevance** — BM25 scores on the title, the body, the headings (each a separate signal).
- **Document quality** — popularity, link authority, spam signals, freshness.
- **User/context signals** — location, device, personalization, time, prior behavior.
- **Engagement** — historical click-through and dwell time for this query-document pair.

A modern ranker might combine *hundreds* of such features. The problem: how do you weigh them? Is a fresh, popular, weak-text-match document better or worse than a stale, obscure, strong-text-match one? Hand-tuning the weights for hundreds of features is hopeless — the combinations are too many and the right trade-offs too subtle for human intuition. This is exactly the situation machine learning was made for (ML series, post 1): when the rules are too complex to write, *learn them from examples.*

## Learning to rank: the ML formulation

**Learning to rank (LTR)** treats ranking as a supervised machine-learning problem. The ingredients map directly onto the ML series:

- **Features** — for each query-document pair, compute a feature vector: BM25 scores on various fields, document quality signals, engagement signals, query features, etc. (post 2 of the ML series — feature engineering, here for ranking). These features are the model's view of "how might this document relate to this query?"
- **Training labels** — the relevance judgments from post 5 (human-rated or derived from clicks): which documents are relevant to which queries, and how relevant.
- **Model** — learn a function from the feature vector to a relevance score, trained so that ordering documents by the learned score reproduces the known-good rankings.

The subtlety that makes LTR its own topic is that *the objective is a ranking, not a single prediction*, and there are three ways to frame it:
- **Pointwise** — predict an absolute relevance score per document (plain regression/classification), then sort. Simple, but it ignores that ranking is about *relative* order.
- **Pairwise** — learn from *pairs*: for two documents, predict which should rank higher. This directly optimizes relative order and is a very effective, widely-used framing (the well-known LambdaMART family is pairwise/listwise).
- **Listwise** — optimize the quality of the *whole ranked list* directly against a metric like NDCG (post 5). The most principled (it optimizes what you actually measure) and often the best-performing, though harder to train.

In practice, **gradient-boosted trees** (ML series, post 4) have long dominated learning to rank on the kind of tabular feature vectors described above — the same reason trees win on tabular data generally applies to ranking features. LTR is, for most of the industry, "compute good ranking features, then train a gradient-boosted ranker on relevance judgments."

## From learned ranking to neural retrieval

Learning to rank is the bridge from classical IR to the modern neural and embedding-based retrieval this blog covers, and seeing the progression clarifies the whole landscape:

- **Classical LTR** (above) learns to *combine hand-engineered features* (including BM25 as one feature). It's still the workhorse for large-scale ranking because it's effective, efficient, and interpretable, and it cleanly incorporates BM25 and business signals.
- **Neural ranking** goes further, using neural networks to *learn relevance from the text itself* rather than from hand-engineered features — letting the model read query and document and judge relevance, capturing meaning that term-based features miss (the vocabulary gap, post 1).
- **Embedding-based (dense) retrieval** — the vector-search this blog covers — represents queries and documents as learned **embeddings** (vectors capturing meaning) so relevance becomes vector similarity. This is retrieval by *meaning*, the semantic approach that overcomes BM25's lexical ceiling (post 4), and it's the engine of modern RAG.
- **Cross-encoders / rerankers** — a powerful modern pattern: use fast retrieval (BM25 or embeddings) to get candidates, then a heavier neural model to *rerank* the top candidates by reading each query-document pair closely. This mirrors the two-stage retrieve-then-rank architecture seen across search, recommendations, and RAG.

The throughline across the whole progression is the same idea escalating: ranking is too complex to hand-specify, so *learn* it — first learning to weigh features (LTR), then learning relevance from text (neural), then learning representations of meaning (embeddings). Each step hands more of the relevance judgment to learned models. And crucially, these don't fully replace each other: production systems layer them — BM25 for cheap candidate generation, learned ranking or neural rerankers for precision — which is exactly the hybrid, multi-stage architecture of modern retrieval and RAG. Learning to rank is where search stopped being a formula and became a machine-learning system, and it's the direct conceptual ancestor of the retrieval stack behind today's AI.

The throughline: production relevance depends on **hundreds of signals** (text, quality, freshness, personalization, engagement) that are hopeless to hand-weight — so **learning to rank** makes ranking a **supervised ML problem**: features per query-document pair, relevance judgments (post 5) as labels, and a model trained so its scores reproduce good rankings. Because the objective is *order*, it's framed **pointwise**, **pairwise** (optimize relative order — the effective default), or **listwise** (optimize the whole list against NDCG — most principled), typically with **gradient-boosted trees** on tabular ranking features. LTR is the **bridge to neural retrieval**: from learning to *combine features* → **neural ranking** (learn relevance from text) → **embedding/dense retrieval** (relevance as vector similarity — modern RAG's engine) → **cross-encoder rerankers** — the same idea escalating, layered in multi-stage hybrid systems rather than replacing each other.

## Key takeaways

- Production relevance combines **hundreds of signals** (field-level BM25, document quality/popularity/freshness, personalization, engagement) that are **impossible to hand-weight** — the classic case for learning rules from examples (ML series).
- **Learning to rank (LTR)** makes ranking a **supervised ML problem**: per-query-document **feature vectors**, **relevance judgments** (post 5) as labels, and a **model** trained so ordering by its score reproduces good rankings.
- Because the target is *order*, LTR is framed **pointwise** (predict absolute scores, then sort — ignores relativity), **pairwise** (which of two ranks higher — effective, widely used, e.g. LambdaMART), or **listwise** (optimize the whole list against a metric like NDCG — most principled, often best); **gradient-boosted trees** dominate on tabular ranking features.
- LTR is the **bridge to neural retrieval**: learning to *combine features* (LTR) → **neural ranking** (learn relevance from text, capturing meaning) → **embedding/dense retrieval** (relevance = vector similarity — overcomes BM25's lexical ceiling, powers RAG) → **cross-encoder rerankers** (heavy model reranks cheap-retrieval candidates).
- These **layer, not replace**: production uses multi-stage pipelines (BM25 candidate generation → learned/neural reranking) — the hybrid, retrieve-then-rank architecture of modern search, recommendations, and RAG; LTR is where search became a machine-learning system.

## Further reading

- [Learning to rank — ranking as a supervised ML problem](https://en.wikipedia.org/wiki/Learning_to_rank)
- [Information retrieval — the field learning-to-rank advances](https://en.wikipedia.org/wiki/Information_retrieval)
