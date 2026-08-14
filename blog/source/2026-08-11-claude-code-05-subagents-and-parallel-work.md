# Subagents and Parallel Work

*Subagents let Claude Code delegate a focused task to a separate agent with its own context — keeping the main conversation clean and letting independent work run in parallel.*

As tasks grow, two problems appear: the main conversation's context fills with the details of subtasks (searching files, running checks), and genuinely independent pieces of work queue up when they could run at once. Subagents address both. A subagent is a separate Claude Code agent, with its own context window and often a narrower toolset and purpose, that the main session delegates to and gets a result back from. This post is about using them well.

## Why subagents exist

Two distinct benefits, both real:

- **Context isolation.** A subagent does its work (say, "search the codebase and find everywhere we call the old auth API") in *its own* context and returns just the answer. The main conversation stays focused on the task instead of filling up with the noise of the search. This keeps the primary agent sharp on long tasks (post 2's context management).
- **Parallelism.** Independent subtasks can run concurrently. If you need three unrelated modules investigated, or several files transformed independently, subagents can work at the same time instead of one after another — real wall-clock savings on decomposable work.

**The gotcha:** the subagent's detailed work happens in *its* context, and only its final summary comes back — so if you need the full reasoning or intermediate output, ask for it in the result. Delegating something whose details you actually needed to see, then getting only a terse summary, means redoing it in the main session.

## Two ways subagents show up

- **Ad-hoc delegation.** Within a task, the main agent can spin up a subagent to handle a well-scoped piece — "go investigate X and report back" — especially for broad searches or research where you want the conclusion, not the file-by-file trawl.
- **Defined agent types.** You can configure named subagent types (in project config, like the rest of post 3's setup) with a specific purpose, instructions, and tool access — e.g. a "code-reviewer" agent or a "test-writer" agent. These become reusable, shareable roles the team can invoke, each starting fresh with its own tailored system prompt.

Defined agents are the durable version: a well-crafted reviewer or explorer agent, committed to the repo, gives everyone a consistent specialized helper.

## When to delegate to a subagent

Reach for a subagent when a piece of work is:

- **Well-scoped and independent** — it has a clear input and a clear deliverable, and doesn't need to interleave with the main thread.
- **Context-heavy but conclusion-light** — a big search or investigation where you want the finding, not the raw exploration cluttering the main context.
- **Parallelizable** — several such pieces that don't depend on each other.
- **Specialized** — a task a purpose-built agent (reviewer, tester) does better than the generalist main session.

And keep it in the main session when the work is tightly interleaved with what you're doing, needs the full shared context, or is small enough that delegation overhead isn't worth it.

**The gotcha:** subagents have real overhead — spinning one up and handing off context isn't free, and each runs with its own fresh context that lacks the main conversation's history. Delegating a trivial or tightly-coupled task can be *slower* and more error-prone than just doing it inline. Delegate the chunky, independent pieces, not every little step.

## Parallel work in practice

The pattern that pays off: decompose a big task into independent pieces, fan them out to subagents, then synthesize the results in the main session. "Review these four modules for security issues" can become four concurrent reviewers whose findings you then consolidate. The main agent acts as an orchestrator — splitting the work, launching the subagents, and integrating what comes back.

The judgment is in the decomposition: pieces must be genuinely independent (no shared state they'd race on) and worth the coordination cost. Forcing parallelism onto work that's actually sequential just adds overhead and confusion. When the shape fits, though, it's a large speedup and keeps each subagent's context tightly focused on its slice.

## Keep the orchestrator in control

Even with subagents doing the legwork, you and the main agent stay accountable for the result. Subagent outputs are inputs to be reviewed and integrated, not final answers to rubber-stamp — the same "review everything" discipline from the Code Review series applies. The orchestrator decides what to delegate, checks what comes back, resolves conflicts between subagents' results, and owns the final synthesis. Delegation multiplies your reach; it doesn't outsource your judgment.

## Key takeaways

- **Subagents delegate a focused task to a separate agent with its own context**, giving you context isolation and parallelism.
- Use them for **well-scoped, independent, context-heavy, or specialized** work; keep tightly-coupled or trivial work inline.
- They come as **ad-hoc delegation** and as **defined, reusable agent types** (e.g. reviewer/tester) configured and shared in the repo.
- **Only the subagent's summary returns** — ask for the detail you need; its full reasoning stays in its own context.
- **Parallelism requires genuine independence** — decompose, fan out, synthesize; don't force it onto sequential work.
- The main session stays the **orchestrator**: review and integrate subagent results, don't rubber-stamp them.

## Further reading

- [Claude Code — subagents](https://docs.claude.com/en/docs/claude-code/sub-agents) — configuring and using subagents and agent types.
- [Claude Code — best practices](https://www.anthropic.com/engineering/claude-code-best-practices) — delegation and managing multi-step work.
- [Claude Code — common workflows](https://docs.claude.com/en/docs/claude-code/common-workflows) — patterns for decomposing larger tasks.
