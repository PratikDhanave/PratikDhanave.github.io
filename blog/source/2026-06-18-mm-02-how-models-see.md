# How Models See

*To a computer, an image is just a grid of numbers — millions of pixel values with no inherent meaning. Turning that raw grid into something a model can understand (this is a dog, that's a face, here's text on a sign) is the problem of computer vision, and the way it's solved has changed dramatically. The field moved from hand-crafted feature detectors, to convolutional networks that learn features, to — most recently — the surprising discovery that the transformer architecture behind language models works remarkably well for images too. Understanding how models see is the foundation of the vision side of multimodal AI.*

Before models can *connect* vision to language, they must *process* vision — turn images into representations they can work with. This post covers how AI models "see": images as data, the evolution from convolutional neural networks (CNNs) to the **Vision Transformer (ViT)**, how ViT treats an image as a sequence of patches, and what an image encoder produces. It's the vision foundation the rest of the multimodal series builds on — because the image *embeddings* these models produce are what get connected to text and other modalities.

## Images as data

To a model, an **image is a grid of numbers** — pixel values (for color images, typically three values per pixel: red, green, blue) arranged in a 2D grid. There's no inherent "meaning" — just numbers. The challenge of computer vision is turning that raw grid into a useful *representation* that captures what's *in* the image:

- **Raw pixels aren't meaningful features.** Individual pixel values don't directly tell you "there's a dog here" — meaning emerges from *patterns* across many pixels (edges, textures, shapes, objects). So vision models must transform raw pixels into higher-level features that capture content. The whole task is going from low-level pixels to high-level meaning.
- **The goal is a useful representation (embedding).** As with text, the aim is to produce an *embedding* — a vector that represents the image's *content* in a form the model can use (for classification, or, crucially for multimodal, to relate to other modalities). "How models see" is really "how models turn pixels into meaningful embeddings." That representation is what everything downstream (including multimodal connection) uses.
- **Learning features vs hand-crafting them.** Early computer vision *hand-crafted* feature detectors (edge detectors, etc.) — human-designed ways to extract features. The deep-learning revolution replaced this with *learning* features from data: models learn, from many examples, what features matter. This shift from hand-crafted to learned features (first via CNNs, then transformers) is the core story of modern computer vision.

Images are grids of numbers, and vision models turn those raw pixels into meaningful representations (embeddings) by *learning* features from data. The evolution of *how* they learn those features — from CNNs to Vision Transformers — is the rest of this post, and the image embeddings they produce are the foundation for connecting vision to language.

## From CNNs to transformers

The dominant approach to vision for years was **convolutional neural networks (CNNs)**, but recently the **transformer** — the architecture behind LLMs — has become central to vision too. The evolution matters:

- **CNNs: learning visual features hierarchically.** CNNs process images through *convolutions* — sliding small filters across the image that detect local patterns (edges, then textures, then shapes, then objects, in increasingly abstract layers). CNNs are built around the structure of images (locality — nearby pixels relate; and translation — a feature matters wherever it appears), and they learn visual features hierarchically from data. For years, CNNs dominated computer vision and were extremely successful. They're built specifically for images.
- **The transformer turn.** More recently, the *transformer* architecture — originally for language — was applied to images (the Vision Transformer, below) and found to work remarkably well, especially at scale. This was surprising: transformers weren't designed for images (they lack the built-in image structure CNNs have), yet with enough data they match or exceed CNNs. The transformer's generality — the same architecture working across text, images, and more — is a big part of *why* multimodal AI is feasible (one architecture for many modalities, from the previous post).
- **Why the transformer turn matters for multimodal.** Using the *same* architecture (transformers) for vision as for language makes it far easier to *combine* them — you can process images and text with related architectures and connect them in shared spaces (the multimodal payoff). The convergence on transformers across modalities is much of what enabled modern multimodal models. So the CNN→transformer shift isn't just a vision story; it's foundational to multimodal AI.

The evolution from CNNs (image-specific, hierarchical feature learning, long-dominant) to transformers (general, surprisingly effective for vision at scale) is central — both as vision progress and because the transformer's cross-modality generality is what makes combining vision and language natural. The Vision Transformer is how transformers were adapted to images.

## The Vision Transformer: images as patches

The **Vision Transformer (ViT)** adapts the transformer to images with a clever, simple idea: **treat an image as a sequence of patches**, analogous to how a transformer treats text as a sequence of tokens:

