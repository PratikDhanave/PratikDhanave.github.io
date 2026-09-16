# The Long-Context Problem

*MoE scales a model's parameters cheaply. But there's a second scaling axis that matters just as much for modern LLMs: context length — how much text the model can attend to at once. Attention's cost grows with the square of the sequence, and the memory to run it grows linearly and relentlessly, which is why long context was hard and why so much architectural ingenuity has gone into it.*

The series' through-line (post 1) is getting more capability without proportionally more cost — on the *parameter* axis (MoE) and the *context* axis. This post opens the context axis: why attending to long sequences is expensive, on both compute and memory. Understanding the two distinct costs — the quadratic compute of attention and the linear growth of the KV cache — is the setup for the efficiency techniques in the next post.

## Two different costs, often confused

"Long context is expensive" bundles two separate problems that have different shapes and different fixes:
1. **The compute cost of attention scales with the square of sequence length** (quadratic) — dominant during training and prompt processing.
2. **The memory cost of the KV cache scales linearly with sequence length** — dominant during generation.

Keeping these straight is essential, because the techniques (next post) target one or the other. Let's take each.

## The quadratic compute of attention

Recall from post 2 that attention compares every token's query against every token's key — an all-pairs operation. For a sequence of length n, that's n × n comparisons: **attention compute grows as O(n²)** in sequence length.

The consequence is steep: double the context and attention does 4× the work; grow context 10× and attention does 100× the work. This quadratic scaling is why early transformers had short context windows (a few thousand tokens) — going longer meant compute exploding. It's a fundamental property of the all-pairs mechanism: every token attending to every other token is inherently quadratic. Most of the "efficient attention" research exists to soften this O(n²) — either by approximating attention (attend to fewer pairs) or by computing exact attention more cleverly so the constant factors and memory traffic shrink (next post). The quadratic term dominates when processing a long *prompt* (all tokens at once) and during training.

## The KV cache and its linear, relentless growth

The second cost appears during **generation** and is, in practice, often the harder operational problem. Recall LLMs are autoregressive (post 2): they generate one token at a time, and each new token attends to all previous tokens. To avoid recomputing the keys and values of all prior tokens on every step, models **cache** them — the **KV cache**.

The KV cache stores the key and value vectors for every token processed so far, so generating the next token only requires computing the new token's Q/K/V and attending against the cached K/V. This makes generation efficient in compute — but the cache **grows linearly with the sequence length**: every token added appends its keys and values, for every layer and every attention head. A long conversation or document means a large, ever-growing KV cache held in fast accelerator memory.

Why this is often the binding constraint (connecting to the LLM-serving fundamentals):
- **It consumes scarce accelerator memory** — and it grows with *both* context length *and* the number of concurrent requests, so the KV cache, not the model weights, frequently limits how many requests you can serve and how long their contexts can be.
- **Generation is memory-bandwidth-bound** — each token step reads the entire KV cache from memory, so a bigger cache means more memory traffic per token, slowing generation.
- **It sets a hard ceiling** — run out of memory for the KV cache and you simply can't extend the context further.

So the KV cache is the reason long context is expensive *at serving time* even when the quadratic-compute term is manageable: it's a linear but *unbounded* memory cost that scales with everything you care about (context × concurrency).

## Why long context is worth the trouble

Given both costs, why push context length at all? Because long context unlocks major capabilities:
- **Whole-document and multi-document reasoning** — feed in entire codebases, long papers, books, or large sets of retrieved passages at once.
- **Longer memory in conversations and agents** — an agent (or chat) that can hold a long history in context behaves more coherently over extended interactions.
- **Fewer retrieval compromises** — with a large context, you can include more candidate information directly rather than aggressively pre-filtering (though this interacts with the "lost in the middle" effect, where models use the middle of a very long context less reliably — long context isn't a free substitute for good retrieval).

Long context is one of the most visible axes of LLM progress — context windows grew from a few thousand tokens to hundreds of thousands and beyond — and that progress is *architectural*: it came from techniques that attack the two costs above. The quadratic attention compute and the linear KV-cache memory are the walls; the next post covers the ingenuity that gets past them (efficient attention variants, KV-cache reduction, and local/sparse attention patterns), letting modern models attend to far more context without the cost exploding.

## Key takeaways

- "Long context is expensive" bundles **two distinct costs** with different shapes and fixes: attention's **quadratic (O(n²)) compute** (dominant in training/prompt processing) and the **KV cache's linear memory growth** (dominant in generation).
- **Attention compute is O(n²)** because it's all-pairs (every token's query vs. every token's key) — double the context = 4× the work — which is why early transformers had short windows and why "efficient attention" research exists.
- The **KV cache** stores keys/values of all prior tokens so autoregressive generation doesn't recompute them — making generation compute-efficient but growing the cache **linearly and unboundedly** with sequence length, per layer and head.
- The KV cache is often the **binding serving constraint**: it consumes scarce accelerator memory scaling with context × concurrency (limiting how many requests/how-long contexts you can serve), makes generation memory-bandwidth-bound, and sets a hard memory ceiling — frequently more than the model weights themselves.
- Long context is worth it (whole-document reasoning, agent/chat memory, less retrieval pre-filtering — with the "lost in the middle" caveat), and the dramatic growth in context windows is **architectural** — the next post's techniques attack the quadratic compute and the linear KV-cache memory.

## Further reading

- [Attention Is All You Need — Vaswani et al. (arXiv:1706.03762)](https://arxiv.org/abs/1706.03762)
- [Longformer: The Long-Document Transformer — Beltagy et al. (arXiv:2004.05150)](https://arxiv.org/abs/2004.05150)
