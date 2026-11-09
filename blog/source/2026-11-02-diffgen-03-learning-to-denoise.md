# Learning to Denoise — DDPM and the Loss That Trains Every Image Model

*The reverse of destruction is generation — but only if a network can learn to run one small step of the destruction backwards. The surprise at the heart of DDPM is how plain the training recipe turned out to be: corrupt an image, ask the network which noise was added, score it with mean squared error. No adversary, no instability — a regression loss so simple it reads like a tutorial exercise, hiding a derivation that connects it to maximum likelihood.*

This is post 3 of [Diffusion Models from First Principles](/blog/series/diffusion-models-from-first-principles/). Post 2 built the forward process — the fixed Markov chain from image to static, with a closed-form jump to any step. This post builds the half that learns: the reverse process, the denoising objective, and the training and sampling loops that remain essentially unchanged in every production system since.

## The reverse process: Gaussian meets Gaussian

Generation means walking the forward chain backwards: start from pure static (trivially sampleable, as post 2 arranged) and repeatedly produce a slightly *less* noisy image until a clean one remains. Each backward step must answer: given this noisy image at this step, what distribution of slightly-cleaner images could have preceded it?

Exactly reversing the chain is intractable — it would require already knowing the data distribution, which is the thing we're trying to learn. But here the forward process's careful design pays off: **when the forward steps are small and Gaussian, each true reverse step is itself approximately Gaussian**. That reduces the reverse step from "describe an arbitrary distribution over images" to "name the mean (and variance) of a Gaussian" — and naming a mean is just regression, something neural networks do superbly. The **reverse process** is therefore a learned Markov chain of Gaussian steps, mirroring the fixed forward chain, with a network supplying each step's mean.

## The reparameterization: predict the noise

The network could predict the denoised mean directly. **Denoising diffusion probabilistic models (DDPM)** found a reparameterization that works markedly better in practice: have the network predict **the noise that was added**. Because the closed-form jump (post 2) writes the noisy image as *known-scale × clean image + known-scale × noise*, knowing the noisy image and the noise is the same as knowing the clean image — the three are linearly related. Predicting the noise, predicting the clean image, or predicting the step's mean are mathematically interchangeable targets; they differ in how they weight errors across the chain's steps.

Why does noise prediction train better? At heavily-corrupted steps, the clean image is almost unknowable but the *noise* is almost the whole input — the target stays well-scaled across the entire chain rather than vanishing at one end. The derivation from maximum likelihood produces a per-step weighted objective; DDPM's empirical finding is that *dropping the weights* — treating every step's noise-prediction error equally, as plain **mean squared error** — produces better samples than the "correct" weighting. The simple loss is not a corner cut; it is the published recipe.

## The training loop, in full

The entire training algorithm fits in four lines:

1. Draw a real image from the dataset.
2. Draw a random step of the chain, and a fresh sample of Gaussian noise.
3. Form the noisy image with the closed-form jump; feed the noisy image and the step number to the network.
4. Minimize mean squared error between the network's noise prediction and the actual noise used.

Every property that made diffusion win the trilemma (post 1) is visible here. The loss is a smooth regression — no adversarial game, so no instability or mode collapse. The objective descends from maximum likelihood, so the model is pushed to cover the whole distribution, not just fool a judge. Each batch samples random images at random corruption levels, so the network sees the full spectrum from "sharpen fine detail" to "hallucinate global structure from near-static" every few batches. One network, conditioned on the step number, learns the entire family of denoisers.

## The sampling loop

Generation reverses the chain: sample pure Gaussian static, then for each step from the last to the first, have the network predict the noise, use the prediction to compute the mean of the slightly-cleaner image, and — crucially — **add back a small amount of fresh noise** before the next step. That injected noise is not a bug: the reverse step is a Gaussian *distribution*, and sampling from it means mean plus scaled randomness. Skipping it collapses the walk onto an over-smoothed path. (Post 5 shows a principled way to remove the randomness — DDIM — which is a different sampler, not a shortcut inside this one.)

Run the loop for the full thousand steps and a clean image emerges that exists nowhere in the training set. The cost is also visible: **a thousand network evaluations per image**, versus a GAN's single forward pass. This is the price post 1 flagged, and posts 5, 9, and 10 progressively negotiate it down.

The takeaway: small Gaussian forward steps make each true reverse step **approximately Gaussian**, reducing generation to regression — a network names each backward step's mean. **DDPM** parameterizes that regression as **noise prediction**, trained with unweighted **mean squared error** over random images at random corruption levels: stable, mode-covering, and derived (then deliberately simplified) from maximum likelihood. Sampling walks the chain backwards with fresh noise injected at each step — a thousand evaluations per image, the cost the rest of the series works to erase.

## Key takeaways

- The **reverse process** is a learned Markov chain mirroring the forward one; because small Gaussian steps are approximately Gaussian to reverse, each step only needs a predicted **mean** — generation becomes regression.
- **DDPM's reparameterization**: predict the **added noise** rather than the clean image — the targets are linearly interchangeable, but noise prediction stays well-scaled across the whole chain and trains better.
- The loss is unweighted **mean squared error** on noise prediction — the maximum-likelihood derivation gives per-step weights, and DDPM's empirical result is that dropping them *improves* samples.
- The training loop is four lines: random image, random step, closed-form corruption, MSE on the noise. Stable (no adversary), mode-covering (likelihood-based), and parallel across steps.
- Sampling injects **fresh noise each backward step** — the reverse step is a distribution, not a point estimate — and costs ~a thousand network evaluations per image, the price tackled in posts 5, 9, and 10.

## Further reading

- [Diffusion model — DDPM, the reverse process, and the training objective](https://en.wikipedia.org/wiki/Diffusion_model)
- [Mean squared error — the loss that trains the denoiser](https://en.wikipedia.org/wiki/Mean_squared_error)
