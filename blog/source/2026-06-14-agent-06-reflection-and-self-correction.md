# Reflection and Self-Correction

*The first output is rarely the best output — a truth as old as writing, and one that applies to agents too. An agent that acts once and moves on repeats its mistakes; an agent that looks back at what it did, judges whether it worked, and tries again can dramatically improve. Reflection — the agent evaluating and correcting its own work — is what turns a one-shot attempt into an iterative process that gets better, and it's one of the most powerful patterns for making agents reliable on hard tasks.*

**Reflection and self-correction** is the pattern where an agent *evaluates its own work* and *improves* based on that evaluation — catching and fixing mistakes rather than accepting the first attempt. This post covers what reflection is, how the reflect-and-revise loop works (the Reflexion idea), why it improves results, and its costs and limits. It's a key pattern for agent reliability, building on the loop, and it connects closely to the reasoning-models series' ideas about self-correction and verification.

## What reflection is

**Reflection** (or self-critique/self-correction) is when an agent *examines its own output or actions*, *evaluates* them (is this correct? did it work? is it good enough?), and *uses that evaluation to improve* — revising, retrying, or correcting. The core idea:

- **The agent judges its own work.** Instead of producing an output and moving on, a reflective agent *steps back and critiques* what it produced or did — checking for errors, gaps, or quality issues. It turns a critical eye on its own work, much as a person reviews a draft before considering it done. This self-evaluation is the essence of reflection.
- **Evaluation drives improvement.** The point of reflecting isn't just to judge but to *improve*: based on the critique, the agent *revises* the output, *retries* a failed action differently, or *corrects* a mistake. Reflection feeds into a *revision* — the agent uses its self-assessment to do better. Evaluate, then improve, is the loop. Reflection without acting on it is pointless; the value is in the correction it drives.
- **It mirrors human iterative work.** Reflection formalizes what people do naturally on hard work — draft, review, revise; try, see if it worked, adjust. The first attempt is rarely the best, and *reviewing and improving* it produces better results. Agents that reflect capture this iterative-improvement dynamic, which is why reflection helps: it replaces one-shot output with an iterative refine-until-good process. Iteration beats one-shot.

Reflection is the agent evaluating its own work and using that evaluation to improve (revise, retry, correct) — formalizing the human "draft, review, revise" dynamic. It replaces accepting the first attempt with an iterative process that catches and fixes mistakes. The concrete mechanism is a reflect-and-revise loop.

## The reflect-and-revise loop

Reflection is implemented as a *loop*: attempt → evaluate → revise → repeat — a pattern crystallized by ideas like **Reflexion**. How it works:

```text
   Reflect-and-revise loop:
     1. ATTEMPT   — produce output / take action
     2. EVALUATE  — critique it (correct? worked? good enough?)
     3. REVISE    — if not good enough, improve based on the critique
     4. repeat    — until satisfactory (or a limit)
```

