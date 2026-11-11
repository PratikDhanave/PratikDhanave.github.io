# Flow Matching — Straightening the Path from Noise to Image

*Diffusion arrived at "follow a velocity field from noise to data" the hard way — through Markov chains, variational bounds, and reverse-time SDEs. Flow matching asks the question that framing begs: if generation is just transporting noise to data along a path, why inherit a curved path from a noising process you never actually cared about? Why not simply choose the path — and choose it straight? The answer now trains the frontier: Stable Diffusion 3, Flux, and much of the current video generation stack are flow-matching models.*

This is post 9 of [Diffusion Models from First Principles](/blog/series/diffusion-models-from-first-principles/). Post 4 ended with the probability flow ODE and a promise; post 5 hit a ~10-step floor caused by path curvature. This post cashes both in. The spirit is the one that recurs across this blog's systems series: when a derivation gets simpler the second time a field writes it, the simpler form wins — and gets adopted.

## Generation as transport

Strip away diffusion's history and the task that remains: move samples from an easy distribution (Gaussian static) to the data distribution. Any smooth **velocity field** — an assignment of "which way and how fast" to every point in space at every time along the way — defines such a transport: drop a noise sample in, integrate the ODE, read out where it lands. Post 4 showed diffusion *implicitly* builds one such field (the probability flow ODE, with velocity derived from the learned score). **Flow matching** makes the field the primary object: pick the paths you want, then regress a network onto their velocities.

The construction is disarmingly direct. Pair each training image with a random noise sample. Connect them with a path — and take the simplest possible choice, the **straight line**: at time t, the point is just the appropriately-weighted blend of noise and image. The velocity along that path is constant: *image minus noise*. Training: sample an image, a noise draw, and a random time; form the blend; train the network to predict the difference vector, with mean squared error.

That is the whole recipe — compare it to post 3. No noise schedule to design (the straight-line blend *is* the schedule, and a particularly clean one: this is the "signal-to-noise ratio falling smoothly" framing post 2 alluded to, made literal). No variational bound; the thing regressed is the thing sampling uses. DDPM's noise-prediction target and the flow velocity are, once again, linear relatives of each other — flow matching is not a different kind of model so much as diffusion with the cleanest possible parameterization. The frameworks converged: modern codebases implement one noising-blend + velocity-regression core and recover classic diffusion as a setting.

## Straight-ish, not straight — and rectification

A subtlety keeps the theory honest. Individual training pairs are connected by straight lines, but the *learned* field at any point must average over every (noise, image) pair whose line passes through that point — random pairing means massive crossing, and the average of crossing straight lines is a **curved** marginal flow. So a flow-matching model's actual sampling trajectories are straighter than diffusion's, empirically, but not perfectly straight; you still integrate with a solver over multiple steps.

**Rectified flow** turns straightening into an explicit, iterable operation. Train a first flow; generate with it, recording which noise sample produced which image; *re-pair* the training data using those generated couplings — each noise point now matched to the image its own flow transported it to, eliminating the crossings — and retrain on the straightened pairs ("reflow"). Each round makes trajectories straighter; genuinely straight paths can be followed in **one Euler step**. This is one of the two principled routes to few-step generation (post 10's distillation is the other), and the Stable Diffusion 3 lineage trains directly on the rectified-flow formulation, with a practical refinement: sampling intermediate times non-uniformly, concentrating training where prediction is hardest (the middle of the path), measurably improves large-model results.

## Why the frontier switched

The migration (SD3, Flux, and the bulk of current video systems) was driven by compounding practical wins rather than one theoretical knockout. **Simplicity**: fewer coupled design choices (schedules, prediction-target variants, loss weightings collapse into the path choice), which matters more as everything else — data, architecture (post 8's DiT), parallelism — gets harder. **Trainability at scale**: the well-conditioned constant-velocity target trains stably in exactly the large-batch, high-resolution regimes frontier systems occupy. **A cleaner route to speed**: straighter paths ease the solver's job today and define the one-step limit via reflow. **The same interfaces**: CFG (post 7) applies verbatim — run the velocity network conditioned and unconditioned, extrapolate; DiT backbones (post 8) slot in unchanged; post 6's latent spaces host it all. Everything the series built survives; only the path got straighter.

The takeaway: flow matching reframes generation as **transport along a chosen velocity field** — pair noise with data, connect with **straight lines**, regress the network onto the constant velocity (*image minus noise*) at random blend times. Crossing paths keep the learned marginal flow merely straight-*ish*, so **rectified flow** re-pairs data with the model's own couplings and retrains, straightening toward one-step generation. With simpler training, scale-friendly conditioning of the objective, and full compatibility with CFG, DiT, and latents, it became the frontier's default formulation — diffusion, rewritten the simple way.

## Key takeaways

- Generation = **transport**: a velocity field carrying Gaussian noise to data; diffusion's probability flow ODE (post 4) was one such field, derived the hard way. Flow matching chooses the field directly.
- The recipe: blend noise and image at a random time along a **straight line**; regress the network onto the constant velocity **image − noise** with MSE. Schedule, prediction target, and loss weighting collapse into one path choice — and classic diffusion reappears as a special setting.
- Random pairing makes lines cross, so the learned marginal flow is **curved anyway** — straighter than diffusion's, still multi-step.
- **Rectified flow / reflow**: re-pair noise→image using the model's own generations and retrain; each round straightens trajectories, approaching **one-step** sampling — the SD3-lineage training formulation (with hardest-in-the-middle time sampling as a scale refinement).
- Adoption logic: fewer knobs, stable large-scale training, a principled speed path — while **CFG, DiT backbones, and latent spaces carry over unchanged**.

## Further reading

- [Flow-based generative model — generation by invertible transport, the family flow matching streamlines](https://en.wikipedia.org/wiki/Flow-based_generative_model)
- [Diffusion model — the score/SDE formulation flow matching re-derives simply](https://en.wikipedia.org/wiki/Diffusion_model)
