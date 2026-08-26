# What Multimodal AI Is

*For most of the deep-learning era, an AI model did one thing with one kind of data: this model classifies images, that one translates text, another transcribes speech. Multimodal AI breaks that separation. A single model can now look at an image and describe it, answer questions about a chart, generate a picture from a sentence, or transcribe and reason about audio — because it works across modalities rather than being confined to one. This shift, from single-modality specialists to models that bridge vision, language, audio, and more, is one of the most important developments in modern AI.*

This series is a practical, conceptual guide to **multimodal AI** — AI that works across multiple kinds of data (modalities): text, images, audio, video, and more. It's aimed at engineers who understand LLMs and want to understand how AI extends beyond text. This first post frames what multimodal AI is, what a "modality" means, why multimodal matters, and the core idea that makes it possible: representing different modalities in a shared space. It sets up the rest of the series, which goes deep on vision, cross-modal connection, generation, audio, video, and building with these models.

## Modalities and the single-modality past

A **modality** is a *type* or *form* of data — text, images, audio, video, and so on. Each modality is a different way information comes to us, with its own structure (text is sequences of tokens; images are grids of pixels; audio is waveforms over time). For most of deep learning's history, models were *single-modality* specialists:

- **One model, one modality, one task.** Historically, a model handled *one* kind of data for *one* kind of task: an image classifier took images and output labels; a translation model took text and output text; a speech recognizer took audio and output text. Each was built and trained separately for its modality and task, with architectures specialized to that data (convolutional networks for images, recurrent networks then transformers for text). The modalities were siloed.
- **The world isn't single-modality.** But real information and real tasks are *inherently multimodal* — a web page has text and images, a video has visuals and audio, understanding a scene combines what you see and read, and humans effortlessly integrate senses. Single-modality models couldn't do this: they couldn't relate an image to text, or reason across what they saw and heard. Bridging modalities required separate systems awkwardly stitched together.

Multimodal AI is the move *beyond* this single-modality past — toward models that work across *multiple* modalities, relating and integrating them the way real information and real understanding do. Understanding what a modality is, and how AI was long confined to one at a time, frames what's new: AI that crosses the modality boundaries it was previously trapped within.

## What multimodal AI is

**Multimodal AI** refers to models that can *process and/or generate multiple modalities* — working with combinations of text, images, audio, video, etc., rather than a single one. Concretely, multimodal models can do things single-modality models can't:

- **Understand across modalities.** A multimodal model can take an *image and text together* and reason about both — answering a question about an image (visual question answering), describing what's in a picture (captioning), reading a chart, or understanding a document with text and figures. It relates the modalities: connecting what's in the image to the words. This cross-modal *understanding* is a core multimodal capability.
- **Generate one modality from another.** Multimodal models can *translate between* modalities — generate an image from a text description (text-to-image), transcribe audio to text (speech recognition), describe an image in text, or generate speech from text. Crossing from one modality to another (especially text ↔ other modalities) is a defining multimodal ability.
- **Combine modalities in one model.** Increasingly, a *single* model handles many modalities — the modern multimodal LLMs that accept text, images, and audio as input and respond, unifying what used to be separate systems. The trend is toward general models that work across modalities natively, not narrow single-modality tools.

So multimodal AI is AI that works *across* modalities — understanding combinations of them, translating between them, and increasingly handling many in one model. It's what lets AI describe images, answer questions about visuals, generate pictures from text, transcribe and reason about audio, and more. This breadth is a major expansion of what AI can do, and it rests on one key idea.

## The key idea: a shared representation

How can a single model relate an *image* to *text*, or generate a *picture* from a *sentence*, when these are such different kinds of data? The core enabling idea of multimodal AI is representing different modalities in a *shared space*:

