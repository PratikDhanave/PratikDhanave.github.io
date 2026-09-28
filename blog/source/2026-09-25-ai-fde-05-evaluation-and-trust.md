# Evaluation and Trust for Deployed AI

*You cannot ship AI you cannot measure, and no enterprise grants a probabilistic system authority over real work on faith. Both problems have the same answer: evaluation. Building the customer's own evaluation set — real examples, their definition of correct — is how the AI forward deployed engineer turns "it seemed good in the demo" into a reliability number, and that number is how trust gets earned.*

Grounding (post 4) made the system answer from real data. But how *often* is it right? Nobody knows until you measure — and measurement is what makes AI deployable at all. This post is about evaluation as the AI FDE's central discipline, and about the thing evaluation ultimately buys: the customer's trust. The two are inseparable, because in an AI deployment trust is not given, it's demonstrated, and demonstration means numbers.

## Why evaluation is non-negotiable for AI

Traditional software is largely deterministic: it works or it has a bug you can reproduce and fix. AI is different in a way that makes evaluation mandatory, not optional:
- **It's probabilistic.** The same input can yield different outputs, and the system is right *most* of the time and wrong *some* of the time. "Does it work?" has no yes/no answer — only a distribution, which you have to measure.
- **It fails silently and confidently.** A wrong answer looks exactly as fluent and assured as a right one. Without evaluation you can't tell them apart, and neither can the user — which is precisely why unmeasured AI is dangerous.
- **It's the only way to improve deliberately.** Every change (a new prompt, better retrieval, a different model) might help some cases and hurt others. Without an eval set you're guessing, and you'll regress silently. With one, you iterate with evidence.

This is the same lesson as the [AI Evaluation and Benchmarking](/blog/series/ai-evaluation-and-benchmarking/) series, applied at a customer: evaluation is the bottleneck and the enabler. For the AI FDE it's also the trust-building instrument, which raises the stakes.

## The customer's eval set is the crown jewel

Generic benchmarks (MMLU and the like) tell you almost nothing about whether the system does *this customer's* job. What matters is an evaluation set built from the customer's own reality:
- **Real, representative examples** — actual inputs from the customer's work (real documents, real questions, real tickets), covering the common cases and the tricky edge cases that matter to them.
- **The customer's definition of correct** — success defined in *their* terms, ideally with known-good answers or judgments from their domain experts. What counts as a good answer is a domain question only the customer can settle, and getting them to define it is itself valuable alignment work.
- **The failures you've seen** — every wrong answer from the demo, pilot, and production becomes a new eval case (post 3's "failures are the roadmap"). The eval set grows as you learn, and it's how you ensure fixed bugs stay fixed.

This eval set is one of the most valuable artifacts the AI FDE produces. It encodes what "working" means for this customer, it's the ground truth for every improvement, and it's the evidence base for trust. Building it — sitting with the customer's experts to collect examples and adjudicate correct answers — is core FDE work, not a side task.

## How to evaluate

Evaluation for a deployed AI system operates at two levels, mirroring the offline-online split:
- **Offline evaluation** — run the system over the eval set and score it. Scoring uses the right method per task: exact/structural checks where there's a definite answer, reference-based or semantic similarity for generation, and **LLM-as-a-judge** (a model scoring outputs against a rubric) for open-ended quality — calibrated against human judgment so you trust the judge. For grounded systems, evaluate **retrieval** separately from **generation** (post 4): did the right context get retrieved, *and* did the model use it correctly? Isolating the two tells you what to fix.
- **Online evaluation** — measure real usage: are users accepting the outputs, editing them, overriding them, or abandoning the tool? Real behavior is the ultimate signal, and (as in recommendation and elsewhere) offline and online can disagree, so you need both. Techniques like A/B testing and shadow deployment let you compare versions on real traffic safely.

Crucially, evaluation is **continuous**, not a one-time gate. Wire it into the pipeline so every change is scored against the eval set (catching regressions before they ship) and production quality is monitored over time (catching drift — post 7). An eval set that's run once and forgotten is a fraction as valuable as one that guards every release.

## Guardrails: handling the wrong answers you will have

