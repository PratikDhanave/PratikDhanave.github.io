# How Reasoning Models Are Trained

*You can't teach deep reasoning by showing a model more examples of good reasoning — because the best reasoning for a hard problem often isn't in any dataset, and imitation caps a model at the quality of what it imitates. The breakthrough behind modern reasoning models was to stop imitating and start rewarding: let the model try to solve problems, check whether it got them right, and reinforce whatever thinking led to correct answers. That shift — from imitation to reinforcement on verifiable outcomes — is why reasoning models can think in ways no one wrote down.*

Earlier posts showed reasoning helps and that chain-of-thought is elicitable by prompting. But reasoning models are *trained* to reason natively, and how they're trained is central to why they're so much more capable than prompted standard models. This post covers the training approach — primarily **reinforcement learning on verifiable rewards** — the distinction between outcome and process rewards, and why this produces reasoning that emerges rather than being imitated. It's a conceptual overview, not a training manual.

## Why imitation isn't enough

The default way to teach an LLM a skill is **supervised fine-tuning**: show it many examples of the desired behavior and train it to imitate them. For reasoning, that would mean training on datasets of worked solutions with their reasoning. This helps, but it has fundamental limits:

- **You're capped by the demonstrations.** Imitation makes the model reproduce the style and quality of the examples it's shown. If the demonstrations aren't better than what the model could already produce, imitation doesn't push capability much higher — and hand-writing vast amounts of expert reasoning for hard problems is expensive and limited.
- **The best reasoning may not be human-like.** The most effective way for a *model* to reason through a problem might not match how a human writes it up. Imitation forces the model into human-demonstrated patterns, potentially missing reasoning strategies that work better for the model itself.
- **It doesn't optimize for *correctness*.** Supervised training optimizes for *matching the demonstration*, not for *getting the answer right*. A model can learn to produce plausible-looking reasoning that imitates the training data without actually being good at reaching correct answers.

So imitation alone can't produce the deep, self-correcting, sometimes-alien reasoning that makes reasoning models special. The insight was to optimize for what actually matters — *correct answers* — rather than for imitating demonstrations. That means reinforcement learning.

## Reinforcement learning on verifiable rewards

The core technique behind modern reasoning models is **reinforcement learning (RL) with verifiable rewards** (sometimes called RLVR). The idea is elegant:

- **Let the model attempt problems.** Give the model problems and let it generate its own reasoning and answers — many attempts, exploring different approaches.
- **Reward correct answers.** For problems where the answer can be *automatically checked* — math problems with known answers, coding problems that either pass tests or don't, formal logic that can be verified — you get a clean, objective reward signal: did it get the right answer? This is what "verifiable" means: correctness can be checked automatically, so you don't need human labels for every attempt.
- **Reinforce the reasoning that led to correct answers.** RL then adjusts the model to make the reasoning that produced correct answers *more likely* and the reasoning that produced wrong answers less likely. Over many iterations, the model learns to generate reasoning that *actually leads to correct answers* — because that's exactly what's being rewarded.

This is powerful because the model *discovers* effective reasoning through trial and reward, rather than imitating demonstrations. It can find reasoning strategies no one wrote down, because it's optimized for the outcome (correctness), not the process (matching examples). And the *verifiability* is what makes it scalable: for math and code, correctness is cheap to check automatically, so you can generate enormous amounts of training signal without human labeling. DeepSeek-R1 notably demonstrated that this RL-centric approach — reinforcing reasoning that produces verifiably-correct answers — could produce strong reasoning capabilities, and did so fairly openly. RL on verifiable rewards is the engine of reasoning models.

## Emergent reasoning behaviors

A remarkable result of this training is that sophisticated reasoning *behaviors emerge* — the model develops them on its own because they help it get correct answers, without being explicitly taught:

- **Longer thinking on harder problems.** Models trained this way learn to *spend more reasoning* on harder problems — generating longer chains of thought when needed — because doing so leads to more correct answers. The test-time-compute behavior (effort matching difficulty) emerges from optimizing for correctness.
- **Self-correction and backtracking.** Reasoning models learn to catch their own mistakes mid-stream, reconsider, and try different approaches — because a chain of thought that catches and fixes an error is more likely to reach the right answer, so RL reinforces it. This self-checking wasn't programmed; it emerged as a strategy for correctness.
- **Exploring alternatives.** Models learn to consider multiple approaches, evaluate them, and pursue promising ones — again because this improves the odds of a correct answer. The thinking becomes exploratory and deliberate.

