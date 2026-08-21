# Brute Force and When It's Enough

*The most underrated vector index is no index at all. Brute-force search — compare the query to every vector — is the one method with perfect recall, zero build time, and no tuning, and for a surprising number of real systems it's not just adequate but optimal. Knowing when you don't need an ANN index is as valuable as knowing how they work.*

Before the clever algorithms, honor the baseline. **Brute-force** search (also called *flat* or *exact* search) computes the distance from the query to every stored vector and returns the closest — the exact kNN from the first post. It's the method every approximate index is measured against, and, crucially, it's the *right* choice more often than the hype around vector databases suggests. This post covers how it works, its real performance, and the genuine cases where reaching for an ANN index is premature optimization.

## How flat search works

There's almost nothing to it, which is part of the appeal:

```text
for each stored vector v:
    d = distance(query, v)      # using your chosen metric
keep the K smallest distances   # e.g. a bounded heap
return those K vectors
```

No index structure, no build step, no parameters. You store the vectors (a "flat" list) and scan them at query time. This simplicity has real virtues that the fancier methods sacrifice:

- **Perfect recall.** It returns the *exact* nearest neighbors, always — recall@K = 1.0 by definition. No approximation, no missed neighbors.
- **Zero build time.** There's no index to construct; a new vector is usable the instant it's added. ANN indexes, by contrast, take time (sometimes significant) to build and to insert into.
- **No tuning.** There are no recall/latency knobs to get wrong — it just works. ANN indexes require tuning parameters to hit your operating point.
- **Trivial updates.** Adding or removing a vector is just appending to or removing from a list; ANN indexes can make deletion and incremental updates awkward.

Brute force is the gold standard for *correctness* — which is also why it's used to *measure* ANN recall (you compare an ANN index's results against brute-force ground truth). The only thing it lacks is speed at scale, which is the whole reason ANN exists.

## Its real performance

The cost is O(N × d) per query, as the first post noted — linear in the number of vectors. The practical question is: *at what scale does that become too slow?* And the answer surprises people, because modern hardware computes distances very fast:

- At **thousands to tens of thousands** of vectors, brute force is effectively instant — microseconds to low milliseconds. An ANN index here is pure overhead with no benefit.
- At **hundreds of thousands** of vectors, brute force is often still fast enough for many applications (single-digit to tens of milliseconds), especially with optimized (SIMD/GPU) distance computation.
- At **millions and beyond**, brute-force latency climbs into the range where interactive search suffers, and ANN's speedup becomes worth its costs.

The exact crossover depends on your dimension, hardware, latency budget, and query rate — but the key realization is that it's *higher than most people assume*. Vectors are compared with highly optimized math, and a modern machine can scan a lot of them per second. Many systems that reach for a vector database would be perfectly served by brute force.

## When brute force is the right call

Reaching for an ANN index has real costs — build time, memory overhead, tuning, imperfect recall, update complexity — so brute force is genuinely better when those costs outweigh the speed you don't yet need:

- **Small to moderate datasets.** Below the crossover (roughly tens of thousands, often up to hundreds of thousands depending on constraints), brute force is faster *end-to-end* once you count that ANN needs building and tuning — and it gives perfect recall for free.
- **Per-user or per-tenant small corpora.** This is the big one: if each user/tenant searches only *their own* data (a few hundred to a few thousand vectors each — exactly the on-device RAG case from the edge-AI series), brute force per user is trivially fast and avoids maintaining an index per tenant. Many "personal assistant" and multi-tenant apps fall here.
- **High update churn.** If vectors are added and removed constantly, brute force's trivial updates beat an ANN index that's expensive to rebuild or degrades with incremental changes.
- **Recall is non-negotiable.** When you cannot afford to miss a true neighbor, exact search guarantees it — no recall knob to under-tune.
- **Prototyping.** Start with brute force to get a working system and a recall baseline, then add an ANN index only when measurements show you need it.

The recurring theme, consistent with the [AI Architecture Decisions](/blog/posts/ai-decisions-07-vector-storage.html) reasoning: **don't add infrastructure you don't need.** An ANN index (or a dedicated vector database) is justified by scale; below that scale it adds complexity, tuning burden, and imperfect recall in exchange for a speedup you won't notice.

## When you've outgrown it

Brute force stops being the answer when its linear cost genuinely hurts:

- **Latency exceeds your budget** at your data size and query rate — queries take too long and users feel it.
- **Query volume is high** — even fast per-query scans add up when you're doing thousands per second, and brute force's total compute cost becomes expensive.
- **The corpus is large and shared** — millions of vectors searched by all users is the canonical ANN case, where the speedup is transformative.

At that point you accept approximate results (the ANN trade from post one) to buy speed — and the next posts cover the two dominant ways to do it: IVF (partition and search part) and HNSW (navigate a graph). But adopt them *because a measurement told you to*, not because vector search "should" use a fancy index. The mark of good engineering here is starting simple and escalating on evidence.

## Key takeaways

- Brute-force (flat/exact) search compares the query to every vector — no index, no build step, no tuning — and gives perfect recall, making it the ground truth against which ANN recall is measured.
- Its virtues are exactness, zero build time, no tuning knobs, and trivial updates; its only weakness is O(N×d) linear query cost, which matters only at scale.
- The scale at which brute force becomes too slow is higher than most assume — instant at thousands, often fine at hundreds of thousands with optimized math — so many systems that reach for a vector DB don't need one.
- Brute force is the right call for small/moderate datasets, per-user/per-tenant small corpora (e.g. on-device RAG), high update churn, non-negotiable recall, and prototyping — because ANN's build/memory/tuning/recall costs outweigh a speedup you don't need.
- Escalate to an ANN index (IVF, HNSW) when a measurement shows latency exceeds budget, query volume is high, or the corpus is large and shared — on evidence, not because vector search "should" use a fancy index.

## Further reading

- [Distance metrics and dimensionality (previous post)](/blog/posts/vecsearch-02-distance-and-dimensionality.html)
- [Postgres/pgvector vs a Dedicated Vector Database](/blog/posts/ai-decisions-07-vector-storage.html)
- [On-Device AI: on-device RAG (per-user brute force in practice)](/blog/posts/edgeai-06-on-device-rag-and-memory.html)
