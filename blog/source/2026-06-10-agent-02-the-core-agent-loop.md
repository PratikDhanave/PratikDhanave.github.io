# The Core Agent Loop

*Strip away the frameworks, the tooling, and the jargon, and every LLM agent reduces to one simple loop: think about what to do, do it, look at what happened, repeat. This reason-act-observe cycle — crystallized by the ReAct pattern — is the beating heart of every agent, and understanding it deeply is understanding agents themselves. Once you see the loop clearly, agent frameworks stop being mysterious: they're all just implementations of this same fundamental cycle.*

The previous post defined an agent as an LLM deciding actions in a loop. This post is about *that loop* — the fundamental **reason-act-observe** cycle at the core of every agent, best known as the **ReAct** pattern. It covers what the loop is, how ReAct works, why interleaving reasoning and acting is powerful, and how the loop terminates. This is the single most important pattern in agent design, because every agent is built on it.

## The fundamental loop

Every agent operates on the same fundamental **loop**: the LLM repeatedly *decides what to do*, *does it*, and *observes the result*, until the goal is reached. Broken down:

```text
   The core agent loop:
     1. REASON  — the LLM thinks about the situation and decides the next action
     2. ACT     — it takes that action (usually calls a tool)
     3. OBSERVE — it sees the result of the action
     4. repeat  — back to reason, now knowing the result
     ... until the goal is achieved (or a stop condition)
```

- **Reason: decide the next action.** The LLM considers the goal, what's happened so far, and the current situation, and *decides what to do next* — which action/tool to use, or that the task is done. This is the "brain" step where the model directs the flow (from the previous post). The reasoning determines the action.
- **Act: take the action.** The agent *executes* the decided action — typically calling a *tool* (search, code, API — the tool-use post) to actually do something or gather information. This is where the agent affects the world or retrieves what it needs. The action is the model's decision made real.
- **Observe: see the result.** The agent *observes the outcome* of the action — the tool's result, the new information, what happened. This observation feeds back into the next reasoning step, so the agent's next decision is *informed by* the result. Observation closes the feedback loop.
- **Repeat until done.** The loop *repeats* — reason (now knowing the result), act, observe — accumulating progress toward the goal, until the agent decides the goal is achieved (or a stop condition triggers). Each iteration builds on the last. This iteration is what lets an agent handle *multi-step* tasks that no single LLM call could.

This reason-act-observe loop, repeated until done, is the fundamental mechanism of every agent — the engine that turns a deciding LLM into a system that accomplishes multi-step goals. Every agent, in every framework, is built on this loop. The canonical formulation of it is ReAct.

## ReAct: reasoning and acting interleaved

**ReAct** (Reasoning + Acting) is the influential pattern that formalized the core loop: the LLM *interleaves* explicit **reasoning** (thinking) with **acting** (taking actions), in a loop. It's the archetypal agent pattern:

- **Interleave thought and action.** In ReAct, the model alternates between *reasoning* ("I need to find X, so I should search for it") and *acting* (performing the search), using the reasoning to decide actions and the action results to inform further reasoning. Rather than reasoning *or* acting in isolation, ReAct *interleaves* them in the loop — think, act, observe, think again. This interleaving is the key idea.
- **Reasoning guides action; results inform reasoning.** The power is the synergy: *reasoning* helps the agent decide *what* action to take and *interpret* results, while *acting* (and observing) gives the reasoning real information to work with (grounding it in actual results rather than the model's assumptions). Reasoning without acting is ungrounded (the model guesses); acting without reasoning is blind (no strategy). ReAct combines them so each improves the other. This synergy — reasoning made effective by action, action made smart by reasoning — is why ReAct works well.
- **It builds on chain-of-thought.** ReAct extends the chain-of-thought idea (reasoning step by step — the reasoning-models series) by adding *acting*: the model reasons *and* acts, so its reasoning can *use tools and real information*. It's chain-of-thought that can *do things* and *learn from results*, not just think in isolation. This connection roots agents in the reasoning capabilities of LLMs.

ReAct formalizes the core loop as interleaved reasoning and acting: the model thinks, acts (via tools), observes, and thinks again — with reasoning guiding action and results grounding reasoning. This reasoning-acting synergy is the archetypal agent pattern and the standard formulation of the agent loop. Understanding ReAct is understanding how agents fundamentally work.

## Why the loop is powerful

The reason-act-observe loop is what gives agents their power over single LLM calls — worth making explicit:

- **It enables multi-step tasks.** A single LLM call produces one response; the loop lets the agent take *many* steps, building toward a goal that requires a sequence of actions. Complex tasks (research something, then act on it, then verify) need multiple steps, and the loop provides them. The loop is what turns "answer a question" into "accomplish a task."
- **It grounds the agent in reality via observation.** Because the agent *observes* the results of its actions and feeds them back, it works with *real information* (actual tool results, real data) rather than only the model's internal (possibly wrong) knowledge. Observation lets the agent *react to what actually happens* — correcting course based on real results, not assumptions. This grounding in observed reality is a major source of agents' capability (and reliability, when it works).
- **It's adaptive.** Because the agent decides each step *based on the current situation* (including observations), it *adapts* — handling unexpected results, changing approach when something doesn't work, responding to what it finds. This adaptivity (deciding dynamically based on real results) is exactly the "model directs the flow" agentic property, and it's what lets agents handle open-ended tasks a fixed sequence couldn't. The loop makes the agent responsive to reality.
- **It composes with the other components.** The loop is where tools (act), memory (remembering across iterations), planning (deciding the sequence), and reflection (evaluating and correcting) all come together — each operates *within* or *around* the loop. The loop is the integrating structure that the other patterns plug into. It's the backbone of the whole agent.

The core loop is powerful because it enables multi-step tasks, grounds the agent in observed reality (real results, not assumptions), makes it adaptive (deciding each step based on the actual situation), and integrates all the other components. It's the mechanism behind agents' ability to accomplish complex, open-ended goals. But a loop needs to know when to stop.

## Termination: knowing when to stop

A practical but crucial aspect of the loop is **termination** — how and when it *stops*, which is both important and a common source of problems:

- **The agent decides it's done.** Normally, the loop terminates when the *agent decides the goal is achieved* — it reasons that the task is complete and stops (often by producing a final answer rather than another action). The model's judgment that it's done is the natural stop condition. This is part of the "model directs the flow" — including deciding when to finish.
- **Safeguards are essential.** But relying only on the agent to stop is risky — agents can *loop indefinitely* (never deciding they're done, repeating actions, getting stuck). So practical agents add *safeguards*: a maximum number of iterations/steps, a cost/time budget, or other stop conditions that force termination. These prevent runaway loops (a real failure mode, and a real cost risk — many LLM calls). Never build an agent loop without a hard limit. Bounding the loop is basic agent hygiene.
- **Termination failures are common.** Agents *failing to terminate well* — looping, getting stuck repeating the same failing action, or stopping too early (giving up or declaring success prematurely) — is a frequent agent problem. Good agent design attends to termination: ensuring the agent recognizes completion, doesn't loop forever (safeguards), and doesn't quit prematurely. This connects to reliability (the final post). The loop's termination is where a lot of agent reliability lives.

The core agent loop — reason, act, observe, repeat — formalized as ReAct (interleaved reasoning and acting), is the fundamental mechanism of every agent: it enables multi-step tasks, grounds the agent in observed reality, and makes it adaptive, integrating all the other components, and it must terminate well (the agent deciding it's done, with safeguards against runaway loops). Understanding this loop is understanding agents. Next: tool use — how agents actually *act* on the world.

## Key takeaways

- Every agent operates on the same fundamental loop: REASON (the LLM decides the next action) → ACT (execute it, usually via a tool) → OBSERVE (see the result) → repeat, until the goal is achieved — this iteration is what turns a deciding LLM into a system that accomplishes multi-step goals, and every agent in every framework is built on it.
- ReAct (Reasoning + Acting) is the archetypal pattern formalizing the loop: the LLM *interleaves* explicit reasoning with acting, so reasoning guides which action to take and interprets results, while acting/observing grounds the reasoning in real information — a synergy where reasoning makes action smart and action makes reasoning effective (extending chain-of-thought with the ability to act).
- The loop is powerful because it enables multi-step tasks (vs a single call's one response), grounds the agent in observed reality (working with real tool results, not just the model's assumptions), makes it adaptive (deciding each step based on the actual situation — the "model directs the flow" property), and integrates all other components (tools, memory, planning, reflection plug into it).
- Termination normally happens when the agent reasons that the goal is achieved (and produces a final answer) — the model deciding it's done — but this needs safeguards.
- Never build an agent loop without a hard limit (max iterations, cost/time budget) — agents can loop indefinitely (a real failure mode and cost risk), and termination failures (looping, getting stuck repeating a failing action, or quitting prematurely) are a frequent agent problem where much reliability lives.

## Further reading

- [ReAct: Synergizing Reasoning and Acting in Language Models (Yao et al., 2022)](https://arxiv.org/abs/2210.03629)
- [Reasoning Models & Test-Time Compute — the reasoning that drives the loop](/blog/series/reasoning-models-test-time-compute/)
- [What an AI agent is (previous post)](/blog/posts/agent-01-what-an-ai-agent-is.html)