These emergent behaviors are the difference between a prompted standard model (which produces shallow, non-self-correcting steps) and a trained reasoning model (which thinks deeply, checks itself, and explores). They emerged because the model was optimized for *correct outcomes* over many attempts, and these behaviors *are* what produces correct outcomes on hard problems. This is why RL-trained reasoning is so much more capable than elicited reasoning — the model learned, by trial and reward, how to actually solve hard problems, not just how to look like it's reasoning.

## Outcome rewards vs process rewards

An important nuance in how reasoning is rewarded is *what* you reward — the final answer, or the steps:

- **Outcome rewards (ORM).** Reward based only on whether the *final answer* is correct. This is simple and verifiable (check the answer) and is the primary signal in RLVR. Its limitation: it doesn't distinguish a correct answer reached by sound reasoning from one reached by luck or flawed reasoning that happened to land right — the reward is the same. It can also reward reasoning that's correct in conclusion but unreliable in method.
- **Process rewards (PRM).** Reward the *individual reasoning steps* — is each step valid? — not just the final answer. A **process reward model** scores the reasoning process step by step. The influential "Let's Verify Step by Step" work showed that rewarding correct *steps* (process supervision) can produce more reliable reasoning than rewarding only the outcome, because it directly encourages every step to be sound, not just the endpoint to be right. Its cost: labeling or scoring *steps* is harder than checking a final answer (steps are less obviously verifiable).

The trade-off is real: outcome rewards are cheap and scalable but coarse (they don't police the reasoning process); process rewards are finer-grained and can yield more trustworthy reasoning but are costlier to obtain. Modern reasoning-model training uses these ideas in combination, and process reward models also serve at *inference* time as verifiers that score reasoning (the next post's best-of-N and verifier techniques). Knowing the distinction clarifies a key tension in reasoning: getting the right answer versus reasoning correctly to get it.

## What this means

The training story explains the reasoning-model phenomenon:

- **Reasoning is trained, not just prompted** — which is why reasoning models vastly outperform prompted standard models on hard problems. The capability comes from RL optimizing for correct outcomes, producing deep, self-correcting reasoning.
- **Verifiable domains led the way** — math and code, where correctness is automatically checkable, provided the clean reward signal that made RLVR work. This is also why reasoning models are especially strong in these domains, and why extending reasoning to less-verifiable domains (open-ended writing, judgment) is harder (there's no clean automatic reward).
- **The behaviors emerge from the objective** — long thinking, self-correction, and exploration weren't hand-coded; they emerged because they produce correct answers. This is a recurring lesson in modern AI: optimize for the right objective at scale, and sophisticated behavior emerges.
- **Outcome vs process is a live tension** — whether to reward answers or steps shapes how reliable the reasoning is, and process reward models bridge into inference-time verification.

Reasoning models are trained mainly by reinforcement learning on verifiable rewards — attempt problems, reward correct (automatically-checkable) answers, reinforce the reasoning that led to them — which produces emergent deep reasoning that imitation can't. Next: the inference-time techniques (best-of-N, verifiers, search) that spend test-time compute to extract even more accuracy.

## Key takeaways

- Supervised imitation of worked solutions can't produce deep reasoning: it's capped by the demonstrations, forces human-like patterns that may not be optimal for the model, and optimizes for *matching examples* rather than for *correct answers*.
- The core training technique is reinforcement learning on verifiable rewards (RLVR): let the model attempt problems, reward correct answers where correctness is automatically checkable (math answers, code passing tests), and reinforce the reasoning that led to correct answers — so the model *discovers* effective reasoning rather than imitating it.
- Verifiability makes it scalable (automatic correctness checks yield vast training signal without human labels) and explains why reasoning models are strongest in math/code and why less-verifiable domains are harder; DeepSeek-R1 demonstrated this RL-centric approach openly.
- Sophisticated behaviors *emerge* from optimizing for correctness: longer thinking on harder problems, self-correction/backtracking, and exploring alternatives — none hand-coded, all reinforced because they produce correct answers — which is why trained reasoning far exceeds prompted reasoning.
- Reward design matters: outcome rewards (final answer only) are cheap, scalable, but coarse; process rewards (score each step, via a process reward model) can produce more reliable reasoning ("Let's Verify Step by Step") but are costlier to obtain — and process reward models double as inference-time verifiers.

## Further reading

- [Let's Verify Step by Step — process vs outcome supervision (Lightman et al., 2023)](https://arxiv.org/abs/2305.20050)
- [DeepSeek-R1: Incentivizing Reasoning Capability in LLMs via RL](https://arxiv.org/abs/2501.12948)
- [Test-time compute (previous post)](/blog/posts/reason-03-test-time-compute.html)
