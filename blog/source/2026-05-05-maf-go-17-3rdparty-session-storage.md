# step07 · Third-Party Session Storage

*How to teach an agent to load and persist conversation memory in your own store via a custom history provider.*

---

## What this lesson demonstrates

By default the agent keeps no memory between runs. A **history provider** is the extension point that changes that: the framework calls it *before* each run to load prior messages, and *after* each run to persist the new ones. This lesson backs one with the filesystem — one JSON file per message — so a conversation survives a process restart.

The neat trick: the `Session` itself stays tiny. It holds only the **list of message IDs**; the third-party store owns the message bodies. So the session serializes to a compact blob you can save now and reload later — even in a different process — no matter how long the conversation grows.

## The core code

A history provider is two hooks plus `DisableStoreOutput` so the local store is the single source of truth:

```go
func newFSHistoryProvider(dir string) agent.HistoryProvider {
	store := &fsMessageStore{Dir: dir}
	return agent.NewHistoryProvider(agent.HistoryProviderConfig{
		SourceID: "fsMessageStore",
		Provide:  store.provideMessages, // load prior messages, chronological
		Store:    store.persistMessages, // persist new messages after a run
	})
}
```

## What to notice

- **A history provider is two hooks.** `Provide` loads, `Store` persists. Everything else — the `fsMessageStore` — is ordinary Go: read/write files keyed by message ID.
- **`SourceID` prevents double-persisting.** Messages this provider loads are source-stamped with `SourceID: "fsMessageStore"`; the framework's default store filter skips them, so a reloaded message isn't written back on the next run. Omitting this is the classic bug — reloaded history gets re-persisted and duplicates.
- **`DisableStoreOutput: true` is the crucial companion.** It tells Foundry *not* to keep server-side conversation state, making the local provider the single source of truth. Omit it and the two histories conflict.
- **The session stays small on purpose.** `Store` records only IDs in `session.Set("fsMessageStore.files", ids)`; the bodies live on disk, so `json.Marshal(session)` produces a compact blob you can persist and later `Unmarshal`.

## How it maps to Azure AI Foundry

Foundry can hold conversation state server-side, but many production systems need history in *their own* store — a database, an object store, an audit-compliant log. The `HistoryProvider` interface is how the Microsoft Agent Framework lets you own that: swap `newFSHistoryProvider` for a SQLite- or Redis-backed provider and the agent code doesn't change. The offline `TestFSMessageStore_RoundTrip` drives `Store` then `Provide` against a temp directory — serializing and deserializing the session in between — and asserts the messages come back from disk, in order, with no model.

## Run it

```bash
go run ./tutorial/02-agents/agents/step07_3rdparty_session_storage
```

The program needs Foundry; the persist/reload path is tested offline, and the live end-to-end call is gated behind `AF_LIVE=1`.

---

Next: [step08 · Observability (OpenTelemetry)](/blog/posts/maf-go-18-observability.html)
