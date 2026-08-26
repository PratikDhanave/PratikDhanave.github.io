# Generating Images

*Typing a sentence and watching a detailed, coherent, never-before-seen image appear is one of the most striking capabilities in modern AI — and the technique behind it is beautifully counterintuitive. Rather than paint an image stroke by stroke, these models start with pure noise and gradually remove it, step by step, sculpting a picture out of static, guided by your text. Understanding diffusion — and how text steers it — demystifies text-to-image generation and reveals one of the most important generative techniques in AI.*

Having covered understanding images (vision, VLMs), this post covers *generating* them: **text-to-image** models and the **diffusion** technique behind them. It explains how diffusion models work (the denoising idea), how text conditions the generation (using the shared-space alignment from CLIP), the role of latent diffusion in making it efficient, and what this enables. Image generation is one of the most visible and impressive multimodal capabilities, and diffusion is the key idea to understand.

## Text-to-image generation

**Text-to-image** generation takes a text description (a "prompt") and produces an *image* matching it — creating novel images from language. It's a striking cross-modal capability (text → image) that has become widely used:

- **From prompt to novel image.** You describe what you want ("a watercolor painting of a fox in a forest at sunset") and the model *generates* an image matching the description — an image that didn't exist before, synthesized to fit the text. This is generation, not retrieval (it's not finding an existing image; it's *creating* one). The ability to conjure arbitrary images from text is what makes it so striking.
- **It's a cross-modal translation.** Text-to-image crosses from the text modality to the image modality — the model must understand the text's *meaning* and produce a *visual* realization of it. This requires connecting text and image (the shared-space idea from CLIP) *and* a way to actually *generate* image content. The connection grounds the generation in the text; the generation technique (diffusion) produces the pixels.
- **Diffusion is the dominant technique.** While there have been various approaches to image generation, **diffusion models** became the dominant, most successful technique behind modern text-to-image systems. Understanding text-to-image generation today largely means understanding diffusion. So the rest of the post focuses on how diffusion works and how text steers it.

Text-to-image generation creates novel images from text descriptions — a striking cross-modal (text → image) capability, requiring both connecting text to images and generating image content, with *diffusion* the dominant technique. The counterintuitive-but-elegant diffusion idea is the key to understanding how it works.

## How diffusion works: denoising

**Diffusion models** generate images through a surprising process: start with pure random noise and *gradually remove* the noise, step by step, until a coherent image emerges. The idea, and why it works:

- **Learn to denoise.** A diffusion model is trained by taking real images, progressively *adding* noise to them (until they become pure static), and learning to *reverse* this — to *remove* noise step by step, predicting a slightly-less-noisy image at each step. By learning to undo noise, the model learns the structure of images (what real images look like) well enough to reconstruct them from noise.
- **Generate by denoising from pure noise.** To *generate* a new image, start with *pure random noise* and apply the learned denoising *repeatedly* — each step removes a bit of noise, and over many steps, a coherent image gradually emerges from the static. The model "sculpts" an image out of noise by iteratively denoising. It's generation as gradual noise-removal — starting from randomness and refining toward a real-looking image.

```text
   Diffusion generation (simplified):
     pure noise → denoise → less noise → denoise → ... → coherent image
     (many steps, each removing a bit of noise, guided toward a real image)
   Training: add noise to real images, learn to reverse it step by step
```

- **Why it works well.** This iterative, gradual approach produces high-quality, diverse, coherent images — the step-by-step refinement lets the model build up detail and structure progressively (rather than generating an image in one shot), which turns out to produce excellent results. Diffusion's quality and controllability made it the dominant image-generation technique. It's also an example of *test-time compute* (from the reasoning series) in a different domain: more denoising steps = more compute = (up to a point) better/more-refined images.

Diffusion generates images by learning to *remove* noise (trained by reversing noise added to real images) and then generating by iteratively denoising from pure random noise into a coherent image. This counterintuitive "sculpt an image from static, step by step" process produces high-quality, diverse images and is the dominant technique. But so far this generates *some* image — the crucial piece is steering it with text.

## How text steers generation: conditioning

For *text-to-image*, the diffusion process must be *guided* by the text prompt so the generated image matches the description. This is **conditioning**, and it relies on the cross-modal connection from CLIP:

