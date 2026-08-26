# Test-Time Compute: The New Scaling Axis

*The dominant story of AI progress for years was training-time scale: bigger models, more data, more training compute. Test-time compute is a second, independent axis — spend more computation when you run the model, not when you train it, and get better answers on hard problems. It reframes a trained model not as a fixed-capability artifact but as one whose performance you can dial up per query by letting it think more.*

The previous posts showed that generating reasoning improves answers, and that sampling multiple reasoning paths improves them further. The unifying principle is **test-time compute** (also called inference-time compute): using *more computation at inference time* to get better results. This post makes the principle explicit — what it is, why it's a genuinely new scaling axis alongside training-time scale, the forms it takes, and its central trade-off. It's the conceptual core of the whole series.

## Two axes of scale

Historically, improving an AI model meant scaling *training*:

- **Training-time scale.** More parameters, more training data, more training compute — the "scaling laws" that drove years of progress. This increases what the model *learns* and its baseline capability, and it's a one-time cost: you pay it during training, then the trained model has a fixed capability that you invoke cheaply at inference. Every query to the finished model costs roughly the same, regardless of difficulty.

Test-time compute adds a second, orthogonal axis:

- **Test-time (inference-time) scale.** Spend more computation *when running* the model on a given problem — let it generate a longer chain of thought, sample multiple solutions, search over possibilities, verify and revise — to get a better answer, *without changing the model*. Here the cost is paid *per query*, and it can be *dialed up for harder problems*: an easy question gets a little compute, a hard one gets a lot.

The key realization is that these are *independent* levers. Training-time scale sets the model's baseline ability; test-time compute extracts more performance from that fixed model at inference. You can improve results by scaling either — and, importantly, research (below) found that scaling test-time compute is sometimes a *more effective* use of compute than scaling parameters. This is why test-time compute is described as a new scaling axis: it's a distinct, additional way to get better AI, not just a tweak to the old one.

## What "more compute at inference" looks like

