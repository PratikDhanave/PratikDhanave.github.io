# Evaluating Search — How Do You Know Your Results Are Good?

*You changed the ranking function and the results look different — but are they better? Search quality feels subjective, yet the entire field rests on measuring it rigorously, because you cannot improve what you cannot measure. Evaluating search means quantifying relevance with metrics that respect what users actually care about: not just whether the right documents appear, but whether they appear near the top. This post is about measuring relevance honestly, offline and online.*

Posts 2–4 built matching and ranking; this post asks whether the ranking is any good. Evaluation is what turns search tuning from guesswork into engineering — and the metrics here (precision, recall, NDCG) are the same ones used to evaluate RAG retrieval, so this is directly load-bearing for modern AI systems too.

## Relevance and the two basic measures

Evaluation starts with **relevance judgments**: for a set of test queries, humans (or usage signals) label which documents are relevant. With those labels, the two foundational metrics (familiar from the ML series' classification metrics) apply:

- **Precision** — of the results you returned, what fraction were relevant? High precision = few irrelevant results cluttering the list.
- **Recall** — of all the relevant documents that exist, what fraction did you return? High recall = you didn't miss the good ones.

They trade off, as always: return everything and recall is perfect but precision terrible; return only your single most confident result and precision may be perfect but recall tiny. For search, though, these raw measures have a critical blind spot that forces something better: **they ignore order.** Precision and recall treat the result set as a bag — but search is a *ranked list*, and a relevant document at position 1 is worth vastly more than the same document at position 50 that nobody scrolls to. Measuring search well means measuring *rank-awareness*, which basic precision/recall don't.

## Rank-aware metrics: position matters

Real search metrics account for *where* relevant results appear, because users read top-down and rarely go past the first few results:

- **Precision@k** — precision among just the top *k* results (e.g. precision@10). Simple and practical: it measures "of the first page, how many were good?", which is close to what users experience. Its limit is that it still ignores order *within* the top k and treats all relevant docs as equally relevant.
- **Mean Reciprocal Rank (MRR)** — for queries with one right answer, how high up is it? The score is 1/(rank of the first relevant result), so a right answer at position 1 scores 1.0, at position 2 scores 0.5, and so on. MRR rewards getting *the* answer to the top — ideal for known-item search and question-answering.
- **NDCG (Normalized Discounted Cumulative Gain)** — the gold standard for ranked relevance. It handles two things the others don't: **graded relevance** (results can be "perfect," "good," or "marginal," not just relevant/not) and **positional discounting** (a relevant result's contribution is *discounted* the lower it appears, matching how attention falls off down the list). NDCG then normalizes against the ideal ranking so scores are comparable across queries. It's the metric most used to compare ranking systems because it best captures "the right things, in the right order, graded by how right."

The unifying idea: good search metrics reward putting *more relevant* results *higher*, because that's what users actually value. Choosing the metric is choosing what you optimize for — MRR if there's one target answer, NDCG if quality and order across many results matter, precision@k for a simple top-of-page proxy.

## Offline test sets vs online reality

Having metrics, you need something to compute them *on*, and there are two complementary regimes — exactly mirroring the offline/online evaluation split from the LLMOps and ML series:

- **Offline evaluation** uses a fixed **test collection**: a set of queries with human relevance judgments, against which you score any ranking change repeatably. This is how you iterate safely — change BM25's parameters or add a feature, re-score, and see if NDCG went up *before* shipping. Its limits are that relevance judgments are expensive to produce, can go stale, and can never cover the full, shifting diversity of real queries (the classic test collections drove decades of IR research precisely because good judgments are so valuable and so costly).
- **Online evaluation** measures real user behavior on live traffic, because the ultimate judge of search quality is whether *users* found what they wanted. Signals include **click-through rate**, **dwell time** (did they stay on the result or bounce back and try again?), **reformulation rate** (did they have to rephrase — a sign of failure?), and task success. The gold-standard method is **A/B testing**: serve the new ranking to some users, the old to others, and compare behavior — the same approach as the ML/LLMOps series, because it measures the real objective, not a proxy.

The disciplined practice combines both: offline metrics for fast, safe, repeatable iteration, and online tests as the ground-truth check before and after shipping — with the crucial caution that offline relevance judgments are a *proxy*, and a change that improves NDCG on your test set can still hurt real users (Goodhart's law again). And because these exact metrics (precision, recall, NDCG, MRR) are what's used to evaluate **RAG retrieval** quality, learning to measure search is learning to measure the retrieval half of modern AI systems — a bad retriever caps a RAG system's quality no matter how good the LLM, and these metrics are how you catch it.

The throughline: you can't improve search you can't measure, so evaluation quantifies **relevance** using human judgments. **Precision** (of returned, how many relevant) and **recall** (of relevant, how many returned) are the base measures but **ignore order** — fatal for search, a ranked list where position 1 ≫ position 50. So use **rank-aware** metrics: **precision@k** (top-page proxy), **MRR** (how high is the one right answer), and especially **NDCG** (graded relevance + positional discounting, normalized — the gold standard), all rewarding *more relevant results, higher*. Measure them **offline** (a fixed test collection for fast, safe, repeatable iteration — but judgments are costly, stale, and a proxy) *and* **online** (real behavior — CTR, dwell, reformulation — via **A/B testing**, the ground truth). These are the same metrics that evaluate **RAG retrieval**, so measuring search is measuring modern AI's retrieval half.

## Key takeaways

- Search quality must be **measured**, starting from human **relevance judgments**; **precision** (returned→relevant fraction) and **recall** (relevant→returned fraction) are the base metrics but **ignore rank order** — a fatal blind spot for a ranked list where top positions matter far more.
- **Rank-aware metrics** fix this: **precision@k** (quality of the top k — simple top-page proxy), **MRR** (1/rank of the first relevant result — for known-item/QA search), and **NDCG** (the gold standard — handles **graded relevance** *and* **positional discounting**, normalized for cross-query comparison).
- Good metrics all reward **more relevant results, higher** — and choosing the metric chooses what you optimize (MRR for one target answer, NDCG for graded quality + order, precision@k for a simple proxy).
- Evaluate **offline** (a fixed **test collection** with judgments — fast, safe, repeatable iteration; but judgments are expensive, go stale, and are a *proxy*) and **online** (real user signals — **CTR, dwell time, reformulation rate** — via **A/B testing**, the ground-truth measure of the real objective); beware Goodhart (better offline NDCG can still hurt users).
- These exact metrics (precision, recall, NDCG, MRR) evaluate **RAG retrieval** too — a weak retriever caps a RAG system regardless of the LLM — so measuring search *is* measuring modern AI's retrieval half.

## Further reading

- [Evaluation measures (information retrieval) — precision, recall, and beyond](https://en.wikipedia.org/wiki/Evaluation_measures_(information_retrieval))
- [Discounted cumulative gain — NDCG and rank-aware relevance](https://en.wikipedia.org/wiki/Discounted_cumulative_gain)