- **Condition the denoising on the text.** The denoising process is *conditioned* on the text prompt — at each denoising step, the model is guided by the text's meaning, so the image that emerges *matches* the description. Rather than denoising toward *any* coherent image, it denoises toward an image *consistent with the text*. The text steers the generation throughout.
- **Text meaning comes from a shared/aligned space.** How does the model use the *text's meaning* to guide *image* generation? Via the text-image alignment from CLIP-style shared spaces (earlier post): the text is embedded into a space connected to image meaning, and that embedding guides the denoising toward matching visual content. The shared-space connection between text and images is what lets text steer image generation — the CLIP idea is a building block of text-to-image. (This is why the "connecting modalities" post is foundational here.)
- **Guidance strength is a knob.** How *strongly* the generation adheres to the text (vs producing a more freely-generated image) is a tunable knob (classifier-free guidance) — stronger guidance makes the image follow the prompt more closely (sometimes at the cost of diversity/naturalness). This controllability is part of diffusion's practical appeal. You can dial how tightly the output matches the prompt.

Text steers image generation through *conditioning*: the denoising process is guided at each step by the text prompt's meaning (via CLIP-style text-image alignment), so the emerging image matches the description, with tunable guidance strength. This is where the "connecting modalities" shared-space idea meets the diffusion generation technique — together enabling text-to-image. One more piece makes it efficient enough to be practical.

## Latent diffusion and what it enables

A key advance made diffusion *efficient* enough for widespread use — **latent diffusion** — and the overall capability enables a lot:

- **Latent diffusion: denoise in a compressed space.** Running diffusion directly on full-resolution images (millions of pixels) is computationally expensive. *Latent diffusion* (behind models like Stable Diffusion) runs the diffusion process in a *compressed latent space* (a lower-dimensional representation of images) instead of on raw pixels — dramatically reducing computation while maintaining quality. The image is encoded to a compact latent, diffusion happens there, and the result is decoded to a full image. This efficiency made high-quality text-to-image *practical and accessible* (runnable on consumer hardware), which drove its explosion. It's a key reason image generation became widely available.
- **What it enables.** Text-to-image (and diffusion generally) enables: creating images from descriptions (art, design, content, illustration), *editing* images (inpainting — filling/changing parts, guided by text), generating variations, and more. It's a powerful creative and practical tool, and diffusion techniques extend to other generation (some audio and video generation use diffusion too — later posts). The generative capability is broadly useful and still rapidly advancing.
- **It's cross-modal generation at its most visible.** Text-to-image is the most visible example of *generating one modality from another* (text → image) — the generative flip side of the understanding capabilities (VLMs). Together, understanding (image → text, VLMs) and generation (text → image, diffusion) show multimodal AI crossing modalities in both directions, all enabled by connecting modalities in shared/aligned representations. It rounds out the vision side of multimodal AI.

Image generation via diffusion — generating images by iteratively denoising from noise, steered by text through conditioning (using CLIP-style text-image alignment), made efficient by latent diffusion — is a striking, widely-used cross-modal capability. It's the generative counterpart to visual understanding, enabling creating and editing images from text. Next: audio and speech — extending multimodal AI to sound.

## Key takeaways

- Text-to-image generation creates *novel* images from text prompts — a striking cross-modal (text → image) capability that synthesizes new images (not retrieval), requiring both connecting text to images and generating image content, with *diffusion* the dominant technique.
- Diffusion models generate by *denoising*: trained to reverse noise added to real images (learning image structure), they generate by starting from pure random noise and iteratively removing noise over many steps until a coherent image emerges — a counterintuitive "sculpt an image from static, step by step" process that produces high-quality, diverse images (and is a form of test-time compute: more steps = more compute = more refinement).
- Text steers generation through *conditioning*: the denoising is guided at each step by the prompt's meaning (via CLIP-style text-image shared-space alignment — making the "connecting modalities" post foundational here) so the emerging image matches the description, with tunable guidance strength controlling how closely it follows the prompt.
- Latent diffusion (e.g. Stable Diffusion) runs the diffusion process in a compressed latent space rather than on raw pixels — dramatically cutting computation while keeping quality — which made high-quality text-to-image practical and accessible (runnable on consumer hardware), driving its widespread adoption.
- Image generation enables creating images from descriptions, editing (inpainting), and variations, and diffusion extends to other modalities (some audio/video) — it's the generative flip side of visual understanding (VLMs), showing multimodal AI crossing modalities in both directions, all enabled by connecting modalities in shared representations.

## Further reading

- [Denoising Diffusion Probabilistic Models (Ho et al., 2020)](https://arxiv.org/abs/2006.11239)
- [High-Resolution Image Synthesis with Latent Diffusion Models — Stable Diffusion (Rombach et al., 2021)](https://arxiv.org/abs/2112.10752)
- [Vision-language models (previous post)](/blog/posts/mm-04-vision-language-models.html)
