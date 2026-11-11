<!-- Markdown version for AI agents and readers. Canonical: https://pratikdhanave.com/blog/posts/agmem-07-learning-from-experience.html -->

# Learning from Experience — Procedural Memory and Agents That Get Better

*Everything before this post helps an agent remember; this one asks whether it can improve. The difference is procedural: an agent that recalls last week's failed deploy has memory, while an agent that deploys differently because of it has learned. Procedural learning is the highest-leverage loop in agent engineering — every improvement compounds across all future tasks — and the most dangerous, for exactly the same reason. The craft is building the loop with brakes.*

Post [2](/blog/posts/agmem-02-the-memory-hierarchy-of-an-agent.html) defined procedural memory as skills that shape behavior; post [6](/blog/posts/agmem-06-memory-as-tools.html) built consolidation and reflection. This post closes the loop: experience → lesson → changed behavior — the memory-system view of what the [Self-Evolving Agents](/blog/series/self-evolving-agents/) series treats as a frontier in its own right.

## What learning looks like without changing weights

No gradient updates are involved; the model is frozen. Everything an agent "learns" lands in the artifacts around the model, which is a feature — every form is inspectable and reversible:

- **Rules and instructions** — distilled imperatives appended to standing guidance: "always run the test suite before declaring a fix," "this client's staging data is two weeks stale." The most compact and most powerful form.
- **Playbooks and skills** — step-by-step procedures for recurring tasks, learned once and loaded on demand (post 2's load-by-task-type retrieval). A good playbook converts a two-hour exploration into a ten-minute execution.
- **Worked examples** — successful past solutions stored and injected as few-shot context for similar tasks; the humblest form of learning and often the most reliable, because it transfers texture no rule captures.
- **Failure memory** — the anti-library: approaches that didn't work and *why*, retrieved when the agent is about to walk the same dead end. Cheap to keep, disproportionate in value — post 1's "repeated mistakes" cost, finally paid down.

## The learning loop, and where it breaks

The loop is simple to draw: act → observe outcome → reflect (post 6's consolidation extracts the lesson) → encode (write the rule/playbook/example) → apply (future retrieval changes behavior). Each stage has a characteristic failure, and naming them is most of the engineering:

- **Outcome attribution** — did the approach fail, or did the network flake? A lesson learned from a misattributed outcome is a superstition. Learning needs outcome signals sturdier than the agent's own impression: test results, user confirmations, explicit error classes.
- **Overgeneralization** — one bad experience with an API becomes "never use this API." The lesson encoder must capture *scope* with the rule: the conditions under which it held, and ideally the episode receipts (post 5's pattern) behind it.
- **Lesson rot** — the workaround for last year's bug outlives the bug. Procedures need the same revision discipline as semantic facts: dates, periodic revalidation, and retirement when the world moves.
- **Conflict accumulation** — new lessons contradicting old ones, both retrieved. Procedural memory needs supersession semantics — a new rule *replaces* its predecessor, with the history kept, exactly like post 5's temporal edges.

## Brakes: why procedural writes are different

A bad episodic memory pollutes one retrieval; a bad procedure pollutes *every future task*. That asymmetry justifies treating procedural writes with the gravity of production deploys — and the toolkit is post 4 of the enterprise series transplanted: an **autonomy ladder for learning**. Suggested lessons land as proposals a human reviews (the diff-based review post 6 set up); confirmed-safe classes (worked examples, failure notes) auto-apply; standing-instruction changes always gate. Add **provenance** (every learned rule links to the episodes that taught it — when the rule misfires, the receipts say why it existed), **blast-radius limits** (lessons scoped to a project or client before being promoted to global), and **regression evals** (post 8: a learned procedure is a change to agent behavior, so it runs the same eval gate any behavior change would). Teams that skip the brakes don't get faster learning; they get an agent whose behavior drifts on an unreviewed stream of self-written rules — post 3's silent goal drift, now compounding and persistent.

## Start humble: the two highest-ROI loops

The full loop sounds grand; the versions that pay this quarter are modest. **Failure memory first**: log every failed approach with its error and context at consolidation time, retrieve it when task similarity spikes — "you tried X here before; it failed with Y" injected at the right moment prevents the most expensive category of waste, and it's nearly risk-free because it *informs* rather than instructs. **Worked examples second**: store the final, verified solution of each completed task; inject the nearest one or two as examples on similar tasks. Both are append-mostly, low-conflict, and need no standing-instruction writes — the brakes stay simple while the compounding starts. Graduate to self-written rules and playbooks only when attribution signals and review paths exist, because that's where the leverage — and the drift — lives.

The takeaway: learning without weight changes lands in artifacts — **rules, playbooks, worked examples, failure memory** — through the loop act → attribute → reflect → encode → apply, whose failure modes (misattribution, overgeneralization, rot, conflict) each need explicit counters: sturdy outcome signals, scoped lessons with receipts, revision discipline, supersession. Procedural writes deserve deploy-grade brakes — proposal review, provenance, blast-radius limits, regression evals — and the humble loops (failure memory, worked examples) deliver most of the compounding at a fraction of the risk.

## Key takeaways

- Learning lands in **artifacts, not weights**: standing rules, loadable playbooks, injected worked examples, and failure memory (the anti-library) — all inspectable and reversible.
- The loop breaks at known points: **misattribution** breeds superstition (need real outcome signals), **overgeneralization** (encode scope + receipts), **lesson rot** (date, revalidate, retire), **conflicts** (supersession semantics).
- Procedural writes are **deploy-grade**: one bad rule pollutes every future task — so proposals + review for standing instructions, provenance links, project-scoped blast radius, regression evals before promotion.
- Highest ROI first: **failure memory** (inform, don't instruct — nearly risk-free) and **worked examples**; graduate to self-written rules only once attribution and review exist.

## Further reading

- [Procedural memory — knowing how, as distinct from knowing that](https://en.wikipedia.org/wiki/Procedural_memory)
- [Transfer learning — carrying what was learned into new tasks](https://en.wikipedia.org/wiki/Transfer_learning)

---

Author: Pratik Dhanave (https://pratikdhanave.com) | Published: 2026-11-10
Canonical: https://pratikdhanave.com/blog/posts/agmem-07-learning-from-experience.html
Attribution: please link the canonical URL when citing or quoting this post.
