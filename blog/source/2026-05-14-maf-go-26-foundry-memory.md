# step22 · Foundry Memory

*How a memory ContextProvider backed by an Azure AI Foundry store lets an agent recall you in a brand-new session.*

---

## What this lesson demonstrates

A plain agent forgets everything the moment a session ends. This lesson attaches a **memory context provider** to the agent. It runs *around* every turn: before a run it searches a Foundry memory store for relevant memories and injects them as context; after a run it submits the conversation so the store can extract new memories.

The payoff is that memories live in the **store** — partitioned by a `scope` key — not in the session. So the demo teaches a travel assistant a few facts about "Taylor" in one session, then opens a *fresh* session and asks it to summarize what it knows — and it still recalls Taylor, pulled from the store rather than any in-memory history.

## The core: memory is a ContextProvider

```go
func newMemoryProvider(endpoint, storeName string, cred azcore.TokenCredential) *foundryprovider.MemoryProvider {
    return foundryprovider.NewMemoryProvider(
        endpoint, cred, storeName,
        // scope callback: invoked once per run; returns the memory partition key.
        func(*agent.Session) string { return memoryScope },
        foundryprovider.MemoryProviderConfig{
            Logger:      slog.New(slog.NewTextHandler(os.Stderr, nil)),
            UpdateDelay: 0, // submit extraction immediately after each run
        },
    )
}
```

The provider is attached with `agent.Config{ContextProviders: []agent.ContextProvider{memory}}` — the same slot any context provider uses.

## What to notice

- **The `scope` callback is the partition key.** Invoked once per run, it returns the bucket to read and write. Here it's a constant, so *every* session shares one bucket — which is precisely what lets session 2 recall session 1. Real apps return a stable per-user or per-tenant key.
- **`UpdateDelay: 0`** submits memory extraction immediately after each run, so later turns in the same demo can already see what earlier turns taught the agent.
- **Memory is not session state.** Because it's a `ContextProvider` reading and writing an external store, it survives across sessions that share no history — unlike the todo list from the additional-AI-context lesson, which lived in the session.
- **The gotcha:** the store must already exist. This lesson expects `AZURE_AI_MEMORY_STORE_ID` to name a Foundry memory store (with a chat model for extraction and a text-embedding model for search); provisioning it uses an SDK-internal client, so create it via the portal or a throwaway program outside the tutorial module.

## How it maps to the SDK

`foundryprovider.NewMemoryProvider` returns a `*MemoryProvider` that satisfies `agent.ContextProvider`, wiring the retrieve-before / store-after loop directly onto an Azure AI Foundry memory store. It's the productionized version of the manual "memories provider" you could hand-roll — persistence and extraction handled by Foundry.

## Run it

```bash
# Needs az login, FOUNDRY_PROJECT_ENDPOINT, FOUNDRY_MODEL, and an existing store named by AZURE_AI_MEMORY_STORE_ID.
go run ./tutorial/02-agents/agents/step22_foundry_memory
```

The offline structural test builds the provider and agent with a fake credential (constructing the client sends no request) and runs anywhere; the live path is gated behind `AF_LIVE=1`.

---

Next: [Getting Started](/blog/posts/maf-go-27-getting-started.html)
