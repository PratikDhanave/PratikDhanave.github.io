# Making Models Fit: Quantization for the Edge

*On the cloud, quantization is an optimization you reach for to cut costs. On a phone, it's the difference between the model running and not running at all. Nearly every on-device LLM you'll ever ship is quantized, because full-precision weights simply don't fit — so understanding the bit-width trade-off is non-negotiable for edge AI.*

The last post established that memory is the tightest edge constraint and named quantization as the primary way to fit within it. This post goes deeper on quantization *specifically for on-device* — why it's mandatory rather than optional, what bit-widths mean for a phone, the formats you'll actually encounter (`.task`, GGUF, LiteRT), and how to choose. The LLM serving series covered quantization for cloud throughput; here the lens is *fitting on the device at all*.

## Why quantization is mandatory on-device

Recall the memory math: a model's weight memory is roughly parameters × bytes-per-parameter. In full precision (FP16, 2 bytes), even a "small" model is large:

- A 2-billion-parameter model in FP16 ≈ 4 GB of weights — already too much for many phones' app memory budgets.
- The same model quantized to 4-bit (~0.5 bytes) ≈ 1 GB — comfortably runnable on a wide range of devices.

That roughly 4× reduction is what turns "won't fit / gets killed by the OS" into "runs smoothly." And from the edge-constraints post, quantization doesn't only help memory — smaller weights mean less data to move (faster generation on memory-bound decode), less energy per token (battery), and less heat (thermal). It improves *all four* edge constraints at once, which is why it's the first and most important edge decision. On-device, you essentially never ship full-precision weights; the only question is *how aggressively* you quantize.

## The bit-width trade-off, edge edition

The precision-vs-quality trade-off from the serving series applies, but the calculus shifts on-device because your *ceiling* is lower and your *pressure* to compress is higher:

- **8-bit (INT8)** — halves size vs FP16 with typically small quality loss. A conservative choice when memory allows and quality is paramount, but often still too large for the smallest devices.
- **4-bit (INT4)** — quarters size; the **workhorse of on-device LLMs**. With good quantization methods the quality loss is modest, and the memory savings are what make phone-sized deployment feasible. This is the default you'll reach for most often.
- **Below 4-bit (3-bit, 2-bit)** — squeezes further for the most constrained devices, but quality degradation becomes real and model-dependent; use only when you've verified the smaller footprint is worth it for your task.

The edge-specific reality: you're often choosing between *a more capable model quantized harder* versus *a smaller model quantized less*. A larger model at 4-bit frequently beats a tiny model at 8-bit for the same memory budget — but not always, and it depends on your task. This is a real experiment to run, not a rule to assume: for a given memory budget, compare a few (model size, bit-width) combinations on your actual workload.

## Models built for the edge

An important development makes this easier: model families now include variants *designed* for on-device use rather than just shrunk cloud models. Google's **Gemma** family, this series' focus, includes small open models suited to local deployment, and Google has released variants specifically engineered for efficient on-device and mobile execution (with multimodal capability). Choosing a model that was built and optimized for the edge — rather than aggressively quantizing a model designed for servers — often gives better quality at a given footprint, because the model and its quantization were co-designed. When picking an on-device model, prefer families with explicit edge/mobile variants and official quantized releases.

## The formats you'll actually encounter

On-device quantized models come in specific file formats tied to their runtimes, and knowing them prevents confusion when you go to load one:

- **`.task` / `.bin` (MediaPipe)** — the formats used by Google's **MediaPipe LLM Inference** runtime, which is the mobile/web engine behind `flutter_gemma`. A `.task` bundle packages the quantized model for on-device execution on Android, iOS, and web. This is what you'll most often use with Gemma on Flutter mobile.
- **GGUF (llama.cpp)** — the widely-used format from the llama.cpp ecosystem, with a range of quantization presets (various 4-bit and other levels). Ubiquitous for running quantized open models across platforms, especially CPU and desktop.
- **LiteRT / `.litertlm`** — Google AI Edge's runtime format (LiteRT, formerly TensorFlow Lite); the `flutter_gemma` desktop path uses LiteRT-LM. Different runtime, different file type from the mobile `.task` models — they are not interchangeable across the mobile/desktop boundary.

The practical point: the model file format is coupled to the runtime that executes it, so you choose them together. For Gemma + Flutter on mobile you'll typically use a quantized `.task` model with the MediaPipe engine; the next posts on the runtime and `flutter_gemma` make this concrete. Get the format wrong for your target platform and the model simply won't load.

## Choosing quantization for your app

- **Start at 4-bit and validate on your task.** It's the on-device default; measure quality on *your* real workload (the eval discipline from the production and RAG series), because aggregate benchmarks hide task-specific degradation — and reasoning/code/math are more precision-sensitive than casual chat.
- **Prefer official quantized releases and edge-designed models.** A Gemma variant built for on-device with an official quantized `.task` release beats hand-quantizing a server model.
- **Match the (model size, bit-width) pair to your lowest-end device's memory budget** — remember to leave room for the KV cache and the loading spike, and test that the OS doesn't kill the app.
- **Choose the format for your platform/runtime** — `.task` for MediaPipe on mobile/web, LiteRT for desktop, GGUF in the llama.cpp ecosystem — and don't mix them across incompatible targets.
- **Consider going smaller before going lower.** If 4-bit of your chosen model doesn't fit, a smaller *model* at 4-bit is often better quality than the same model at 2-bit.

Quantization is the enabling technology of on-device AI — without it, phone-sized LLMs wouldn't exist. With a 4-bit, edge-designed model in the right format, you have something that fits. Next: the runtime that actually executes it on the phone's hardware.

## Key takeaways

- On-device, quantization is mandatory, not optional: full-precision weights (e.g. a 2B model ≈ 4 GB at FP16) don't fit in a phone's app memory budget, but 4-bit (~1 GB) does — and it improves memory, speed, battery, and thermal all at once.
- 4-bit (INT4) is the on-device workhorse (best footprint/quality balance for phones); 8-bit is more conservative when memory allows; below 4-bit squeezes further at real quality cost — and a larger model quantized harder often beats a tiny model quantized less for the same budget (test it).
- Prefer models designed for the edge (like Gemma's on-device variants) with official quantized releases over aggressively quantizing server models — co-designed model+quantization gives better quality per byte.
- Formats are coupled to runtimes: `.task`/`.bin` for MediaPipe (mobile/web, the flutter_gemma default), GGUF for the llama.cpp ecosystem, LiteRT/`.litertlm` for desktop — choose model and format together for your target platform.
- Choose by starting at 4-bit, validating quality on your real task, matching the (size, bit-width) pair to your lowest-end device's memory (leaving room for KV cache + load spike), and going to a smaller model before going below 4-bit.

## Further reading

- [Google AI Edge — LLM Inference (MediaPipe)](https://ai.google.dev/edge/mediapipe/solutions/genai/llm_inference)
- [The constraints of the edge (previous post)](/blog/posts/edgeai-02-constraints-of-the-edge.html)
- [LLM Inference and Serving: Quantization](/blog/posts/llmserve-04-quantization.html)
