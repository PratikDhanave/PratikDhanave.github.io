# Self-Play and Co-Evolution

*The technique that produced superhuman game-playing — a system improving by competing against copies of itself — has an LLM analogue: models that generate their own training signal and bootstrap their way up without new human labels.*

Self-play is one of the most powerful ideas in machine learning: rather than learn from a fixed dataset, a system improves by playing against, or learning from, versions of itself, generating an ever-harder curriculum as it goes. For language models the analogue is subtler — there is no game board — but the principle transfers: a model can produce its own training data and its own reward signal, and iterate. This fourth post in the Self-Evolving Agents: The Frontier series covers self-play and co-evolution, and the hard question at their center: where does a *trustworthy* self-generated signal come from?

## The self-play principle

Classic self-play works because the opponent scales with the learner: as the system improves, so does the adversary it faces, producing a curriculum that stays challenging without any human designing it. That is genuine open-ended improvement — the system manufactures its own increasing difficulty. The catch for language models is that most tasks are not two-player games with a clear win/loss, so the "opponent" and the "reward" have to be reconstructed some other way. Two influential approaches show two different reconstructions.

## SPIN: the model as its own sparring partner

[Self-Play Fine-Tuning (SPIN, Chen et al., 2024)](https://arxiv.org/abs/2401.01335) turns fine-tuning into a self-play game without any new human-annotated data. Starting from a supervised fine-tuned model, the LLM generates its own responses and then learns to *distinguish* its self-generated responses from the human-written reference responses — refining its policy to close the gap between them. Each iteration, the model's previous version is the "opponent" whose outputs the new version learns to tell apart from and improve upon the reference.

The elegance is that the signal is grounded in *real* data: the human reference responses are the anchor, and self-play is the mechanism for squeezing more capability out of them without collecting more. The model bootstraps toward the reference distribution by repeatedly generating, discriminating, and refining. It converts weak models into stronger ones using only the data already in hand — a concrete, grounded form of self-improvement.

## Self-Rewarding models: the model as its own judge

[Self-Rewarding Language Models (Yuan et al., 2024)](https://arxiv.org/abs/2401.10020) takes a bolder step: the model provides its *own reward*. In each iteration the model generates candidate responses to new prompts and then, acting as an **LLM-as-judge**, assigns rewards to its own outputs — creating preference data it then trains on. Crucially, the same training improves *both* the model's instruction-following *and* its ability to judge, so the reward model gets better alongside the policy. The reward source is no longer a fixed external judge that caps how good the policy can get; it improves in lockstep.

This is genuinely open-ended in a way SPIN is not — there is no fixed reference distribution to converge to; the model is lifting itself by its own evaluative bootstraps. Which is exactly why it is also the more dangerous shape, and the reason the reward-source problem below is the heart of this post.

## The reward-source problem

Self-play and self-rewarding both confront the frontier's deepest question: **a system that generates its own training signal can only be trusted to the extent that signal tracks reality.** This connects straight back to a limit the foundations series hammered — a model correcting itself with no grounding in something real often fails to improve and can degrade. Self-improvement without a trustworthy signal is not improvement; it is drift, dressed up as progress.

The approaches differ precisely in how they ground the signal:

- **SPIN grounds in real human data** — the reference responses are the anchor, so self-play squeezes capability out of genuine ground truth. Its ceiling is that reference distribution.
- **Self-rewarding grounds in the model's own judgment** — powerful and open-ended, but it inherits every bias of the model-as-judge, and a flaw in the judge becomes a flaw the policy is trained to satisfy.

The failure mode to fear is **reward hacking through self-reference**: if the judge has a blind spot — a preference for verbosity, confident tone, a particular style — the policy learns to exploit it, and both the policy and the judge can spiral toward a shared delusion of quality that reality does not share. The more the system judges itself with nothing external checking the judge, the more room there is for this collapse.

## Making self-improvement safe(r)

The practical guardrails follow directly from the reward-source problem. Anchor the signal in something real wherever you can — human references, execution results, tests, tools, verifiable outcomes — rather than pure self-judgment. Where you must use the model as judge, *calibrate it against human labels* and periodically re-check it, so you catch a drifting judge before it drags the policy with it. Keep held-out evaluation the model never trains on, so "improvement" is measured against a fixed external yardstick, not the moving one the system optimizes. And treat unbounded self-rewarding loops with suspicion: the tighter the loop between a model and its own reward with nothing external in it, the faster it can go wrong. Self-play is a genuinely powerful engine of open-ended improvement — but only when something real remains in the loop.

## Key takeaways

- Self-play improves a system by competing against or learning from copies of itself, generating its own increasing-difficulty curriculum — powerful, but LLM tasks lack a game's clear win/loss, so the reward must be reconstructed.
- SPIN makes fine-tuning a self-play game grounded in real human reference data: the model generates responses and learns to distinguish them from the references, bootstrapping capability from data already in hand.
- Self-Rewarding LMs go further — the model judges its own outputs (LLM-as-judge) to create its own preference data, improving policy *and* judge together, which is open-ended but riskier.
- The reward-source problem is central: a self-generated signal is trustworthy only insofar as it tracks reality; ungrounded self-reference produces drift and reward-hacking, not improvement.
- Guard it by anchoring in real signals (references, execution, tests), calibrating any self-judge against humans, keeping held-out external evaluation, and distrusting tight unbounded self-reward loops.

## Further reading

- [Self-Play Fine-Tuning Converts Weak Language Models to Strong Language Models — Chen et al., 2024](https://arxiv.org/abs/2401.01335)
- [Self-Rewarding Language Models — Yuan et al., 2024](https://arxiv.org/abs/2401.10020)
- [Large Language Models Cannot Self-Correct Reasoning Yet — Huang et al., 2023](https://arxiv.org/abs/2310.01798)
