# What Are Self-Evolving Agents?

*Most agents are frozen the moment they ship, repeating the same mistakes forever, and self-evolving agents are the attempt to break that ceiling by letting the system improve itself as it runs.*

Build an agent today and, by default, it is static. Its prompt, its tools, and its weights are fixed at deployment. It can be brilliant on Monday and make the identical mistake on Friday, because nothing about Friday's failure changes Tuesday's behavior. Self-evolving agents are the research direction — and, increasingly, the engineering practice — aimed at that ceiling: systems that improve themselves over time from their own experience. This series builds the idea up carefully, grounded in the papers that defined it. This first post sets the terms: what "self-evolving" actually means, the axes along which an agent can change, and the loop underneath all of them.

## Why static agents plateau

A conventional LLM agent is a fixed policy wrapped around a fixed model. You can make it better only by *you* doing work — rewriting the prompt, adding a tool, fine-tuning the weights, editing the orchestration. The agent itself contributes nothing to its own improvement. That has two costs. First, it does not scale: every gain requires human effort proportional to the number of tasks and edge cases. Second, it cannot adapt in place: an agent that hits a novel situation in production has no mechanism to get better at it before the next human intervention.

Self-evolving agents ask a different question: what if the agent could close some of that loop itself? What if experience — successes, failures, feedback — could feed back into the agent's own configuration, so that it is measurably better later than it was earlier, without a human editing it each time?

## A working definition

A **self-evolving agent** is one that updates some part of *itself* — its memory, its instructions, its tools, its structure, or its weights — based on its own experience or feedback, in order to improve future performance. The emphasis is on *self* and on *persistence*: a one-off retry within a single task is not evolution; a change that carries forward and compounds is.

That definition deliberately spans a spectrum. At the light end, an agent that writes lessons from its failures into a memory it consults next time is self-evolving in a modest, practical sense. At the heavy end, a meta-agent that programs entirely new agent architectures is self-evolving in an ambitious, research sense. Both belong to the same family because both route the system's own output back into its own future behavior.

## The axes of change

It helps to name *what* can evolve, because the techniques differ sharply by axis. There are roughly five.

- **Memory.** The agent accumulates experience — episodes, reflections, facts — and retrieves it to act better later. Nothing about the model or prompt changes; the *context* the agent brings to bear does.
- **Prompts and instructions.** The agent (or a process around it) rewrites the very prompts that drive it, searching for wording that works better on the task distribution.
- **Tools and skills.** The agent acquires new capabilities — writing new tools or composing reusable skills — and banks them for reuse, so its action space grows over time.
- **Structure.** The *arrangement* of components evolves: how many agents, how they are wired, what roles they play, which control flow connects them.
- **Weights.** The model parameters themselves are updated from self-generated data, the heaviest and most powerful axis, and the one with the steepest cost and risk.

Most real systems evolve on the first three axes because they are cheap, reversible, and safe relative to touching weights or restructuring. The later posts take memory, prompts, and skills each in turn, then structure and the harder questions.

## The loop underneath all of it

Strip away the specifics and every self-evolving method is the same feedback loop:

1. **Act.** The agent attempts a task and produces a trajectory — its actions, tool calls, and outputs.
2. **Evaluate.** Some signal judges that trajectory: an environment reward, a test that passes or fails, a critic model, a human rating, or the agent's own reflection.
3. **Update.** That signal is turned into a change to one of the axes — a memory written, a prompt rewritten, a skill saved, a structure altered, a weight nudged.
4. **Repeat.** The improved agent attempts the next task, and the loop compounds.

The interesting design choices all live in steps 2 and 3. Where does the evaluation signal come from, and how trustworthy is it? And how is that signal turned into a durable change without breaking what already worked? Get the evaluation wrong and the agent "improves" toward the wrong target; get the update wrong and it forgets more than it learns. These two questions — the quality of the signal and the safety of the update — recur in every post of this series, and they are why evaluation and guardrails get a dedicated post near the end.

## What this is not

Two clarifications keep expectations honest. First, self-evolution is not the same as a model that self-corrects within a single answer. As we will see when we examine the limits, a model asked to fix its own reasoning with no external signal often does not improve, and can get worse — evolution needs a *real* feedback signal, not just the model second-guessing itself. Second, self-evolution is not autonomy run amok: the most useful systems keep humans and hard evaluations in the loop precisely so that "improvement" stays anchored to something true. The goal is an agent that gets better at what you want, not one that drifts wherever its own gradient points.

## Where the series goes

From here we go axis by axis, each grounded in the work that established it: memory and reflection, self-refining prompts, tool and skill acquisition, then self-critique and its documented limits, then population and search methods that evolve whole agent designs. We close with how to evaluate evolution safely and how to assemble a self-evolving agent from these parts. The throughline is practical skepticism — these techniques are real and useful, and they only work when the feedback signal is real.

## Key takeaways

- Static agents plateau because only human effort improves them; self-evolving agents route their own experience back into their own future behavior.
- A self-evolving agent updates part of *itself* — memory, prompts, tools/skills, structure, or weights — from experience, in a way that persists and compounds.
- Most practical systems evolve memory, prompts, and skills, because those axes are cheaper, safer, and more reversible than changing weights or structure.
- Every method is the same act → evaluate → update → repeat loop; the hard design choices are the quality of the evaluation signal and the safety of the update.
- Self-evolution is not single-answer self-correction and is not unbounded autonomy; it needs a real feedback signal and human/evaluation anchoring to improve toward what you actually want.

## Further reading

- [Reflexion: Language Agents with Verbal Reinforcement Learning — Shinn et al., 2023](https://arxiv.org/abs/2303.11366)
- [Generative Agents: Interactive Simulacra of Human Behavior — Park et al., 2023](https://arxiv.org/abs/2304.03442)
- [Automated Design of Agentic Systems — Hu et al., 2024](https://arxiv.org/abs/2408.08435)
