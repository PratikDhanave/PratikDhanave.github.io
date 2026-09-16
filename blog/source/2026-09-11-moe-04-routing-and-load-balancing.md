# Routing and the Load-Balancing Problem

*The router is where Mixture of Experts succeeds or fails. Left to its own devices, it tends to collapse — sending most tokens to a handful of favorite experts while the rest starve, wasting the model's capacity. Making routing spread load evenly, without hurting quality, is the central engineering challenge of MoE, and the techniques for it are what separate a working sparse model from a broken one.*

The previous post introduced the router that picks top-k experts per token. This post confronts what goes wrong with it. Routing sounds simple — score experts, pick the best — but naive routing produces a pathology called expert collapse, and the fixes (load-balancing losses, capacity limits) are essential, subtle, and shape how MoE models train and behave.

## Why routing wants to collapse

Here's the problem. The router learns which experts to use, and there's a self-reinforcing feedback loop lurking in that: early in training, a few experts happen to be slightly better, so the router sends them more tokens; because they get more tokens, they train more and get better still; so the router sends them *even more*. The rich get richer.

The result is **expert collapse** (or load imbalance): a small number of experts receive most of the tokens and do most of the work, while many experts are rarely or never used. This is a disaster for MoE specifically, because the entire premise is *many* experts providing capacity. If only 3 of 64 experts are ever used, you've paid for 64 experts' worth of parameters and gotten 3 experts' worth of capability — the model has the memory cost of a huge model with the effective capacity of a tiny one. Collapse silently destroys the value proposition.

So the central routing challenge isn't "pick the best expert" — it's "pick good experts *while keeping all experts meaningfully used*." Those two goals pull against each other, and balancing them is the art of MoE.

## Load-balancing loss

The primary fix is an **auxiliary load-balancing loss** added during training. Alongside the main language-modeling loss, the model is penalized when token routing is *uneven* across experts — the loss is minimized when tokens are distributed roughly evenly, and it grows as routing concentrates on a few experts.

This creates a counter-pressure against collapse: the router is pushed to spread tokens out, not just chase the few experts that seem marginally best. It's a gentle nudge, not a hard rule — the router still routes based on the token, but with a thumb on the scale toward balance. Tuning this loss is delicate: too weak and the model collapses; too strong and you force tokens to experts that aren't well-suited to them, hurting quality. The load-balancing loss is the knob that trades off "route to the best expert" against "keep all experts busy," and getting it right is much of what makes training an MoE work.

## Expert capacity and token dropping

A second mechanism handles balance more directly at the systems level: **expert capacity**. Because MoE is implemented efficiently on hardware, each expert is given a fixed **capacity** — a maximum number of tokens it can process in a batch (there has to be a fixed buffer size for the batched computation). If the router sends more tokens to an expert than its capacity, the overflow tokens are **dropped** — they skip the expert entirely (typically passing through via the residual connection unprocessed by any expert this layer).

This is a blunt but real balancing force: an expert can't hog *unlimited* tokens because it's capped. A **capacity factor** tunes the buffer — higher capacity drops fewer tokens (better quality) but wastes more compute/memory on padding; lower capacity is more efficient but drops more tokens (worse quality). Token dropping is a genuinely strange property unique to MoE — some tokens get *less* processing than others depending on routing luck — and managing it (via capacity factor plus the load-balancing loss keeping routing even so few tokens overflow) is part of the MoE tuning problem.

## Routing variants

Because routing is so central, several variants exist, each a different answer to the balancing problem:
- **Top-k token-choice routing** (the standard from post 3) — each token picks its top-k experts. Simple and common, but prone to the imbalance above, needing the load-balancing loss.
- **Expert-choice routing** — flip it around: each *expert* picks the top tokens it wants (up to its capacity). This guarantees balance by construction (every expert gets exactly its capacity) and avoids dropped tokens from overflow, at the cost that some tokens might be chosen by many experts and others by none.
- **Adjustments like adding noise** to routing scores during training (to encourage exploration so the router doesn't lock onto a few experts too early) and various refinements to the gating.

The existence of these variants underscores the point: **routing is the hard, active part of MoE.** The experts are just FFNs; the intelligence and the difficulty are in getting tokens to the right experts while keeping the whole set of experts productively used.

## Why this matters for the whole model

Routing quality determines whether an MoE model actually delivers on its promise:
- **Good routing** → tokens reach genuinely useful, specialized experts, and all experts are used, so the model realizes its full capacity — high capability at low per-token compute, as intended.
- **Bad routing** → collapse, wasted experts, dropped tokens, and a model that cost a fortune in parameters but performs like something far smaller.

This is why so much MoE research is about routing and load balancing rather than the experts themselves, and why MoE models are trickier to train than dense ones — you're training the experts *and* a router that must stay balanced, with auxiliary losses and capacity limits in the mix. When you hear that MoE models can be "finicky" to train, this is what's meant: the routing has to be kept healthy throughout, or the model quietly wastes most of what you paid for. With routing understood, the next post turns to the consequence that shapes everything downstream — MoE's distinctive memory-versus-compute trade at training and serving time.

## Key takeaways

- Routing tends toward **expert collapse**: a self-reinforcing loop (favored experts get more tokens → train more → get favored more) concentrates tokens on a few experts while the rest starve — catastrophic for MoE, since you pay for all experts' parameters but get only a few experts' capability.
- The central challenge isn't "pick the best expert" but "pick good experts *while keeping all experts used*" — two goals that pull against each other.
- An **auxiliary load-balancing loss** penalizes uneven routing during training, counter-pressuring collapse — but it's delicate to tune (too weak → collapse; too strong → tokens forced to ill-suited experts, hurting quality).
- **Expert capacity** caps how many tokens each expert processes per batch; overflow tokens are **dropped** (skip the layer's experts via the residual) — a systems-level balancing force tuned by a **capacity factor** (quality vs. compute/memory), and a property unique to MoE.
- Routing variants (top-k token-choice vs. **expert-choice**, noise for exploration) all target the balance problem — routing is the **hard, active part of MoE** (experts are just FFNs), which is why MoE is finicky to train and why routing quality decides whether the model realizes its capacity or wastes it.

## Further reading

- [Switch Transformers — Fedus et al. (arXiv:2101.03961)](https://arxiv.org/abs/2101.03961)
- [Outrageously Large Neural Networks: The Sparsely-Gated MoE Layer — Shazeer et al. (arXiv:1701.06538)](https://arxiv.org/abs/1701.06538)
