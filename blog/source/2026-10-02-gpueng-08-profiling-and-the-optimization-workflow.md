# Profiling and the Optimization Workflow — Measure, Don't Guess

*Everything in this series converges on one discipline: you cannot optimize what you haven't measured. GPU performance is unintuitive — the bottleneck is rarely where you'd guess — so the engineers who make inference fast are the ones who profile first, identify the actual limit, apply the one lever that moves it, and measure again. This closing post ties the series into a workflow you can actually run, and looks at where inference engineering is heading.*

The series built a toolkit: the hardware (post 1), the memory hierarchy (2), the roofline (3), the execution model (4), precision (5), and two canonical optimizations (6–7). This post is about *using* them as a method rather than a bag of tricks. The thesis is simple and hard-won: optimization is an empirical loop grounded in measurement, and intuition is a trap.

## Why guessing fails on GPUs

On a CPU you can often reason your way to the hot spot. On a GPU, intuition is actively misleading, because the limit is usually invisible from the code:
- The code *looks* compute-heavy, but it's **memory-bound** (post 3) — the units are idle waiting on HBM.
- The kernel *looks* busy, but **occupancy** is low (post 4) — there aren't enough warps resident to hide memory latency.
- The model *looks* like it needs a faster algorithm, but it just needs **bf16** (post 5) — fewer bits to move.

Every one of these is a case where the obvious fix (optimize the arithmetic) does nothing because the real limit is elsewhere. This is why the roofline matters so much: it replaces "what do I think is slow?" with "what is this operation's arithmetic intensity, and which ceiling is it under?" — a question you *measure*, not guess.

## The optimization loop

Real inference optimization is a disciplined cycle:

1. **Measure the baseline.** Get real numbers — latency, throughput, and GPU utilization — on a representative workload. Without a baseline you can't tell whether a change helped, and "it feels faster" is not data.
2. **Profile to find the bottleneck.** Use a GPU profiler (NVIDIA Nsight, PyTorch's profiler, or framework-level traces) to see where time actually goes and *why*. The key questions: Is the GPU even busy (utilization)? Are kernels memory-bound or compute-bound (roofline)? Is occupancy limiting things? Is time going to compute, to data movement, or to gaps between kernels?
3. **Identify the dominant limit.** There's usually one — and per Amdahl's law, speeding up anything *other* than the dominant cost barely moves the total. Find the biggest bar in the profile.
4. **Apply the matching lever.** Memory-bound → reduce data movement (quantization, fusion, batching). Compute-bound → faster math (tensor cores, precision). Low occupancy → tune resource usage or pick a better kernel. Capacity-bound → quantize or shard. The lever follows from the *diagnosis*, not from habit.
5. **Measure again, then repeat.** Verify the change helped, then re-profile — because fixing the top bottleneck *promotes a new one*. Optimization is iterative: you're always chasing the current dominant cost, and you stop when you're close enough to the relevant roofline ceiling or you've hit your latency/cost target.

The meta-point: this is the scientific method applied to a GPU. Hypothesis (the roofline), measurement (the profiler), one changed variable, re-measure. Most failed optimization efforts skip straight to step 4 with a guess.

## Knowing when to stop — and where this is heading

Two closing judgments matter as much as the technique:

- **Stop at "good enough."** The goal is a latency and cost *target*, not the theoretical peak. Once a kernel is near its roofline ceiling, further effort has diminishing returns — and your time is better spent on the *next* bottleneck or on the layers above the GPU. Over-optimizing a non-dominant cost is the most common waste in performance work.
- **Lean on the ecosystem.** You rarely write kernels. The highest-leverage move is usually to adopt the libraries and serving engines that already embody posts 5–7 — optimized kernels, FlashAttention, PagedAttention, quantization — and spend your effort on *choosing and configuring* them correctly for your workload (batch sizes, precision, parallelism). Inference engineering is mostly integration plus measurement, not kernel authorship.

Where it's heading: the limits don't change — the memory wall and the roofline are physics — but the frontier keeps attacking them. Hardware adds bandwidth and lower-precision formats (FP8 and below); algorithms keep raising arithmetic intensity (better fusion, sparsity, mixture-of-experts routing that touches fewer weights per token); and serving systems keep squeezing more concurrency out of the same HBM. The constant across all of it is the mental model this series built: **find what's moving through HBM, measure which ceiling you're under, and move the one lever that matters.** Master that loop and you can reason about optimizations that don't exist yet.

The takeaway: GPU optimization is an **empirical loop**, not intuition — the bottleneck is usually invisible from the code (memory-bound work that looks compute-heavy, low occupancy, or a model that just needs bf16). The discipline: **measure a baseline → profile to find the bottleneck → identify the single dominant limit → apply the lever the diagnosis demands (not habit) → measure again and repeat**, since fixing the top cost promotes a new one. Stop at a latency/cost *target* near the relevant roofline ceiling rather than chasing theoretical peak, and get most of your wins by **adopting optimized libraries/serving engines** and configuring them well rather than writing kernels. The enduring model — find what moves through HBM, measure which ceiling you're under, move the one lever that matters — outlasts any specific trick.

## Key takeaways

- On GPUs, **intuition misleads**: code that looks compute-heavy is often memory-bound, a busy-looking kernel may have low **occupancy**, and an apparent algorithm problem may just need **bf16** — the obvious fix does nothing when the real limit is elsewhere.
- The **optimization loop**: (1) measure a baseline (latency/throughput/utilization on a real workload), (2) **profile** to find where time goes and why, (3) identify the *single dominant* limit (Amdahl's law — fixing anything else barely helps), (4) apply the **matching lever** (memory-bound→less data movement; compute-bound→faster math; low occupancy→better kernel; capacity-bound→quantize/shard), (5) re-measure and repeat.
- Each fix **promotes a new bottleneck**, so optimization is iterative — you chase the current dominant cost and stop at a **latency/cost target** near the relevant roofline ceiling, not theoretical peak (over-optimizing a non-dominant cost is the classic waste).
- The highest-leverage move is usually **adopting optimized libraries and serving engines** (FlashAttention, PagedAttention, quantization, good kernels) and *configuring* them for your workload — inference engineering is mostly integration + measurement, not kernel authorship.
- The frontier keeps attacking the same physics (FP8 and lower precision, sparsity/mixture-of-experts, better fusion, more concurrency per HBM), but the durable skill is the **mental model**: find what moves through HBM, measure which ceiling you're under, move the one lever that matters.

## Further reading

- [Profiling (computer programming) — measuring where time is spent](https://en.wikipedia.org/wiki/Profiling_(computer_programming))
- [Roofline model — diagnosing the binding performance ceiling](https://en.wikipedia.org/wiki/Roofline_model)
