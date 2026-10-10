# The Memory Hierarchy — Why Bandwidth Rules Inference

*Post 1 ended on a reversal: GPUs are fast at arithmetic, but arithmetic is rarely the bottleneck — moving data is. This post makes that concrete by walking the GPU's memory hierarchy, from the tiny ultra-fast registers next to the compute units down to the big slow memory that holds the model's weights. Once you see the orders-of-magnitude gaps between these levels, every performance decision in LLM inference starts to make sense.*

The central fact of GPU performance is that there isn't one "memory" — there's a hierarchy of them, each a trade-off between speed and size. Compute units are fast; the memory holding your data is comparatively slow; and the whole game is keeping data as close to the compute as possible. This post builds that hierarchy and explains why, for LLM inference specifically, **memory bandwidth** — not compute — is usually the number that decides your speed.

## The hierarchy, fastest to slowest

Like a CPU, a GPU has a **memory hierarchy**: small-and-fast at the top, large-and-slow at the bottom, with each level roughly an order of magnitude bigger and slower than the one above.

- **Registers** — tiny, per-thread, effectively instant. The compute units read operands from here.
- **Shared memory / L1 cache** — a small fast scratchpad *inside each SM* (post 1), shared by the threads running there. Software-managed, it's the key tool for avoiding trips to slower memory — if a block of data is reused, you stage it here once.
- **L2 cache** — a larger cache shared across the whole chip; a middle tier.
- **Global memory (HBM)** — the big pool, gigabytes of **High Bandwidth Memory** stacked on the GPU package. This is where model weights, activations, and the KV cache live. It's enormous compared to the caches but, in relative terms, *slow* — and crucially, it's the level you hit constantly during inference.

The gaps are large: reading from registers is perhaps a hundred times faster than reading from global memory. So a kernel that constantly reaches down to HBM will run at a fraction of the speed of one that keeps its working data in shared memory and registers. "Where does the data live?" is the question that governs GPU performance.

## Bandwidth vs. capacity: two different limits

Global memory imposes *two* separate constraints, and conflating them causes a lot of confusion:

- **Capacity** — how much fits. A model's weights plus its KV cache (the attention memory, see the [serving series](/blog/series/llm-inference-and-serving/)) must fit in HBM, or you can't run it on that GPU at all. This is why a 70-billion-parameter model needs a big-memory GPU (or several) and why quantization (post 5) matters — it shrinks the weights to fit.
- **Bandwidth** — how fast data moves between HBM and the compute units, measured in terabytes per second. Even when a model fits, *every token generated* requires reading relevant data from HBM, and the time to do that reading is often the dominant cost.

Capacity determines *whether* you can run the model; bandwidth often determines *how fast*. Both are about memory, not compute — which is already a strong hint about where LLM inference spends its time.

## Why LLM generation is memory-bound

Here is the fact that surprises people new to inference. When an LLM generates text one token at a time (*decoding*), each step must read the model's entire set of weights from HBM to compute just *one* token's worth of output. For a large model that's gigabytes of weights read per token — an enormous amount of data movement to produce a tiny amount of compute.

The result: the compute units finish their small amount of arithmetic and then sit idle, *waiting for the next chunk of weights to arrive from memory*. The GPU is **memory-bandwidth-bound** — its speed is set by how fast it can stream weights out of HBM, not by how many FLOPS it can do. This single fact explains a huge amount of inference engineering:
- **Why batching helps so much** (serving series): if you read the weights once and use them for *many* sequences at once, you amortize the expensive memory read across many tokens — turning a memory-bound workload compute-bound.
- **Why quantization is so effective** (post 5): smaller weights mean less data to stream from HBM per token, so a more compact model is directly a *faster* model, not just a smaller one.
- **Why the KV cache is a bandwidth problem**, not just a capacity one: it too must be read every step.

Not everything is memory-bound — the *prefill* phase (processing the prompt) does enough parallel compute to be compute-bound, and large batches shift the balance. Knowing *which* regime you're in is the whole point of the roofline model (post 3). But the default mental model for single-stream LLM generation is: **you are waiting on memory bandwidth.**

The takeaway: a GPU has a **memory hierarchy** — registers → shared memory/L1 → L2 → **global memory (HBM)** — each level roughly an order of magnitude larger and slower, so performance is governed by *where the data lives* (keep it in shared memory and registers; every trip to HBM is expensive). Global memory imposes two distinct limits: **capacity** (does the model + KV cache fit at all?) and **bandwidth** (how fast weights stream to the compute units). And the defining fact of LLM generation is that it's **memory-bandwidth-bound** — each token requires reading the whole model from HBM — which is precisely why batching and quantization work: they reduce data movement per token.

## Key takeaways

- The GPU **memory hierarchy** runs fastest-smallest to slowest-largest: **registers** (per-thread, instant) → **shared memory / L1** (per-SM software-managed scratchpad) → **L2** (chip-wide cache) → **global memory (HBM)** (gigabytes, holds weights/activations/KV cache, relatively slow). Reading registers is ~100× faster than HBM.
- Global memory imposes two separate limits: **capacity** (the model + KV cache must *fit* — drives GPU choice and quantization) and **bandwidth** (TB/s of data movement — often the real speed limit).
- LLM token generation (*decoding*) is **memory-bandwidth-bound**: each token requires reading the *entire* model's weights from HBM for a tiny amount of compute, so the units idle waiting on memory.
- This one fact explains core optimizations: **batching** amortizes the weight read across many sequences (→ compute-bound), **quantization** shrinks weights so less data streams per token (→ faster, not just smaller), and the **KV cache** is a bandwidth cost too.
- *Prefill* (prompt processing) and large batches can be compute-bound instead — which regime you're in is what the roofline model (post 3) tells you.

## Further reading

- [High Bandwidth Memory — the GPU's main memory](https://en.wikipedia.org/wiki/High_Bandwidth_Memory)
- [Memory hierarchy — the speed/size trade-off across levels](https://en.wikipedia.org/wiki/Memory_hierarchy)
