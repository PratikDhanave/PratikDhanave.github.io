<!-- Markdown version for AI agents and readers. Canonical: https://pratikdhanave.com/blog/posts/diffgen-07-conditioning-and-classifier-free-guidance.html -->

# Conditioning and Classifier-Free Guidance — How Text Steers the Image

*Everything so far generates an image — any image the training distribution contains. A product needs the image you asked for. Conditioning is how a prompt gets wired into every denoising step, and classifier-free guidance — a two-line trick discovered almost apologetically — is the single knob that most determines whether the output actually obeys the prompt. The famous "CFG scale" slider in every image UI is this post.*

This is post 7 of [Diffusion Models from First Principles](/blog/series/diffusion-models-from-first-principles/). Post 6 built the space the denoiser runs in; this post wires the *prompt* into the denoiser that runs there. It connects naturally to the [Multimodal AI](/blog/series/multimodal-ai/) series — text-to-image is multimodality run in reverse, and the text encoders that steer diffusion are exactly the contrastively-trained models that series covers.

## Conditioning: the denoiser gets a second input

Unconditional diffusion learns "denoise toward *some* plausible image." Conditional diffusion learns "denoise toward a plausible image *consistent with this label/prompt/layout*" — the network simply receives the condition as an extra input at **every step**, and training pairs each image with its condition. Nothing in posts 2–5's math changes; the noise predictor just becomes a function of (noisy latent, step, condition).

For text, the condition is produced by a frozen or jointly-trained **text encoder** — in Stable Diffusion's lineage, the text tower of **CLIP**, a model contrastively pretrained to put images and their captions near each other in a shared embedding space; later systems add or substitute large language-model-style encoders (the T5 family) whose richer token sequences markedly improve spelling, counting, and compositional instructions. The prompt enters the denoiser through **cross-attention**: at each layer, image positions *query* the prompt's token embeddings, so "red hat" can attach to the hat region while "wooden table" attends elsewhere. One encoder choice, one attention mechanism — this is the entire text-image interface, and prompt-following quality tracks the encoder's language understanding more than any other single factor.

## Why plain conditioning isn't enough

Train that conditional model and sample from it, and the results *loosely* follow the prompt — too loosely. The model has learned the true conditional distribution, which includes all the images only weakly coupled to their captions (training captions are noisy, often generic alt-text). Sampling the honest distribution reproduces that weak coupling. What products need is to *over-weight* the prompt — to push samples toward the region where the condition is strongly expressed, even at some cost to diversity.

The first solution, **classifier guidance**, bolted on a separately-trained classifier that could recognize the condition in noisy images, and added its input-gradient (a score, in post 4's exact sense — an arrow toward "more consistent with the label") to the diffusion score at each step. It worked, but demanded training a second model on noisy data for every kind of condition — and a classifier over all possible *text prompts* is barely coherent.

## Classifier-free guidance: the model argues with itself

**Classifier-free guidance (CFG)** gets the same arrow with no classifier at all. Two moves:

**Training:** randomly drop the condition (replace the prompt with a null token) a small fraction of the time — in practice around 10% of training examples. One network thereby learns *both* the conditional and the unconditional denoising task.

**Sampling:** at each step, run the network twice — once with the prompt, once with the null token — and take the difference of the two predictions. That difference is precisely "what the prompt changes about the denoising direction": an implicit classifier's arrow, derived from the generative model itself (Bayes' rule makes this literal — the conditional-minus-unconditional score *is* the score of the classifier you never trained). Then **extrapolate**: take the unconditional prediction and add the difference scaled by a **guidance scale** greater than one. The final direction over-commits to the prompt by exactly the chosen factor.

The guidance scale is the most consequential user-facing knob in image generation. At scale 1, the honest distribution: diverse, loosely prompt-bound. Around 5–9 (typical defaults, in the convention where 1 means unguided): strong prompt adherence, vivid saturated detail. Push far higher and quality degrades distinctively — burnt colors, waxy over-sharpened textures — because extrapolating a difference vector far off-distribution leaves the manifold the denoiser knows. The knob trades **fidelity against diversity**, and its cost is concrete: two network evaluations per step, doubling post 5's bill (production systems mitigate with batching the pair, distilling guidance into the weights — post 10 — or related tricks).

CFG also explains a beloved UI feature almost for free: the **negative prompt**. Replace the null token's slot with *unwanted* content ("blurry, extra fingers, watermark") and the extrapolation pushes away from it — the same arithmetic, aimed in reverse.

The takeaway: conditioning feeds the prompt — encoded by **CLIP**-style or T5-style text encoders — into every denoising step via **cross-attention**; that alone follows prompts only as loosely as training captions did. **Classifier-free guidance** fixes it by co-training an unconditional mode (random condition dropout) and, at sampling, extrapolating conditional-minus-unconditional predictions by a **guidance scale**: a classifier's steering arrow conjured from the generative model itself. One knob governs the fidelity-diversity trade, costs 2× evaluations per step, degrades into burnt saturation when pushed, and gives negative prompts by running the same arithmetic backwards.

## Key takeaways

- **Conditioning** = the condition enters the noise predictor at *every step*; for text, a **text encoder** (CLIP tower, later T5-class) supplies token embeddings that image positions read through **cross-attention** — prompt-following tracks encoder quality above all.
- The honest conditional distribution is **too loosely coupled** to prompts (caption noise); products need deliberate over-weighting of the condition.
- **Classifier guidance** added a noisy-data classifier's input-gradient (a score arrow, post 4) — effective but needs an extra model per condition type.
- **CFG**: drop the condition ~10% of training; at sampling, extrapolate (conditional − unconditional) by the **guidance scale** — an implicit classifier via Bayes' rule, no classifier trained. Scale ≈ 1 honest/diverse; ~5–9 faithful/vivid; too high → burnt, waxy off-manifold artifacts. Cost: 2× evaluations per step.
- **Negative prompts** are CFG's difference vector aimed away from unwanted content — same mechanism, reversed.

## Further reading

- [Text-to-image model — the task and its system anatomy](https://en.wikipedia.org/wiki/Text-to-image_model)
- [Contrastive Language-Image Pre-training (CLIP) — the text encoder lineage that steers diffusion](https://en.wikipedia.org/wiki/Contrastive_Language-Image_Pre-training)

---

Author: Pratik Dhanave (https://pratikdhanave.com) | Published: 2026-11-06
Canonical: https://pratikdhanave.com/blog/posts/diffgen-07-conditioning-and-classifier-free-guidance.html
Attribution: please link the canonical URL when citing or quoting this post.
