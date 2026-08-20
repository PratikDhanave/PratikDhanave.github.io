# Building a Self-Evolving Agent

*The pieces from this series — memory, self-refinement, a skill library, and an evaluation gate — combine into one modest architecture that actually gets better as it runs, without the hype and without the footguns.*

We have taken self-evolving agents apart axis by axis: memory and reflection, self-refining prompts, tool and skill acquisition, the limits of self-critique, population search, and the evaluation and guardrails that keep it all honest. This final post puts the pieces back together into a single, buildable architecture — a practical self-evolving agent you could implement today, deliberately built on the cheap, safe axes and gated by real evaluation. This is the capstone of the series.

## Design principles first

Before any code, the principles the series earned:

- **Evolve the cheap axes first.** Memory, prompts, and skills give most of the benefit at a fraction of the cost and risk of touching weights or structure. Start there.
- **Every change is gated by a real signal.** No memory, skill, or prompt update takes effect until an evaluator that is not the model's bare opinion has approved it.
- **Make everything reversible.** Version changes; keep a known-good baseline; roll back instantly.
- **Keep it observable.** You cannot manage evolution you cannot see; log every change and its evaluation.

An architecture that honors these four is boring in the best way — it improves steadily and fails safely.

## The architecture

The agent has four components, mapping directly to earlier posts:

- a **memory** of past episodes and distilled lessons (post 2);
- a **skill library** of verified, reusable capabilities as code (post 4);
- a **reflect-and-refine** loop grounded in real feedback (posts 3 and 5);
- an **evaluation gate** that every proposed change must pass before it persists (post 7).

The four components form a single feedback loop — the agent acts through the model, the evaluation gate grades the result, and only what passes is written back to the evolving state that the next task draws on:

```text
        ┌─────────────┐   reason / act    ┌───────────────┐
        │     LLM     │◄──────────────────│ Self-Evolving │◄── Task
        │  (reasoning)│                   │    Agent      │
        └─────────────┘                   └───────┬───────┘
                          trajectory + result     │  ▲
                                     ┌─────────────┘  │ retrieve
                                     ▼                │ lessons + skills
                             ┌───────────────┐        │
                             │ Evaluation    │   ┌────┴─────────────────┐
                             │ Gate          │   │  Evolving state      │
                             │ (real signal) │   │  ┌────────┐┌────────┐│
                             └──────┬────────┘   │  │ Memory ││ Skill  ││
                    write reflection│  promote    │  │ store  ││ library││
                                    └────────────►│  └────────┘└────────┘│
                                   verified skill │  (persists across    │
                                                  │   tasks)             │
                                                  └──────────────────────┘
```

> **▸ [Open the interactive diagram](/blog/handbook-diagrams/self-evolving-agent-architecture.html)** — pan, zoom, and trace every step (light/dark, self-contained).

Here is the shape, with the control flow that ties them together:

```python
class SelfEvolvingAgent:
    def __init__(self, model, memory, skills, evaluate):
        self.model = model
        self.memory = memory        # episodic + semantic store
        self.skills = skills        # verified skill library
        self.evaluate = evaluate    # the real, trusted signal

    def run(self, task):
        # 1. Bring experience to bear: relevant lessons + skills.
        lessons = self.memory.retrieve(task, k=5)
        available = self.skills.retrieve(task, k=5)

        # 2. Act.
        trajectory = self.model.run(task, context=lessons, tools=available)

        # 3. Evaluate against a real signal (tests, tools, rubric).
        result = self.evaluate(task, trajectory)

        # 4. Grounded refine: one bounded pass if the signal says "failed".
        if not result.success:
            trajectory = self.model.refine(task, trajectory, result)
            result = self.evaluate(task, trajectory)

        # 5. Learn — but only what passes the gate.
        self._maybe_evolve(task, trajectory, result)
        return trajectory, result

    def _maybe_evolve(self, task, trajectory, result):
        # Write a lesson from a real outcome (success or failure).
        lesson = self.model.reflect(task, trajectory, result)
        self.memory.add(task=task, lesson=lesson, outcome=result.success)

        # Promote a genuinely new, verified capability into the library.
        if result.success and self.model.is_novel_skill(trajectory):
            candidate = self.model.extract_skill(trajectory)
            if self.evaluate.verify_skill(candidate):   # gate!
                self.skills.add(candidate)
```

Trace the loop against the principles. Step 3 makes the feedback real — the refine in step 4 is grounded in `result`, not in ungrounded self-doubt, which is exactly the distinction post 5 insisted on. Step 5 evolves only the cheap axes (memory and skills), and the skill promotion is gated by `verify_skill` — nothing enters the library on the model's say-so. Reflection is written from a real outcome, not from vibes.

## Closing the loop over time

The `run` method improves the agent within and across tasks, but two periodic background jobs make the evolution compound and stay healthy:

- **Synthesis.** Periodically, compress many episodic lessons into a few semantic ones (post 2), so memory stays small, general, and retrievable instead of an ever-growing log.
- **Curation.** Periodically, prune the skill library (post 4): deduplicate near-identical skills, retire ones that have started failing, and re-verify survivors against the current evaluator.

Both are themselves changes to the agent, so both run behind the same evaluation gate and versioning as everything else. Evolution that is never curated eventually collapses under its own accumulated weight; these jobs are what keep a long-running agent sharp.

## What to measure

Per the guardrails post, wrap the whole thing in continuous evaluation against a frozen baseline. Track a held-out success rate the evolution never trains on, watch per-category scores for regressions, and compare live against the pre-evolution agent. The moment the held-out metric stops rising — or a category regresses — you stop, inspect, and roll back if needed. The agent is only allowed to keep the changes that provably help on data it could not game.

## Knowing when not to evolve

The honest closing note: self-evolution is not free, and it is not always warranted. If your task is stable, well-specified, and already handled by a good static agent, adding an evolution loop buys you complexity and risk for little gain. Reach for these techniques when the task distribution is genuinely open-ended, when edge cases keep arriving that a static agent cannot adapt to, or when the value of steady in-place improvement justifies the machinery to do it safely. When you do, build on the cheap axes, gate every change behind a real signal, and keep it reversible. Done that way, a self-evolving agent is not a research curiosity — it is a system that quietly gets better at your problem while staying under your control.

## Key takeaways

- Combine the series' pieces into one architecture: a memory of lessons, a verified skill library, a grounded reflect-and-refine loop, and an evaluation gate every change must pass.
- Evolve the cheap, safe axes first (memory, prompts, skills); leave weights and structure for when those are exhausted and the task justifies it.
- Ground refinement in a real signal, and let nothing — a lesson, a skill, a prompt — persist until a trusted evaluator, not the model's opinion, approves it.
- Run periodic synthesis (compress episodic lessons into semantic ones) and curation (prune and re-verify skills), themselves gated and versioned, so evolution compounds without collapsing.
- Wrap everything in continuous evaluation against a frozen baseline, keep changes reversible, and decline to evolve when a static agent already suffices.

## Further reading

- [Reflexion: Language Agents with Verbal Reinforcement Learning — Shinn et al., 2023](https://arxiv.org/abs/2303.11366)
- [Voyager: An Open-Ended Embodied Agent with Large Language Models — Wang et al., 2023](https://arxiv.org/abs/2305.16291)
- [Automated Design of Agentic Systems — Hu et al., 2024](https://arxiv.org/abs/2408.08435)
