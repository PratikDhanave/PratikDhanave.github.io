# Why Generating Images Is Hard — The Problem Diffusion Solved

*Every text-to-image system — Stable Diffusion, Midjourney, DALL·E, Imagen — rests on one idea: destroy an image with noise, then learn to run the destruction backwards. Before that idea, a decade of generative modeling fought a three-way trade-off between sample quality, training stability, and diversity — and every architecture picked two. This series builds diffusion models from first principles: what problem they solve, why the math works, and how the pieces (latents, guidance, transformers, flow matching) assembled into the systems generating images and video today.*

This series is the *generation* companion to the [Multimodal AI](/blog/series/multimodal-ai/) series. That one covers how models *understand* images and audio alongside text; this one goes the other direction — how a model synthesizes an image from nothing but noise and a prompt. It also leans on ideas from [Machine Learning from First Principles](/blog/series/machine-learning-from-first-principles/) (distributions, gradients, maximum likelihood), and post 1 sets up the problem every generative model must solve.

## Generation is sampling, not prediction

A classifier answers a question with one right answer: *is this a cat?* A generative model has a fundamentally different job: **produce new samples from the distribution of all plausible images**. There is no single correct output — there are billions of valid images of "a cat on a beach," and the model must be able to produce *any* of them, with frequencies that match how plausible they are.

Formally, the training set is treated as samples from some unknown distribution over images, and the model's job is to learn a distribution it can *sample from* that matches it. This is harder than classification in a specific way: an image is a point in a space with hundreds of thousands of dimensions (one per pixel channel), and almost all of that space is noise. Natural images occupy a vanishingly thin region — the **data manifold** — and a generative model must learn where that region is *and* how to land on it, every time, starting from randomness.

## The first generation: VAEs and GANs

Two families dominated the 2014–2020 era, and their failure modes explain why diffusion won.

A **variational autoencoder (VAE)** learns a compressed latent space: an encoder maps an image to a small latent vector, a decoder maps the vector back, and the latent space is regularized so that sampling a random vector and decoding it yields a plausible image. VAEs train stably and cover the distribution well — but their samples are characteristically **blurry**. The root cause is the training objective: reconstruction under a pixel-wise likelihood pushes the decoder to output the *average* of all images consistent with a latent, and the average of many sharp images is a smooth one. (Hold onto the VAE, though — it returns in post 6 as the compression layer inside Stable Diffusion.)

A **generative adversarial network (GAN)** replaces the likelihood with a game: a generator produces images, a discriminator learns to tell them from real ones, and the generator is trained to fool it. Because the discriminator judges *realism* rather than pixel-wise closeness, GAN samples are **sharp** — GANs produced the first photorealistic generated faces. But the adversarial game is notoriously unstable, and it has a failure mode baked into its structure: **mode collapse**. The generator is never required to cover the whole distribution — only to fool the discriminator — so it can win the game while producing a narrow sliver of what the data contains. GANs bought sharpness at the price of stability and coverage.

## The trilemma

By 2020 the pattern was clear enough to name: generative models were stuck choosing between **sample quality**, **mode coverage / diversity**, and **stable, scalable training**. VAEs had coverage and stability but not quality. GANs had quality but fought for stability and coverage. Autoregressive models (generating pixels one at a time, the way LLMs generate tokens) had quality and coverage but were painfully slow to sample and awkward to scale to high resolution.

What made diffusion models the breakout is that they refuse the trade-off: they train with a simple, stable regression loss (no adversarial game, no collapse), they cover modes because the objective is likelihood-based, and they produce samples that match or beat GANs in quality. The price they pay is a new one — **sampling is slow**, because generation happens in many small steps rather than one forward pass. Much of this series (posts 5, 9, and 10) is about how that price was negotiated down from a thousand steps toward one.

## The idea in one paragraph

Here is the whole series in miniature. Take an image and add a small amount of Gaussian noise. Add a little more, and a little more, until after enough steps nothing remains but static. That destruction is easy, mechanical, and requires no learning. Now train a neural network to undo *one small step* of it: given a slightly-noisier image, predict the noise that was added. Undoing one small denoising step is vastly easier than generating an image outright — and if you can undo one step, you can chain hundreds of undoings to walk from pure static all the way back to a clean image that never existed. Generation becomes **iterative refinement**: start from noise, remove a little, repeat. Every system in this series — Stable Diffusion's latents, classifier-free guidance, diffusion transformers, flow matching, video models — is an optimization of some stage of that walk.

The takeaway: generation is **sampling from a learned distribution**, not predicting a single answer, and natural images live on a thin **manifold** inside an astronomically large pixel space. The first-generation models each sacrificed something structural — **VAEs** average their way to blur, **GANs** buy sharpness with instability and **mode collapse**, autoregressive models buy coverage with crippling slowness. Diffusion models escaped the trilemma by decomposing generation into hundreds of tiny, individually-easy denoising steps, trained with a stable regression loss — trading away only sampling speed, a price the rest of this series shows being bought back.

## Key takeaways

- A generative model's job is to **sample new points from the data distribution** — fundamentally harder than classification because there is no single right answer, and natural images occupy a thin **manifold** in a huge pixel space.
- **VAEs** (encoder → latent → decoder) train stably and cover the distribution, but pixel-wise likelihood makes them output averages — hence **blur**. The VAE idea returns as Stable Diffusion's compression layer in post 6.
- **GANs** replace likelihood with an adversarial game, producing **sharp** samples — but the game is unstable and permits **mode collapse**: fooling the discriminator without covering the data.
- The generative **trilemma**: quality, diversity/coverage, training stability — pre-2020 families picked two.
- Diffusion's move: make generation **iterative refinement** — destroy images with gradual noise, learn only to undo one small step, chain the undoings. Stable training, full coverage, GAN-level quality; the cost is multi-step **sampling speed**, which posts 5, 9, and 10 claw back.

## Further reading

- [Generative adversarial network — the adversarial game and its failure modes](https://en.wikipedia.org/wiki/Generative_adversarial_network)
- [Variational autoencoder — latent-variable generation and why samples blur](https://en.wikipedia.org/wiki/Variational_autoencoder)