Evaluation tells you the system is wrong X% of the time. Since X is never zero, you must design for those wrong answers — this is where evaluation meets [guardrails](/blog/series/guardrails-and-prompt-injection-defense/):
- **Abstention.** The system should recognize when it doesn't know (the answer isn't in the retrieved data) and say so, rather than confabulate. "I don't have that information" is a *correct* answer that builds trust; a confident wrong answer destroys it.
- **Confidence and citations.** Surface how grounded an answer is and show its sources (post 4), so users can calibrate their trust per answer and verify the important ones.
- **Output checks and policy.** Validate outputs (format, safety, policy compliance) before they reach users, and define behavior for out-of-scope or adversarial inputs.
- **Human-in-the-loop where the stakes demand it.** For consequential actions, keep a human in the decision (post 6). This is often what makes a customer willing to deploy at all — the failure mode is bounded because a person is checking.

The mindset: you are not deploying a system that's always right; you're deploying one that's right often enough *and fails safely*. Designing the failure behavior is as important as improving the accuracy, and it's what lets an imperfect system be trustworthy.

## Trust is earned, measured, and maintained

All of this serves the real currency of an AI deployment: trust. Nobody grants a probabilistic system authority over real decisions on faith — trust is built the way the general FDE builds it (small kept promises, honest communication — the [foundational series](/blog/series/forward-deployed-engineering/)), plus something AI-specific: **demonstrated, measured reliability on the customer's own problems.**

- **Start where the stakes are low** and let the system prove itself before expanding its authority. Trust compounds — a system reliable on small things earns the right to bigger ones.
- **Show the numbers.** "Here's how often it's right on your examples, here's how it's improving, here's how it fails and what happens when it does." Transparency about limitations builds *more* trust than claims of perfection, because the customer can see you're being honest about a probabilistic system.
- **Never let a silent regression erode it.** One confidently-wrong answer on something important can undo months of earned trust. Continuous evaluation and monitoring exist partly to protect the trust you've built.

Trust and evaluation are the same project: you earn trust by demonstrating reliability, you demonstrate reliability by measuring it, and you maintain both by never stopping.

The takeaway: evaluation is the AI FDE's central discipline because AI is probabilistic and fails silently and confidently — you can't ship what you can't measure, and you can't improve without an eval set. The crown-jewel artifact is the *customer's own* evaluation set (real examples, their definition of correct, growing from every failure), run continuously offline and online, with retrieval evaluated separately from generation. Since the system is never perfectly right, design it to fail safely (abstention, citations, output checks, human-in-the-loop). And all of it serves trust — which in an AI deployment is not given but demonstrated, through measured reliability on the customer's own problems, shown honestly and maintained relentlessly.

## Key takeaways

- Evaluation is **non-negotiable** for AI: it's **probabilistic** (right most of the time, quantifiably), **fails silently and confidently** (wrong looks like right), and is only improvable **deliberately** with an eval set — "does it work?" has no yes/no answer, only a measured distribution.
- The **customer's own eval set** is the crown jewel: real representative examples, **their** definition of correct (from their domain experts), growing from every observed failure — it encodes what "working" means and is the evidence base for trust.
- Evaluate **offline** (score over the eval set; exact/semantic/LLM-as-judge; evaluate **retrieval separately from generation** for grounded systems) and **online** (acceptance/edit/override/abandon behavior) — **continuously**, wired into the pipeline to catch regressions and drift, not as a one-time gate.
- Since accuracy is never 100%, **design safe failure** with guardrails: **abstention** ("I don't know" is a trust-building correct answer), **confidence + citations**, output/policy checks, and **human-in-the-loop** for consequential actions — designing the failure behavior matters as much as the accuracy.
- **Trust is earned, measured, and maintained**: start low-stakes and expand as it proves itself, **show the numbers** (transparency about limits builds more trust than claims of perfection), and protect trust with continuous evaluation — trust and evaluation are the same project.

## Further reading

- [Concept drift — why model quality degrades over time (monitor it)](https://en.wikipedia.org/wiki/Concept_drift)
- [A/B testing — comparing versions on real traffic](https://en.wikipedia.org/wiki/A/B_testing)
