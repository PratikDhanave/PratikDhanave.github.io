# Acquiring Tools and Skills

*An agent whose action space is fixed can only ever recombine what it was given, but an agent that writes and banks its own skills grows more capable the longer it runs.*

Memory evolves what an agent knows; prompts evolve how it is instructed. This post is about the axis that expands what an agent can *do*: acquiring tools and skills. An agent that can write new capabilities, verify them, and store them for reuse has an action space that grows over time instead of staying frozen at deployment. This is the fourth post in a series on self-evolving agents, and the ideas here are among the most striking in the field.

## The skill library idea

The landmark demonstration is [Voyager (Wang et al., 2023)](https://arxiv.org/abs/2305.16291), an agent that plays Minecraft as an open-ended, lifelong learner. What makes it relevant far beyond games is its architecture, which has three parts worth lifting into any agent:

- an **automatic curriculum** that proposes progressively harder goals to maximize exploration, so the agent is always working at the edge of its competence rather than repeating what it can already do;
- an **ever-growing skill library** of executable code, where each mastered behavior is stored as a reusable program that can be retrieved and composed later;
- an **iterative prompting mechanism** that incorporates environment feedback, execution errors, and self-verification to refine a program until it works.

The skill library is the heart of it. When the agent figures out how to accomplish something, it does not throw the solution away — it saves the working code as a named skill. Later, harder tasks retrieve and combine existing skills instead of solving from scratch. Capability compounds: early skills become the building blocks of advanced ones, and the agent that has run for a long time is meaningfully more capable than the one that just started. That is self-evolution on the action-space axis, made concrete.

## Why code is the right unit of skill

Voyager stores skills as executable code, and the choice is deliberate. Code is precise, composable, and — crucially — **verifiable**. You can run a candidate skill, observe whether it does what was intended, and only admit it to the library if it passes. That verification step is the feedback signal this whole series keeps returning to, applied to skills: a skill is not saved because the model felt good about it, but because it demonstrably worked.

This generalizes past Minecraft. Any domain where an agent's actions can be expressed as code — data pipelines, API orchestration, automation scripts — can support a skill library. An agent that solves a data-cleaning task can save the working transformation as a reusable function; the next similar task retrieves it. The pattern is: solve, verify, name, store, retrieve.

## Agents that write their own tools

A close cousin of skill acquisition is tool creation: rather than only using the tools you hand it, an agent generates new tools on demand. Faced with a task no existing tool covers, the agent writes one — a function with a clear signature and purpose — tests it, and adds it to its toolset. Where a fixed-tool agent is stuck when the task falls outside its equipment, a tool-creating agent extends its own equipment.

The engineering shape mirrors the skill library:

```python
def acquire_skill(task, skills, model, verify):
    # Try to solve with existing skills first.
    plan = model.plan(task, available=skills.list())
    if plan.solved:
        return plan.result

    # Otherwise, write a new skill as code.
    candidate = model.write_skill(task, context=skills.retrieve(task))

    # Verify before trusting it — this is the load-bearing step.
    if verify(candidate):
        skills.add(name=candidate.name, code=candidate.code, doc=candidate.doc)
        return candidate.run(task)

    return None  # failed verification; do not pollute the library
```

The comment on `verify` is the whole point. An unverified skill library rots: buggy or subtly wrong skills get retrieved and composed into larger failures. The discipline that keeps a growing skill set an asset rather than a liability is admitting only what passes a real check.

## Retrieval and curation

A library that only grows becomes its own problem. Two practices keep it healthy. **Retrieval** must surface the *right* skill for a task — usually by embedding skill descriptions and matching against the task — because a library the agent cannot search is dead weight. And **curation** must prune: deduplicate near-identical skills, retire ones that later fail, and prefer general skills over hyper-specific ones. The automatic curriculum in Voyager helps here too, by steering the agent toward genuinely new capabilities rather than re-learning what it already has.

Think of the skill library like a well-kept codebase, not a junk drawer. The value is not in how many skills it holds but in how reliably the agent can find and trust the right one.

## Where this fits

Skill and tool acquisition is the most capability-expanding form of self-evolution, and also one of the safer ones when done with verification, because every addition is gated by a check before it can affect behavior. It composes naturally with the earlier axes: memory records *when* a skill helped, prompt optimization tunes *how* the agent decides to use skills, and the skill library grows *what* it can do. An agent that combines all three — remembers, refines its instructions, and banks verified skills — is evolving on three fronts at once, which is exactly the architecture the final post assembles.

## Key takeaways

- Tool and skill acquisition evolves an agent's action space, so it grows more capable the longer it runs instead of being frozen at deployment.
- Voyager's architecture — automatic curriculum, an ever-growing skill library of executable code, and iterative self-verifying prompting — is the template; the skill library is where capability compounds.
- Storing skills as code makes them precise, composable, and verifiable; a skill earns a place in the library by demonstrably working, not by the model's confidence.
- Tool-creating agents write, test, and bank new tools on demand, extending their own equipment when a task falls outside existing tools.
- A skill library needs retrieval (find the right skill) and curation (prune, dedupe, retire failures); verified additions make it an asset, unverified ones make it rot.

## Further reading

- [Voyager: An Open-Ended Embodied Agent with Large Language Models — Wang et al., 2023](https://arxiv.org/abs/2305.16291)
- [Reflexion: Language Agents with Verbal Reinforcement Learning — Shinn et al., 2023](https://arxiv.org/abs/2303.11366)
- [Self-Refine: Iterative Refinement with Self-Feedback — Madaan et al., 2023](https://arxiv.org/abs/2303.17651)
