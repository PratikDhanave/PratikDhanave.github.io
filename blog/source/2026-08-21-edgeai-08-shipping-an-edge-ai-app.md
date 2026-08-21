# Shipping an Edge-AI App

*The demo runs on your phone; now you have to get it running on thousands of phones you'll never touch. Shipping on-device AI has its own hard problems — a model file too big to bundle, first-run downloads, a fleet of wildly different devices, and updates you can't push instantly — and handling them is what separates a hackathon project from a product.*

Everything so far has been about making on-device AI *work*. This final post is about making it *ship*: delivering the model to devices, managing app size, testing across the device population, updating in the field, and knowing when the whole approach is the right call. These are the practical concerns that decide whether your edge-AI feature survives contact with real users — and they're where teams new to on-device AI get surprised.

## The model delivery problem

The first shipping problem is unique to on-device AI: **the model is a large file that has to get onto the device.** A quantized LLM is hundreds of megabytes to a few gigabytes — far larger than a normal app. You have two strategies, each with trade-offs:

- **Bundle the model in the app.** The model ships inside the app package, so it's available immediately on install with no network needed — the purest offline experience. The cost is a **huge app download size**: adding a multi-hundred-MB model to your app can push it past app-store size limits or warnings, and makes the initial install slow and data-heavy. Users on metered connections or low storage may balk.
- **Download the model on first run.** Ship a small app, then download the model when the user first opens it (or first uses the AI feature). This keeps the app download small, but introduces a **first-run experience problem**: the user waits for a large download before the feature works, needs connectivity at that moment (ironic for an offline feature), and you must handle interrupted/failed downloads, resumption, and storage checks.

The common, pragmatic choice is **download-on-first-run with careful UX**: a small app, a clear "setting up your private assistant…" flow with progress, resumable downloads, and a storage-space check before starting. Some apps offer a choice or download in the background after install. The key is to *design* the model-delivery experience deliberately — it's the user's first impression of the feature, and a silent multi-hundred-MB download or an opaque wait is a bad one.

## App size and storage

Beyond the download, the model *occupies storage* on the device permanently, which has consequences:

- **Respect the user's storage.** A multi-gigabyte model is a lot to ask of a budget phone that's already full. Be transparent about the space required, check availability before downloading, and consider letting users remove the model (and the feature) to reclaim space.
- **Ship one model, not many.** It's tempting to bundle multiple model sizes for different devices, but each adds storage/download cost; usually better to pick one right-sized model (or download the appropriate one for the device) than to carry several.
- **Account for the KV cache and working memory at runtime** (the constraints post) — storage is the file, but running the model also needs the RAM budget you planned for.

Storage and download size are real adoption barriers, not afterthoughts — a feature users won't install because it's too big is worse than a smaller model that ships.

## Testing across the device population

From the constraints post: devices are wildly heterogeneous, and this is a *testing* problem, not just a runtime one. The feature that runs beautifully on your flagship dev phone may be unusably slow, memory-killed, or thermally throttled on a three-year-old budget device — which is what a large share of your users actually carry.

- **Test on real, low-end, on-battery devices** — not just the simulator and your flagship. Performance, memory kills, and thermal throttling only show up on real constrained hardware under real conditions.
- **Test sustained use, not cold single runs** — thermal throttling degrades performance over a session (constraints post), so a realistic test is repeated inference over time, on battery.
- **Define a minimum supported device** — decide the floor below which you disable the on-device feature (or fall back), based on RAM and capability, rather than letting it fail badly on devices that can't handle it.
- **Verify graceful fallback** — the paths for "model won't load," "out of memory," and "device too weak" must actually work, because on a large device population, they *will* be exercised.

## Updating in the field

A cloud model updates instantly for everyone; an on-device model does not, and that changes your update strategy:

- **Model updates are downloads, not deploys.** To ship a better model, users must download the new file — so model updates carry the same size/UX concerns as first-run delivery, and you should version models and update them in the background with consent rather than forcing a large re-download at a bad moment.
- **Decouple model version from app version where possible.** If the model can be updated independently of an app-store release, you can improve the model without a full app update — but you must handle compatibility (a new model with an old app, or vice versa).
- **You can't observe inference in the field** — which is the flip side of privacy (post seven). You can't watch prompts and outputs on users' devices, so you rely on on-device evaluation before release and privacy-respecting, opt-in, aggregate signals (never user content) to know how the feature performs. Test thoroughly *before* shipping, because you can't hotfix a bad generation by watching logs.

## Knowing when on-device is the right call — a shipping checklist

Pulling the series together, on-device AI is a strong choice when the pieces line up, and shipping-readiness is the final gate:

- **Does a small, quantized model meet the quality bar** for your task, validated on real evaluation data? (If only a frontier model suffices, reconsider or go hybrid.)
- **Do the benefits justify it** — privacy, offline, latency, or zero per-request cost — enough to accept the constraints? (Post one's decision.)
- **Does it fit your lowest-end target device** — memory, and acceptable speed/battery/thermal under sustained real use? (Posts two/three.)
- **Is the model-delivery UX designed** — download size, first-run flow, storage — so adoption isn't blocked by a giant download?
- **Are privacy and the data path audited** — local inference, local storage, encrypted at rest, no incidental exfiltration, honest hybrid boundaries? (Post seven.)
- **Are fallback and updates handled** — graceful degradation on weak devices, and a field-update strategy for the model?

If those hold, on-device AI delivers something cloud AI can't: a private, offline-capable, zero-inference-cost intelligent feature that runs entirely in the user's hand. That's the whole series realized — and for the class of apps where the user's data is the product and their trust is the moat, it's not just a viable architecture, it's the right one.

## Key takeaways

- The model-delivery problem is unique to on-device AI: a large model file (hundreds of MB to GB) must get onto the device — bundle it (immediate, offline, but huge app size) or download on first run (small app, but a first-run wait needing connectivity); download-on-first-run with careful, resumable, progress-shown UX is the common pragmatic choice.
- The model permanently occupies storage: be transparent about space, check availability before downloading, let users reclaim space, and ship one right-sized model rather than several — download size and storage are real adoption barriers.
- Heterogeneity is a testing problem: test on real low-end, on-battery devices under sustained use (not just the flagship/simulator), define a minimum supported device with fallback below it, and verify the load-failure/OOM/weak-device paths actually work.
- On-device models update by download, not deploy: version models, update in the background with consent, decouple model from app version where possible, and — since you can't observe inference in the field (privacy's flip side) — evaluate thoroughly before release using opt-in aggregate signals, never user content.
- Ship on-device when a small quantized model meets the quality bar, the benefits justify the constraints, it fits your lowest-end device, the delivery UX is designed, the privacy/data path is audited, and fallback/updates are handled — then it delivers a private, offline, zero-cost feature cloud AI can't.

## Further reading

- [Privacy and local-first design (previous post)](/blog/posts/edgeai-07-privacy-and-local-first.html)
- [Why on-device AI? — start of the series](/blog/posts/edgeai-01-why-on-device-ai.html)
- [flutter_gemma — on-device LLMs for Flutter](https://pub.dev/packages/flutter_gemma)
