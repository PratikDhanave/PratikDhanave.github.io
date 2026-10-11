# CNN Architectures — How Networks Got Deeper and Better

*Once convolution proved it could crack vision, the race was on to build better CNNs — and the story of how they improved is a compact lesson in deep learning itself. From AlexNet to VGG to ResNet, each landmark architecture solved a specific problem that was blocking progress, and the solutions (depth, small filters, skip connections) became foundational ideas used far beyond vision. This post traces that evolution and the principles it taught.*

Post 3 built the CNN. This post is about how CNN *architectures* evolved — not to memorize model names, but because each breakthrough taught a transferable lesson about building deep networks. The arc from AlexNet to ResNet is one of the most instructive stories in deep learning, and its ideas echo across the whole field.

## The breakthrough and the deeper-is-better era

**AlexNet (2012)** is where modern deep learning began: a CNN (post 3) that crushed the ImageNet image-recognition benchmark, dramatically beating classical methods and proving that *learned* features beat hand-designed ones (post 2) at scale. It worked because three things came together — a deep enough CNN, a huge labeled dataset (ImageNet), and GPUs fast enough to train it. That combination (architecture + data + compute) is the recipe behind essentially every deep-learning breakthrough since, and AlexNet was the proof of concept.

AlexNet's success launched a clear trend: **deeper networks are more powerful.** More layers mean a richer feature hierarchy (post 3) — more levels between pixels and concepts — so researchers pushed depth:
- **VGG (2014)** showed that stacking many *small* (3×3) filters in deep, uniform layers worked better than fewer large filters. The lesson — *small filters stacked deep* — became a standard design principle, because stacking small filters achieves the same receptive field as a large one with fewer parameters and more nonlinearity.
- Networks kept getting deeper because depth kept helping... until it suddenly stopped, which exposed the problem that the next breakthrough had to solve.

## The depth problem and ResNet's fix

As networks grew past ~20 layers, something counterintuitive happened: **deeper networks got *worse*, even on training data.** This wasn't overfitting (they were worse at *training*, not just testing) — it was a *training* failure. Very deep networks became extremely hard to optimize, largely due to the **vanishing gradient problem**: the learning signal (gradient) has to propagate back through every layer, and across dozens of layers it shrinks toward zero, so early layers barely learn. Depth, the thing that helped, had become impossible to train past a point. The field was stuck.

**ResNet (2015)** solved it with an idea so simple it's almost shocking: the **residual connection** (skip connection). Instead of each block of layers having to learn a full transformation, it learns a *residual* — the *change* to add to its input — and the input is passed directly forward via a "skip" that bypasses the block. In effect, each block only has to learn "what to add" to what it already has, and the skip connections give the gradient a direct highway back through the network, bypassing the vanishing-gradient bottleneck.

The impact was enormous:
- **It made very deep networks trainable** — suddenly 50, 100, even 1000+ layer networks trained fine and kept improving, shattering the depth barrier. ResNet won ImageNet and became the default backbone for years.
- **Skip connections became a universal tool.** The residual idea turned out to be fundamental far beyond vision — **transformers use residual connections in every block**, so the architecture behind modern LLMs directly inherits ResNet's insight. A fix for a vision problem became a building block of all deep learning.

ResNet is the pivotal lesson: a simple architectural idea (pass the input forward, learn only the residual) unlocked depth that was otherwise untrainable, and that idea generalized everywhere. It's the single most influential CNN architecture, and its skip connection is one of the most important ideas in all of deep learning.

## What the evolution teaches

The arc from AlexNet to ResNet (and beyond, to efficient architectures and the vision transformers of post 6) teaches principles that transfer well past CNNs:

- **Architecture + data + compute is the recipe.** AlexNet worked because all three aligned; this remains the pattern for breakthroughs (including LLMs). Great architectures need the data and compute to match.
- **Depth is powerful but hard to train.** More layers give richer representations, but naive depth hits optimization walls — so much of deep-learning progress is *enabling* depth (better initialization, normalization, and especially skip connections). Depth is the goal; trainability is the obstacle.
- **The right architectural idea unlocks a barrier.** VGG's small-filters and ResNet's residual connections weren't incremental tweaks — each removed a specific blocker (parameter efficiency, vanishing gradients) and enabled a leap. Progress often comes from one elegant idea that makes the previously-impossible trainable.
- **Good ideas generalize.** Residual connections, born to train deep CNNs, became core to transformers and thus to modern AI broadly. The best architectural insights escape their original domain.
- **Backbones and transfer.** These architectures (ResNet especially) became reusable **backbones** — pretrained feature extractors that everyone builds on via transfer learning (post 7), rather than training from scratch. The evolution of architectures is also the evolution of the shared foundation the whole field reuses.

The practical upshot: you rarely design a CNN from scratch — you use a proven architecture (a ResNet or a modern successor) as a backbone and adapt it (post 7). But knowing *why* these architectures look the way they do — depth for richer features, small filters for efficiency, skip connections to make depth trainable — lets you understand what you're using, choose sensibly among architectures, and recognize these same ideas when they reappear (as they constantly do) across deep learning. The CNN architecture story isn't vision trivia; it's a distilled course in how deep networks are made to work.

The throughline: CNN architectures evolved through landmark leaps, each teaching a transferable lesson. **AlexNet (2012)** launched modern deep learning by crushing ImageNet — proving learned features beat hand-designed ones and establishing the **architecture + data + compute** recipe. The **deeper-is-better** era followed (**VGG**'s *small 3×3 filters stacked deep* becoming a standard principle), until networks past ~20 layers got *worse at training* — the **vanishing-gradient** depth barrier. **ResNet (2015)** shattered it with the **residual/skip connection** (learn only the change to add; give gradients a highway back), making 100+ layer nets trainable — and that idea **generalized everywhere**, including the residual connections in every **transformer** block (so LLMs inherit ResNet's insight). The lessons: architecture+data+compute is the recipe, depth is powerful but hard to train (progress = *enabling* depth), one elegant idea unlocks a barrier, good ideas escape their domain, and these architectures become reusable **backbones** for transfer learning (post 7) — so you adapt a proven CNN rather than design one.

## Key takeaways

- **AlexNet (2012)** began modern deep learning by crushing ImageNet — proving **learned features beat hand-designed ones** (post 2) at scale, and establishing the **architecture + data + compute** recipe behind essentially every deep-learning breakthrough since.
- It launched a **deeper-is-better** era (more layers = richer feature hierarchy): **VGG (2014)** showed **small 3×3 filters stacked deep** beat fewer large filters (same receptive field, fewer parameters, more nonlinearity) — a standard design principle.
- Past ~20 layers, **deeper networks got *worse at training*** (not overfitting — an optimization failure), largely from the **vanishing-gradient problem** (the signal shrinks toward zero propagating back through many layers) — the depth barrier that stalled the field.
- **ResNet (2015)** fixed it with the **residual/skip connection**: each block learns only the *residual* (change to add) while the input skips forward, giving gradients a direct highway back — making **50/100/1000+ layer networks trainable**, and the idea **generalized universally** (every **transformer** block uses residual connections, so LLMs inherit it).
- Lessons that transfer past CNNs: architecture+data+compute is the recipe; **depth is powerful but hard to train** (progress = enabling depth via normalization, init, skip connections); **one elegant idea unlocks a barrier**; good ideas escape their domain; and these architectures become reusable **backbones** for transfer learning (post 7) — so in practice you **adapt a proven architecture** (ResNet/successors), not design from scratch.

## Further reading

- [Convolutional neural network — architectures and their evolution](https://en.wikipedia.org/wiki/Convolutional_neural_network)
- [Residual neural network — ResNet and skip connections](https://en.wikipedia.org/wiki/Residual_neural_network)