Test-time compute is a family of techniques, all spending inference computation for accuracy (later posts detail them; here's the shape):

- **Longer chains of thought.** The simplest form: let the model generate more reasoning tokens before answering. Each token is a forward pass, so a longer chain of thought is literally more computation spent on the problem — and on hard problems, more thinking yields better answers. This is what reasoning models do natively.
- **Sampling multiple attempts.** Generate several independent solutions and select among them — by majority vote (self-consistency), by picking the best according to a verifier (best-of-N, a later post), or by other aggregation. More samples = more compute = better odds of a correct answer surfacing and being chosen.
- **Search.** Explore a *tree* of reasoning steps — trying different branches, evaluating partial solutions, backtracking from dead ends (tree-of-thought-style search). This spends compute exploring the solution space rather than committing to one path, and is a more structured way to use inference compute.
- **Verification and revision.** Generate an answer, check it (with a verifier or the model itself), and revise if it's wrong — iterating until satisfied. Each round of check-and-revise is more inference compute traded for a better result.

What unites these is the pattern: **do more work at inference to produce a better answer.** Whether that work is a longer single chain, many parallel samples, a search tree, or iterative revision, the lever is the same — spend more inference compute, get better results on hard problems. Reasoning models make some of this native (long chains, self-correction); other forms (best-of-N, search) are applied on top at inference time.

## Why it can beat scaling parameters

The most striking research finding is that, for some problems, **scaling test-time compute can improve results more effectively than scaling model parameters** — a given amount of extra compute spent at inference (letting a smaller model think harder) can outperform spending it to train or run a bigger model. Why would that be?

- **Effort matches difficulty.** A bigger model spends its extra capacity on *every* query, easy or hard. Test-time compute lets you spend extra effort *only where it's needed* — think hard on the hard problems, answer easy ones cheaply. This targeting is efficient: you're not paying for capability you don't need on easy queries.
- **Hard problems benefit from process, not just knowledge.** Many hard problems (math, logic, planning) are limited less by what the model *knows* and more by whether it can *work through* the steps without error. Extra thinking, sampling, and verification attack exactly that — they reduce process errors — which a bigger model doesn't necessarily do better. So on reasoning-heavy problems, inference compute is well-targeted.
- **It's flexible after training.** A bigger model is a fixed, expensive artifact. Test-time compute is a knob you turn *per query at run time* — no retraining, adjustable on the fly. This flexibility (spend more when the problem or the stakes warrant it) is itself valuable.

The nuance, which the research also shows, is that this isn't universal: test-time compute helps most on problems within reach of more thinking, and there are limits (the final post discusses diminishing returns and problems no amount of thinking solves). But the headline holds: inference compute is a real, sometimes-superior way to spend compute, which is why it's a first-class scaling axis and not just an optimization.

## The central trade-off: accuracy for cost and latency

Test-time compute is not free — its defining trade-off is the whole reason it's a *choice* rather than an always-on default:

- **More compute means more cost.** Reasoning tokens, extra samples, and search all consume inference compute, which costs money (you pay for the thinking tokens) and grows with how much you spend. A reasoning model working hard on a problem can generate many times more tokens than a direct answer — and you pay for all of them (the economics post quantifies this trade-off).
- **More compute means more latency.** Thinking takes time. A model that generates a long chain of thought before answering is *slower* to respond than one that answers immediately — sometimes dramatically so. For interactive or latency-sensitive uses, this matters a lot.
- **So it's a dial, not a default.** Because more test-time compute buys accuracy at the price of cost and latency, the right amount depends on the problem: spend a lot on a hard, high-stakes problem where accuracy is worth it; spend little on an easy or latency-sensitive one where a fast answer suffices. Many reasoning models expose this as a *reasoning-effort* setting. The skill (covered later) is matching the compute to the need.

This trade-off is the practical heart of test-time compute: it's a way to *buy* accuracy with compute, cost, and time. Understanding that framing — accuracy is now something you can purchase per query with more thinking — is what lets you use reasoning models well.

Test-time compute is the new scaling axis: spend more computation at inference (longer chains, sampling, search, verification) to get better answers from a fixed model, targeting effort to difficulty, sometimes more effectively than scaling parameters — at the cost of latency and money. The next post covers how models are *trained* to use this thinking well.

## Key takeaways

- There are two independent axes of scale: training-time (more parameters/data/training compute — sets baseline capability, paid once, fixed per-query cost) and test-time/inference-time (more compute when *running* the model — extracts more performance from a fixed model, paid per query, dialable by difficulty).
- Test-time compute is a family of techniques that all "do more work at inference for a better answer": longer chains of thought, sampling multiple attempts and selecting among them, searching a tree of reasoning steps, and verify-and-revise loops.
- Research found scaling test-time compute can beat scaling parameters for some problems, because it matches effort to difficulty (spend compute only where needed), attacks *process* errors that plague reasoning-heavy problems (not just knowledge), and is a flexible per-query knob rather than a fixed expensive artifact.
- It isn't universal — test-time compute helps most on problems reachable by more thinking, with diminishing returns and hard limits elsewhere — but it's a real, sometimes-superior way to spend compute, making it a first-class scaling axis.
- The central trade-off makes it a dial, not a default: more inference compute buys accuracy at the cost of money (you pay for thinking tokens) and latency (thinking is slow), so the right amount depends on the problem's difficulty and stakes — often exposed as a reasoning-effort setting.

## Further reading

- [Scaling LLM Test-Time Compute Optimally can be More Effective than Scaling Parameters (Snell et al., 2024)](https://arxiv.org/abs/2408.03314)
- [Chain of thought (previous post)](/blog/posts/reason-02-chain-of-thought.html)
- [LLM Inference and Serving — the cost and latency of token generation](/blog/series/llm-inference-and-serving/)
