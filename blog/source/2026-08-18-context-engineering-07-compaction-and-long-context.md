# Compaction, Summarization, and Long Context

*When context threatens to overflow, you compress it; and when you have a huge window to spend, you still should not fill it — because a long context is not used as well as a short, focused one.*

Two forces meet in this post. On one side, agents accumulate context until it overflows, and the answer is compaction — compressing what has piled up. On the other, models now offer very large context windows, tempting you to just fit everything in. The theme of the series resolves the tension: a long context is not used uniformly well, so even with room to spare, a compressed, focused context usually wins. This seventh post covers compaction and summarization, and how to think about long-context models.

## Why compaction is necessary

Any long-running agent trends toward overflow. History grows, tool results accumulate, retrieved material adds up. Left alone, the context eventually hits the window limit — at which point something gets truncated, often silently and often the wrong thing. Compaction is the deliberate alternative: rather than letting the context grow until it breaks, you periodically compress it, replacing verbose material with a denser representation that preserves what matters. It is the maintenance that keeps a long session from degrading into a bloated, unfocused window.

## Summarization: the primary tool

The workhorse of compaction is summarization — using the model itself to condense a stretch of context into a shorter form. The common pattern for conversations: keep the most recent turns verbatim, and replace the older history with a running summary that captures decisions made, facts established, and threads still open, while discarding the verbatim back-and-forth. As the conversation continues, the summary is updated and the recency window slides forward. The agent always sees "a summary of everything earlier + the recent turns in full," which stays roughly bounded no matter how long the session runs.

Summarization is lossy, and the skill is controlling *what* it loses. A good compaction summary preserves the load-bearing content — the goal, the constraints, the key results, the current state — and sheds the disposable — pleasantries, superseded intermediate steps, raw tool dumps. The risk is summarizing away something that turns out to matter later, which is why critical facts are often *pinned* (kept explicitly, outside the summary) rather than trusted to survive compression. Summarize aggressively, but protect the few things that must not be lost.

## Other compaction techniques

Summarization is not the only lever:

- **Distilling tool output.** Replace a raw tool result with just the information the agent extracted from it once it has been used — the answer, not the whole payload.
- **Deduplication.** Remove repeated or near-identical content; long contexts accumulate redundancy that costs budget for nothing.
- **Pruning stale context.** Drop material that is no longer relevant to the current task — an earlier subtopic that is finished, retrieved documents that have served their purpose.
- **Externalizing.** Move detail out of the window into external storage (files, a scratchpad, memory) and keep only a reference or summary in context, retrieving the full detail only if needed again.

Each trades a little completeness for a lot of focus and budget — usually a good trade.

## Long-context models do not repeal the rules

Large context windows are genuinely useful — they raise the ceiling and reduce how often you must compact. But they do not change the core fact this series keeps returning to: models use long contexts unevenly. As "Lost in the Middle" (Liu et al., 2023) showed, information at the start and end of a long input is used well while information buried in the middle is often effectively ignored, and a large body of experience since is consistent with the practical lesson — quality does not scale up with the number of tokens the way capacity suggests. Practitioners describe the related tendency for a model's effectiveness to degrade as its context fills with more, and more marginal, material. A window you *can* fill to a million tokens is not a window you *should* fill.

The implication is that long-context capability is best spent buying you *headroom and simplicity*, not an excuse to stop curating. Use the larger window to compact less frequently, to tolerate a bit more retrieved context, to avoid brittle truncation — but keep placing the important content at the edges, keep the context dense with signal, and keep compacting when it grows. A focused 8,000-token context will routinely beat a lazy 800,000-token one on cost, latency, *and* accuracy.

## When to compact

Compaction has a cost — it takes a model call and it is lossy — so you do not do it every turn. Trigger it on thresholds: when the context approaches a target fraction of the window, when history exceeds a certain length, or at natural boundaries (a subtask completes, a topic changes). The goal is to compress *before* overflow forces a crude truncation, while not compressing so eagerly that you pay the cost and lose fidelity for no benefit. Like the rest of context engineering, it is a budget decision — spend a compaction call when the budget pressure justifies it.

## Key takeaways

- Long-running agents trend toward context overflow; compaction is the deliberate compression that prevents silent, crude truncation.
- Summarization is the primary tool: keep recent turns verbatim, replace older history with an updated running summary of decisions, facts, and open threads, and slide the recency window.
- Compaction is lossy — preserve the load-bearing content, shed the disposable, and pin the few critical facts that must not be summarized away.
- Other levers include distilling tool output, deduplication, pruning stale context, and externalizing detail to storage with only a reference in the window.
- Large context windows raise the ceiling but do not repeal "lost in the middle" — spend the extra capacity on headroom and simplicity, keep curating, and a focused small context beats a lazy huge one; compact on thresholds, not every turn.

## Further reading

- [Lost in the Middle: How Language Models Use Long Contexts — Liu et al., 2023](https://arxiv.org/abs/2307.03172)
- [Anthropic documentation](https://docs.anthropic.com)
- [OpenAI Cookbook](https://github.com/openai/openai-cookbook)
