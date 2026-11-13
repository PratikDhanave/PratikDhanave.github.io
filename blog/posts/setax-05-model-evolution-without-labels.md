<!-- Markdown version for AI agents and readers. Canonical: https://pratikdhanave.com/blog/posts/setax-05-model-evolution-without-labels.html -->

# Model Evolution I: Learning Without Gold Answers

*The deepest locus of self-evolution is the weights — and the interesting frontier there is not supervised fine-tuning on human labels but the family of methods where the model improves from signals it generates or uncovers itself: pseudo-labels from its own consensus, rewards from self-play, curricula it proposes to itself. This post organizes that family by one question — where does the training signal come from when no gold answer exists — and traces the shared failure mode every branch inherits: a model learning from itself can amplify its knowledge, and can just as efficiently amplify its errors.*

[Post 4](/blog/posts/setax-04-harness-evolution.html) ended at the harness ceiling: scaffolding elicits frozen ability but can't exceed it. Crossing the ceiling means changing weights — and the self-evolution question is whether weights can improve *without* the expensive ingredient, human-labeled answers. The answer is a qualified yes, with the qualification doing a lot of work.

## The signal taxonomy

Every labeled-data-free training method answers "what do we train toward?" one of four ways:

- **Consensus as pseudo-truth.** Sample the model many times on the same problem; take the majority or self-consistent answer as the label; train toward it. This is [semi-supervised learning](https://en.wikipedia.org/wiki/Semi-supervised_learning)'s oldest trick — self-training on pseudo-labels — revived for reasoning models, where consensus across sampled chains of thought stands in for ground truth (the test-time-reinforcement-learning pattern). It works exactly when the model's errors are *uncorrelated* enough that truth wins the vote; it fails — confidently and invisibly — where errors are systematic, because the vote then launders a shared bias into a training target. Consensus sharpens a model toward what it already mostly-knows; it cannot teach what the majority gets wrong.
- **An opponent as the curriculum.** Self-play turns one model into both learner and adversary: a generator trying to make its outputs indistinguishable from reference data while a discriminator role sharpens at telling them apart (the SPIN-style pattern), or a proposer inventing problems tuned to the edge of a solver's ability while the solver trains on them (the Absolute-Zero-style pattern — which still needs an *executor*, typically a code runner, to decide who won). The deep property, inherited from the [reinforcement learning](https://en.wikipedia.org/wiki/Reinforcement_learning) tradition that produced superhuman game-players: self-play manufactures an automatic curriculum that scales with the learner — the opponent is always exactly as strong as you. The catch it also inherits: without an external anchor (game rules, an executor, reference data), two models can co-evolve into a private language that scores perfectly and means nothing.
- **A verifier as the reward.** Where post 3's spectrum offers a strong verifier — the proof checks, the tests pass, the program runs — its output can be used as a reinforcement signal directly, no human labels involved. This is the sturdiest branch, because the signal is anchored outside the model; it's bounded by the same spectrum: verifier-rewarded training is only as trustworthy as the verifier, and weight-level optimization applies *maximum* search pressure, so every exploit the verifier admits will eventually be found and — worse than in artifact search — *internalized*.
- **The world as the teacher.** Environment interaction: the agent acts, the world responds, and the response (task completed, user corrected, revenue moved) is the signal. Richest and most honest in principle; in practice the slowest, noisiest, and least attributable — which specific weight should change because a deployment went badly? — and the one that raises the governance stakes of post 8, because the training loop is now entangled with production.

## The shared failure mode: drift without an anchor

All four branches train the model on data shaped by the model, and that circularity has one universal consequence: **errors compound unless something external breaks the cycle.** The mechanisms differ by branch — consensus launders bias, self-play escapes into private equilibria, verifier-reward internalizes exploits, environment signals reinforce whatever got rewarded including the accidents — but the discipline is the same, and it's the closest thing this field has to a safety checklist: keep an **anchor** (reference data, an executor, a frozen baseline model, periodic human-verified batches) that the loop cannot modify; **evaluate on held-out, never-trained-on measures** watching for the signature of drift (self-scored metrics up, external metrics flat or down); and **gate weight updates** like production deploys — staged, compared against the frozen baseline, reversible. The branches that respect the anchor have produced real capability gains; the ones that don't produce models that are extremely good at agreeing with themselves — the weight-level rhyme of everything post 3 said about verifier pressure, at higher stakes, because the exploit ends up *in the weights*.

The takeaway: label-free model evolution is a four-branch family sorted by signal source — **consensus** (sharpens existing knowledge, launders shared bias), **self-play** (manufactures a scaling curriculum, risks private equilibria), **verifier reward** (sturdiest, inherits and internalizes verifier weaknesses), and **environment signal** (honest but slow, noisy, and governance-heavy). The circularity is common to all: the model trains on model-shaped data, so drift is the default — and external anchors, held-out evaluation, and deploy-grade gating on weight updates are what separate self-improvement from self-reinforcement.

## Key takeaways

- The four signal sources, in one line each: **consensus** = majority vote as pseudo-label; **self-play** = an opponent as automatic curriculum; **verifier reward** = post 3's spectrum turned into RL signal; **environment** = the world grades you, slowly and noisily.
- Each branch's characteristic failure: bias laundering, private equilibria, internalized verifier exploits, mis-attributed reinforcement — all instances of one circularity: *training on model-shaped data*.
- The anchor discipline: something external the loop can't touch (reference data, executor, frozen baseline, human-verified batches), held-out metrics watched for self-score/external-score divergence, and weight updates gated like deploys.
- Consensus-style methods **sharpen** what the model mostly-knows rather than teach what it doesn't — the honest framing for most "model improved itself" claims.

## Further reading

- [Semi-supervised learning — self-training and pseudo-labels, the family's oldest branch](https://en.wikipedia.org/wiki/Semi-supervised_learning)
- [Reinforcement learning — the framework self-play and verifier-reward methods build on](https://en.wikipedia.org/wiki/Reinforcement_learning)

---

Author: Pratik Dhanave (https://pratikdhanave.com) | Published: 2026-11-10
Canonical: https://pratikdhanave.com/blog/posts/setax-05-model-evolution-without-labels.html
Attribution: please link the canonical URL when citing or quoting this post.
