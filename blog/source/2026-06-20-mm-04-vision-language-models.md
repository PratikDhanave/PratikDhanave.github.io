# Vision-Language Models

*The multimodal capability people actually experience — uploading a photo and asking a chatbot what's in it, or having it read a screenshot, explain a diagram, or extract data from a chart — comes from vision-language models: LLMs that can see. The clever part is how it's done. Rather than build a seeing-and-reasoning model from scratch, you take a language model that already reasons brilliantly and give it eyes, by connecting a vision encoder to it. Understanding how that connection works explains the multimodal AI most people use.*

**Vision-language models (VLMs)** — also called multimodal LLMs — combine visual understanding with language: they take images (and text) as input and reason and respond in text. This post covers what VLMs are, how they're built (connecting a vision encoder to an LLM), what they can do (visual question answering, captioning, document understanding), and their significance. This is the multimodal capability most visible in today's AI assistants, and it builds directly on the vision encoders and shared-space ideas from earlier posts.

## What vision-language models are

A **vision-language model (VLM)** is a model that understands *both* images and text together — taking visual input along with text, and reasoning and responding about it in language. They're essentially *LLMs that can see*:

- **They accept images as input alongside text.** Where a text-only LLM takes only text, a VLM takes *images and text together* — you can show it a picture and ask a question about it, give it a screenshot and text instructions, or have it analyze a document with figures. It processes the visual and textual input jointly. This is the "multimodal LLM" or "multimodal chat" capability of modern AI assistants.
- **They reason and respond in language.** A VLM *understands* the image in the context of the text and responds in language — describing, answering questions, explaining, extracting information, reasoning about what it sees. It brings the LLM's language and reasoning abilities to bear on visual input. The output is (typically) text, grounded in the image.
- **They combine vision understanding with LLM reasoning.** The power of VLMs is combining *visual perception* (understanding what's in an image) with the *reasoning and knowledge* of an LLM — so the model can not just see but *reason about* what it sees, using all the capability of a large language model. This combination is what makes VLMs so useful: perception plus reasoning plus knowledge.

Vision-language models are LLMs extended to see — accepting images with text, understanding them, and reasoning/responding in language. They're the most prominent multimodal capability today (the "analyze this image" feature of AI assistants), combining visual perception with LLM reasoning. The clever question is *how* you give a language model vision, which is mostly about *connecting* a vision encoder to an LLM.

## How VLMs are built: connecting vision to an LLM

The dominant way to build a VLM is not to train a seeing-reasoning model from scratch, but to **connect a (pretrained) vision encoder to a (pretrained) LLM** — a modular, efficient approach:

- **Reuse a vision encoder and an LLM.** Start with a pretrained *vision encoder* (e.g. a ViT, often CLIP's — already aligned with language, from earlier posts) that turns images into embeddings, and a pretrained *LLM* that reasons in language. Both are strong, existing components. The VLM combines them rather than building either from scratch — leveraging the huge investment already in vision encoders and LLMs.
- **Bridge the encoder's output into the LLM.** The key connection: the vision encoder produces image *embeddings*, which are *projected/adapted* into the LLM's input space so the LLM can "read" them as if they were tokens. A small *connector* (a projection/adapter, sometimes called a bridge) maps image embeddings into the representation the LLM consumes — effectively turning the image into "tokens" the LLM processes alongside text tokens. The LLM then reasons over the combined image-derived and text tokens.

```text
   image → vision encoder → image embeddings → [connector/projection]
                                                     ↓
   text  → tokens ─────────────────────────────→ LLM → text response
   (the LLM reads image-derived "tokens" alongside text tokens)
```

- **Train the connection (and adapt the parts).** The model is trained on *image-text data* (images with associated text, instructions, Q&A) so the LLM learns to *use* the visual information — the connector is trained (and parts of the model adapted) so the LLM correctly interprets and reasons about the image embeddings. Often the vision encoder and LLM are largely reused (frozen or lightly tuned) while the connection is trained, which is efficient. The result is an LLM that can incorporate visual input into its reasoning.

VLMs are built by connecting a pretrained vision encoder to a pretrained LLM via a trained connector that bridges image embeddings into the LLM's input, then training on image-text data so the LLM learns to use vision. This modular "give the LLM eyes by plugging in a vision encoder" approach — reusing strong existing components — is how most VLMs are made, and it's efficient and effective. (The shared-space alignment from CLIP helps: a language-aligned vision encoder is easier to connect to a language model.)

## What VLMs can do

VLMs enable a range of visual-understanding tasks, unified under one model that sees and reasons in language:

- **Visual question answering (VQA).** Answer questions *about* an image — "what's in this picture?", "how many people are there?", "what does this sign say?", "is this safe?" The model perceives the image and reasons to answer in language. This general "ask questions about an image" ability is a core VLM capability and very versatile.
- **Image captioning and description.** Generate a *description* of an image — useful for accessibility (describing images for people who can't see them), content understanding, and indexing. Describing what's in an image in natural language is a fundamental VLM task.
- **Document and chart understanding.** Read and understand *documents, screenshots, charts, diagrams, and tables* — extracting text (OCR-like), interpreting layouts, reading data from charts, understanding diagrams. This "document AI" / visual-document-understanding capability is hugely practical (processing forms, screenshots, reports) and a major VLM application.
- **Visual reasoning.** Reason about what's in an image — understanding relationships, inferring context, explaining scenes, following visual instructions, even reasoning through visual problems. VLMs bring LLM reasoning to visual input, enabling tasks beyond simple recognition. (Combined with the reasoning-models ideas from that series, VLMs can reason carefully about visual input.)
- **Grounded assistance.** Act as an assistant that can *see* — helping with tasks that involve images (analyzing a photo, helping with a screenshot, understanding visual context). This is the multimodal-assistant experience: an AI you can *show* things to, not just tell.

VLMs can do visual question answering, captioning/description (including accessibility), document/chart understanding, visual reasoning, and grounded assistance — a broad range of "understand and reason about images in language" tasks, unified in one model. These capabilities are what make multimodal AI assistants able to work with the visual world, and they're widely applicable.

## Why VLMs matter

Vision-language models are significant — they're a major expansion of AI's usefulness and the leading edge of everyday multimodal AI:

- **They bring AI to the visual world.** Enormous amounts of information and tasks are visual (documents, screenshots, photos, charts, real-world scenes). VLMs let AI *engage with all of it* — vastly expanding what AI assistants and applications can do beyond text. Much of the world's information becomes accessible to AI through VLMs.
- **They're the multimodal AI people actually use.** The "upload an image and ask about it" capability of modern AI assistants *is* a VLM — this is the most widely-experienced multimodal AI. Understanding VLMs is understanding the multimodal capability in the tools people use daily. It's not niche; it's mainstream.
- **They combine perception and reasoning powerfully.** By bringing LLM reasoning to visual input, VLMs can do more than recognize — they can *reason about* what they see, answer complex questions, and follow instructions involving images. This perception-plus-reasoning combination is genuinely powerful and enables sophisticated applications (analyzing complex documents, visual problem-solving, grounded assistance). It's more than "computer vision plus a chatbot" — it's integrated understanding.
- **They exemplify the modular, reuse-based approach.** VLMs' construction (connect a vision encoder to an LLM) exemplifies how multimodal AI is often built — by *combining and connecting* strong pretrained components (vision encoders, LLMs) rather than building monoliths from scratch. This modular approach (leveraging the shared-space alignment and reusable encoders from earlier posts) is a key pattern in multimodal AI, and VLMs are its clearest success. It's efficient and it works.

Vision-language models — LLMs given sight by connecting a vision encoder, enabling visual question answering, captioning, document understanding, and visual reasoning — are the most prominent, widely-used multimodal AI, bringing LLM reasoning to the visual world through a modular, reuse-based construction. They're where multimodal AI meets most people. Next: generating images — the flip side, creating visuals from text with diffusion models.

## Key takeaways

- Vision-language models (VLMs, or multimodal LLMs) are LLMs that can see — they take images along with text, understand them, and reason/respond in language, combining visual perception with the LLM's reasoning and knowledge; they're the "analyze this image" capability of modern AI assistants.
- VLMs are typically built by connecting a *pretrained* vision encoder (e.g. a ViT, often CLIP's language-aligned one) to a *pretrained* LLM via a trained connector/projection that bridges image embeddings into the LLM's input (turning the image into "tokens" the LLM reads alongside text), then training on image-text data so the LLM learns to use the visual information — a modular, efficient reuse of strong existing components.
- VLMs enable visual question answering (ask questions about an image), captioning/description (including accessibility), document/chart/screenshot understanding (highly practical "document AI"), visual reasoning (relationships, context, following visual instructions), and grounded assistance (an AI you can show things to).
- They matter because they bring AI to the vast visual world (documents, screenshots, photos, charts), they're the multimodal AI people actually use daily, and they combine perception with reasoning powerfully (more than recognition — integrated understanding and reasoning about what's seen).
- VLMs exemplify multimodal AI's modular, reuse-based construction — combining/connecting strong pretrained components (vision encoders + LLMs, aided by CLIP-style shared-space alignment) rather than building monoliths from scratch — a key, effective pattern in the field.

## Further reading

- [End-to-End Object Detection with Transformers — transformers applied to vision tasks (Carion et al., 2020)](https://arxiv.org/abs/2005.12872)
- [Connecting modalities: CLIP (previous post)](/blog/posts/mm-03-connecting-modalities-clip.html)
- [Reasoning Models & Test-Time Compute — bringing careful reasoning to any input](/blog/series/reasoning-models-test-time-compute/)
