# The Roofline Model — Are You Compute-Bound or Memory-Bound?

*Posts 1 and 2 kept drawing a line between two worlds: workloads limited by how fast the GPU can compute, and workloads limited by how fast it can move data. The roofline model is the single tool that tells you which world you're in for any given operation — and therefore which optimizations will help and which are a waste of time. It is the most useful mental model in performance engineering, and it fits on one chart.*

Every optimization decision in inference comes down to one question: is this operation limited by compute or by memory bandwidth? Optimizing the wrong one is effort with zero payoff — adding compute to a memory-bound kernel does nothing. The **roofline model** answers the question quantitatively using just two hardware numbers and one property of your workload. This post builds it from scratch and shows why LLM inference lives on a specific part of the chart.

## Arithmetic intensity: the one number that matters

The key property of any operation is its **arithmetic intensity**: the ratio of compute to data movement.

```
Arithmetic intensity = FLOPs performed / bytes moved from memory
```

It measures how much useful math you do for each byte you pull out of HBM. A high-intensity operation does lots of arithmetic per byte (good — the expensive memory read is well amortized). A low-intensity operation does little arithmetic per byte (bad — you move a lot of data for a little compute, so you're starved waiting on memory).

- **Matrix-matrix multiply** (big × big) is *high* intensity: each byte of input participates in many multiply-adds. This is what makes large-batch inference and training compute-efficient.
- **Matrix-vector multiply** (a matrix times a single vector) is *low* intensity: each weight is read from memory and used exactly once. This is *exactly* LLM single-token decoding (post 2) — read the whole weight matrix, use each weight once, produce one token. Inherently memory-bound.

Arithmetic intensity is a property of the *operation and how it's done*, and raising it (doing more math per byte read) is the deep goal behind batching, kernel fusion, and FlashAttention — all later posts.

## The chart: two ceilings

Plot achievable performance (FLOPS, vertical) against arithmetic intensity (horizontal) and the hardware imposes two limits that together form a "roofline":

- A **slanted ceiling** on the left: at low intensity you're **memory-bound**, and the most you can achieve is `arithmetic intensity × memory bandwidth`. Performance rises as intensity rises — every extra FLOP per byte buys speed, because memory is the constraint.
- A **flat ceiling** on the right: at high intensity you're **compute-bound**, capped at the GPU's peak FLOPS. Past a certain intensity, adding more math per byte buys nothing — you've saturated the arithmetic units.

The corner where the slant meets the flat is the break-even intensity. An operation's intensity places it under one ceiling or the other, and *that tells you what to optimize*:
- **Memory-bound (under the slant):** the only thing that helps is reducing data movement or raising intensity — smaller data types (quantization), reusing data in shared memory (fusion), or batching. Adding compute does nothing.
- **Compute-bound (under the flat):** now faster arithmetic helps — tensor cores, lower-precision math, better algorithms. Reducing memory traffic does nothing.

This is the model's payoff: it turns "my kernel is slow" into "my kernel is at X% of the *relevant* ceiling, and here is which lever moves it."

## Where LLM inference sits

The roofline explains the two phases of LLM inference precisely:

- **Prefill** (processing the whole prompt at once) is a matrix-*matrix* multiply over all prompt tokens — high intensity, **compute-bound**. It sits under the flat ceiling, and tensor cores and lower precision speed it up.
- **Decode** (generating one token at a time) is a matrix-*vector* multiply — low intensity, **memory-bound**. It sits under the slant, and only reducing data movement (quantization, batching to amortize the weight read across sequences) speeds it up.

This is why the same model can feel compute-limited while chewing through a long prompt and bandwidth-limited while streaming out the answer — they're different points on the roofline. And it's why **batching is the master lever for throughput**: batching many sequences turns the memory-bound matrix-vector decode into a higher-intensity matrix-matrix operation, sliding it rightward up the slant toward the compute ceiling. The roofline makes "batch to go faster" not folklore but geometry.

The takeaway: the **roofline model** answers the one question that governs every optimization — compute-bound or memory-bound? — from two hardware numbers (peak FLOPS, memory bandwidth) and one workload property, **arithmetic intensity** (FLOPs per byte moved). Low intensity → **memory-bound** (under the slanted ceiling; only *less data movement* helps — quantization, fusion, batching). High intensity → **compute-bound** (under the flat ceiling; only *faster math* helps — tensor cores, lower precision). LLM **prefill** is compute-bound (matrix-matrix) and **decode** is memory-bound (matrix-vector), which is why batching — raising intensity — is the master throughput lever.

## Key takeaways

- **Arithmetic intensity** = FLOPs performed ÷ bytes moved from memory — how much math you do per byte read from HBM. High intensity amortizes the expensive memory read; low intensity starves the compute units.
- **Matrix-matrix** multiply is high-intensity (each byte reused many times); **matrix-vector** multiply is low-intensity (each weight read once) — and LLM single-token decode *is* matrix-vector, hence inherently memory-bound.
- The **roofline** has two ceilings: a **slant** (`intensity × bandwidth`) where you're **memory-bound**, and a **flat** (peak FLOPS) where you're **compute-bound**; an operation's intensity places it under one, telling you which lever works.
- **Memory-bound** → reduce data movement (quantization, shared-memory reuse/fusion, batching); **compute-bound** → faster arithmetic (tensor cores, lower precision). Optimizing the wrong axis buys *nothing*.
- LLM **prefill** (matrix-matrix) is compute-bound; **decode** (matrix-vector) is memory-bound — and **batching** raises decode's intensity, sliding it up the slant toward the compute ceiling, which is why it's the master throughput lever.

## Further reading

- [Roofline model — the performance ceiling chart](https://en.wikipedia.org/wiki/Roofline_model)
- [FLOPS — measuring floating-point throughput](https://en.wikipedia.org/wiki/FLOPS)