- **Everything becomes vectors (embeddings).** Modern AI represents data as *embeddings* — vectors in a high-dimensional space capturing meaning (as LLMs do for text). The key multimodal move is representing *different modalities* as embeddings in a *shared* space, so an image and the text describing it map to *nearby* points. Once different modalities live in a common representational space, the model can relate them — because "a photo of a dog" (text) and an actual photo of a dog (image) are close together in that space.
- **Shared space enables cross-modal operations.** With modalities in a shared space, cross-modal tasks become possible: to find images matching a text query, find image embeddings near the text's embedding; to generate an image from text, generate in a space connected to the text's meaning; to caption an image, map the image embedding to text. The shared representation is the bridge across modalities — the thing that makes relating and translating between them possible. (The next posts show how this is built — CLIP being the canonical example.)
- **Transformers made it feasible.** The transformer architecture (behind LLMs) turned out to be a general tool that works across modalities — images, audio, and text can all be turned into sequences of tokens/patches and processed by transformers, and represented in shared embedding spaces. This architectural generality is much of *why* multimodal AI took off: one flexible architecture can handle and connect many modalities.

The shared-representation idea — mapping different modalities into a common embedding space where related things are close — is the conceptual heart of multimodal AI. It's what lets a model bridge the previously-siloed modalities, and it's the foundation the series builds on (vision encoders, CLIP's cross-modal alignment, generation, and more all rest on it).

## Why multimodal matters

Multimodal AI matters — it's not just a feature addition but a significant expansion of AI's capabilities and applicability:

- **It matches how information and the world actually are.** Real information is multimodal (documents with figures, videos, web pages), and real understanding integrates modalities. Multimodal AI can therefore engage with the world *as it is* — reasoning over images and text together, understanding videos, working with the mixed-modality data that's everywhere — rather than being confined to text. This vastly broadens what AI can be applied to.
- **It unlocks new capabilities and applications.** Multimodal enables things text-only AI can't: describing images for accessibility, answering questions about photos or documents, generating images/video/audio, transcribing and understanding speech, analyzing medical images with reports, robots perceiving their environment, and much more. Whole categories of application (visual assistants, image/video generation, document AI, multimodal search) depend on multimodal AI.
- **It's the direction of frontier AI.** The leading AI models are increasingly *multimodal by default* — accepting and producing text, images, and audio — moving toward general models that work across all modalities (the "any-to-any" future, from the final post). Multimodal capability is now a core part of frontier AI, not a niche. Understanding it is understanding where AI is going.
- **It's closer to human-like intelligence.** Humans are deeply multimodal (we see, hear, read, and integrate seamlessly). AI that combines modalities is, in that sense, closer to how human intelligence engages the world — able to ground language in perception and connect what it reads to what it sees. This integration is part of building more capable, general AI.

Multimodal AI — models that work across modalities via shared representations — matters because it matches the multimodal reality of information and the world, unlocks vast new capabilities and applications, is the direction of frontier AI, and moves toward more general, human-like intelligence. It's a major expansion beyond text-only AI. The rest of the series goes deep: how models see (vision), how modalities connect (CLIP), vision-language models, image generation, audio/speech, video, and building with it all. Next: how models see — the vision side of multimodal AI.

## Key takeaways

- A modality is a type of data (text, images, audio, video), and for most of deep learning's history models were single-modality specialists (one model, one modality, one task — image classifiers, translators, speech recognizers built separately) — but real information and understanding are inherently multimodal, which single-modality models couldn't handle.
- Multimodal AI is models that process and/or generate multiple modalities — understanding across modalities (visual question answering, captioning, reading charts/documents), translating between them (text-to-image, speech-to-text), and increasingly handling many modalities in one model (modern multimodal LLMs).
- The key enabling idea is a shared representation: mapping different modalities into a common embedding space where related things (an image and its description) are close — which lets the model relate and translate between modalities, and is the bridge that makes cross-modal operations possible.
- The transformer architecture (behind LLMs) is a general tool that works across modalities (images, audio, text can all become token/patch sequences in shared embedding spaces), which is much of why multimodal AI took off — one flexible architecture connecting many modalities.
- Multimodal AI matters because it matches the multimodal reality of information and the world, unlocks vast new capabilities/applications (visual assistants, image/video/audio generation, document AI, multimodal search), is the direction of frontier AI (increasingly multimodal by default), and moves toward more general, human-like intelligence.

## Further reading

- [Multimodal learning (Wikipedia)](https://en.wikipedia.org/wiki/Multimodal_learning)
- [Learning Transferable Visual Models From Natural Language Supervision — CLIP (Radford et al., 2021)](https://arxiv.org/abs/2103.00020)
- [Reasoning Models & Test-Time Compute — the reasoning side of frontier AI](/blog/series/reasoning-models-test-time-compute/)
