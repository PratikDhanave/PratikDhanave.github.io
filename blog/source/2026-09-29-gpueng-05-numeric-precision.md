# Numeric Precision — Why Lower Precision Makes Inference Faster

*The fastest way to speed up LLM inference is often not a better algorithm but fewer bits per number. Precision — how many bits represent each weight and activation — is a direct lever on both of the limits this series has built up: it halves or quarters the data you move (bandwidth, post 2) and unlocks the GPU's fastest arithmetic units (compute, post 3). Understanding floating-point formats is understanding why fp16, bf16, and int8 are everywhere in modern inference.*

Post 2 said LLM decoding is memory-bound because every token reads the whole model from HBM. The most direct attack on that is to make the model *physically smaller in bits* — and that's what reduced precision does. This post explains the number formats a GPU uses, the trade-off between range and precision, and why lower precision is a double win (less data to move *and* faster math) that costs surprisingly little accuracy.

## How a floating-point number spends its bits

A floating-point number splits its bits into two jobs: the **exponent** (how big the number can be — its *range*) and the **mantissa** (how finely it's resolved — its *precision*). The standard formats trade these differently:

- **FP32** (single precision, 32 bits) — 8 exponent + 23 mantissa bits. The traditional default: wide range, fine precision. Accurate but twice the memory and (on tensor cores) slower than the 16-bit formats.
- **FP16** (half precision, 16 bits) — 5 exponent + 10 mantissa. Half the bytes, but its *narrow range* (only 5 exponent bits) means large or tiny values overflow/underflow — a real hazard in training, less so in inference.
- **BF16** (bfloat16, 16 bits) — 8 exponent + 7 mantissa. The key insight: keep FP32's *full exponent range* but sacrifice mantissa precision. This makes it a near drop-in for FP32's dynamic range at half the size, which is why it became the workhorse for modern models — you rarely overflow, you just carry fewer significant digits.
- **INT8 / INT4** — 8- or 4-bit integers, used via *quantization* (below). A quarter or an eighth of FP32's size.

The theme: **range and precision are separate budgets**, and for neural networks — which tolerate noise well but can have occasional large values — spending bits on range (bf16) often matters more than spending them on precision. That empirical fact is the whole reason 16-bit and 8-bit inference works.

## Why fewer bits is a double win

Reducing precision attacks *both* roofline ceilings at once, which is what makes it so effective:

1. **Less data to move (the bandwidth win).** Going FP32 → FP16/BF16 halves the bytes of every weight; going to INT8 quarters them. Since decode is memory-bound and reads the whole model per token (post 2), halving the weights roughly *doubles* decode throughput — the single biggest, cheapest speedup available. It also halves capacity, so the model fits on smaller/fewer GPUs.
2. **Faster arithmetic (the compute win).** Tensor cores (post 1) run lower-precision matrix multiplies at much higher throughput — 16-bit is typically 2× FP32, and 8-bit faster still. So the compute-bound prefill phase speeds up too.

Both wins come from the same change, which is why "just use bf16" is the first and highest-leverage optimization for almost any model. There's no algorithmic cleverness — you're moving and crunching fewer bits.

## Quantization: pushing below 16 bits

Going below 16 bits means leaving floating-point for integers, via **quantization** — mapping a range of float values onto a small set of integers using a scale factor (and sometimes a zero-point). INT8 quantization stores weights as 8-bit integers plus a scale, dequantizing on the fly. The remarkable empirical result is that LLMs tolerate this well: with care, INT8 (and increasingly INT4) weights preserve nearly all of a model's quality while cutting memory 4–8× versus FP32.

The craft is in *where and how* you quantize, because precision loss isn't uniform:
- **Weight-only quantization** (compress the weights, compute in higher precision) is the easy win for memory-bound decode — it shrinks the thing you stream from HBM.
- **A few outlier values dominate the error**, so good schemes isolate or scale them specially rather than quantizing everything uniformly — this is why modern quantization methods are more than "round to 8 bits."
- **Too aggressive** (naive INT4 everywhere) can degrade quality noticeably, so quantization is always a measured trade-off: check output quality, don't assume it's free.

The serving series covers quantization from the operational angle; here the point is the physics — fewer bits means less HBM traffic per token, which for memory-bound inference translates almost directly into speed. Precision is the knob that sits right on top of this series' two fundamental limits.

The takeaway: a floating-point number splits bits between **exponent (range)** and **mantissa (precision)**, and the formats trade them — **FP32** (accurate, big, slower), **FP16** (half-size but narrow range), **BF16** (half-size keeping FP32's full range, sacrificing mantissa — the modern workhorse), and **INT8/INT4** via quantization (¼–⅛ the size). Lower precision is a *double win*: it halves/quarters the bytes streamed from HBM (huge for memory-bound decode — roughly doubling throughput per halving) *and* runs faster on tensor cores (helping compute-bound prefill). **Quantization** pushes below 16 bits by mapping floats to integers with a scale; LLMs tolerate it remarkably well, especially *weight-only* schemes that handle outliers carefully — but it's a measured trade-off, not free.

## Key takeaways

- A float spends bits on **exponent (range)** and **mantissa (precision)** — separate budgets. **FP32** (8+23) is the accurate default; **FP16** (5+10) halves size but has narrow range (overflow risk); **BF16** (8+7) keeps FP32's *full range* at half size (the modern workhorse); **INT8/INT4** go ¼–⅛ size via quantization.
- For neural nets, spending bits on **range** (bf16) usually matters more than precision — they tolerate noise but hit occasional large values — which is why 16-bit and 8-bit inference works at all.
- Lower precision is a **double win**: *less data moved* (FP32→FP16 halves weights → ~2× memory-bound decode throughput; also halves capacity) **and** *faster math* (tensor cores run 16-bit ~2× FP32, 8-bit faster) — so "just use bf16" is the highest-leverage first optimization.
- **Quantization** maps float ranges to integers via a scale (+zero-point); LLMs preserve near-full quality at INT8/INT4, cutting memory 4–8×. **Weight-only** quantization is the easy win for memory-bound decode.
- Precision loss isn't uniform — **a few outliers dominate the error**, so good schemes handle them specially, and overly aggressive quantization degrades quality: always *measure* output quality rather than assuming it's free.

## Further reading

- [Half-precision floating-point format (FP16) — 16-bit floats](https://en.wikipedia.org/wiki/Half-precision_floating-point_format)
- [bfloat16 floating-point format — full range, reduced precision](https://en.wikipedia.org/wiki/Bfloat16_floating-point_format)
