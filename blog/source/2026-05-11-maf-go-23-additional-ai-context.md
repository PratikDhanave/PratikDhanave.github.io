# 17 · Additional AI Context

*How a ContextProvider injects extra messages and tools into every run — a live todo list and calendar — with state that survives serialize and resume.*

---

## What this lesson demonstrates

A `ContextProvider` runs on **every** agent invocation and can add two things to the request before it reaches the model: **messages** (extra context) and **options** (extra tools). It's the standard hook for injecting RAG results, memories, a live todo list, or calendar events — without hard-coding them into the instructions.

This lesson builds a `PersonalAssistant` with two providers. A **todo-list** provider injects the current list *and* contributes `AddTodoItem` / `RemoveTodoItem` tools whose handlers mutate state stored in the **Session**. A **calendar** provider injects the next few events (read-only, no tools). Because provider state lives in the Session, the whole conversation — chat history plus the todo list — serializes to JSON and resumes later.

## The core: a provider can add context and tools at once

```go
func provideTodoListContext(_ context.Context, invoking agent.InvokingContext) ([]*message.Message, []agent.Option, error) {
    session, _ := agent.GetOption(invoking.Options, agent.WithSession)
    state := getTodoListState(session)
    // ... render state.Items into a text message ...
    return []*message.Message{message.NewText(output.String())},
        []agent.Option{agent.WithTool(addTodoItemTool), agent.WithTool(removeTodoItemTool)},
        nil
}
```

The `Provide` hook returns both a message *and* `[]agent.Option`. The tool handlers close over this run's `session` — pulled out with `agent.GetOption(opts, agent.WithSession)` — and mutate `todoListState` stored under a stable `todoListSourceID`.

## What to notice

- **Providers fire in order.** `ContextProviders: []agent.ContextProvider{todo, calendar}` run in sequence; each `Provide` receives what the previous one accumulated and appends its own.
- **State lives in the Session, keyed by SourceID.** `session.Get` / `session.Set` under a stable `SourceID` is what makes the todo list survive `json.Marshal` → `Unmarshal`. The demo serializes the session, round-trips it, and continues.
- **History stays clean.** The custom history provider uses `messagefilter.NotSourceTypes(SourceTypeHistoryProvider, SourceTypeContextProvider)` so the injected todo/calendar context is *not* persisted as conversation history — only genuine user/assistant turns are.
- **Inject the data source.** `newPersonalAssistant` takes `loadEvents` as a parameter, so the test feeds a deterministic fake calendar instead of the real one.

## How it maps to the SDK

`agent.NewContextProvider` and the `ContextProviders` slot are the SDK's general extension point for enriching a run; combined with `DisableStoreOutput: true`, history stays client-side so the `Session` fully owns it. This same provider mechanism is what later lessons specialize for compaction and for Foundry-backed memory.

## Run it

```bash
go run ./tutorial/02-agents/agents/step17_additional_ai_context
```

The offline tests (wiring, todo state round-trip, calendar injection) run anywhere; the live turn needs `az login` + `FOUNDRY_PROJECT_ENDPOINT` and is gated behind `AF_LIVE=1`.

---

Next: [step18 · Compaction Pipeline](/blog/posts/maf-go-24-compaction-pipeline.html)
