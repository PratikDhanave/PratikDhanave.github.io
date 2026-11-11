<!-- Markdown version for AI agents and readers. Canonical: https://pratikdhanave.com/blog/posts/diffgen-02-the-forward-process.html -->

# The Forward Process — Destroying Images with Noise, Carefully

*Diffusion models begin with the only part of the pipeline that involves no learning at all: a fixed, mechanical procedure that gradually turns any image into pure static. It seems almost too simple to matter — yet every design choice in it (Gaussian noise, small steps, a schedule, a closed-form shortcut) is load-bearing for everything the model later learns. Understanding the destruction is half of understanding the generation.*

This is post 2 of [Diffusion Models from First Principles](/blog/series/diffusion-models-from-first-principles/). Post 1 framed generation as sampling from a learned distribution and previewed the core idea — destroy, then learn to un-destroy. This post builds the destruction half precisely, because the reverse process (post 3) is defined entirely in its terms.

## A Markov chain of small corruptions

The **forward process** (also called the *diffusion process*) is a chain of steps. Start with a real image from the training set — call it the step-zero image. At each step, produce a slightly noisier version of the previous one: scale the image down a whisker and add a small amount of **Gaussian noise**. Repeat for a fixed number of steps — the original formulation used a thousand. By the final step, no trace of the image's structure survives; what remains is statistically indistinguishable from pure Gaussian static.

Two structural properties matter. First, the chain is **Markov**: each step depends only on the immediately preceding one, not on the history. Second, the chain is *fixed* — there are no learned parameters anywhere in it. The noise amounts are set by a predetermined **noise schedule**, chosen before training begins. All learning happens later, in the reverse direction.

Why Gaussian noise, specifically? Because Gaussians compose beautifully: the sum of two Gaussians is a Gaussian, scaling a Gaussian keeps it Gaussian. That closure property is what makes the math of the next two sections possible — and it has a deeper consequence, previewed in post 3: when the steps are small, *reversing* a Gaussian corruption step is itself (approximately) a Gaussian step. The entire learnability of diffusion rests on that symmetry.

## The noise schedule

The **noise schedule** specifies how much noise each step adds — equivalently, how fast signal gives way to static. It is a small design dial with outsized effects:

- A **linear schedule** adds noise at a steady rate. It works, but it spends many late steps on images that are already essentially pure static — wasted resolution at the destroyed end of the chain.
- A **cosine-style schedule** destroys information more gently at the start and more evenly across the chain, keeping more steps in the regime where the image is partially recognizable — which is where the interesting learning happens.

A useful way to think about the schedule: it allocates the model's *practice time*. Each step of the chain becomes a training example of "remove this much noise." The schedule decides how those examples are distributed between nearly-clean images (where the task is fine detail restoration) and nearly-destroyed ones (where the task is conjuring global structure). Later work often reframes the schedule in terms of the **signal-to-noise ratio** falling smoothly from high to zero across the chain — a framing that post 9's flow matching makes even more explicit.

## The shortcut: jump to any step in one draw

Simulating a thousand sequential corruption steps per training example would be ruinously slow. The closure property of Gaussians saves us: composing many scale-and-add-Gaussian-noise steps is itself just one scale-and-add-Gaussian-noise step. So there is a **closed form** for the forward process at any step: for any chosen step, the noisy image equals the original image scaled by a known factor, plus Gaussian noise scaled by a complementary known factor. Both factors are determined entirely by the schedule.

This single fact shapes diffusion training more than any other. It means a training step can be: pick a real image, pick a *random* step of the chain, and produce the corresponding noisy image **in one draw** — no simulation of the intervening steps. Training can sample the chain's steps uniformly at random, in any order, in parallel across a batch. The forward process is not just a conceptual device; it is a random-access corruption oracle.

## What the endpoint buys us

The chain is designed so that its final distribution is a **standard Gaussian** — pure static with known statistics, containing zero information about the input image. This endpoint is the whole point. Generation (post 3 onward) must start *somewhere*, and that somewhere must be a distribution we can sample from exactly, with no model and no data. The forward process is engineered backwards from this requirement: it exists to connect the unknowable distribution of natural images to a trivially-sampleable one, through a sequence of steps small enough that each is individually learnable to reverse.

It is worth pausing on how unusual this is as a design pattern. Most of machine learning defines a model first and a training signal second. Diffusion defines a *destruction* first — fixed, learning-free, analytically tractable — and the destruction then defines both the training data (noisy image, noise pair at every step) and the generation procedure (walk the chain backwards). Get the forward process right and the rest of the system is, in a precise sense, implied.

The takeaway: the forward process is a fixed **Markov chain** that scales the image down and adds **Gaussian noise** at each of many small steps, under a predetermined **noise schedule**, ending at a **standard Gaussian** that carries no information about the input. Gaussian closure gives a **closed form** to jump to any step in one draw — making training random-access instead of sequential — and small Gaussian steps are approximately Gaussian to reverse, which is the property the learned half of the system (post 3) will exploit.

## Key takeaways

- The **forward process** is a fixed, learning-free **Markov chain**: repeatedly scale the image slightly toward zero and add a small dose of **Gaussian noise**, until only static remains.
- **Gaussian noise is chosen for closure**: Gaussians compose into Gaussians, which yields the closed-form shortcut — and small Gaussian steps are approximately Gaussian to *reverse*, the fact post 3's learned model depends on.
- The **noise schedule** (linear vs cosine-style) controls how fast signal dies and allocates training practice between fine-detail and global-structure regimes — a small dial with large sample-quality effects.
- The **closed-form jump** lets training corrupt any image to any step in one draw — no sequential simulation — enabling uniform random sampling of steps across a batch.
- The chain's endpoint is a **standard Gaussian**: a known, data-free distribution that generation can start from. The forward process exists to connect the image distribution to it in individually-reversible steps.

## Further reading

- [Diffusion model — the forward/reverse process framework](https://en.wikipedia.org/wiki/Diffusion_model)
- [Gaussian noise — the corruption applied at every step](https://en.wikipedia.org/wiki/Gaussian_noise)

---

Author: Pratik Dhanave (https://pratikdhanave.com) | Published: 2026-11-01
Canonical: https://pratikdhanave.com/blog/posts/diffgen-02-the-forward-process.html
Attribution: please link the canonical URL when citing or quoting this post.
