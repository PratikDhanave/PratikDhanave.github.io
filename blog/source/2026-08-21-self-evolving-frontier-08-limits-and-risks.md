# Limits, Risks, and Open Problems

*The frontier is genuinely exciting and genuinely oversold, and telling the difference matters — so this closing post is an honest accounting of what self-evolving agents cannot yet do, what can go wrong, and what remains unsolved.*

Across this series the methods have grown more impressive: meta-agents that design agents, evolutionary search over populations, self-play, reflective optimizers, self-reference. It would be easy to end on hype. Instead, this final post in the Self-Evolving Agents: The Frontier series does the more useful thing — a clear-eyed account of the limits, the risks, and the open problems, so you can build with the frontier without believing its most breathless claims.

## The limits

**Self-improvement needs a real signal — this has not changed.** The single most important limit runs through every post: a system improving itself with no trustworthy external signal does not improve, it drifts. [Huang et al. (2023)](https://arxiv.org/abs/2310.01798) showed intrinsic self-correction without external feedback often fails and can degrade, and nothing at the frontier repeals it. Every method that works — SPIN grounded in real data, GEPA reflecting on real trajectories, ADAS scored by a real evaluator — works *because* it keeps something real in the loop. The frontier has not solved "improve with no ground truth"; it has found richer ways to use the ground truth you have.

**The base model is a ceiling.** These systems evolve prompts, code, tools, and structure on top of a fixed underlying model. That is a large and useful space, but it is not unbounded self-improvement — the substrate caps what the search can reach. A self-evolving system built on a given model gets much better at *using* that model; it does not transcend it.

**Cost scales brutally.** Every frontier method is a search, and search means running many candidates many times — multiplied again at each meta level. What is a research result with a big compute budget is often uneconomical in production. The lighter self-evolution axes (memory, prompts, skills) deliver far more per dollar for most systems; the frontier is what you reach for when the value justifies an expensive search.

**Results plateau, and transfer is uncertain.** Empirically these loops flatten out, and a design discovered for one task or benchmark does not automatically generalize to another. Impressive numbers on a target task are not a guarantee of broad capability.

## The risks

**Reward hacking, at machine speed.** The previous post's theme is also the top risk: a powerful search over a gameable objective produces agents that exploit the objective, thoroughly and fast. This is not an edge case at the frontier; it is the default failure mode, and the more capable the search, the more certainly it finds the loophole.

**Drift, forgetting, and collapse.** Self-modifying systems degrade in ways that accumulate silently: behavior drifts from small compounding changes; an update that improves one thing erases a capability elsewhere; and a system trained or tuned on its own outputs round after round can spiral into self-reinforcing mediocrity as its own artifacts crowd out real signal. None of these throw an error — they only show up in continuous evaluation against a fixed external yardstick.

**Safety of self-modification.** The more a system rewrites itself — its prompts, its tools, its own improvement operator — the harder it is to predict and the more important it is that changes are bounded, reversible, and reviewable. An unbounded self-modifying loop with real-world tool access is a genuine safety concern, not a hypothetical, and it deserves the same seriousness as any system that can act consequentially without a human in the loop.

## The open problems

Honesty about what is *unsolved* is the most useful thing a frontier survey can offer:

- **A trustworthy signal for open-ended goals.** We can evaluate narrow tasks; we cannot robustly measure open-ended novelty or general capability, which is exactly what open-ended self-improvement needs. This is the field's central bottleneck.
- **Reliable recursive self-improvement.** We have working meta-level systems and early self-referential operators, but not dependable, stacking recursion that keeps paying off without drifting or exploding in cost.
- **Generalization of discovered designs.** Making a search discover agents that transfer across tasks, rather than overfit one, is largely open.
- **Alignment of self-modifying systems.** Keeping a system that changes itself pointed at what we actually want — as it changes — is unsolved and increasingly important as capability grows.

None of these are reasons to dismiss the frontier; they are the map of where the real work remains.

## Building with the frontier, responsibly

The practical posture that falls out of all this: **use the frontier where it earns its cost, keep something real in every loop, and govern self-modification like the consequential capability it is.** Concretely — reach for heavy search (automated design, evolution, self-play) only when the value justifies it and lighter axes are exhausted; anchor every improvement loop in a grounded, held-out, human-audited signal; bound the recursion, the cost, and the scope of self-modification; keep every self-made change reversible and versioned; and keep a human able to inspect and veto what the system becomes. Do that, and self-evolving agents are a powerful, controllable tool. Skip it, and you have built an efficient machine for optimizing the wrong thing.

## The series, in one line

The frontier of self-evolving agents is a set of ever-more-powerful *searches* over the space of agent designs — and every one of them lives or dies by the trustworthiness of the signal that ranks its candidates. The impressiveness is in the search; the value, the safety, and the honesty are all in the evaluator. Build the evaluator first.

## Key takeaways

- The core limit is unchanged: self-improvement needs a real external signal — every working frontier method keeps something real (data, execution, a grounded evaluator) in the loop; none has solved improving with no ground truth.
- Further limits: the fixed base model is a ceiling, search cost scales brutally (worse at each meta level), and results plateau and don't automatically transfer across tasks.
- The risks are reward hacking at machine speed (the default failure mode of powerful search over a gameable objective), silent drift/forgetting/collapse, and the safety of unbounded self-modification.
- Open problems: a trustworthy signal for open-ended goals, reliable recursive self-improvement, generalization of discovered designs, and alignment of self-modifying systems.
- Build responsibly: use heavy search only when it earns its cost, ground every loop in a held-out human-audited signal, bound and version self-modification, and keep a human able to veto — the value is in the evaluator, so build it first.

## Further reading

- [Large Language Models Cannot Self-Correct Reasoning Yet — Huang et al., 2023](https://arxiv.org/abs/2310.01798)
- [Automated Design of Agentic Systems — Hu et al., 2024](https://arxiv.org/abs/2408.08435)
- [Self-Evolving Agents (the foundations series)](/blog/series/self-evolving-agents/)
