# Automated Design of Agentic Systems

*The most striking frontier result is a meta-agent that writes agents — defining them as code, testing them, archiving the good ones, and inventing architectures that outperform the best humans hand-built.*

If the design axis is the frontier, automated design is its sharpest edge: a system that programs *new agents* rather than tuning an existing one. This second post in the Self-Evolving Agents: The Frontier series covers the two landmark approaches — a meta-agent that discovers agent designs in code, and a search that automates agentic *workflows* — and the key idea that unites them: express the agent as code, and the space of agents becomes searchable.

## Agents as code, design as search

The enabling insight is representational. If you express an agent — its control flow, its tool use, the arrangement of its steps — as **code**, then "designing an agent" becomes "writing a program," and "searching for a better agent" becomes "searching the space of programs." Code is expressive enough to capture any agentic pattern, precise enough to execute and evaluate, and open-ended enough that a search can invent building blocks no template anticipated. This is what turns agent design from a human craft into an automatable search.

## ADAS: a meta-agent that programs agents

[Automated Design of Agentic Systems (Hu et al., 2024)](https://arxiv.org/abs/2408.08435) makes this concrete. Its core move: a **meta-agent** programs new agents in code, stores the strong ones in an **archive**, and draws on that archive to invent progressively better agents over time. Each candidate agent is defined as executable code; the meta-agent proposes a new design, that design is run and scored on a task, and the result feeds back into the meta-agent's next proposal.

Two mechanisms make this work. The **archive** is a growing library of discovered designs — the search does not start from scratch each round; it builds on what already worked, combining and extending prior agents much as a researcher builds on prior papers. And because agents are code, the meta-agent can invent *novel building blocks* and combine existing ones in ways a fixed template could not express. The reported result is that this open-ended search progressively discovers agent designs that **outperform state-of-the-art hand-designed agents** across domains including coding, math, and science.

The significance is conceptual, and it is large: agent architecture — historically a human sitting down to wire components together — becomes something a search process does, and the search finds structures humans would not have thought to try. This is self-evolution on the structure axis taken to its logical conclusion: the system is not adjusting an agent, it is *authoring* agents.

## AFlow: searching the space of workflows

A closely related approach narrows the target from whole agents to agentic **workflows** — the orchestration of LLM calls and operations that solve a task. [AFlow (Zhang et al., 2024)](https://arxiv.org/abs/2410.10762) frames workflow construction as a search problem and automates it with **Monte Carlo Tree Search** over workflows represented as code. It iteratively refines candidate workflows through code modification, a tree-structured record of past attempts, and execution feedback, exploring the space efficiently rather than exhaustively.

AFlow matters because it shows the automated-design idea is not one monolithic technique but a *family*: pick a representation (whole agents, or workflows-as-code), pick a search algorithm (archive-guided proposal, or MCTS), and let it discover structures. The common thread with ADAS is unmistakable — code representation, execution-grounded evaluation, and a search that reuses prior discoveries. The differences are the knobs: what you search over and how you search it.

## Why this beats hand design (when it does)

It is worth being precise about *why* an automated search can beat expert humans, because it is not magic. Humans design agents from a small mental library of patterns (ReAct, plan-and-execute, supervisor-workers) and limited patience for trying combinations. A search, given a trustworthy evaluator and enough compute, tries vastly more combinations, discovers non-obvious ones, and — crucially — is guided at every step by measured performance rather than intuition. When the task is well-defined and cheaply evaluable, that combination of breadth plus measured feedback outperforms a human's narrow, intuition-guided exploration.

The qualifier is load-bearing: *given a trustworthy evaluator*. Automated design inherits the frontier's central dependency in full. The meta-agent optimizes for whatever the evaluation rewards, run thousands of times, so a weak or gameable metric produces agents that are elaborate machines for exploiting it. The search is only discovering "better" agents in the sense your evaluator defines better.

## The cost and when to reach for it

Automated design is the most expensive self-evolution technique by a wide margin: every candidate agent is generated (a model call), executed (often many calls), and scored, across many search iterations. It is justified when the payoff clears that cost — a high-value task run at scale where a better agent design pays back the search, a problem where human-designed agents have plateaued, or a setting where you genuinely do not know the best architecture. For most applications, the lighter axes from the foundations series deliver more per dollar; automated design is what you graduate to when those are exhausted and the task warrants an expensive, thorough search for a fundamentally better design.

## Key takeaways

- Expressing an agent (or workflow) as code turns "designing an agent" into "searching the space of programs" — the enabling insight of automated design.
- ADAS uses a meta-agent to program new agents in code, archive the strong ones, and build on them, discovering designs that outperform hand-built agents across coding, math, and science.
- AFlow applies the same family idea to agentic workflows, using Monte Carlo Tree Search over code with execution feedback — showing automated design is a family (choose representation + search algorithm), not one technique.
- Automated search beats expert humans when the task is well-defined and cheaply evaluable, because breadth plus measured feedback outdoes narrow intuition — but only relative to what the evaluator rewards.
- It is the most expensive self-evolution technique; reach for it when lighter axes are exhausted and a high-value task justifies searching for a fundamentally better design.

## Further reading

- [Automated Design of Agentic Systems — Hu et al., 2024](https://arxiv.org/abs/2408.08435)
- [AFlow: Automating Agentic Workflow Generation — Zhang et al., 2024](https://arxiv.org/abs/2410.10762)
- [Self-Evolving Agents (the foundations series)](/blog/series/self-evolving-agents/)