- **Split the image into patches.** ViT divides the image into a grid of small fixed-size *patches* (e.g. 16×16 pixels each). Each patch is flattened and turned into an embedding (a vector) — so the image becomes a *sequence of patch embeddings*, much like text is a sequence of token embeddings. This is the key move: turning a 2D image into a 1D sequence of patches the transformer can process.
- **Process patches with a transformer.** The sequence of patch embeddings is then processed by a standard transformer, using *self-attention* — letting each patch "attend to" every other patch, so the model can relate different parts of the image (this part connects to that part) regardless of distance. Attention across patches lets ViT integrate information across the whole image to build up understanding. (Position information is added so the model knows where each patch is, since the raw sequence loses spatial layout.)
- **Why "an image is worth 16×16 words."** The ViT insight (captured in its paper's title) is that an image can be treated as a sequence of patches ("words") and fed to a transformer just like text — and with enough training data, this works excellently. It unified vision and language under one architecture: both become sequences (of patches or tokens) processed by transformers. This unification is exactly what makes multimodal models natural — vision and text handled by related transformer machinery.

The Vision Transformer treats an image as a sequence of patches processed by a transformer with self-attention — bringing images under the same architecture as language. This "image as a sequence of patches" idea both advanced vision and, crucially, aligned vision with language architecturally, enabling the shared-space multimodal connections the rest of the series relies on.

## The image encoder and its output

Whether CNN or ViT, the practical result relevant to multimodal AI is an **image encoder** that turns an image into an *embedding* — and understanding its output is what matters going forward:

- **An image encoder maps image → embedding.** The image encoder (a trained CNN or ViT) takes an image and produces an *embedding* — a vector representing the image's content. This is the vision analog of a text encoder producing a text embedding. The embedding captures *what's in the image* in a form usable for downstream tasks (classification, or relating to other modalities).
- **The embedding is what connects to other modalities.** For multimodal AI, the crucial point is that the image encoder produces an embedding *in a space that can be shared with (or connected to) text embeddings*. The next post (CLIP) is precisely about training image and text encoders so their embeddings live in a *shared* space — and that starts from having an image encoder that produces good image embeddings. The encoder's output embedding is the bridge to multimodality.
- **Encoders are often reused (transfer learning).** Image encoders are typically trained on large datasets and then *reused* — their learned representations transfer to many tasks. In multimodal models, a pretrained image encoder (often a ViT) provides the vision understanding, connected to a language model. So the image encoder is a reusable component that provides the "seeing," which multimodal systems build on. You rarely train vision from scratch; you use/adapt a strong pretrained encoder.

How models see comes down to: images are grids of pixels, vision models *learn* to turn them into meaningful embeddings, the field moved from CNNs to transformers (the Vision Transformer treating images as sequences of patches), and the result is an *image encoder* producing embeddings — which, crucially, can be connected to text and other modalities in a shared space. That connection is the next post's topic: CLIP, and how vision and language are linked. Next: connecting modalities.

## Key takeaways

- To a model, an image is just a grid of pixel numbers with no inherent meaning — computer vision's task is turning those raw pixels into a meaningful *representation (embedding)* capturing what's in the image, by *learning* features from data (replacing early hand-crafted feature detectors).
- Vision moved from CNNs (convolutional networks built around image structure — locality and translation — learning visual features hierarchically, long-dominant) to transformers (the LLM architecture, surprisingly effective for vision at scale despite lacking built-in image structure).
- The CNN→transformer shift is foundational to multimodal AI, not just vision progress: using the *same* architecture for vision and language makes combining and connecting them natural (shared spaces), which is much of what enabled modern multimodal models.
- The Vision Transformer (ViT) treats an image as a sequence of fixed-size patches (like text as a sequence of tokens), processed by a transformer with self-attention (relating patches across the whole image) — "an image is worth 16×16 words" — unifying vision and language under one architecture.
- The practical output is an *image encoder* (CNN or ViT) that maps an image to an embedding capturing its content — this embedding is the bridge to other modalities (the next post trains image and text encoders to share a space), and encoders are typically pretrained and reused (transfer learning) rather than trained from scratch.

## Further reading

- [An Image is Worth 16x16 Words: Transformers for Image Recognition (Dosovitskiy et al., 2020)](https://arxiv.org/abs/2010.11929)
- [Vision transformer (Wikipedia)](https://en.wikipedia.org/wiki/Vision_transformer)
- [What multimodal AI is (previous post)](/blog/posts/mm-01-what-multimodal-ai-is.html)
