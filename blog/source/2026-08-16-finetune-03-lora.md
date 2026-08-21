# Parameter-Efficient Fine-Tuning: LoRA

*Full fine-tuning updates every weight in a model — billions of numbers — which needs enormous memory and produces a full-size copy per task. LoRA sidesteps all of it with one insight: the change a model needs for a task is "low-rank," so you can train a tiny pair of matrices instead of the whole model. It's the technique that put fine-tuning within reach of anyone with a single GPU.*

The last post placed supervised fine-tuning at the center of applied work. This post covers the technique that made SFT *practical* for most people: **LoRA** (Low-Rank Adaptation), the leading form of **parameter-efficient fine-tuning (PEFT)**. Before LoRA, fine-tuning a large model meant the resources to update all its weights; after LoRA, you can fine-tune a big model on modest hardware and ship tiny per-task adapters. Understanding why it works — and why it barely costs quality — is essential to modern fine-tuning.

## The problem with full fine-tuning

**Full fine-tuning** updates *all* of a model's weights during training. For a large model this is brutally expensive in a specific way — memory:

- **You must hold the whole model plus training state.** Training needs not just the weights but gradients and optimizer state for *every* parameter, typically several times the model's size in memory. Fine-tuning a big model this way can require far more memory than just running it.
- **Every fine-tune is a full-size copy.** Each task produces an entirely new set of billions of weights to store and serve. Ten fine-tuned variants means ten full model copies.
- **It's slow and hardware-hungry** — often needing multiple high-end GPUs for a model a single GPU could *run*.

This put fine-tuning out of reach for most teams and made multi-task deployment (a different fine-tune per customer or task) prohibitively expensive. PEFT exists to break this — to fine-tune by training only a *small* number of new parameters while leaving the original model frozen.

## The LoRA insight: updates are low-rank

LoRA rests on an elegant observation. When you fine-tune a model, the *change* to its weight matrices — the difference between the fine-tuned and original weights — turns out to have **low intrinsic rank**. In plain terms: the adjustment a task requires is far simpler (has far less independent information) than the full weight matrix it modifies. You don't need to change the weights in billions of independent ways; the useful change lives in a small subspace.

That means you can *approximate* the weight update with a product of two much smaller matrices. Instead of learning a full update matrix ΔW (huge), you learn two thin matrices A and B whose product BA approximates it:

```text
Full fine-tuning:   W_new = W + ΔW          (ΔW is full-size, all trained)

LoRA:               W_new = W + B·A          (W frozen; only A and B trained)
                    where A and B are small (low "rank" r):
                    if W is d×d, A is r×d and B is d×r, with r ≪ d
```

The **rank r** is small (often just a handful to a few dozen), so A and B together have *orders of magnitude* fewer parameters than W. You freeze the original weights entirely and train only these tiny matrices. That's the whole idea — and it works remarkably well because the update genuinely is low-rank.

## Why LoRA is a big deal

The consequences of training two small matrices instead of the whole model are dramatic:

- **Tiny trainable footprint.** You train a fraction of a percent of the model's parameters, so the memory for gradients and optimizer state collapses — fine-tuning that needed multiple GPUs can fit on one.
- **Frozen base is shared.** The original model is untouched and shared across all your fine-tunes; each task adds only its small **adapter** (the A/B matrices), which is megabytes, not gigabytes.
- **Cheap multi-task deployment.** You can serve one base model and swap in different LoRA adapters per task or per customer — dozens of "fine-tuned models" that are really one model plus dozens of tiny adapters. This is transformative for multi-tenant and multi-task serving.
- **Near-full-fine-tuning quality.** Because the update really is low-rank, LoRA typically matches full fine-tuning's quality on most tasks despite training a fraction of the parameters — the rare case of getting most of the benefit for a fraction of the cost.
- **No inference latency penalty (when merged).** The adapter can be merged back into the weights for deployment (W + BA becomes a single matrix), so a merged LoRA model runs exactly as fast as the original — or kept separate for hot-swapping, with negligible overhead.

## The knobs: rank and where to apply it

LoRA has a couple of choices that shape the trade-off:

- **Rank (r)** — the size of the low-rank matrices, and the main lever. Higher rank means more trainable parameters and capacity to capture a more complex update (potentially higher quality on harder tasks), at more memory and slight overfitting risk; lower rank is cheaper and often sufficient. A modest rank works for many tasks; you tune it to the task's complexity.
- **Which layers/matrices to adapt** — you apply LoRA to specific weight matrices (commonly the attention projections). Adapting more matrices adds capacity and cost. Sensible defaults exist, and you rarely need to touch every matrix.
- **Alpha (scaling)** — a scaling factor on the adapter's contribution, tuned alongside rank.

The practical guidance: start with a modest rank and the common target matrices (the defaults in libraries like Hugging Face PEFT are well-chosen), and only increase rank if the task needs more capacity. Most tasks don't need large ranks — the low-rank insight is that a little goes a long way.

## LoRA in practice

Using LoRA is straightforward with modern tooling (Hugging Face PEFT and similar):

- **You keep the base model frozen** and attach LoRA adapters to the chosen matrices.
- **Training updates only the adapters** — dramatically less memory, so it fits on accessible hardware.
- **The output is a small adapter file** you store and version per task — not a full model.
- **At deployment**, merge the adapter for maximum speed, or keep it separate to hot-swap adapters on a shared base for multi-task serving.

LoRA is the reason fine-tuning went from "needs a cluster" to "runs on one GPU," and its adapter model is why serving many fine-tuned variants became cheap. But there's still the memory of the *base model itself* to hold during training — and the next technique, QLoRA, shrinks that too, pushing fine-tuning of even large models onto a single consumer GPU.

## Key takeaways

- Full fine-tuning updates all weights, needing memory for gradients/optimizer state across every parameter (several times the model size) and producing a full-size copy per task — putting it out of reach for most teams.
- LoRA rests on the insight that a task's weight *update* is low-rank (far simpler than the full matrix), so it can be approximated by the product of two small matrices (BA) while the original weights stay frozen.
- Training only those tiny matrices collapses the memory cost (fine-tuning fits on one GPU), keeps the base model shared, produces megabyte-sized per-task adapters, and typically matches full fine-tuning quality — most of the benefit for a fraction of the cost.
- The adapter model enables cheap multi-task/multi-tenant serving (one base model + many swappable adapters) and adds no inference latency when merged back into the weights.
- Tune mainly the rank r (capacity vs. cost — modest is usually enough) and which matrices to adapt (attention projections by default); libraries like Hugging Face PEFT provide well-chosen defaults.

## Further reading

- [LoRA: Low-Rank Adaptation of Large Language Models (Hu et al.)](https://arxiv.org/abs/2106.09685)
- [Hugging Face PEFT documentation](https://huggingface.co/docs/peft)
- [The fine-tuning spectrum (previous post)](/blog/posts/finetune-02-the-spectrum.html)
