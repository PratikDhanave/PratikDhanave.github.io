# Deep Learning Recommenders

*Modern large-scale recommenders — the ones running at the biggest consumer platforms — are built on neural networks. Deep learning didn't replace the core ideas (embeddings, two stages) so much as supercharge them: neural models learn richer embeddings, ingest far more features, and capture complex non-linear patterns that dot products can't. This post covers the two workhorses — two-tower retrieval and neural ranking — that power today's systems.*

Matrix factorization (post 4) gave us embeddings and the dot product; the two-stage architecture (post 5) gave us retrieve-then-rank. Deep learning fills in *how* each stage is built at the frontier: a neural retrieval model for stage 1, a neural ranking model for stage 2. Understanding these two shows how the classical ideas scale to the modern era.

## Why deep learning for recommendation

Classical matrix factorization is powerful but limited: it learns embeddings purely from the interaction matrix, and it models compatibility as a simple dot product (a *linear* interaction between factors). Real preference is richer than that. Deep learning helps in three ways:
- **Richer features.** Neural models can ingest far more than interactions: user attributes, item content (text, images), context (time, device, location), and cross-features. Matrix factorization sees only who-interacted-with-what; neural models see the whole picture, which directly helps cold start (post 3 — a new item with content features is representable).
- **Non-linear patterns.** A dot product is linear; neural networks learn complex, non-linear interactions between features ("this user likes long-form content, but only on weekends, and only in this genre"). That expressiveness captures preference structure simple models miss.
- **Learned embeddings from anything.** Instead of factorizing a fixed matrix, neural models *learn* embeddings from rich inputs — turning any feature into a vector in the shared space, and letting the same embedding machinery power both retrieval and ranking.

The result isn't a new paradigm — it's the *same* embeddings-and-two-stages architecture, with neural networks as the engine that makes each part richer and more powerful.

## The two-tower model (neural retrieval)

The dominant architecture for **candidate generation** (stage 1) at scale is the **two-tower model**. It's the neural evolution of matrix factorization, purpose-built for fast retrieval:
- **Two separate networks (towers).** One tower encodes the **user** (from user features, history, context) into a user embedding; the other encodes the **item** (from item features/content) into an item embedding. Both towers output vectors in the *same* shared embedding space.
- **Compatibility = similarity of the two embeddings** (dot product / cosine) — exactly the matrix-factorization idea, but now each embedding is produced by a *deep network* over rich features rather than looked up from a factorized matrix.

The architectural genius of the two towers is why it dominates retrieval: because the user and item are encoded *separately*, you can **precompute all item embeddings offline** and index them for fast approximate-nearest-neighbor (ANN) search. At request time you only compute the *user* embedding once, then do an ANN lookup to retrieve the nearest items from millions — sublinear and fast. This is exactly what stage-1 retrieval needs (post 5): the two-tower structure makes embedding retrieval over huge catalogs practical. (Contrast with a model that jointly encodes a user-item *pair* — more expressive, but you'd have to run it for every item, which is impossible at retrieval scale. That kind of model belongs in ranking, next.)

## Neural ranking (stage 2)

For **ranking** (stage 2), where you only score a few hundred candidates, you can afford a much richer model — and deep learning shines here because expressiveness matters more than speed:
- **Rich feature interactions.** Ranking models take the user, the candidate item, and context, and predict a precise score (e.g. probability of click/engagement/conversion). Because they score a *pair* (user + specific item together), they can model **cross-features** — interactions between user and item features — that the separately-encoded two-tower can't. This is where the precise ordering comes from.
- **Deep architectures.** Modern ranking models use deep networks, sometimes combining a "wide" memorization component with a "deep" generalization component (the classic wide-and-deep idea), or attention/sequence models over the user's interaction history to capture evolving intent. Sequence models (transformers over what a user recently engaged with) are increasingly central — treating a user's history as a sequence and predicting what comes next.
- **Multi-objective.** Real ranking often optimizes *multiple* objectives at once (click, watch time, satisfaction, not-just-engagement) — neural models handle this by predicting several targets and combining them, which is how platforms balance engagement against quality.

The key contrast with retrieval: ranking can be expensive-per-item and jointly model the user-item pair (maximizing precision on a shortlist), while retrieval must be cheap-per-item and encode user/item separately (maximizing recall/speed over millions). Two stages, two model shapes, matched to their jobs (post 5).

## The modern stack, assembled

Putting it together, a modern deep-learning recommender is:
1. **Two-tower retrieval** — user tower + item tower → embeddings → ANN search retrieves a few hundred candidates from millions (stage 1).
2. **Neural ranking** — a rich deep model scores each candidate precisely, modeling cross-features and often sequences and multiple objectives (stage 2).
3. **Filtering/shaping** — diversity, freshness, policy (post 5).

Every piece is the classical architecture, upgraded: embeddings (post 4) learned by neural towers; two stages (post 5) each powered by a neural model suited to its job. Deep learning is how the field's core ideas run at the scale and quality of today's largest platforms — not a replacement for them, but their most powerful realization.

A caveat worth keeping: deep learning adds real complexity and cost (training pipelines, feature infrastructure, serving latency, harder debugging). Not every recommender needs it — for many products, matrix factorization or even well-tuned neighborhood CF plus good candidate sources is enough. Reach for deep learning when scale, rich features, and the value of small quality gains justify the engineering — which at consumer-platform scale, they usually do.

The takeaway: deep-learning recommenders keep the embeddings-and-two-stages architecture but power each stage with neural networks — **two-tower models** for retrieval (separate user/item towers → shared embeddings → precomputed item index + fast ANN search, the neural evolution of matrix factorization) and **rich neural ranking models** for scoring the shortlist (cross-features, sequence models, multi-objective, precise ordering). They ingest far more features (helping cold start), capture non-linear patterns dot products can't, and are how the field's core ideas scale to the largest platforms — at the cost of real complexity that not every system needs.

## Key takeaways

- Deep learning **supercharges the classical architecture** (embeddings + two stages) rather than replacing it: it ingests **richer features** (content, context, cross-features — helping cold start), captures **non-linear patterns** a dot product can't, and learns embeddings from any input.
- The **two-tower model** is the dominant neural **retrieval** (stage-1) architecture: separate **user** and **item** towers produce embeddings in a shared space, with compatibility as their similarity — the neural evolution of matrix factorization.
- Two towers win at retrieval because encoding user and item **separately** lets you **precompute all item embeddings offline** and do fast **ANN search** at request time (compute only the user embedding, then look up nearest items) — exactly what stage-1 scale needs.
- **Neural ranking** (stage 2) affords a richer model on the few-hundred shortlist: it scores the user-item **pair jointly** (modeling **cross-features**), uses deep/wide-and-deep and **sequence** architectures over history, and often optimizes **multiple objectives** (engagement + quality) for precise ordering.
- The modern stack is two-tower retrieval → neural ranking → filtering/shaping — every piece the classical architecture upgraded with neural engines; but deep learning adds real **complexity/cost**, so reach for it when scale and rich features justify the engineering (not every recommender needs it).

## Further reading

- [Google — Recommendation Systems (deep neural network models)](https://developers.google.com/machine-learning/recommendation/dnn/softmax)
- [Recommender system — deep learning approaches](https://en.wikipedia.org/wiki/Recommender_system)
