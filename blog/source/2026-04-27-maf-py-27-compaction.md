# Compaction

*Keeping a growing transcript under a token budget with layered compaction strategies.*

---

## What it demonstrates

Every model call resends the whole transcript, so a long chat eventually blows the context window, costs more, and slows down. Compaction shrinks older history while keeping what matters. You attach a `CompactionProvider` next to a history provider; its `before_strategy` runs before each model call and rewrites the in-memory message list using one or more `CompactionStrategy` objects — truncate, sliding window, collapse tool results, LLM summarize, or a token-budget pipeline of all of them.

## One real excerpt

```python
pipeline = TokenBudgetComposedStrategy(
    token_budget=2_000,
    tokenizer=tokenizer,
    strategies=[
        ToolResultCompactionStrategy(keep_last_tool_call_groups=1),
        SummarizationStrategy(client=summarizer_client, target_count=4, threshold=2),
        SlidingWindowStrategy(keep_last_groups=8),
    ],
)
history = InMemoryHistoryProvider()
compaction = CompactionProvider(before_strategy=pipeline, history_source_id=history.source_id)
```

The composed strategy runs children gentlest-first and stops as soon as the budget is met.

## The gotcha

Compaction ONLY affects agents that keep history in memory — pair `CompactionProvider` with an `InMemoryHistoryProvider` and wire `history_source_id=history.source_id`. Order matters in `context_providers=[history, compaction]`: the history provider stores the transcript, then compaction trims it before each model call. `SummarizationStrategy` fires only when the non-system message count exceeds `target_count + threshold`, and it needs its OWN chat client (a smaller/cheaper model is recommended). `CharacterEstimatorTokenizer` is just a ~4-chars/token heuristic. These types are experimental.

## Azure / MAF mapping

Using `FoundryChatClient` as a plain chat client with an in-memory history provider keeps history client-side, so compaction applies. A server-managed Foundry Agent with persistent service-side history would ignore compaction entirely.

## Run it

`uv run tutorial/02-agents/conversations/03_compaction.py` — needs Foundry creds. Worked if five shopping turns run and later turns use a compacted history.

---

Next: [Chat Middleware](/blog/posts/maf-py-28-chat-middleware.html)
