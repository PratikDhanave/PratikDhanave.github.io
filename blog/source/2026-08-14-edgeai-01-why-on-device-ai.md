# Why On-Device AI?

*For a decade the default answer to "where does the AI run?" was "someone else's GPU, over the network." On-device AI flips that: the model runs on the phone in the user's hand, and once you internalize what that changes — privacy, offline capability, latency, and cost all at once — a whole class of apps becomes possible that a cloud API can't build.*

Most AI applications send the user's data to a server, run a model there, and send the answer back. That works, but it carries assumptions — a network connection, a per-request bill, and the user's data leaving their device — that aren't always acceptable. **On-device AI** (edge AI) runs the model *locally*, on the phone, tablet, or laptop itself. This series is about building that with **Gemma** (Google's open model family) and **Flutter**, and it starts with the question that justifies all the constraints ahead: why run AI on-device at all?

## The four reasons, and why they compound

On-device AI is worth its real difficulties because it delivers four benefits *simultaneously* — and it's the combination, not any single one, that makes it compelling:

- **Privacy** — the user's data never leaves their device. There's no server to send a photo, a journal entry, a medical note, or a bank balance to, because inference happens locally. For sensitive domains this isn't a feature, it's the whole point: you can't leak what you never transmit.
- **Offline** — the app works with no network at all. On a plane, in a tunnel, in a rural area, or in a country with unreliable connectivity, a cloud-dependent AI feature is simply broken; an on-device one keeps working.
- **Latency** — no network round-trip. There's no request to a data center and back, so responses can start immediately. For interactive features, eliminating network latency and queueing can make the difference between "sluggish" and "instant."
- **Cost** — no per-request inference bill. The computation runs on hardware the *user* already owns and paid for, so serving a million requests costs you nothing in inference fees. This changes the economics of AI features entirely — they become free to run at scale.

The reason to notice the *combination* is that each addresses a different failure mode of cloud AI, and many real products need several at once. A personal finance app needs privacy *and* wants zero per-user inference cost. A field tool needs offline *and* low latency. When two or more of these matter, on-device stops being an optimization and becomes the right architecture.

## The local-first philosophy

On-device AI is the AI expression of a broader idea: **local-first software**, where the user's data and the app's core functionality live on their device rather than on a server, with the cloud as an optional enhancement rather than a requirement. Local-first apps are private by construction, work offline, respond instantly, and don't hold the user hostage to a service staying online or a subscription staying paid.

This philosophy fits a specific and growing class of applications especially well:

- **Personal and sensitive data** — finance, health, journaling, notes — where sending data to a server is a liability users increasingly reject.
- **Always-available utilities** — tools that must work regardless of connectivity.
- **High-volume, low-margin features** — where per-request cloud inference costs would sink the business model, but on-device inference is free.

If you're building an app where the user's data is the product and their trust is the moat, local-first with on-device AI aligns the architecture with the promise: *we can't misuse your data because we never receive it.* That's a claim a cloud app can only ask users to believe; a local-first app can prove it.

## What you give up

Honesty requires naming the trade-off, because on-device AI is not free — it exchanges cloud's problems for edge's constraints, the subject of the next post:

- **Smaller models.** A phone can't run a frontier-scale model; you run a small model (a few billion parameters, quantized). The gap has narrowed dramatically — small models are far more capable than they were — but a local model is not a giant cloud model, and you must design for its ceiling.
- **Device resources are finite and shared.** Memory, compute, battery, and thermal budget are limited and shared with every other app; a heavy model can drain battery or make the device hot.
- **You ship the model.** Model files are large, so you must get them onto the device (bundled or downloaded), which affects app size and first-run experience.
- **Harder to update and observe.** A cloud model updates instantly for everyone; an on-device model updates only when the user updates the app or re-downloads it, and you can't watch it run on the user's device (which is also *why* it's private).

The engineering craft of on-device AI is getting the four benefits while managing these four costs — and the rest of the series is exactly that craft.

## When to choose on-device (and when not)

On-device AI is the right call when the benefits align with your product's needs — but it's not universal, and choosing it dogmatically is as wrong as ignoring it:

- **Choose on-device** when privacy is paramount, offline operation is required, per-request cost must be zero, or low latency for a modest-sized model matters — and when a small model is *capable enough* for the task.
- **Choose cloud** when you need a frontier-scale model's capability, the task is too heavy for a phone, you need instant model updates, or the data isn't sensitive and connectivity is assumed.
- **Choose hybrid** — increasingly the sophisticated answer — where on-device handles the common, private, latency-sensitive cases and the cloud handles the rare hard ones. A later post returns to designing this split.

The decision is the same requirements-driven trade-off analysis as any architecture choice (the [AI Architecture Decisions](/blog/series/ai-architecture-decisions/) series' method applies): match the tool to the constraints. On-device AI has simply become a *viable* option it wasn't a few years ago — small models got good, and the runtimes to execute them on phones matured.

## Where the series goes

From here the series is practical: the constraints of the edge (what makes phones different from servers), quantization (how you make a model fit), the on-device runtime (how inference actually executes on phone hardware), running Gemma on Flutter (the concrete code), on-device RAG and memory (retrieval without a server), privacy and local-first design (the architecture), and shipping (model delivery, app size, updates). Throughout, the concrete stack is Gemma + Flutter, but the principles transfer to any on-device model and framework. The goal by the end: build a private, offline-capable, zero-inference-cost AI feature that runs entirely in the user's hand.

## Key takeaways

- On-device (edge) AI runs the model locally on the user's device instead of a server, delivering privacy (data never leaves the device), offline operation, low latency (no network round-trip), and zero per-request inference cost — all at once.
- The value is the *combination*: each benefit addresses a different failure mode of cloud AI, and many real products (personal finance, health, offline tools, high-volume features) need two or more simultaneously.
- It's the AI form of local-first software — private by construction, offline-capable, instant, not dependent on a service or subscription — ideal when the user's data is sensitive and their trust is the moat (you can prove privacy, not just promise it).
- The trade-offs are real: smaller (quantized) models, finite/shared device resources (memory, battery, thermal), shipping large model files, and harder updates/observability — the craft is getting the benefits while managing these costs.
- Choose on-device when privacy/offline/cost/latency align and a small model suffices; choose cloud for frontier capability or instant updates; increasingly, choose hybrid (on-device for common private cases, cloud for rare hard ones).

## Further reading

- [Google AI — Gemma open models](https://ai.google.dev/gemma)
- [flutter_gemma — on-device LLMs for Flutter](https://pub.dev/packages/flutter_gemma)
- [AI Architecture Decisions series](/blog/series/ai-architecture-decisions/)
