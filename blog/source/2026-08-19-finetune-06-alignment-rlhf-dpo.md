# Alignment: RLHF and DPO

*Supervised fine-tuning teaches a model to produce a correct answer; alignment teaches it to produce the answer people actually prefer. That shift — from "right" to "better" — is what turned raw language models into helpful assistants, and the move from RLHF's complex machinery to DPO's direct approach made it something ordinary teams can do.*

The fine-tuning spectrum post placed **alignment** at the far end: shaping *which* of several valid responses a model should prefer, using comparison data rather than single correct outputs. This is how models are made helpful, harmless, and on-tone — qualities SFT can't easily express as input→output pairs. This post covers the two dominant approaches: **RLHF**, the powerful-but-complex original, and **DPO**, the simpler method that made preference tuning practical.

## Why SFT isn't enough

SFT (from earlier posts) trains on input→output examples: for this input, produce this output. That's perfect for teaching a format or a narrow skill. But some qualities can't be captured as a single "correct" output, because they're about *preference among valid responses*:

- Two answers are both factually correct, but one is more helpful, clearer, or better-toned.
- A response is accurate but the *way* it's phrased matters — respectful, appropriately cautious, well-structured.
- You want the model to avoid certain kinds of responses (harmful, evasive) that aren't "wrong" in a format sense.

You can't easily write these as SFT examples, because there isn't one right answer — there's a *better* one. What you *can* provide is **comparisons**: shown two responses, humans say which is preferred. Alignment learns from those comparisons to make the model produce responses people prefer. This is the "helpfulness and harmlessness" training that turns a capable-but-raw model into a good assistant, and it's why aligned models feel so much more usable than base ones.

## RLHF: the original approach

**RLHF (Reinforcement Learning from Human Feedback)** was the breakthrough method (behind the instruction-following assistant models that popularized LLMs), and it works in three stages:

```text
1. SFT          — start with a supervised fine-tuned model (does the task)
2. Reward model — collect human preference comparisons (A vs B);
                  train a separate "reward model" to predict which
                  response humans prefer (a learned scorer of quality)
3. RL           — use reinforcement learning (e.g. PPO) to optimize the
                  LLM to maximize the reward model's score, while staying
                  close to the original (a penalty keeps it from drifting)
```

The idea is elegant: since you can't write a formula for "a good response," you *learn* one — a reward model trained on human preferences — then use RL to push the LLM toward responses that reward model rates highly. It works, and it produced the first genuinely helpful assistant models.

But RLHF is **complex and fragile**:

- **Multiple models** — you juggle the policy model being trained, the reward model, and usually a reference model, all in memory and interacting.
- **RL is unstable** — reinforcement learning is notoriously finicky to tune; it can collapse, over-optimize the reward model (exploiting its flaws — "reward hacking"), or drift away from good behavior.
- **It's expensive and expert-heavy** — the multi-model RL loop needs significant resources and real expertise to run well.

RLHF's power came with a barrier: it was hard enough that mostly well-resourced labs could do it reliably. That's the gap DPO closed.

## DPO: alignment made direct

**Direct Preference Optimization (DPO)** achieves the goal of RLHF — a model aligned to human preferences — but *without the reward model and without reinforcement learning*. Its insight is mathematical: the RLHF objective (optimize a policy against a reward model derived from preference data) can be rewritten so that you optimize the language model **directly on the preference comparisons** with a simple, stable, supervised-style loss.

```text
RLHF:  preferences → train reward model → RL-optimize LLM against it   (3 stages, RL)

DPO:   preferences → directly optimize LLM to prefer chosen over rejected  (1 stage, no RL)
```

In DPO, you feed the model the same preference data (for each prompt, a *chosen* and a *rejected* response) and train it directly to make the chosen response more likely and the rejected less likely, relative to a reference model. The consequences are why DPO largely displaced RLHF for most teams:

- **No separate reward model** — one fewer model to train and maintain.
- **No reinforcement learning** — it's a stable, supervised-style optimization, far easier and more reproducible to run than a finicky RL loop.
- **Same data, similar results** — it uses the same preference comparisons and achieves comparable alignment quality on many tasks, at a fraction of the complexity.
- **Accessible** — a team that can do SFT can do DPO; it doesn't require RL expertise or a multi-model orchestration.

DPO made preference alignment something ordinary teams can actually do, the same way LoRA/QLoRA made SFT accessible. It's the default starting point for alignment today, with RLHF (and its variants) reserved for cases that need the full machinery. (Other preference methods in the same family — ORPO, KTO, and others — offer further variations, but DPO is the widely-adopted baseline.)

## Where alignment fits in your pipeline

Alignment is an *addition* to, not a replacement for, the earlier stages — the typical order:

1. **SFT first** — teach the model the task and basic behavior with input→output examples. Alignment assumes a model that already does the task.
2. **Then align** (DPO, or RLHF if warranted) — refine *which* responses it prefers, using preference comparisons, to make it more helpful/harmless/on-tone.

And the data reality from the last post applies doubly: alignment needs **preference data** (comparisons of responses), which is a different and often harder-to-collect asset than SFT's input→output pairs. You need pairs of responses with a judgment of which is better — from humans, or increasingly from a strong model acting as judge (with the same caveat that AI-generated judgments must be checked). Collecting good preference data is the main practical cost of alignment.

## Do you even need alignment?

Be honest about whether your project needs this stage, because it adds cost:

- **Many applied fine-tunes stop at SFT.** If you need a format, a narrow skill, or a taxonomy, SFT alone often suffices — alignment is about *preference quality* you may not need.
- **Reach for alignment when response *quality of judgment* matters** — a user-facing assistant where helpfulness, tone, and safety of phrasing are the product, not just correctness.
- **Start with DPO** when you do — it's the accessible, stable choice; escalate to RLHF only if you have the resources and a reason the simpler method falls short.

Alignment is the polish that turns a correct model into a genuinely good one — but only worth it when that polish is what your application needs. With the model trained and aligned, the remaining question is the one every fine-tune must answer honestly: did it actually work? That's the next post — evaluation.

## Key takeaways

- SFT teaches a correct output; alignment teaches the *preferred* one — using comparison data (which of two valid responses is better) to capture helpfulness, tone, and harmlessness that can't be written as single input→output examples.
- RLHF (the original) trains a reward model on human preferences, then uses reinforcement learning to optimize the LLM against it — powerful (it created the first helpful assistants) but complex, fragile (unstable RL, reward hacking), and expensive with multiple models.
- DPO achieves the same preference alignment directly from the comparison data with a stable, supervised-style loss — no separate reward model, no RL — making it far simpler, more reproducible, and accessible to ordinary teams.
- Alignment comes *after* SFT in the pipeline and needs preference data (chosen/rejected response pairs), a different and harder-to-collect asset than SFT pairs — collecting good comparisons is its main practical cost.
- Many applied fine-tunes stop at SFT; reach for alignment (starting with DPO, escalating to RLHF only if needed) when quality of judgment — helpfulness, tone, safety of phrasing — is the product.

## Further reading

- [Direct Preference Optimization (Rafailov et al.)](https://arxiv.org/abs/2305.18290)
- [InstructGPT: Training language models to follow instructions with human feedback (RLHF)](https://arxiv.org/abs/2203.02155)
- [Data: the real determinant (previous post)](/blog/posts/finetune-05-data.html)
