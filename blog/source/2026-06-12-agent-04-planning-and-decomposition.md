# Planning and Decomposition

*Ask an agent to "research this market and write a report" and it faces the same problem a person would: the task is too big to do in one leap. The answer, for agents as for people, is to break it down — decompose the goal into steps, and work through them. Planning is how agents handle complexity that the basic reason-act loop alone would fumble, and the patterns for doing it — from planning upfront to decomposing on the fly — are among the most important in agent design.*

**Planning and task decomposition** is how agents handle *complex, multi-step* tasks — breaking a big goal into manageable steps. This post covers why planning matters, the core idea of decomposition, planning patterns (plan-then-execute vs decompose-as-you-go), and the tradeoffs. It builds on the core loop: planning is about *structuring* the sequence of actions the loop takes, so the agent can tackle tasks too complex to handle step-by-step without a plan.

## Why planning matters

The basic reason-act-observe loop (deciding one step at a time) works for many tasks, but *complex* tasks benefit from — or require — **planning**: thinking about the *overall approach* and breaking the goal into steps. Why:

- **Complex tasks are too big for one-step-at-a-time.** For a genuinely complex, multi-step goal (research and write a report, build a feature, solve a multi-part problem), deciding purely one step at a time — without any overall plan — can lead the agent to wander, miss steps, or lose the thread. Planning gives the agent an *overall structure* to work toward, so it tackles the task coherently rather than myopically. Complexity calls for structure.
- **Decomposition makes hard tasks tractable.** A big, complex task is hard to do all at once but often manageable *broken into smaller steps* (each of which is simpler). Decomposing the goal into sub-tasks turns one hard problem into a sequence of easier ones — the same divide-and-conquer principle that helps in programming and reasoning (the chain-of-thought idea from the reasoning series, at the task level). Decomposition is the core of planning.
- **Planning improves reliability on complex tasks.** With a plan, the agent is less likely to skip steps, go in circles, or lose track of the goal — it has a structure to follow and check against. For complex multi-step tasks, planning meaningfully improves the odds of success (vs pure step-by-step). It's a key pattern for making agents work on hard tasks.

Planning matters because complex, multi-step tasks benefit from an overall structure and from being decomposed into manageable steps — turning one hard problem into a sequence of easier ones and improving reliability. The core of planning is *decomposition*: breaking the goal down. How and when the agent does this defines the planning patterns.

## Decomposition: breaking down the goal

**Decomposition** — breaking a goal into sub-tasks/steps — is the heart of planning. The idea and how agents do it:

- **Break the goal into sub-goals/steps.** Decomposition means taking the overall goal and dividing it into a sequence (or hierarchy) of *sub-tasks* — smaller, more concrete steps that together accomplish the goal. "Research the market and write a report" decomposes into "identify key players → gather data on each → analyze trends → write sections → assemble report." Each sub-task is simpler and more actionable than the whole. The agent (using the LLM) generates this decomposition.
- **The LLM does the decomposing.** In an LLM agent, the *model* decomposes the task — reasoning about how to break the goal into steps (leveraging its reasoning ability, from the reasoning-models series). The agent essentially asks the LLM to *plan*: "what are the steps to accomplish this?" — producing a decomposition it then works through. So decomposition is a reasoning task the LLM performs, guided by the agent structure.
- **Hierarchical decomposition for very complex tasks.** Complex sub-tasks can themselves be decomposed further — a hierarchy of tasks and sub-tasks. This *hierarchical* decomposition (breaking down, then breaking down the pieces) handles very complex goals by recursively simplifying. Not every task needs this, but it's a powerful pattern for genuinely large, complex tasks.

Decomposition — breaking the goal into a sequence or hierarchy of simpler sub-tasks, done by the LLM's reasoning — is the core of planning. It's how an agent turns an overwhelming goal into a workable set of steps. The key design question is *when* the agent decomposes and plans: all upfront, or as it goes.

## Planning patterns: plan-then-execute vs decompose-as-you-go

There are two main patterns for *when* an agent plans, with a spectrum between — and the choice is a key design decision:

