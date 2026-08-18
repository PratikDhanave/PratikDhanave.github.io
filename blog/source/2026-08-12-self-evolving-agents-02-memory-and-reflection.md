# Learning from Experience: Memory and Reflection

*The cheapest way to make an agent evolve is to let it remember what happened and reflect on it, turning yesterday's failure into today's context.*

The lightest and most practical axis of self-evolution is memory. You do not retrain anything or rewrite the agent's structure; you let it accumulate experience and consult that experience when it acts again. Done well, an agent that failed a task once carries the lesson into the next attempt and succeeds. This post covers the two ideas that made memory-based evolution concrete — verbal reflection and the memory stream — and how to build a modest version yourself. It is the second in a series on self-evolving agents.

## Reflection as a learning signal

The key insight behind [Reflexion (Shinn et al., 2023)](https://arxiv.org/abs/2303.11366) is that language itself can serve as the learning signal. Classic reinforcement learning updates numeric weights from a scalar reward. Reflexion instead converts feedback — a failed test, a wrong answer, an environment signal — into a *verbal* self-reflection: a short written analysis of what went wrong and what to do differently. That reflection is stored and prepended to the agent's context on the next attempt.

Nothing in the model changes. The agent improves because its *context* now contains a pointed lesson written by itself after seeing the outcome. On the next episode it reads "last time I assumed the file was JSON and it was actually CSV; check the format first" and adjusts. The reflection acts like a semantic gradient — a direction to improve — expressed in words rather than numbers. It is a strikingly cheap mechanism: no training, no labeled data, just a feedback signal, a place to write reflections, and the discipline to read them back.

The crucial dependency is that same feedback signal we keep returning to. Reflexion works when there is a real evaluator — tests that pass or fail, a task that is objectively completed or not — to reflect *on*. Reflection over a trustworthy signal is powerful; reflection over nothing but the model's own vibes is not, a limit we treat directly in a later post.

## The memory stream

Where Reflexion focuses on learning from task outcomes, [Generative Agents (Park et al., 2023)](https://arxiv.org/abs/2304.03442) tackles a different memory problem: how an agent accumulates and uses a long history of experience believably over time. Its architecture stores a complete record of the agent's experiences as natural-language observations in a **memory stream**, then does two things with them that are worth stealing for any agent.

First, **retrieval** is not just recency. The architecture scores memories by a combination of how recent, how important, and how relevant to the current situation they are, and pulls the top ones into context. That balance matters: a purely recent memory forgets the important-but-old; a purely relevant one ignores what just happened.

Second, and more interesting for evolution, the system periodically **synthesizes** low-level memories into higher-level **reflections** — condensed conclusions drawn from many observations. Rather than let the raw log grow forever, the agent distills patterns ("I keep getting stuck when the API is rate-limited") into durable, reusable insights. Those synthesized reflections then inform future planning. This is memory that compounds: experience becomes observations, observations become reflections, reflections shape behavior.

## Kinds of memory worth separating

Putting these ideas to work, it helps to distinguish the roles memory plays, because they have different retention and retrieval needs:

- **Episodic memory** — records of specific past episodes ("on task 47 I tried X and it failed because Y"). Useful for not repeating exact mistakes.
- **Semantic memory** — distilled, general facts and lessons ("CSV files in this pipeline use semicolons"). This is what reflection synthesis produces, and it generalizes across tasks.
- **Working memory** — the current task's scratchpad, which does not persist.

Self-evolution lives mostly in episodic and semantic memory. The move that makes an agent genuinely better over time is promoting scattered episodic experiences into semantic lessons — exactly the synthesis step Generative Agents formalizes.

## Building a modest version

You do not need the full machinery to benefit. A practical reflective-memory loop looks like this in outline:

```python
def attempt_with_memory(task, memory, model, evaluate):
    # 1. Retrieve relevant lessons for this task.
    lessons = memory.retrieve(task, k=5)

    # 2. Act, with lessons in context.
    trajectory = model.run(task, context=lessons)

    # 3. Evaluate against a real signal.
    result = evaluate(trajectory)          # e.g. tests pass/fail

    # 4. If it failed, reflect and store the lesson.
    if not result.success:
        reflection = model.reflect(task, trajectory, result)
        memory.add(task=task, lesson=reflection)

    return trajectory, result
```

Three design decisions make or break it. **What triggers a write** — reflect on failures for sure, and optionally on notable successes, but do not write noise on every step or the store fills with junk. **How retrieval scores** — blend relevance with recency and importance rather than dumping the whole store into context. **When to synthesize** — periodically compress many episodic entries into a few semantic lessons so the memory stays small, sharp, and generalizable instead of an ever-growing log the model cannot use.

The failure modes are the mirror of those decisions: a memory that grows without bound stops fitting in context and drowns signal in volume; retrieval that only considers recency forgets hard-won old lessons; and reflections written without a real evaluation signal record confident-sounding nonsense. Memory evolution is cheap, but it is not free of judgment.

## Key takeaways

- Memory is the cheapest self-evolution axis: no retraining, just accumulating experience and consulting it when acting again.
- Reflexion turns a real feedback signal (a failed test, a wrong answer) into a verbal self-reflection stored and reused next time — a semantic gradient in words, dependent on a trustworthy evaluator.
- Generative Agents' memory stream scores memories by recency, importance, and relevance, and periodically synthesizes low-level observations into higher-level reflections that compound.
- Separate episodic memory (specific past episodes) from semantic memory (distilled lessons); the evolution that generalizes comes from promoting episodic experience into semantic lessons.
- Control what triggers a memory write, how retrieval is scored, and when to synthesize — an unbounded or recency-only memory, or reflection without a real signal, degrades rather than helps.

## Further reading

- [Reflexion: Language Agents with Verbal Reinforcement Learning — Shinn et al., 2023](https://arxiv.org/abs/2303.11366)
- [Generative Agents: Interactive Simulacra of Human Behavior — Park et al., 2023](https://arxiv.org/abs/2304.03442)
- [Self-Refine: Iterative Refinement with Self-Feedback — Madaan et al., 2023](https://arxiv.org/abs/2303.17651)
