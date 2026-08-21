# The Constraints of the Edge

*A phone is not a small server — it's a fundamentally different environment with four hard limits a data center never imposes: a tight memory budget, modest and heterogeneous compute, a battery that your model drains, and a thermal ceiling that throttles you when you push it. Every on-device AI decision is a negotiation with these four.*

The previous post made the case for on-device AI. This one is the reality check: *why* it's hard. Running a model on a phone means operating inside constraints that simply don't exist on the cloud GPU it was designed for. Understanding these four constraints — memory, compute, battery, and thermal — is what lets you choose a model, quantization level, and runtime that actually work on real devices instead of only in the demo on your high-end phone.

## Memory: the first and hardest wall

The tightest constraint is **RAM**. A cloud server has tens or hundreds of gigabytes; a phone has a handful, and your app gets only a *slice* of it — the OS, the system, and every other app are competing for the same pool, and mobile operating systems will **kill your app** without ceremony if it uses too much.

This has direct consequences for what model you can run:

- **The model must fit in your memory budget, not the device's total RAM.** A model that needs 6 GB won't run reliably on a device where your app realistically gets 2–3 GB, even if the phone has 8 GB total. You budget against your *slice*, and against the low end of your target devices, not the flagship.
- **The KV cache adds to it.** As covered in the LLM serving series, generation needs a KV cache that grows with context length — that's *additional* memory on top of the weights, so long conversations cost more RAM, and you must bound context accordingly.
- **Loading is a spike.** Getting a model into memory can momentarily use more than steady-state, and on constrained devices that spike can trigger an out-of-memory kill.

Memory is why **quantization is mandatory** on-device (the next post): it's the primary lever for making a model fit at all. The practical rule is to pick the largest model whose quantized weights *plus* a reasonable KV cache fit comfortably within the app's realistic memory slice on your *lowest-end* target device — then test that it doesn't get killed under real conditions.

## Compute: modest and heterogeneous

A phone's processors are far less powerful than a data-center GPU, and — unlike the cloud's uniform hardware — wildly **heterogeneous** across devices. Your app runs on last year's flagship and a three-year-old budget phone, with completely different performance. This shapes on-device inference in two ways.

First, **which processor runs the model matters**, and phones have several:

- **CPU** — always available, universally compatible, but slowest for model inference. A safe fallback.
- **GPU** — much faster for the parallel math of inference, available on most modern phones, and the common target for on-device LLMs.
- **NPU / accelerators** — dedicated neural processing units (Apple Neural Engine, Android NPUs) that are fastest and most power-efficient, but the most fragmented — availability and API support vary by device and OS.

A good on-device runtime abstracts this, using the best available accelerator and falling back gracefully — but you must expect a spread of performance and design for the slow end.

Second, **generation speed will be modest** compared to the cloud. On-device token generation is measured in a handful to some tens of tokens per second depending on model and hardware — usable for many features, but slow enough that you design the UX around it (stream tokens, keep outputs concise, avoid making users wait on long generations). Don't assume cloud-like speed; design for what a mid-range phone actually delivers.

## Battery: your model spends the user's power

On a server, energy is the operator's cost. On a phone, energy is the *user's battery*, and a feature that drains it fast will be uninstalled no matter how clever it is. LLM inference is computationally intensive and therefore **power-hungry** — sustained generation, especially on the GPU/NPU, measurably consumes battery.

The design implications:

- **Inference should be intermittent, not constant.** A model invoked on demand for a user action is fine; a model running continuously in the background is a battery disaster.
- **Efficiency compounds.** Smaller, quantized models and efficient accelerators (NPU over CPU) use less energy per token — quantization helps battery, not just memory.
- **Respect the platform.** Background execution limits exist partly to protect battery; heavy on-device AI belongs in the foreground, tied to user intent.

Battery is easy to forget in development (your test phone is plugged in) and impossible for users to forgive. Measure energy impact on a real device on battery, under realistic use.

## Thermal: the ceiling that throttles you

The subtlest constraint is **heat**. Sustained heavy computation makes a phone hot, and to protect itself the device **thermally throttles** — deliberately slowing its processors to cool down. This creates a failure mode absent from benchmarks:

- **Performance degrades over time under sustained load.** Your model might generate quickly for the first minute, then slow noticeably as the device heats up and throttles. A benchmark of a single short generation looks great; a real session of repeated use tells a different story.
- **Small/budget devices throttle sooner** — less thermal mass and cheaper cooling.

The lesson is to test *sustained*, repeated inference, not just a cold-start single run, and to keep workloads short and spaced enough that the device doesn't cook itself into throttling. Thermal is why the honest performance number is "tokens per second during extended real use," not "peak tokens per second on the first try."

## Designing within the four constraints

These constraints interlock, and the good news is that the same moves help all of them:

- **Right-size and quantize the model.** A smaller, quantized model uses less memory, less compute, less energy, and generates less heat — it's the single highest-leverage decision, improving all four constraints at once (hence the next post).
- **Budget for the low end.** Choose the model and settings that work on your *weakest* target device on battery under sustained use — not your dev phone plugged in.
- **Bound context length.** Long contexts inflate the KV cache (memory) and per-token compute (speed, battery, heat); keep context as short as the task allows.
- **Make inference on-demand and foregrounded.** Tie it to user intent, stream output, and keep generations concise to respect battery and thermal limits.
- **Use the best available accelerator with graceful fallback,** and let the runtime handle the heterogeneity.

The edge is a harder environment than the cloud, but a *predictable* one: memory, compute, battery, and thermal are the whole story. Design against all four — on real, low-end devices — and on-device AI is entirely practical. The next post covers the tool that makes fitting within these limits possible: quantization for the edge.

## Key takeaways

- On-device AI operates within four hard constraints absent from the cloud: memory, compute, battery, and thermal — every decision is a negotiation with these four.
- Memory is the tightest wall: you budget against your app's *slice* of RAM on your *lowest-end* target device (not total RAM), including the KV cache — and the OS kills apps that overrun, which is why quantization is mandatory.
- Compute is modest and heterogeneous: phones have CPU (slow/universal), GPU (fast/common), and NPU (fastest/most fragmented); a good runtime picks the best with fallback, but generation is measured in tens of tokens/sec — design the UX around that.
- Battery is the user's, not yours: LLM inference is power-hungry, so keep it intermittent and on-demand, prefer efficient accelerators and small models, and measure energy on a real device on battery.
- Thermal throttling degrades performance under *sustained* load (and sooner on budget devices), so test repeated real-use inference, not a cold single run — and the same move (right-size + quantize) improves all four constraints at once.

## Further reading

- [Google AI Edge — on-device inference](https://ai.google.dev/edge)
- [Why on-device AI? (previous post)](/blog/posts/edgeai-01-why-on-device-ai.html)
- [LLM Inference and Serving series — the KV cache and quantization in depth](/blog/series/llm-inference-and-serving/)
