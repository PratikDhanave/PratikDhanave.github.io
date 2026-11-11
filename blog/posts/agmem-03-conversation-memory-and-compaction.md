<!-- Markdown version for AI agents and readers. Canonical: https://pratikdhanave.com/blog/posts/agmem-03-conversation-memory-and-compaction.html -->

# Conversation Memory and Compaction — Surviving the Long Session

*The first memory problem every agent hits is the humblest: the conversation itself outgrows the window. Tool outputs pile up, reasoning accumulates, and somewhere past the first hour the agent must start forgetting parts of its own session — the only question is whether it forgets with judgment or at random. Compaction is where memory engineering starts, and it's harder than it looks because the thing doing the summarizing is the thing that needs the summary.*

Posts [1](/blog/posts/agmem-01-why-agents-forget.html)–[2](/blog/posts/agmem-02-the-memory-hierarchy-of-an-agent.html) framed the problem and the type system. This post is about working memory under pressure: the strategies for keeping a live session coherent as it exceeds the window, from naive buffers to the compaction pipelines production harnesses run today.

## The naive ladder

Conversation-memory strategies form a ladder, and every team climbs it in the same order because each rung's failure teaches the next:

- **Full buffer** — keep everything until the window fills. Works until it doesn't; then the session simply dies. Fine for short tasks, disqualifying for agents.
- **Sliding window** — keep the most recent N turns, drop the oldest. Cheap and predictable, but it forgets *by age, not by importance*: the user's core constraint stated in minute one falls off the cliff while yesterday's pleasantries survive. Recency is a terrible proxy for relevance.
- **Selective eviction** — drop the bulkiest, least-referenced items first: old tool outputs are the classic target, since a 4,000-token file listing that was read once is pure dead weight. A large improvement per token freed, and the first rung that requires *judgment* about content rather than position.
- **Summarization / compaction** — replace a span of the transcript with a model-written summary of it, freeing tokens while retaining (some of) the information. This is the load-bearing rung, and the rest of this post lives here.

## Compaction is lossy — engineer what survives

A summary keeps the gist and discards detail, and for conversation that trade is treacherous, because agent sessions are full of load-bearing detail: exact file paths, error messages, IDs, the precise wording of a constraint, which of three similar options was chosen. A generic "summarize this conversation" prompt reliably destroys exactly these. Production compaction therefore engineers *what must survive*:

- **A preservation contract.** The compaction prompt names categories that must be carried verbatim: open tasks and their state, decisions made and their reasons, hard constraints, file/resource identifiers, unresolved errors, user corrections. Everything else is fair game to compress.
- **Structure over prose.** Summaries that feed a machine should look structured — current goal, done, in progress, blocked, key facts, next steps — because downstream the model will *act* on this, not read it for pleasure.
- **Protected spans.** Some content is never compacted: the system prompt, standing instructions, the most recent turns (working context), and anything flagged as pinned. Compaction targets the middle of the transcript — old enough to compress, recent enough to still be in the window.
- **Recursion handling.** Long sessions compact multiple times, and summaries-of-summaries degrade like photocopies-of-photocopies. Mitigations: keep one rolling summary that is *revised* rather than re-summarized, and spill what falls out of it to episodic storage rather than oblivion.

That last point is the architectural one: **compaction should demote, not delete**. What leaves the window belongs in the episodic store (post 4 makes it retrievable), so "forgotten" means "no longer resident," not "gone." The window becomes a cache over durable memory — and eviction stops being scary.

## When to compact

Timing is a real design axis. **Threshold-triggered** compaction (at ~70–80% window occupancy) is the default — but compacting mid-task can drop the thread exactly when the context mattered most. **Boundary-triggered** compaction — at task completion, topic shift, or a natural pause — produces far better summaries because the just-finished unit has a clean shape ("we did X, result Y") that an arbitrary token cutoff never has. Production harnesses combine them: prefer boundaries, force at threshold. A refinement worth stealing: **compact the completed, keep the live** — when a sub-task finishes, immediately collapse its tool outputs and intermediate reasoning to a result line, so the window at any moment holds full detail for live work and summaries for finished work.

## The quiet failure modes

Compaction bugs are insidious because the agent continues fluently — just subtly wrong. The characteristic ones: **silent goal drift** (the summary rephrased the objective and nobody noticed — manifest as the agent happily solving a slightly different problem); **laundered uncertainty** (hedges and open questions in the transcript become confident statements in the summary); **lost negations** ("do NOT touch prod" compressing to a mention of prod); and **identity confusion** (who said what blurring, so a user's hypothetical becomes an instruction). Two disciplines help: keep compaction prompts under version control and *evaluate* them like any model output (post 8's methods — feed sessions, compact, check the contract held); and log what was compacted away, so when the agent acts oddly an hour later, the diff between transcript and summary is inspectable. If you can't see what memory dropped, every downstream bug becomes unexplainable.

The takeaway: conversation memory climbs a ladder — buffer, sliding window, selective eviction, **compaction** — and the top rung is lossy by design, so engineer what survives: a preservation contract (tasks, decisions, constraints, identifiers, corrections carried verbatim), structured summaries, protected spans, and revision instead of re-summarization. Prefer task-boundary compaction with a threshold backstop, and above all **demote rather than delete** — what leaves the window lands in episodic memory, turning the context into a cache over durable storage rather than the only copy of the session.

## Key takeaways

- The strategy ladder: full buffer → sliding window (forgets by age, not importance) → selective eviction (bulky, unreferenced tool outputs first) → **compaction**, the load-bearing rung.
- Compaction needs a **preservation contract** — open tasks, decisions + reasons, constraints, exact identifiers, unresolved errors, user corrections survive verbatim; structure over prose; protected spans (system prompt, recent turns, pinned items).
- **Revise one rolling summary** instead of re-summarizing summaries; **demote, don't delete** — evicted content goes to the episodic store, making the window a cache, not the only copy.
- Timing: boundary-triggered beats threshold-triggered (finished units summarize cleanly); combine them, and collapse each completed sub-task's detail to a result line immediately.
- The quiet failures — goal drift, laundered uncertainty, lost negations, who-said-what confusion — demand versioned, *evaluated* compaction prompts and a log of what was dropped.

## Further reading

- [Short-term memory — the bounded, displaceable store this post engineers around](https://en.wikipedia.org/wiki/Short-term_memory)
- [Automatic summarization — the lossy compression at the heart of compaction](https://en.wikipedia.org/wiki/Automatic_summarization)

---

Author: Pratik Dhanave (https://pratikdhanave.com) | Published: 2026-11-06
Canonical: https://pratikdhanave.com/blog/posts/agmem-03-conversation-memory-and-compaction.html
Attribution: please link the canonical URL when citing or quoting this post.
