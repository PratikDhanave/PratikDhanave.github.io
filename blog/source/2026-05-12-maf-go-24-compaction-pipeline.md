# step18 · Compaction Pipeline

*How to keep a long-running conversation inside the context window by chaining compaction strategies from gentle to aggressive.*

---

## What this lesson demonstrates

As a chat grows, its history eventually overflows the model's context window. A **compaction context provider** rewrites the message history *before each run* so it stays bounded. The rewrite is driven by a **pipeline** of strategies, ordered gentle to aggressive — each runs against the same message index, and each only fires when its **Trigger** says the history is too big.

The four stages, least aggressive first:

| # | Strategy | Fires when | What it does |
|---|----------|-----------|--------------|
| 1 | `ToolResultStrategy` | `MessagesExceed(7)` | collapse old tool-call groups into a short `[Tool Calls]` summary |
| 2 | `SummarizationStrategy` | `TokensExceed(0x500)` | ask a cheaper summarizer agent to fold older spans into one `[Summary]` |
| 3 | `SlidingWindowStrategy` | `TurnsExceed(4)` | keep only the most recent user turns |
| 4 | `TruncationStrategy` | `TokensExceed(0x8000)` | emergency: drop oldest groups under budget |

## The core: a pipeline is an ordered list of strategies

```go
func buildPipeline(summarizer compaction.Summarizer) *compaction.PipelineStrategy {
    return &compaction.PipelineStrategy{
        Strategies: []compaction.Strategy{
            &compaction.ToolResultStrategy{Trigger: compaction.MessagesExceed(7), MinimumPreservedGroups: 4},
            &compaction.SummarizationStrategy{Trigger: compaction.TokensExceed(0x500), Summarizer: summarizer, MinimumPreservedGroups: 4},
            &compaction.SlidingWindowStrategy{Trigger: compaction.TurnsExceed(4), MinimumPreservedTurns: 4},
            &compaction.TruncationStrategy{Trigger: compaction.TokensExceed(0x8000), MinimumPreservedGroups: 8},
        },
    }
}
```

Each `Strategy.Compact` runs in turn against the *same* index, so later stages see the effect of earlier ones.

## What to notice

- **Triggers decide *whether*, floors decide *how much*.** A strategy fires only when its `Trigger` (`MessagesExceed`, `TokensExceed`, `TurnsExceed`) hits, and its `MinimumPreserved…` field guarantees recent context survives.
- **Summarization uses a second agent.** `SummarizationStrategy.Summarizer` is a `compaction.Summarizer`. `summarizerFromAgent(...)` adapts a plain agent — which could point at a smaller, cheaper model — into one via `compaction.SummarizerFunc`.
- **The pipeline is a pure function.** `buildPipeline` takes no credentials and touches no network, so the offline test runs the identical pipeline over a synthetic long conversation with `compaction.Compact(...)` using a stub summarizer, and asserts the history shrinks while the system message survives.
- **The provider does the plumbing.** `compaction.NewContextProvider(...)` groups messages into a `MessageIndex`, applies the pipeline before each run, and stores group state across turns.

## How it maps to the SDK

Compaction is built on the same `ContextProviders` slot as the previous lesson's todo/calendar providers — it's just a provider that rewrites rather than appends. That means it composes cleanly with a Foundry-backed agent: attach the provider, and every run to Azure AI Foundry gets a bounded history without you touching the call site.

## Run it

```bash
go run ./tutorial/02-agents/agents/step18_compaction_pipeline
```

The offline test runs anywhere (the pipeline is pure); the seven-turn live demo needs `az login` + `FOUNDRY_PROJECT_ENDPOINT` and is gated behind `AF_LIVE=1`.

---

Next: [21 · Shell with Environment](/blog/posts/maf-go-25-shell-with-environment.html)
