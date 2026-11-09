# The Score-Based View — Gradients, SDEs, and Why Denoising Learns Direction

*DDPM looks like a clever trick: predict noise, subtract it, repeat. The score-based view reveals it as something deeper — the denoiser is secretly learning the gradient of the data distribution, the arrow that points from anywhere in image space toward "more like a real image." Two research threads, denoising and score matching, turned out to be the same thing seen from different angles, and their unification under stochastic differential equations is what every modern sampler and flow-matching method builds on.*

This is post 4 of [Diffusion Models from First Principles](/blog/series/diffusion-models-from-first-principles/). Posts 2–3 built the discrete chain: corrupt in steps, learn to reverse each one. This post rebuilds the same system in continuous form, because the continuous view is where sampling speed (post 5), flow matching (post 9), and most post-2021 progress actually live.

## The score: an arrow toward the data

For any probability distribution, the **score** is the gradient of its log-density with respect to the *input* — not with respect to model parameters, as gradients usually are in ML. At any point in image space, the score is a vector pointing in the direction of increasing probability: "images slightly more plausible than this one lie *that* way."

If you had the score of the image distribution everywhere, you could generate images without ever writing down the distribution itself: start anywhere and climb. **Langevin dynamics** makes this precise — repeatedly step in the score's direction while injecting a bit of random noise, and the points you visit will, in the limit, be distributed according to the target distribution. The noise injection matters: pure hill-climbing would collapse onto a few peaks, while noisy ascent *explores* the distribution in proportion to its density. If that "step toward the data, plus a little noise" loop sounds exactly like DDPM sampling — that is the punchline, made precise below.

## Denoising is score estimation

The score is unlearnable head-on — natural images concentrate on a thin manifold (post 1), so almost everywhere the density is effectively zero and its gradient uninformative. The fix mirrors post 2: *blur the distribution with Gaussian noise*. The noised distribution spreads over all of image space, giving a well-defined, learnable score everywhere; learn scores at many noise levels and you get a sequence of progressively sharper arrows, usable coarse-to-fine.

Then comes the identity that fuses the two research threads: **for Gaussian corruption, the score of the noised distribution is the expected noise, negated and rescaled**. Intuitively: if you can say which direction is "toward clean images," you can say which component of the input is noise — they are the same vector read in opposite directions. So DDPM's noise-prediction network (post 3) *is* a score estimator at every noise level of its chain. Denoising diffusion and **score matching** are one method with two derivations — one from likelihood, one from geometry.

## The continuous limit: two differential equations

Let the thousand-step chain's steps shrink toward zero and the discrete corruption becomes a **stochastic differential equation (SDE)**: a continuous-time process that drifts the image toward zero while continuously injecting Gaussian noise. The forward SDE is fixed and learning-free, exactly as the discrete chain was. The classical theory of such processes supplies the gift: a **reverse-time SDE** exists, running from static back to images, and the only unknown in it is — the score. Learn the score (which post 3 already showed how to do, via denoising), plug it into the reverse SDE, and generation is the numerical solution of that equation. DDPM sampling turns out to be one particular, rather basic, numerical solver for it.

The same theory yields a second, stranger object: the **probability flow ODE** — an *ordinary* differential equation, with no randomness at all, whose solutions trace smooth deterministic paths from static to images while producing exactly the same distribution of outputs as the SDE. Same score network, same endpoints, two kinds of path: a jittery random walk or a smooth glide.

## Why the reframe matters

The ODE is the practically consequential one, for three reasons. **Speed**: smooth deterministic paths can be followed with large, sophisticated solver steps — tens of evaluations instead of a thousand — which is post 5's subject. **Invertibility**: the ODE runs both directions, so a *real* image can be driven back to its unique point in noise space and forward again — the basis of image editing and interpolation techniques. **Reframing**: once generation is "follow a learned velocity field along a smooth path," a question becomes natural — why derive the path from a noising process at all, instead of just *choosing* a straight one? That question is flow matching, post 9.

The takeaway: the **score** — the gradient of log-density with respect to the image — is an arrow pointing toward more-plausible images, and **Langevin dynamics** turns that arrow into a sampler. For Gaussian corruption, score estimation and **denoising are the same computation**, so DDPM's network was learning scores all along. In the continuous limit the chain becomes a forward **SDE** with a score-driven reverse SDE — and an equivalent deterministic **probability flow ODE** whose smooth paths make fast sampling, inversion, and ultimately flow matching possible.

## Key takeaways

- The **score** is the gradient of the log-density *with respect to the input image*: at every point in image space, an arrow toward higher probability. **Langevin dynamics** (score steps + injected noise) samples a distribution from its score alone.
- Scores are only learnable after **Gaussian smoothing** — noise the distribution at many levels and learn an arrow at each, coarse to fine; the thin data manifold makes the unsmoothed score useless.
- The fusion identity: under Gaussian corruption, **the score is the (negated, rescaled) expected noise** — DDPM's noise predictor is a score estimator; denoising and score matching are one method.
- In the continuous limit, corruption is a fixed forward **SDE**; a classical result gives a **reverse-time SDE** whose only unknown is the score — generation is numerically solving it, and DDPM sampling is one basic solver.
- The **probability flow ODE** generates the same distribution along smooth deterministic paths — enabling fast solvers (post 5), image inversion/editing, and the "why not straighten the path?" question that becomes flow matching (post 9).

## Further reading

- [Langevin dynamics — sampling by noisy gradient ascent on log-probability](https://en.wikipedia.org/wiki/Langevin_dynamics)
- [Stochastic differential equation — continuous processes with drift and noise](https://en.wikipedia.org/wiki/Stochastic_differential_equation)
