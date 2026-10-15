# Planning and Multi-Step Coding Tasks

*Fixing a typo is one tool call; implementing a feature across a dozen files, with new tests and a migration, is a project. As coding tasks grow, a coding agent needs more than a tight edit-run loop — it needs to plan, decompose, track progress, and manage its own context over a long effort. This post is about how coding agents handle big, multi-step tasks, and why planning and decomposition are what let them tackle real work rather than just small edits.*

Posts 2–4 built the loop, grounding, and tools — enough for small, well-scoped changes. This post is about *scale*: the larger tasks where a flat loop isn't enough and the agent must organize a long, multi-step effort. It connects to the blog's agent-planning and [context engineering](/blog/series/context-engineering/) coverage, applied to substantial coding work.

## Why big tasks need planning

The basic loop (post 2) handles a small change well: find the code, edit it, run the test, done in a few iterations. Large tasks break this, for reasons that drive the need for planning:

- **They're too big for one loop.** "Add authentication to this app" isn't one edit — it's many coordinated changes across many files (models, routes, middleware, tests, config), in a sensible order, with dependencies between them. A flat edit-run loop with no plan flails on this: the agent makes scattered changes, loses track, and produces an incoherent half-done result.
- **They exceed the context window over time.** A long task generates a lot of state — files read, changes made, tests run, decisions taken — far more than fits in context (the [Agent Skills](/blog/series/agent-skills/) constraint). Over a long effort the agent must *manage what it remembers*, or it forgets earlier decisions and context, producing inconsistency. Long tasks are as much a *context-management* problem as a coding one.
- **They need coherence and ordering.** Multi-step changes have a right order (you can't test the feature before building it) and must stay *coherent* (the parts fit together). Without planning, the agent risks doing steps out of order, contradicting earlier work, or missing pieces. Coherence over many steps requires deliberate organization.

So for anything beyond a small change, the agent needs to *plan*: understand the whole task, break it into ordered steps, and work through them while tracking progress — the difference between an agent that handles toy edits and one that does real engineering work.

## How agents plan and decompose

Coding agents handle large tasks through planning and decomposition techniques that mirror how a human engineer approaches a project:

- **Decompose into subtasks.** Break the large task into smaller, well-scoped pieces ("first the model, then the API, then the UI, then tests"), each a manageable unit the basic loop (post 2) can handle. Decomposition turns an intractable "build the feature" into a sequence of tractable steps — the core move, and the same decompose-and-conquer that works for humans and for the blog's [agent orchestration](/blog/series/the-ai-forward-deployed-engineer/).
- **Plan before acting.** Explicitly form a plan — the steps, their order, the approach — *before* diving into edits, so the work is coordinated rather than ad-hoc. For substantial tasks, a short planning phase (understand, then lay out the steps) dramatically improves coherence. This is "think before you act," and it's where many agent improvements come from (plan-then-execute beats react-only on complex tasks).
- **Track progress explicitly.** Maintain a record of what's done and what's left (a task list / todo state the agent updates as it goes), so over a long effort it stays oriented — knowing it finished the model and is now on the API, not re-doing or forgetting steps. Explicit progress tracking is how the agent keeps coherence across many iterations and survives its own context limits.
- **Manage context across the task.** Since the full task exceeds the context window, the agent must *curate* what it keeps in context — the plan, the current step, the relevant code — and offload or summarize the rest (the context-engineering discipline). Keeping the *right* working context over a long task (the plan and current focus, not every detail of every prior step) is what lets the agent sustain a long effort coherently.
- **Iterate within and across steps.** Each subtask runs the basic loop (edit-run-observe, post 2) to completion, and the agent moves to the next, re-planning if something changes (a step reveals the plan was wrong). Planning isn't one-shot — the agent adapts the plan as it learns, like real engineering.

The pattern is *hierarchical*: a high-level plan (the steps) with the basic execution loop (post 2) running *within* each step, and progress tracked across them. This hierarchy — plan the steps, execute each via the loop, track progress, re-plan as needed — is how a coding agent scales from small edits to substantial, multi-file, multi-step engineering work. It's decompose-plan-execute-track, the same structure that lets humans tackle projects bigger than they can hold in their head at once.

## What planning enables and where it strains

Planning is what elevates a coding agent from edits to engineering, and seeing its payoff and limits frames the practical reality:

- **It enables real tasks.** With planning and decomposition, agents handle substantial work — implement a feature, do a multi-file refactor, build something non-trivial — not just one-line fixes. This is the difference between a toy and a tool: planning is what makes coding agents useful for actual engineering tasks.
- **It improves coherence and reduces flailing.** Planned, tracked work stays coherent and on-track, versus the scattered, forgetful behavior of an unplanned agent on a big task. Much of the perceived "intelligence" of a good coding agent on complex tasks is really good planning and progress-tracking.
- **It strains on very large or ambiguous tasks.** Planning helps, but agents still struggle with *very* large tasks (where the plan itself is hard and errors compound over many steps), *ambiguous* tasks (where the right decomposition isn't clear), and tasks requiring deep architectural judgment (post 8's limits). The further a task is from "well-specified and decomposable," the more planning strains — so scoping tasks to what the agent can plan and verify is key.
- **It benefits hugely from human direction.** You help the agent's planning enormously by *scoping the task well*, *providing the plan or approach* for complex work, and *breaking a big task into agent-sized pieces yourself* — meeting the agent where its planning is reliable. The best results on large work often come from the human doing the high-level decomposition and the agent executing the well-scoped pieces (the director model, post 1).

The through-line: small coding changes need only the basic loop (post 2), but **real tasks need planning** — decompose into ordered subtasks, plan before acting, track progress explicitly, manage context over the long effort, and iterate within and across steps — a *hierarchical* structure (high-level plan + per-step execution loop + progress tracking) that scales the agent from edits to substantial multi-file engineering. Planning is what makes coding agents genuinely *useful* (real features and refactors, not just one-liners) and what keeps long work *coherent*, but it **strains on very large, ambiguous, or architecturally-deep tasks** where decomposition is hard and errors compound — so it benefits hugely from **human direction** (scope the task, provide the approach, break big work into agent-sized pieces; the director model). Planning is the bridge from toy to tool.

## Key takeaways

- The basic loop (post 2) handles **small changes**, but **large tasks break it**: too big for one loop (many coordinated changes in order), they **exceed the context window over time** (long tasks are a context-management problem — the agent forgets earlier decisions), and they need **coherence and ordering** (right sequence, parts that fit). Beyond a small change, the agent must **plan**.
- Agents plan via **decomposition** (break the task into well-scoped subtasks the basic loop can each handle — the core decompose-and-conquer move), **plan-before-acting** (form the steps/order/approach first — plan-then-execute beats react-only on complex tasks), **explicit progress tracking** (a todo/task state updated as it goes — stays oriented, survives context limits), **context management** (curate the plan + current step + relevant code, offload the rest — the context-engineering discipline), and **iteration with re-planning** (execute each step via the loop, adapt the plan as it learns).
- The structure is **hierarchical**: a high-level **plan** (steps) with the basic **execution loop** (post 2) running within each step, and **progress tracked** across them — decompose-plan-execute-track, how humans tackle projects bigger than they can hold at once.
- Planning **enables real engineering tasks** (features, multi-file refactors — the difference between a toy and a tool), **improves coherence** (much perceived "intelligence" on complex tasks is good planning + tracking), but **strains on very large, ambiguous, or architecturally-deep tasks** (the plan itself is hard, errors compound, decomposition unclear — post 8's limits).
- Planning **benefits hugely from human direction**: scope the task well, provide the approach/plan for complex work, and **break big tasks into agent-sized pieces yourself** — the best large-work results come from the human doing high-level decomposition and the agent executing well-scoped, verifiable pieces (the director model, post 1).

## Further reading

- [Automated planning and scheduling — decomposing and ordering multi-step work](https://en.wikipedia.org/wiki/Automated_planning_and_scheduling)
- [Decomposition (computer science) — breaking tasks into manageable parts](https://en.wikipedia.org/wiki/Decomposition_(computer_science))
