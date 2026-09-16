# Mixture of Experts: The Core Idea

*Now we open up the mechanism at the heart of modern LLMs. A Mixture-of-Experts layer replaces the transformer's single feed-forward block with many parallel "experts" and a router that sends each token to just a few of them. The result is a model with enormous total capacity that spends only a little compute on any given token — the decoupling the first post promised, made concrete.*

We established that MoE replaces the FFN block (post 2) to pry apart capacity from per-token compute (post 1). This post is the mechanism itself: what an expert is, how the router chooses, and how the outputs combine. Getting this concrete makes the training and serving consequences (next posts) obvious rather than mysterious.

## Experts: many FFNs where there was one

In a dense transformer layer, every token passes through a single feed-forward network. An **MoE layer replaces that one FFN with N separate FFNs**, each called an **expert**. The experts are structurally identical (same shape as the FFN they replaced) but have their own independent weights — so an MoE layer with 8 experts has roughly 8× the FFN parameters of a dense layer.

The word "expert" is suggestive but slightly misleading: experts don't come pre-assigned to human-interpretable topics ("this one does French, this one does code"). They're just parallel FFNs whose specializations *emerge* during training as the router learns to send different kinds of tokens to different experts. What matters is the structure: many parallel sub-networks, only some of which are used per token.

## The router: choosing which experts fire

The piece that makes it work is the **router** (or gating network) — a small learned network, typically just a single linear layer, that sits in front of the experts. For each token, the router:

1. Looks at the token's representation and produces a **score for each expert** — how well-suited each expert is to this token.
2. Selects the **top-k** experts by score (k is small — usually 1 or 2).
3. Turns the top-k scores into weights (softmax over the chosen experts).

Only those top-k experts process the token; the other N−k experts do nothing for this token. This is the **sparse activation** from post 1: with, say, 8 experts and top-2 routing, each token uses 2 of 8 experts — a quarter of the layer's FFN parameters. The router is tiny (negligible compute) but it's the brain of the operation: it decides, per token, where the compute goes.

## Combining expert outputs

Each of the k chosen experts produces an output for the token. The layer combines them as a **weighted sum**, using the router's softmax weights:

```
output = Σ (router_weight_i × expert_i(token))   for i in the top-k experts
```

So if the router weighted expert 3 at 0.7 and expert 5 at 0.3, the token's output is `0.7 × expert3(token) + 0.3 × expert5(token)`. A token routed to different experts than its neighbor gets processed by different parameters — which is the whole point. The router weights being *learned* means the combination is differentiable, so the router trains jointly with the experts via ordinary backpropagation: the model learns *both* what each expert should do *and* how to route tokens to them, together.

## The parameter math that makes it worth it

The payoff is best seen in the two parameter counts, which now differ sharply:
- **Total parameters** include *all* experts across all MoE layers — this is the model's capacity, and it's large. (Every expert's weights must exist and be stored.)
- **Active parameters per token** include only the top-k experts actually used — this is the per-token compute, and it's small.

Concretely, take an MoE model with 8 experts per layer and top-2 routing. Its total FFN parameters are ~8× a dense equivalent, but each token only computes through 2 experts — so its *active* FFN compute is ~2×, not 8×. You've added 8× the FFN capacity for 2× the FFN compute. (The open-weights Mixtral model is a real example: 8 experts, top-2 routing, with total parameters far exceeding the number active on any token — commonly summarized as tens of billions total, roughly a quarter active.) That ratio — total capacity ≫ active compute — is exactly the decoupling that makes sparse models attractive, and it's why frontier models adopted MoE.

## Why not just make k bigger?

If using 2 experts is good, why not use all N and get maximum capacity per token? Because that would defeat the entire purpose — activating all experts is just a dense model again, with the compute cost back to scaling with total parameters. The *sparsity* (small k) is the source of the efficiency; the whole trick is using only a few experts per token. Small k keeps per-token compute low; large N gives high total capacity. MoE lives in the gap between them — many experts, few active — and the art is choosing N and k, and making the routing work well, which is where the difficulties begin.

Because the router *chooses* which experts fire, everything hinges on it routing *well* — sending each token to genuinely useful experts, and (crucially) spreading load so experts are actually used rather than a few getting everything. That routing problem — load balancing, expert collapse, capacity — is subtle enough and important enough to be the entire next post. For now, the core idea is in hand: many experts, a router picking a few per token, outputs combined by learned weights, giving huge capacity at small per-token cost.

## Key takeaways

- An **MoE layer replaces the single FFN with N parallel "experts"** (independent FFNs of the same shape) — so an 8-expert layer has ~8× the FFN parameters — and specializations *emerge* during training rather than being pre-assigned to topics.
- A small learned **router/gating network** scores the experts per token, selects the **top-k** (usually 1–2), and softmaxes their scores into weights — so only k of N experts fire per token (**sparse activation**); the router is tiny but decides where compute goes.
- Outputs combine as a **weighted sum** of the chosen experts (`Σ router_weight_i × expert_i(token)`), and because the weights are learned, the router trains jointly with the experts via ordinary backprop.
- The payoff is the split between **total parameters** (all experts — large capacity, all stored) and **active parameters per token** (only top-k — small compute): e.g. 8 experts/top-2 gives ~8× FFN capacity for ~2× FFN compute (Mixtral is a real instance).
- **Sparsity is the whole point** — activating all experts is just a dense model with the compute back; small k (few active) + large N (many total) is where the efficiency lives, so everything hinges on the router routing *well* and spreading load (next post).

## Further reading

- [Outrageously Large Neural Networks: The Sparsely-Gated MoE Layer — Shazeer et al. (arXiv:1701.06538)](https://arxiv.org/abs/1701.06538)
- [Mixtral of Experts — Jiang et al. (arXiv:2401.04088)](https://arxiv.org/abs/2401.04088)
