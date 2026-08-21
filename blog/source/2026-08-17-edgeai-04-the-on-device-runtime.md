# The On-Device Runtime

*Between your quantized model file and a running feature sits the runtime — the engine that loads the model, maps it onto the phone's CPU, GPU, or NPU, and turns tokens into text. You rarely write inference math yourself; you pick a runtime and let it handle the brutal complexity of executing a neural network across thousands of different devices.*

The last posts got you a quantized model that *fits*. Now something has to *run* it on the phone's hardware — and that's the **on-device runtime**. This is the edge equivalent of the serving engines from the LLM Inference series, but solving a harder problem: not "how do I serve many users on one GPU," but "how do I run this model efficiently on an enormous, fragmented population of devices with wildly different processors." This post explains what the runtime does and the main options for Gemma on Flutter.

## What the runtime does

A runtime is the layer that takes a model file and executes inference on the device's hardware. Its job is substantial and not something you'd reimplement:

- **Load the model** — read the quantized weights into memory in the runtime's expected format, efficiently and without a fatal memory spike.
- **Map computation onto hardware** — decide whether to run on CPU, GPU, or NPU, and translate the model's operations into calls that hardware understands (via the device's ML/graphics APIs).
- **Manage the KV cache and generation loop** — run the autoregressive decode loop (from the serving series) on-device, maintaining the KV cache within the memory budget.
- **Expose a simple API** — hide all of the above behind "give me a prompt, stream me tokens."
- **Handle heterogeneity gracefully** — use the best accelerator available on *this* device and fall back when a feature or chip isn't present.

That last point is the hardest and most valuable thing a runtime does. From the edge-constraints post, devices vary enormously; a good runtime abstracts that so your app code is the same whether it lands on a flagship with a powerful NPU or a budget phone falling back to CPU. Writing that abstraction yourself, per platform, would be a project larger than your actual app.

## Hardware acceleration on a phone

The runtime's central performance decision is *which processor runs the model*, and it maps the model's math onto the device's ML acceleration APIs. Conceptually:

```text
   your quantized model
          │
   ┌──────▼───────┐   picks the best available backend
   │   runtime    │──────────────┬───────────────┬───────────────┐
   └──────────────┘              ▼               ▼               ▼
                               CPU             GPU             NPU
                          (universal,     (fast, most     (fastest &
                           slow)          modern phones)   efficient,
                                                           most fragmented)
```

The trade-offs from the constraints post drive this: the **GPU** is the common target for on-device LLMs (fast, widely available), the **NPU** is fastest and most power-efficient but the most fragmented across devices and OSes, and the **CPU** is the universal fallback that always works but is slowest. A mature runtime tries the best option and degrades gracefully, so your feature runs *everywhere* even if it runs *faster* on better hardware. You generally let the runtime make this choice, optionally hinting a preference.

## The Gemma-on-Flutter runtimes

For this series' stack — Gemma on Flutter — there are two runtimes to know, because they cover different platforms and model formats. The `flutter_gemma` plugin wraps them behind a Flutter-friendly API.

- **MediaPipe LLM Inference** — Google's on-device LLM runtime for **mobile and web** (Android, iOS, web). It executes the `.task`/`.bin` quantized models from the quantization post, using GPU acceleration where available. In `flutter_gemma`, this is the engine you'll use for the mobile app case, provided via the MediaPipe engine package. It's purpose-built for running models like Gemma on phones and is the primary path for a Flutter mobile on-device LLM.
- **LiteRT / LiteRT-LM** — Google AI Edge's runtime (LiteRT, the successor to TensorFlow Lite), used by `flutter_gemma` for the **desktop** path with LiteRT-LM (`.litertlm`) models. It's a different runtime and format from the mobile MediaPipe path — and, importantly, the mobile `.task` models are *not* compatible with the desktop LiteRT path, so cross-platform apps account for both.

The practical takeaway: `flutter_gemma` gives you one plugin, but under it are platform-specific runtimes and model formats. For a mobile-first app (the common case, and the fit for privacy-sensitive phone apps) you'll target the MediaPipe engine with a `.task` Gemma model; if you also ship desktop, you'll add the LiteRT-LM path with its own model file. The next post gets concrete with the `flutter_gemma` API itself.

## Where the runtime fits in your app

It helps to see the layers between your Flutter UI and the silicon:

```text
   Flutter UI / app logic  (Dart)
          │
   flutter_gemma plugin    (Dart API: load model, chat, stream tokens)
          │
   platform runtime        (MediaPipe LLM Inference on mobile/web;
          │                 LiteRT-LM on desktop)
          │
   hardware acceleration   (GPU / NPU / CPU via device ML APIs)
          │
   the phone's silicon
```

Your code lives at the top two layers — Flutter UI and the `flutter_gemma` Dart API. Everything below is the runtime's responsibility, which is exactly the point: **the runtime is what lets a Flutter developer ship on-device AI without becoming a mobile-ML-systems engineer.** You focus on the model choice, the prompts, the UX, and the app; the runtime handles loading, hardware mapping, the generation loop, and device heterogeneity.

## Choosing and using a runtime

- **Use the platform's proven runtime; don't build inference yourself.** MediaPipe LLM Inference (mobile/web) and LiteRT (desktop) exist precisely so you don't have to write per-device inference — reach for them via `flutter_gemma`.
- **Match runtime to platform and model format.** `.task`/MediaPipe for mobile/web; LiteRT-LM for desktop. Choose them together with your model file (from the quantization post).
- **Let the runtime pick the accelerator, with graceful fallback.** Target GPU where available, accept CPU fallback on weaker devices — and test on both so the fallback path is actually acceptable.
- **Plan for both paths if you go cross-platform.** Mobile and desktop use different runtimes/formats; a truly cross-platform on-device app ships more than one model file.

With a model that fits and a runtime to run it, you're ready to write code. The next post builds an actual Gemma feature in Flutter with `flutter_gemma`.

## Key takeaways

- The on-device runtime is the engine that loads your quantized model, maps its computation onto the phone's CPU/GPU/NPU, runs the generation loop and KV cache, and exposes a simple prompt→tokens API — you pick a runtime rather than writing inference yourself.
- Its hardest, most valuable job is handling device heterogeneity: using the best available accelerator (GPU commonly, NPU fastest but fragmented, CPU universal fallback) so your app runs everywhere even if faster on better hardware.
- For Gemma on Flutter there are two runtimes: MediaPipe LLM Inference for mobile/web (runs `.task`/`.bin` models, the primary mobile path) and LiteRT/LiteRT-LM for desktop (`.litertlm`) — different runtimes and incompatible model formats across the mobile/desktop boundary.
- `flutter_gemma` wraps these behind one Dart API, so your code stays at the Flutter/plugin layer while the runtime handles loading, hardware mapping, generation, and heterogeneity — letting a Flutter dev ship on-device AI without being a mobile-ML engineer.
- Use the proven platform runtime, match it to your platform and model format, let it pick the accelerator with graceful fallback (test both paths), and plan for multiple model files if shipping cross-platform.

## Further reading

- [Google AI Edge — LLM Inference (MediaPipe)](https://ai.google.dev/edge/mediapipe/solutions/genai/llm_inference)
- [flutter_gemma — on-device LLMs for Flutter](https://pub.dev/packages/flutter_gemma)
- [Quantization for the edge (previous post)](/blog/posts/edgeai-03-quantization-for-the-edge.html)
