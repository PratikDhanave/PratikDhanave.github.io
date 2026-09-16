# Training and Serving MoE Models

*Mixture of Experts saves compute but not memory — and that single fact reshapes everything about how these models are trained and served. All the experts must exist in memory even though only a few run per token, which turns MoE into a distributed-systems problem as much as a machine-learning one. This post covers the trade MoE actually makes and the parallelism it forces.*

The routing post explained how MoE decides which experts fire. This post covers the consequence: because a sparse model has huge total parameters, you must *store* all of them even though you only *compute* a few per token. That memory-versus-compute asymmetry is the defining practical characteristic of MoE, and understanding it explains why these models are built and deployed the way they are.

## The trade: compute saved, memory not

Here is the fact to internalize, because it governs everything else: **MoE trades a compute saving for a memory cost.**

- **Compute per token is low** — only the top-k experts run, so FLOPs per token are like a much smaller model (post 1's whole point).
- **Memory is high** — *all* experts' parameters must be loaded and available, because *any* token might be routed to *any* expert. You can't know in advance which experts a given batch will need, so they all have to be resident.

So an MoE model with 8× the parameters of a dense model uses ~2× the compute per token (with top-2) but needs ~8× the memory to hold all those experts. The parameters that make MoE cheap on compute make it expensive on memory. This is the opposite of the usual intuition that "cheaper to run" means "smaller everywhere" — an MoE model is cheap in FLOPs and *expensive* in memory footprint.

This asymmetry is why the earlier framing matters: when a model is "47B total, 13B active," the 13B is your compute bill per token, but the 47B is your memory bill. You provision hardware for the total, and pay compute for the active. Every downstream decision follows from this split.

## Why serving MoE is hard

For inference (serving), the memory cost is the dominant challenge, and it manifests in a few ways:
- **The whole model must fit in (fast) memory.** All experts have to be loaded onto your accelerators to serve any request, so a large MoE needs a lot of GPU/accelerator memory — often more than fits on a single device, forcing multi-device serving even though the *compute* would fit on less.
- **Experts are used unevenly across a batch.** Different tokens in a batch route to different experts, so the work is scattered across all experts. Getting good hardware utilization requires gathering tokens by their chosen expert and processing them together — extra data-movement work dense models don't have.
- **Memory bandwidth and communication become bottlenecks.** When experts live on different devices (below), tokens must be *sent* to their experts and results sent back — network/interconnect traffic that can dominate, especially at low batch sizes where there aren't many tokens to amortize it.

The upshot: MoE shifts the serving bottleneck from *compute* to *memory and communication*. This connects directly to the LLM-serving fundamentals — MoE doesn't reduce the memory pressure that dominates LLM inference; it increases it, in exchange for lower compute. You serve MoE well by managing memory and inter-device communication, not by counting FLOPs.

## Expert parallelism

The distinctive way to distribute an MoE model is **expert parallelism**: place different experts on different devices. With 8 experts and 8 GPUs, put one expert on each. When a batch is processed, each token is *routed to the device holding its chosen expert*, processed there, and the result routed back.

This spreads the large memory footprint across devices (each holds only its experts' parameters, not all of them) — which is often *necessary*, since the full model may not fit on one device. But it introduces an **all-to-all communication** step: every device must send its tokens to wherever their experts live and receive tokens destined for its own experts. This all-to-all exchange, twice per MoE layer (dispatch tokens out, combine results back), is the signature systems cost of MoE, and it's why interconnect bandwidth between accelerators matters so much for MoE performance. Expert parallelism is usually combined with the other parallelism strategies (data, tensor, pipeline) from large-model training/serving — MoE adds *expert* parallelism as another axis, specifically to handle the many-experts memory problem.

This is the concrete sense in which MoE is a distributed-systems problem: efficiently serving one is largely about orchestrating which tokens go to which experts on which devices, and moving them there and back without the communication swamping the compute you saved.

## Training consequences

Training inherits the same asymmetry plus the routing difficulties from post 4:
- **The memory cost applies during training too** — all experts' parameters, plus their optimizer state and gradients, must be held, so training a large MoE needs substantial distributed memory (expert parallelism again).
- **Load balancing must be maintained throughout** (post 4) — the auxiliary loss and capacity limits keep experts evenly used as training proceeds; lose balance and you waste the capacity you're paying to train.
- **The payoff is training efficiency per FLOP** — for a given compute budget, an MoE can reach better quality than a dense model, because it packs more parameters (capacity) into the same per-token compute. This is the core reason to train MoE: better capability for a given training-compute budget, accepting the memory and systems complexity as the price.

So MoE's bargain, end to end, is consistent: *more capability per unit of compute, at the cost of more memory and more systems complexity.* Whether that's worth it depends on whether you're compute-bound (MoE helps) or memory/simplicity-bound (dense may be easier). Frontier labs, chasing maximum capability per compute dollar and equipped to handle the distributed complexity, have overwhelmingly found the trade worth it — which is why so many frontier models are sparse.

## Key takeaways

- The defining fact: **MoE trades a compute saving for a memory cost** — only top-k experts run (low FLOPs per token) but *all* experts must be resident (high memory), because any token might route to any expert. "47B total / 13B active" = memory bill 47B, compute bill 13B.
- **Serving MoE is memory- and communication-bound, not compute-bound**: the whole model must fit in fast memory (often forcing multi-device serving), experts are used unevenly across a batch (needing token gathering), and inter-device traffic can dominate — MoE *increases* the memory pressure that already dominates LLM inference.
- **Expert parallelism** places different experts on different devices (spreading the memory footprint, often necessarily) but introduces an **all-to-all communication** step twice per MoE layer (dispatch tokens to their experts, combine results back) — the signature systems cost, making interconnect bandwidth critical.
- **Training** inherits the memory cost (all experts + optimizer state + gradients held) and must maintain load balance throughout, but delivers **better quality per training-FLOP** (more capacity at the same per-token compute) — the core reason to train MoE.
- MoE's end-to-end bargain: **more capability per unit of compute, at the cost of more memory and systems complexity** — worth it when compute-bound (frontier labs), less so when memory/simplicity-bound.

## Further reading

- [Switch Transformers — Fedus et al. (arXiv:2101.03961)](https://arxiv.org/abs/2101.03961)
- [Mixtral of Experts — Jiang et al. (arXiv:2401.04088)](https://arxiv.org/abs/2401.04088)