- **Plan-then-execute (plan upfront).** The agent first *creates a full plan* (decomposes the whole task into steps), then *executes* the steps in order (possibly with a separate executor). Planning and execution are separate phases: think through the whole approach first, then carry it out.
  - *Pros:* a coherent overall strategy, clear structure, the whole task considered upfront, easier to follow and inspect.
  - *Cons:* less adaptive — a rigid upfront plan can fail when reality differs from expectations (a step doesn't work, new information changes things), since it was made before seeing results. Real tasks often don't go as planned.
- **Decompose-as-you-go (dynamic).** The agent decides steps *dynamically* as it goes (the basic ReAct loop) — figuring out the next step based on the current situation and observations, without a fixed upfront plan.
  - *Pros:* highly *adaptive* — it responds to actual results, handling the unexpected (the core strength of the agentic loop from earlier posts).
  - *Cons:* can lack overall coherence/direction — without a plan, the agent may wander, lose the thread, or be inefficient on complex tasks. Good for adaptivity, weaker on overarching structure.
- **The hybrid: plan and adapt.** In practice, the best approach is often a *hybrid*: make an initial plan (for coherence/structure) *but adapt it* as you execute (revising based on results). Plan-and-adapt combines upfront structure with dynamic responsiveness — follow a plan, but update it when reality demands. Many effective agents plan, then adjust the plan as they learn. This balances coherence and adaptivity.

The planning patterns — plan-then-execute (coherent but rigid), decompose-as-you-go (adaptive but potentially unfocused), and the hybrid plan-and-adapt (structure plus responsiveness) — represent the key choice of *when and how much* to plan. The hybrid is often best for complex tasks, but the right choice depends on the task (below). Knowing these patterns is knowing how to structure an agent's approach to complex work.

## When and how much to plan

Planning is powerful but has costs and isn't always needed — so *when and how much* to plan is a real judgment:

- **Match planning to task complexity.** Simple tasks don't need planning — the basic reason-act loop suffices, and explicit planning adds overhead. *Complex, multi-step* tasks benefit from (or need) planning and decomposition. Match the planning effort to the task: don't over-plan simple tasks, do plan complex ones. Planning is a tool for complexity, not a default.
- **Planning costs compute (and can go wrong).** Planning itself is LLM work (reasoning to decompose) — it costs tokens/compute, and the *plan* can be wrong (the model might decompose poorly or plan for a reality that doesn't hold). So planning isn't free and isn't guaranteed to help — a bad plan can misdirect the agent. This is why adaptivity (revising the plan) matters: a plan is a starting structure, not an infallible script.
- **Plans should be revisable.** Because reality often differs from the plan, treating a plan as *revisable* (adapt it as you learn) rather than fixed is usually wiser (the hybrid pattern). Rigidly following an outdated plan is a failure mode; adapting it based on results is the strength. Build agents to *plan and adapt*, not just plan.
- **It connects to reflection.** Planning pairs naturally with *reflection* (the next post) — the agent can *evaluate* its progress against the plan and *revise* (re-plan) when things aren't working. Plan → execute → reflect → re-plan is a powerful cycle for complex tasks. Planning and reflection together make agents capable on hard, long-horizon tasks.

Planning and decomposition — breaking complex goals into manageable steps — is how agents handle complexity the basic loop alone would fumble, via patterns from plan-then-execute (coherent) to decompose-as-you-go (adaptive) to the hybrid plan-and-adapt (usually best), matched to task complexity and treated as revisable. Next: memory — how agents remember, within and across tasks.

## Key takeaways

- Planning matters for complex, multi-step tasks: deciding purely one-step-at-a-time can make an agent wander or lose the thread, so planning gives an overall structure, and decomposition (breaking the goal into simpler sub-tasks) turns one hard problem into a sequence of easier ones — improving coherence and reliability (the divide-and-conquer / chain-of-thought idea at the task level).
- Decomposition is the core of planning: the LLM (using its reasoning) breaks the goal into a sequence or hierarchy of sub-tasks (and complex sub-tasks can be decomposed further — hierarchical decomposition for very large goals), turning an overwhelming goal into workable steps.
- The main patterns differ by *when* the agent plans: plan-then-execute (full plan upfront, then execute — coherent and inspectable but rigid and failure-prone when reality differs) vs decompose-as-you-go (dynamic step-by-step — highly adaptive to results but potentially unfocused on complex tasks).
- The hybrid plan-and-adapt (make an initial plan for structure, but revise it as execution reveals reality) is often best for complex tasks — combining upfront coherence with dynamic responsiveness — because real tasks rarely go exactly as planned.
- Match planning to task complexity (simple tasks need none; the basic loop suffices), remember planning costs compute and a plan can be wrong (so treat plans as revisable, not infallible scripts), and pair planning with reflection (plan → execute → reflect → re-plan) for capability on hard, long-horizon tasks.

## Further reading

- [A Survey on Large Language Model based Autonomous Agents — planning approaches (Wang et al., 2023)](https://arxiv.org/abs/2308.11432)
- [Reasoning Models & Test-Time Compute — the reasoning behind decomposition](/blog/series/reasoning-models-test-time-compute/)
- [Tool use (previous post)](/blog/posts/agent-03-tool-use.html)
