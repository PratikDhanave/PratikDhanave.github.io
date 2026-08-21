# Quantization

*Quantization shrinks a model by storing its numbers in fewer bits — and because LLM decode is bottlenecked on moving those numbers from memory, making them smaller makes inference both cheaper to host and faster to run. It's the rare optimization that improves memory, cost, and speed at once, if you respect its limits on quality.*

The earlier posts established that model weights are huge and that decode is memory-bandwidth-bound — the GPU spends its time hauling weights from memory. **Quantization** attacks both problems directly: represent each weight in 8 or 4 bits instead of 16, and the model takes a quarter to half the memory and is proportionally faster to read. This post explains what quantization is, the main approaches, and the quality trade-off you must manage.

## What quantization is

A trained model's weights are numbers, normally stored in 16-bit floating point (FP16/BF16). **Quantization** stores them in a lower-precision format — commonly 8-bit integers (INT8) or 4-bit (INT4) — mapping the original range of float values onto a smaller set of representable levels. Fewer bits per number means:

- **Less memory.** INT8 halves the model's size versus FP16; INT4 quarters it. A model that needed 140 GB in FP16 fits in ~35 GB at INT4 — the difference between needing several GPUs and fitting on one.
- **Faster decode.** Since decode is limited by *moving weights from memory*, smaller weights mean less data to move per step, so tokens generate faster. The speedup roughly tracks the memory reduction because the bottleneck is bandwidth.
- **Lower cost.** Fitting a model on fewer/smaller GPUs, and freeing memory for more KV cache (hence larger batches), both cut cost per token.

The catch, of course: fewer bits means less precision, and too little precision degrades the model's quality. The whole craft of quantization is getting the memory/speed benefit while keeping quality loss negligible.

## The core trade-off: bits vs. quality

Every quantization choice trades precision for size, and the quality impact is non-linear:

- **FP16/BF16 (16-bit)** — the standard baseline; full quality, full size.
- **INT8 (8-bit)** — roughly half the size; with good methods, quality loss is typically very small to negligible. Often a safe default.
- **INT4 (4-bit)** — a quarter of the size; larger potential quality loss, but modern methods keep it small for many models — the popular sweet spot for fitting big models on limited hardware.
- **Below 4-bit** — aggressive; quality degradation becomes harder to avoid and depends heavily on model and method.

The critical nuance is that **not all weights are equally sensitive.** A small fraction of weights (and activations) are *outliers* whose precision matters disproportionately — quantize them crudely and quality collapses; preserve them and you can quantize everything else aggressively. The best methods exist precisely to identify and protect these sensitive values, which is why "4-bit" from a good method can vastly outperform naive 4-bit rounding.

## Post-training quantization vs. quantization-aware training

There are two broad strategies for *when* quantization happens:

- **Post-training quantization (PTQ)** — take an already-trained model and quantize it directly, without retraining. This is by far the most common for serving because it's cheap and fast (no training run needed). The sophistication is in *how* you round to minimize error, which is where the well-known PTQ methods come in:
  - **GPTQ** — quantizes weights layer by layer using a small calibration dataset to minimize the error introduced, achieving good 4-bit quality.
  - **AWQ (Activation-aware Weight Quantization)** — protects the small set of *salient* weights that matter most (identified via activation statistics), preserving quality at low bit-widths.
  - **GGUF/llama.cpp quantization** — the popular formats for running quantized models on CPUs and consumer/edge hardware, with a range of bit-width presets.
- **Quantization-aware training (QAT)** — simulate quantization *during* training/fine-tuning so the model learns weights robust to it. This can achieve better quality at very low bit-widths but requires a training run, so it's used when PTQ quality isn't sufficient and you can afford the compute.

For most serving, PTQ with a good method (GPTQ/AWQ for GPU, GGUF for CPU/edge) is the practical default; QAT is the escalation when you need the last bit of quality at aggressive compression.

## What gets quantized: weights, activations, and the KV cache

Quantization isn't only about weights — there are three distinct targets, each with different implications:

- **Weight-only quantization** — the most common; store weights in low precision but compute in higher precision (dequantize on the fly). This captures most of the memory and bandwidth benefit with the least quality risk, and it's ideal for the memory-bound decode phase.
- **Weight + activation quantization** — quantize the activations (the intermediate values) too, enabling genuinely lower-precision *compute* (e.g. INT8 matrix math). This can speed the compute-bound prefill phase but is more sensitive to quality loss because activations have those troublesome outliers.
- **KV cache quantization** — quantize the KV cache itself (e.g. to INT8/FP8). Since the KV cache often caps batch size, shrinking it lets you fit *more concurrent requests* or longer contexts — a direct throughput win, connecting quantization to the batching story.

Recognizing these as separate decisions matters: weight-only 4-bit for memory, activation quantization for prefill compute, KV cache quantization for concurrency — you can mix them.

## Using quantization well

Quantization is one of the highest-return serving optimizations, but it needs judgment:

- **Start with INT8 or a good 4-bit (GPTQ/AWQ) and measure quality on *your* tasks.** Aggregate benchmarks can hide degradation that shows up on your specific workload; evaluate before and after on real evaluation data (the discipline from the AI production and RAG series).
- **Prefer proven methods over naive rounding.** The gap between AWQ/GPTQ 4-bit and naive 4-bit is the difference between "indistinguishable" and "noticeably worse."
- **Match the target to the bottleneck.** Weight-only for memory/decode; KV cache quantization to raise batch size; activation quantization when prefill compute dominates.
- **Watch for task-specific sensitivity.** Reasoning, code, and math tasks can be more sensitive to precision loss than casual chat — test the capabilities you actually rely on.
- **Combine with the rest of the stack.** Quantization frees memory that becomes more KV cache → larger batches → higher throughput; the optimizations compound.

Quantization is the lever that makes large models affordable to serve, and — because inference is memory-bound — one of the few that improves cost, memory, *and* speed together. The next post covers a different kind of speedup that attacks decode's sequential nature head-on: speculative decoding.

## Key takeaways

- Quantization stores weights in fewer bits (INT8 halves, INT4 quarters the size vs FP16); because decode is memory-bandwidth-bound, smaller weights mean less memory, faster generation, and lower cost — improving all three at once.
- The trade-off is precision vs. quality, and it's non-linear: INT8 is often near-lossless, 4-bit is the popular sweet spot with good methods, and below 4-bit gets risky — largely because a few outlier weights matter disproportionately.
- Post-training quantization (PTQ) — GPTQ, AWQ, GGUF — quantizes a trained model cheaply and is the serving default; quantization-aware training (QAT) costs a training run but achieves better quality at very low bit-widths.
- There are three targets: weight-only (most memory benefit, least risk, ideal for decode), weight+activation (enables low-precision compute for prefill, more sensitive), and KV cache quantization (shrinks per-request cache → more concurrency/longer context).
- Use it with judgment: prefer proven methods over naive rounding, match the target to your bottleneck, and always measure quality on your own tasks (reasoning/code/math are more sensitive) — the benefits compound with batching by freeing memory for more KV cache.

## Further reading

- [Hugging Face — Quantization overview](https://huggingface.co/docs/transformers/main/en/quantization/overview)
- [Batching and throughput (previous post)](/blog/posts/llmserve-03-batching-and-throughput.html)
- [On-device and edge AI depends heavily on quantization — AI Cost Optimization series](/blog/series/ai-cost-optimization/)
