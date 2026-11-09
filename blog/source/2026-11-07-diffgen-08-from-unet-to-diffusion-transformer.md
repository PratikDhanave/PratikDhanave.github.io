# From U-Net to Diffusion Transformer — The Architecture Underneath the Denoiser

*For the first years of diffusion, "the model" meant a U-Net — a convolutional hourglass borrowed from medical image segmentation. Then the same migration that had already run through NLP and vision ran through generation: replace the handcrafted spatial architecture with a plain transformer over patch tokens, and let scale do the work. The Diffusion Transformer (DiT) is now the backbone of the frontier image and video systems — and the reasons why are a case study in what architectures are actually for.*

This is post 8 of [Diffusion Models from First Principles](/blog/series/diffusion-models-from-first-principles/). Posts 2–7 treated the denoiser as a black box that maps (noisy latent, step, prompt) to predicted noise. This post opens the box. It pairs with the [Mixture of Experts and Modern LLM Architecture](/blog/series/mixture-of-experts-and-modern-llm-architecture/) series — the convergence of generation onto transformers is the same story told there for language, and the scaling behavior transfers with it.

## What the denoiser must be good at

The denoising task sets unusual architectural requirements. The network's input and output have the **same shape** — it predicts a noise field, not a class label — so the architecture must preserve spatial resolution end to end. It must mix information at **every scale**: at high noise the task is global layout (post 2's schedule discussion), at low noise it is local texture, and one network serves the whole chain. And it must ingest two side-inputs everywhere: the **step number** (so one network can be every noise level's denoiser) and the **condition** (post 7).

## The U-Net era

The **U-Net** answers these requirements structurally. Shaped like an hourglass, it downsamples through convolutional stages to a coarse bottleneck, then upsamples back, with **skip connections** copying each resolution's features straight across to the matching upsampling stage. The bottleneck gives cheap global mixing; the skips preserve the fine detail the output must reconstruct; convolutions supply a strong locality-and-translation prior. Diffusion U-Nets add the two side-channels: the step number enters as a sinusoidal **timestep embedding** added into every block, and the prompt enters through the cross-attention layers interleaved at the coarser resolutions (post 7). Stable Diffusion's generations through SDXL are exactly this recipe, and it is superbly sample-efficient — the convolutional prior does real work when data and compute are limited.

But the U-Net is a bundle of baked-in decisions — where attention goes, how channels grow per stage, what mixes with what — each a small ceiling. Vision had already run this experiment: the **Vision Transformer (ViT)** showed that cutting an image into patches, embedding each as a token, and running a standard transformer matches or beats convolutional networks once data and compute are large — the priors that help small models *constrain* big ones.

## DiT: patches in, transformer, patches out

The **Diffusion Transformer (DiT)** applies that lesson to the denoiser, operating in post 6's latent space. **Patchify** the noisy latent into a grid of tokens (a 64×64 latent at patch size 2 becomes a 32×32 = 1,024-token sequence) plus positional embeddings; run a standard transformer stack; un-patchify back to the noise-prediction field. The side-inputs get a characteristically clean mechanism: step and condition embeddings don't just add into the stream but *modulate* it — **adaptive layer norm (adaLN)**, where the conditioning vector predicts per-block scale and shift (and gating) parameters applied inside every transformer block. Among the variants tried, this modulation beat in-context and cross-attention conditioning for class-conditional generation while costing the least.

What the swap buys is less about any single mechanism than about joining the transformer economy:

- **Measured scaling**: DiT's defining experiment showed sample quality tracking total compute smoothly across model sizes and token counts — the same predictable compute-to-quality curves LLMs are planned around, now available to generation.
- **Uniform global attention**: every patch attends to every patch at every layer — no bottleneck asymmetry — at the familiar quadratic price, kept affordable precisely because post 6 shrank the token grid.
- **Infrastructure inheritance**: a decade of transformer tooling — kernels, parallelism strategies, stability recipes, MoE sparsity — applies as-is.
- **Sequence-native generality**: a transformer over patch tokens doesn't care that the tokens came from a 2-D image. Video becomes *spacetime* patches — the same architecture over a 3-D grid — which is structurally why the DiT era and the video-generation era arrived together (post 10). Frontier image systems (Stable Diffusion 3's multimodal DiT lineage, and DiT-style backbones broadly) also run text and image tokens through joint attention rather than one-way cross-attention.

The honest caveats survive scale: at small budgets the U-Net's priors still win on sample efficiency, quadratic attention makes native high-resolution brutal without aggressive patching or compression, and patch grids impose their own artifacts. The migration was not "transformers are better at denoising" — it was "at scale, *generic + scalable* beats *clever + specialized*," the recurring lesson of the scaling era.

The takeaway: the denoiser needs same-shape in/out, all-scales mixing, and step + condition inputs everywhere. The **U-Net** met those needs structurally — hourglass, **skip connections**, timestep embeddings, interleaved cross-attention — and powered the Stable Diffusion era with strong small-budget sample efficiency. **DiT** re-answers them generically: **patchify** the latent into tokens, run a standard transformer, condition by **adaLN modulation** — and in exchange joins the transformer economy: smooth compute-to-quality scaling, uniform global attention, inherited infrastructure, and a sequence interface that extends to spacetime patches, setting up video generation.

## Key takeaways

- Denoising constrains architecture: **same-shape input/output**, mixing from global layout to local texture (one network serves every noise level), plus **timestep** and **condition** side-inputs throughout.
- The **U-Net**: convolutional hourglass + **skip connections**; global mixing at the bottleneck, detail preserved across skips, prompt via interleaved cross-attention — the SD-through-SDXL backbone, and still the sample-efficiency winner at small budgets.
- **DiT**: patchify latent → standard transformer → un-patchify; conditioning via **adaptive layer norm** (conditioning vector modulates every block's scale/shift/gate) — the cleanest-performing variant in the defining experiments.
- The real payoff is economic: **predictable scaling curves**, uniform attention, transformer infrastructure (kernels, parallelism, MoE) inherited wholesale — generation now rides the same scaling laws as language.
- Patch tokens generalize: image grids → **spacetime patches** for video (post 10); joint text-image token attention in frontier systems. Caveats: quadratic attention needs post 6's compression, and convolutional priors still win when data/compute are scarce.

## Further reading

- [U-Net — the convolutional hourglass the diffusion era started on](https://en.wikipedia.org/wiki/U-Net)
- [Vision transformer — patches-as-tokens, the move DiT applies to generation](https://en.wikipedia.org/wiki/Vision_transformer)
