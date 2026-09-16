# From Dense to Sparse: Why Modern LLMs Changed Shape

*The frontier language models of the last few years share a structural secret that isn't obvious from the outside: most of them aren't dense. They're sparse — built from Mixture-of-Experts layers that let a model have hundreds of billions of parameters while only using a fraction of them on any given token. Understanding why models moved from dense to sparse is the key to understanding how modern LLMs are actually built.*

Everyone knows LLMs got bigger. Fewer people know they also changed *shape*. This series is about the architecture of modern large language models — how the frontier ones are actually constructed — with Mixture of Experts at the center, surrounded by the attention and long-context techniques that make them work. This opening post explains the problem that drove the shift from dense to sparse models, because that problem is the "why" behind almost every architectural choice that follows.

## The dense transformer and its scaling wall

A standard ("dense") transformer LLM processes every token through *every* parameter. Each layer has an attention block and a feed-forward block (FFN), and for every token, the full weight matrices of both are used. Scaling laws showed that making these models bigger — more parameters, more data, more compute — reliably made them better, so the field scaled hard.

But dense scaling hits a wall: **in a dense model, compute cost per token scales directly with parameter count.** Double the parameters and you roughly double the FLOPs needed to process each token, at training *and* at inference, forever. You want the *capacity* that more parameters bring (more knowledge, more capability), but you pay for it on every single token you ever process. Beyond a point, dense scaling becomes economically and physically impractical — the compute to train and, especially, to *serve* an ever-larger dense model grows without bound.

This is the tension that reshaped LLM architecture: **capacity and compute-per-token are welded together in a dense model, and we'd like to pry them apart** — to add parameters (capacity) without adding proportional compute to every token.

## The sparse idea: don't use all the parameters every time

The insight behind Mixture of Experts is deceptively simple: **not every parameter needs to be involved in processing every token.** What if a model had a huge pool of parameters, but each token only *activated a small, relevant subset* of them?

That's **conditional computation** / **sparse activation**. Instead of every token flowing through the entire network, the model *routes* each token to a small selection of specialized sub-networks ("experts"), using only those for that token. The total model can be enormous — hundreds of billions of parameters — while the compute spent on any one token stays small, because only a few experts fire.

This pries apart the two things dense models welded together:
- **Total parameters** (the model's capacity — how much it can know) can be very large.
- **Active parameters per token** (the compute cost) stays small and roughly constant.

A sparse model can have, say, 10× the total parameters of a dense one while using similar compute per token — buying capacity almost for free on the compute-per-token axis. That decoupling is the whole game, and it's why the frontier moved sparse.

## Mixture of Experts in one sentence

**Mixture of Experts (MoE)** replaces the dense feed-forward block in transformer layers with *many* parallel feed-forward "experts" plus a small **router** that, for each token, picks a few experts to use. The token goes through only those chosen experts; the rest sit idle for that token.

So a model might have 8, 64, or hundreds of experts per MoE layer but route each token to just 1 or 2 of them. The parameters of all experts count toward the model's *total* size (and must all exist), but only the selected experts' parameters are *computed* per token. That's how you get a model with, for example, ~10× the parameters at ~2× the per-token compute — a dramatically better capacity-per-FLOP trade. The idea traces back to work on sparsely-gated MoE layers and was scaled up in models like the Switch Transformer and, in the open-weights world, Mixtral. We'll build up exactly how the routing and experts work over the next posts.

## Why this matters for understanding modern LLMs

The dense-to-sparse shift isn't a niche optimization; it's a defining feature of how frontier models are built, and it explains a lot of otherwise-puzzling facts:
- **Why total and "active" parameter counts differ.** When you see a model described as "47B total, 13B active," that's MoE — huge capacity, modest per-token compute. The two numbers exist *because* the model is sparse.
- **Why big models can be relatively cheap to serve per token.** Sparse activation is why a very large model can have inference costs closer to a much smaller dense one.
- **Why serving them is hard in a different way.** As we'll see, MoE trades a *compute* saving for a *memory* cost (all experts must be loaded even though few are used) — which reshapes the serving problem.

The rest of the series builds the full picture: the transformer backbone MoE sits inside (post 2), how experts and routing actually work (posts 3–4), the training and serving consequences (post 5), and the parallel story of scaling *context length* with efficient attention (posts 6–7), before assembling the anatomy of a modern frontier model (post 8). The through-line is this post's tension: modern LLM architecture is largely a set of clever answers to "how do we get more capability without paying proportionally more compute — per token, and per unit of context?" MoE is the answer on the parameter axis; efficient attention is the answer on the context axis.

## Key takeaways

- Modern frontier LLMs changed *shape*, not just size: most are **sparse (Mixture of Experts)**, not dense — a structural fact that isn't obvious from the outside but explains how they're built.
- A **dense** transformer runs every token through every parameter, so **compute per token scales directly with parameter count** — you pay for added capacity on every token forever, which hits an economic/physical wall.
- The **sparse idea** (conditional computation): each token activates only a small, relevant subset of parameters, **decoupling total parameters (capacity) from active parameters per token (compute)** — add capacity without proportional per-token compute.
- **Mixture of Experts** replaces the dense feed-forward block with many parallel "experts" plus a **router** that sends each token to just 1–2 of them — so a model can have huge *total* parameters but small *active* per-token compute (e.g. "47B total, 13B active").
- This decoupling explains modern LLM facts (total-vs-active parameter counts, large models cheap-per-token to serve) and reshapes serving (a compute saving traded for a memory cost) — the series' through-line is getting more capability without proportionally more compute, per token (MoE) and per unit of context (efficient attention).

## Further reading

- [Outrageously Large Neural Networks: The Sparsely-Gated Mixture-of-Experts Layer — Shazeer et al. (arXiv:1701.06538)](https://arxiv.org/abs/1701.06538)
- [Switch Transformers — Fedus et al. (arXiv:2101.03961)](https://arxiv.org/abs/2101.03961)
