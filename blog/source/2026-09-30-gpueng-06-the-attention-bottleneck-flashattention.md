# The Attention Bottleneck — and How FlashAttention Fixed It

*Attention is the operation that makes transformers powerful, and for years it was also their worst performance bottleneck — not because it does too much math, but because it moved too much data. FlashAttention is the single most important GPU optimization of the LLM era, and it's a perfect case study in everything this series has built: it's memory-bound, the roofline says so, and the fix is to raise arithmetic intensity by never writing the big intermediate to HBM. Understanding it is understanding how real kernel optimization works.*

Posts 2 and 3 said LLM performance is usually about data movement, not arithmetic. Attention is the clearest possible example. This post explains why naive attention is memory-bound, why that got catastrophically worse as context lengths grew, and how FlashAttention's tiling-and-fusion idea turned it around — the same reasoning you'd apply to optimize any memory-bound kernel.

## Why naive attention is a memory monster

Attention, at its core, has every token look at every other token: for a sequence of length N, it computes an **N×N matrix** of attention scores, softmaxes it, and uses it to weight the values. The arithmetic isn't the problem. The problem is that *materializing* that N×N matrix means **writing N² numbers to HBM and reading them back** — twice, for the scores and the softmaxed weights.

This is a disaster on two fronts from this series' lens:
- **It's memory-bound (post 3):** the operation moves a huge N² intermediate through slow HBM while doing relatively little compute per byte — low arithmetic intensity, pinned under the roofline's memory slant. The GPU's tensor cores sit idle waiting on HBM traffic.
- **It scales quadratically:** double the context length and the N² intermediate quadruples. As models went from 2K to 128K+ context, this quadratic *memory traffic* (not just memory capacity) became the dominant cost of long-context inference. Attention was spending almost all its time shuttling a giant matrix to and from HBM.

The naive implementation was leaving most of the GPU's compute on the table — a textbook memory-bound kernel begging for the post-3 treatment.

## The fix: tiling and fusion, never touch HBM

**FlashAttention**'s insight is pure roofline reasoning: *don't write the N×N matrix to HBM at all.* Instead, compute attention in **tiles** small enough to fit in the SM's fast shared memory (post 2), and **fuse** the whole sequence of operations — scores, softmax, value-weighting — into a single kernel that keeps the intermediate on-chip and only ever writes the final result back to HBM.

Two ideas make this work, and both are general kernel-optimization techniques:
- **Kernel fusion** — instead of separate kernels for matmul → softmax → matmul (each round-tripping its output through HBM), do them as one kernel so intermediates live in shared memory and registers. You pay the HBM cost once (read inputs, write output) instead of several times. Fusion is *the* canonical way to raise arithmetic intensity: same math, far less data movement.
- **Tiling with online softmax** — process the sequence block by block, maintaining a running softmax normalization so you never need the whole row of scores at once. This is the clever part: softmax normally needs all N scores, but FlashAttention computes it incrementally as tiles stream through, so no tile ever needs the full N×N matrix.

The result: attention goes from writing an N² matrix to HBM to writing nothing but the output. It's **exact** — not an approximation — yet dramatically faster and, crucially, its memory traffic scales *linearly* instead of quadratically, which is what made long context practical. On the roofline, FlashAttention slides attention rightward off the memory slant toward the compute ceiling.

## Why this is the lesson of the whole series

FlashAttention didn't invent new math — it did the *same* attention, but respected the hardware. That's the entire thesis of inference engineering in one example:
- The bottleneck was **data movement, not compute** (posts 1–2).
- The **roofline** correctly identified it as memory-bound and pointed at the fix: raise arithmetic intensity (post 3).
- The tools were **shared memory** reuse and **kernel fusion**, bounded by **occupancy** (posts 2, 4).
- The payoff compounded with **lower precision** (post 5), since the tiles are also smaller in bf16.

This is why "use FlashAttention" (via libraries like the ones in the [serving series](/blog/series/llm-inference-and-serving/)) is universal advice, and more importantly why understanding *why* it works lets you reason about the next bottleneck. Nearly every major inference speedup is a variation on the same move: find the big thing being shuffled through HBM, and keep it on-chip instead. FlashAttention is the archetype.

The takeaway: naive attention computes an **N×N score matrix** and materializes it in HBM — the arithmetic is modest but the *data movement* is enormous and grows **quadratically** with context length, making it a textbook memory-bound kernel that starves the tensor cores. **FlashAttention** fixes this with pure roofline reasoning: never write the N×N matrix to HBM. It **tiles** the computation into blocks that fit in shared memory, uses an **online softmax** to avoid needing the full score row, and **fuses** scores+softmax+value-weighting into one kernel — producing the *exact* same result with linear (not quadratic) memory traffic. It's the archetype of all inference optimization: the bottleneck is data movement, the roofline names it, and the fix is keeping the big intermediate on-chip instead of in HBM.

## Key takeaways

- Attention computes an **N×N** score matrix, softmaxes it, and weights the values; the cost isn't the math but **materializing N² numbers in HBM** (written and read back twice) — low arithmetic intensity, hard **memory-bound**.
- It scales **quadratically**: as context grew from 2K to 128K+, the N² *memory traffic* (not just capacity) became the dominant long-context cost, leaving tensor cores idle.
- **FlashAttention** never writes the N×N matrix to HBM: it **tiles** into blocks that fit in **shared memory**, maintains an **online softmax** (incremental normalization, so no full score row is needed), and **fuses** the ops into one kernel — paying the HBM cost once.
- The result is **exact** (not an approximation) but far faster, with **linear** memory traffic — which is what made long context practical; on the roofline it slides attention off the memory slant toward the compute ceiling.
- It's the **archetype of inference optimization**: data movement is the bottleneck, the roofline identifies it, and the fix is **kernel fusion + shared-memory tiling** to raise arithmetic intensity — the same move behind nearly every major speedup.

## Further reading

- [Transformer (deep learning architecture) — the attention mechanism](https://en.wikipedia.org/wiki/Transformer_(deep_learning_architecture))
- [Attention (machine learning) — how attention scores work](https://en.wikipedia.org/wiki/Attention_(machine_learning))
