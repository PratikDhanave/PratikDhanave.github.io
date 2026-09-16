# Efficient Attention

*The two costs of long context — quadratic attention compute and linear KV-cache memory — each have a family of solutions, and together they're why modern models can handle context lengths that were impossible a few years ago. Grouped-query attention shrinks the KV cache; FlashAttention computes exact attention far faster; sliding-window and sparse patterns break the quadratic. This post covers the techniques that made long context practical.*

The previous post laid out the walls: O(n²) attention compute and a linearly-growing KV cache. This post covers the ingenuity that gets past them. The techniques split cleanly by which cost they attack — some shrink the KV-cache memory, some speed up the attention computation, some reduce how many token-pairs attention considers at all. Knowing which does which is the point.

## Shrinking the KV cache: MQA and GQA

The KV cache stores keys and values for every token, *for every attention head* (post 2). A direct way to shrink it: **have fewer key/value heads.**

- **Multi-Query Attention (MQA)** — all query heads share a *single* key/value head. Instead of storing K/V for, say, 32 heads, you store them for 1. This shrinks the KV cache dramatically (by the number of heads), directly attacking the linear memory cost — but sharing one K/V across all heads can cost some quality.
- **Grouped-Query Attention (GQA)** — the middle ground that most modern models adopted (e.g. the Llama family): query heads are split into a few *groups*, each group sharing one K/V head. With 32 query heads and 8 K/V groups, the KV cache is 4× smaller than full multi-head attention, with quality much closer to full attention than MQA. GQA is a tunable knob between full multi-head (best quality, biggest cache) and MQA (smallest cache, some quality loss).

GQA is a great example of a cheap, widely-adopted win: a small architectural change that multiplies how much context and concurrency you can fit in memory, at little quality cost. It targets the KV-cache (memory/generation) cost, not the quadratic compute.

## Computing exact attention faster: FlashAttention

A different and important idea: **make the exact attention computation faster and more memory-efficient without changing what it computes.** This is what **FlashAttention** does — and the distinction matters: it's *not* an approximation. It computes the same attention, but rearranges *how*.

The insight is that attention on GPUs was bottlenecked not by raw compute but by *memory traffic* — repeatedly reading and writing the large intermediate attention-score matrix to slow high-bandwidth memory. FlashAttention is **IO-aware**: it computes attention in tiles that stay in the GPU's fast on-chip memory, never materializing the full n×n score matrix in slow memory. The result is attention that's substantially faster and uses far less memory, with *identical* mathematical output.

Because it's exact, FlashAttention was adopted essentially universally — it's a free speed-and-memory win with no quality tradeoff, which is rare. It doesn't change the O(n²) *arithmetic* fundamentally, but it slashes the constant factors and the memory footprint enough to make long-context training and inference far more practical. The lesson it embodies: sometimes the win isn't a cleverer algorithm but a hardware-aware *implementation* of the same one.

## Breaking the quadratic: sparse and local attention

The remaining family attacks the O(n²) directly by **not attending to every pair** — restricting which tokens each token attends to, so the number of pairs grows less than quadratically:

- **Sliding-window (local) attention** — each token attends only to a fixed window of nearby tokens (say the previous 4,096) rather than all previous tokens. This makes the per-token attention cost *constant* (window-sized) instead of growing with sequence length, breaking the quadratic. Information still propagates across long distances *through the layers* (stacking windowed layers gives an effective receptive field much larger than one window), so quality loss is limited for many tasks. Used in models like Mistral and Longformer.
- **Sparse attention patterns** — attend to a structured subset of tokens (e.g. local window + a few global tokens, or strided patterns) rather than all of them, chosen so important connections are preserved while most pairs are skipped.

These *approximate* full attention (unlike FlashAttention), trading some ability to attend to arbitrary distant tokens for a sub-quadratic cost. The tradeoff is real — a token can't directly attend to something outside its window in one layer — so these are used where the locality assumption holds well, often mixed with occasional full-attention layers to preserve some global reach.

## Which technique attacks which cost

The clean mental model, tying back to post 6's two costs:

| Technique | Attacks | How | Approximate? |
|---|---|---|---|
| **GQA / MQA** | KV-cache memory | fewer K/V heads → smaller cache | slight (MQA more) |
| **FlashAttention** | attention compute + memory traffic | IO-aware exact computation | no (exact) |
| **Sliding-window / sparse** | quadratic compute | attend to fewer pairs | yes |

They're complementary and usually combined: a modern model might use GQA (smaller cache) *and* FlashAttention (fast exact kernels) *and* sliding-window attention on some layers (sub-quadratic) together. Each attacks a different part of the problem, so stacking them compounds the gains — which is exactly how context windows grew from a few thousand to hundreds of thousands of tokens. Alongside these, KV-cache *management* techniques from the serving world (paging, eviction, quantizing the cache) further stretch what's possible at inference. The combination of parameter-scaling (MoE) and context-scaling (efficient attention) is what defines the shape of a modern frontier model — which the final post assembles.

## Key takeaways

- The long-context techniques split by **which cost they attack** (KV-cache memory vs. attention compute vs. the number of pairs), so knowing which does which is the key mental model.
- **GQA / MQA** shrink the **KV cache** by using fewer key/value heads (MQA = one shared K/V; GQA = a few groups) — GQA is the widely-adopted middle ground (Llama family), a cheap win multiplying context/concurrency capacity at little quality cost.
- **FlashAttention** speeds up **exact** attention (not an approximation) by being **IO-aware** — computing in tiles in fast on-chip memory, never materializing the full n×n matrix in slow memory — a near-universal free speed+memory win; sometimes the win is a hardware-aware implementation, not a new algorithm.
- **Sliding-window / sparse attention** break the **quadratic** by attending to fewer pairs (a local window or structured subset), making per-token cost sub-quadratic — an *approximation* (info propagates across distance through layers), used where locality holds, often mixed with some full-attention layers.
- The techniques are **complementary and combined** (GQA + FlashAttention + sliding-window + KV-cache management) — stacking them is how context windows grew from thousands to hundreds of thousands of tokens; parameter-scaling (MoE) + context-scaling (efficient attention) define the modern frontier model.

## Further reading

- [FlashAttention: Fast and Memory-Efficient Exact Attention — Dao et al. (arXiv:2205.14135)](https://arxiv.org/abs/2205.14135)
- [GQA: Training Generalized Multi-Query Transformer Models — Ainslie et al. (arXiv:2305.13245)](https://arxiv.org/abs/2305.13245)