- **Attempt, then evaluate.** The agent produces an output or takes an action, then *evaluates* it — checking whether it's correct, worked, or meets the bar. The evaluation can come from the agent *itself* (self-critique: the LLM assessing its own output), from a *tool* (running tests on generated code, checking a result), or from an *external signal* (feedback, an error). The evaluation is the crucial judgment step.
- **Revise based on the evaluation.** If the evaluation finds problems, the agent *revises* — improving the output or trying the action differently, *using the critique* to guide the improvement. The specific feedback ("this part is wrong because...", "the tests failed on...") directs a targeted fix, not a blind retry. Informed revision is what makes the loop effective.
- **Reflexion: learning from feedback verbally.** The *Reflexion* pattern captures this: an agent *reflects* on feedback about its attempts (in language — "verbal" reflection), storing what went wrong and using it to improve subsequent attempts. It's the agent learning from its failures *within* the task, through reflection on what happened, without changing the model's weights. This verbal self-reflection driving improvement across attempts is a powerful, influential formulation.
- **Repeat until good (with a limit).** The loop repeats — attempt, evaluate, revise — until the output is satisfactory or a limit is hit (like the core loop's termination, reflection loops need bounds too, to avoid endless revision). Iterating toward quality is the mechanism. Each cycle should improve on the last.

The reflect-and-revise loop (attempt → evaluate → revise → repeat), formalized by Reflexion, is how reflection is implemented — with evaluation from self-critique, tools (tests, checks), or external feedback, driving informed revision, bounded by a limit. This iterative loop is what lets agents refine their work toward quality. And it demonstrably improves results.

## Why reflection improves results

Reflection meaningfully improves agent performance on hard tasks — worth understanding why:

- **It catches mistakes the first attempt misses.** LLMs (and agents) make errors, and a first attempt often has mistakes the model *can recognize when it looks again*. Reflection gives the agent a chance to *catch and fix* errors it would otherwise ship — often the model can spot its own mistake on review even if it made it initially. This error-catching is a direct reliability improvement. Two looks beat one.
- **It leverages the verify-vs-generate asymmetry.** As in the reasoning series, *verifying/critiquing* is often easier than *generating* correctly the first time — it's easier to spot that an answer is wrong (or that code fails tests) than to get it perfectly right initially. Reflection exploits this: generate an attempt, then use the (easier) evaluation to catch problems and improve. This asymmetry is why reflect-and-revise works — checking is easier than first-try perfection.
- **It's iterative improvement (test-time compute).** Reflection is a form of *spending more compute at inference to get a better result* (the test-time-compute idea from the reasoning series) — more reflection/revision cycles = more compute = (up to a point) better output. It converts extra compute into higher quality via iteration, especially valuable on hard tasks where the first attempt is likely imperfect. It's test-time compute applied to agent work.
- **It's especially valuable with concrete evaluation.** Reflection works best when there's a *concrete way to evaluate* — like running tests on generated code (pass/fail is objective feedback), checking a result, or verifiable correctness. With objective feedback, the evaluate step is reliable and the revision is well-directed — which is why reflection is especially powerful in domains like coding (test-driven agent loops). Good evaluation makes reflection strong.

Reflection improves results by catching mistakes the first attempt misses, leveraging the verify-vs-generate asymmetry (checking is easier than first-try perfection), spending test-time compute on iterative improvement, and being especially powerful with concrete evaluation (like code tests). It's a key reliability pattern. But it isn't free or unlimited.

## Costs and limits of reflection

Reflection is powerful but has real costs and limits — knowing them is part of using it well:

- **It costs compute (more LLM calls).** Each reflect-and-revise cycle is more LLM calls (evaluate, then revise) — so reflection *multiplies* the compute (and cost and latency) of a task. Like all test-time compute, it buys quality at a price (from the reasoning series' economics). So reflect where the quality gain is worth the cost — not endlessly on everything. More cycles cost more.
- **Self-evaluation can be unreliable.** A key limit: when the agent evaluates *itself* (self-critique, no external check), the evaluation is only as good as the model's judgment — which can be *wrong* (missing real errors, or "correcting" things that were fine, or being overconfident). Self-reflection without an objective signal can fail to catch errors or even make things worse. This is why *concrete/external* evaluation (tests, tools, real feedback) is much more reliable than pure self-critique. Don't over-trust an agent's self-assessment.
- **Diminishing returns and over-revision.** More reflection cycles help *up to a point* — then returns diminish, and excessive revision can even *hurt* (over-editing, second-guessing correct work, wandering). Like reasoning effort (from the reasoning series), there's an appropriate amount; more isn't always better. Bound the reflection loop and don't over-revise.
- **It needs bounds.** Like the core loop, reflection loops need *limits* (max revisions) to avoid endless or wasteful iteration. Unbounded reflection is a cost and reliability risk. Always bound it.

Reflection and self-correction — the agent evaluating and improving its own work in a reflect-and-revise loop (Reflexion) — is a powerful pattern that catches mistakes, leverages the verify-vs-generate asymmetry, and improves results via iterative test-time compute, especially with concrete evaluation (like code tests). But it costs compute, self-evaluation can be unreliable (prefer objective checks), and it needs bounds. Next: multi-agent patterns — coordinating multiple agents.

## Key takeaways

- Reflection (self-critique/self-correction) is the agent examining its own output/actions, evaluating them (correct? worked? good enough?), and using that evaluation to improve (revise, retry, correct) — formalizing the human "draft, review, revise" dynamic and replacing one-shot output with an iterative refine-until-good process.
- It's implemented as a reflect-and-revise loop (attempt → evaluate → revise → repeat, bounded by a limit), where evaluation comes from self-critique, tools (running tests/checks), or external feedback, and drives *informed* revision (specific critique guides a targeted fix); Reflexion formalizes an agent verbally reflecting on failures to improve subsequent attempts within a task.
- Reflection improves results by catching mistakes the first attempt misses (the model can often spot its own error on review), leveraging the verify-vs-generate asymmetry (checking is easier than first-try perfection), spending test-time compute on iterative improvement, and being especially powerful with concrete objective evaluation (like code passing tests).
- Its costs and limits: each cycle is more LLM calls (multiplying compute/cost/latency — reflect where worth it), self-evaluation without an objective signal can be unreliable (missing errors or "fixing" correct work — prefer external checks like tests/tools), and there are diminishing returns and over-revision risks.
- Like the core agent loop, reflection loops need bounds (max revisions) to avoid endless or wasteful iteration — reflection is a powerful reliability pattern used judiciously (with good evaluation, appropriate cycles, and limits), not applied endlessly to everything.

## Further reading

- [Reflexion: Language Agents with Verbal Reinforcement Learning (Shinn et al., 2023)](https://arxiv.org/abs/2303.11366)
- [Reasoning Models: inference-time techniques — verification and revision](/blog/posts/reason-05-inference-time-techniques.html)
- [Agent memory (previous post)](/blog/posts/agent-05-memory.html)
