# Vision Transformers — When Attention Came for Images

*For a decade, convolution was synonymous with computer vision. Then the transformer — the architecture that revolutionized language — was applied to images, and the vision transformer showed that attention could match or beat CNNs given enough data. It's a profound shift: the same architecture now underpins both language and vision, enabling the multimodal models that see and read at once. This post explains how transformers handle images and what their rise means.*

Posts 3–5 built the CNN world. This post covers the architecture that challenged it — the vision transformer (ViT) — and why it matters beyond vision: it unified the architectures of AI's two biggest domains. It connects directly to the blog's transformer and [Multimodal AI](/blog/series/multimodal-ai/) coverage, now from the vision side.

## Treating an image as a sequence of patches

The transformer was built for *sequences* of tokens (words), using **attention** to let every token relate to every other (covered elsewhere on the blog). Images aren't sequences — so how do you apply a transformer to one? The **vision transformer (ViT)** answer is elegantly simple: **chop the image into a grid of fixed-size patches** (say 16×16 pixels), treat each patch as a "token" (like a word), and feed that sequence of patches to a standard transformer.

That's the core trick — *an image becomes a sequence of patches*, and from there it's essentially the same transformer as in language:
- Each patch is linearly projected into a vector (a patch "embedding"), with position information added so the model knows where each patch sat (since attention itself is order-agnostic).
- The transformer's **self-attention** then lets *every patch attend to every other patch*, directly modeling relationships across the whole image in a single layer.

This is the fundamental difference from a CNN (post 3). A CNN builds up global understanding *gradually* — early layers see only local neighborhoods, and it takes many stacked layers for information to travel across the image (post 3's receptive field). A ViT's attention gives **global context immediately**: in the very first layer, a patch in one corner can directly attend to a patch in the opposite corner. Where convolution's inductive bias is *locality*, attention's strength is *long-range, all-to-all relationships* — a genuinely different way of processing an image.

## Convolution vs attention: inductive bias and data

The ViT-vs-CNN comparison is a clean lesson in a deep trade-off: **built-in assumptions vs learning from data.**

- **CNNs have strong inductive biases for images** (post 3) — locality and translation invariance are *baked into* convolution. These assumptions are *correct* for images, so CNNs learn efficiently from *limited* data: the architecture already "knows" useful things about images, so it doesn't have to learn them.
- **ViTs have weaker inductive biases** — a transformer assumes almost nothing about image structure; it must *learn* even basic facts like locality and translation invariance from the data. This is a disadvantage with *small* data (the CNN's built-in assumptions win) but an *advantage* with *large* data: freed from hard-coded assumptions, the ViT can learn whatever patterns actually serve the task, including global relationships a CNN struggles with.

This produces the headline finding: **ViTs underperform CNNs on small datasets but match or beat them when trained on very large datasets.** With enough data, learning the right biases from scratch beats having good-but-fixed biases built in. This is a profound and recurring theme in deep learning (it echoes the "data beats hand-crafted structure at scale" lesson from classical-features-vs-CNNs, post 2) — and it's why ViTs rose as massive datasets and compute became available. The practical consequence: ViTs shine when you can pretrain on huge data (then transfer, post 7); CNNs remain excellent and more data-efficient for smaller problems. In practice, hybrid architectures that combine convolution's efficiency with attention's global reach are also common, getting the best of both.

## Why this matters beyond vision

The vision transformer's deepest significance isn't just competitive accuracy — it's **architectural unification**, and this is the point to carry away:

- **One architecture for vision and language.** Before ViT, vision used CNNs and language used transformers — different worlds. After ViT, *the same core architecture* (the transformer) handles both. This convergence is enormously consequential: advances, tooling, and understanding transfer directly between the fields, and researchers in both now speak the same architectural language.
- **It enables multimodal AI.** If images and text are both just sequences of tokens processed by transformers, you can process them *together* in one model — which is exactly how modern **multimodal models** (vision-language models that see images and read/write text) work. The ViT's patch-as-token idea is what lets an image enter the same transformer that handles text, powering the image-understanding of modern LLMs (the [Multimodal AI](/blog/series/multimodal-ai/) series). Without treating images as token sequences, you couldn't fuse vision and language so cleanly.
- **It's a case study in a general idea winning.** The transformer was designed for language, yet its core mechanism (attention over tokens) turned out to be general enough to conquer vision too — a striking example of a powerful idea escaping its origin domain (like ResNet's skip connections, post 4). It suggests attention is a remarkably universal way to process *structured data of any kind*, not just language.

The honest framing: ViTs didn't make CNNs obsolete — CNNs remain excellent, efficient, and widely used, especially with limited data, and hybrids are common. But the vision transformer changed the landscape by proving attention works for images, by unifying the architectures of vision and language, and above all by enabling the multimodal models that are central to modern AI. It's the bridge that let the two great branches of deep learning become one, which is why it matters far beyond any benchmark.

The throughline: the **vision transformer (ViT)** applies the language transformer to images by **chopping an image into fixed-size patches**, treating each patch as a **token**, and running a standard transformer whose **self-attention gives every patch global context immediately** — the opposite of a CNN's gradual, local build-up (locality vs long-range all-to-all). This exposes a deep trade-off: **CNNs have strong, correct inductive biases** (locality/translation-invariance baked in → data-efficient on small data), while **ViTs assume little and must learn structure from data** (worse on small data, **better at scale**) — the headline finding that *data beats built-in bias when there's enough of it*, echoing classical-features-vs-CNNs. Its deepest significance is **architectural unification**: one architecture (the transformer) now handles both vision and language, which **enables multimodal models** (images-as-tokens enter the same transformer as text — powering vision-language LLMs) and exemplifies a general idea escaping its origin domain. ViTs didn't kill CNNs (still efficient, especially small-data; hybrids common) but bridged deep learning's two branches into one.

## Key takeaways

- The **vision transformer (ViT)** applies the language transformer to images by **splitting the image into fixed-size patches** (e.g. 16×16), treating each patch as a **token** (with position info added), and feeding the patch sequence to a standard transformer — "an image is a sequence of patches."
- Its **self-attention gives global context immediately** (any patch attends to any other in the first layer) — fundamentally unlike a CNN, which builds global understanding *gradually* through stacked local layers; convolution's bias is **locality**, attention's strength is **long-range all-to-all relationships**.
- The deep trade-off: **CNNs have strong, correct inductive biases** (locality + translation invariance baked in → **data-efficient**, win on *small* data), while **ViTs assume little** and must **learn structure from data** (lose on small data, **match or beat CNNs at large scale**) — *data beats built-in bias when there's enough of it* (echoing classical-features-vs-CNNs, post 2).
- Practically: ViTs shine when you can **pretrain on huge data then transfer** (post 7); CNNs stay excellent and more data-efficient for smaller problems; **hybrid** conv+attention architectures combine both strengths.
- The deepest significance is **architectural unification** — one architecture (the transformer) now handles **both vision and language**, which **enables multimodal AI** (images-as-tokens enter the same transformer as text, powering vision-language LLMs — [Multimodal AI](/blog/series/multimodal-ai/)) and exemplifies a general idea (attention) escaping its origin domain (like ResNet's skip connections). ViTs didn't make CNNs obsolete but **bridged deep learning's two great branches into one**.

## Further reading

- [Vision transformer — attention applied to images](https://en.wikipedia.org/wiki/Vision_transformer)
- [Transformer (deep learning architecture) — the architecture ViT brings to vision](https://en.wikipedia.org/wiki/Transformer_(deep_learning_architecture))
