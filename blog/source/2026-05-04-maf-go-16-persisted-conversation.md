# step06 · Persisted Conversation

*How to serialize an agent.Session to storage and resume the same conversation later, even from a new process.*

---

## What this lesson demonstrates

The same Joker agent as `step01`, but now the conversation **survives being written to disk and read back**. An `agent.Session` holds the conversation state — history, the provider's service ID, any per-conversation memory — and it implements `MarshalJSON`/`UnmarshalJSON`. So you can persist those bytes anywhere (a file here; a DB row, cache, or session store in production) and later rehydrate a *fresh* `Session` that continues the exact same chat.

The demo runs turn one, saves the session, loads it back into a brand-new value, and runs turn two — which still retells the same joke, proving the memory came entirely from the persisted bytes.

## The core code

Persistence is plain `encoding/json` — no special serializer:

```go
func saveSession(path string, session *agent.Session) error {
	data, err := json.Marshal(session)
	if err != nil {
		return err
	}
	return os.WriteFile(path, data, 0o644)
}

func loadSession(path string) (*agent.Session, error) {
	data, err := os.ReadFile(path)
	if err != nil {
		return nil, err
	}
	var resumed agent.Session
	if err := json.Unmarshal(data, &resumed); err != nil {
		return nil, err
	}
	return &resumed, nil
}
```

## What to notice

- **A `Session` is the unit of conversation state.** You attach it with `agent.WithSession(session)`; different conversations are just different `Session` values.
- **Resume from a fresh value.** `loadSession` deserializes into a *brand-new* `agent.Session` — exactly what a restarted server or a separate HTTP request would start with — then hands it to `RunText`. The conversation continues seamlessly.
- **`CreateSession` vs. the zero value.** The zero `Session` is usable, but `CreateSession(ctx)` lets the provider seed provider-specific state (and the service ID) before the first run — the safe way to start. The gotcha the test pins: the resumed session must preserve that **service ID** and the stored values, or the provider can't continue the same conversation.

## How it maps to Azure AI Foundry

Because `Session` captures the Foundry service ID alongside the message history, marshalling it and reloading it in another process lets Foundry pick up the conversation where it left off. The offline `TestSessionRoundTrip` is the heart of the lesson — it saves a session carrying a service ID and state, loads it back, and asserts both survive, all with no model call. This is the building block for stateless web services that resume chats from a session store.

## Run it

```bash
go run ./tutorial/02-agents/agents/step06_persisted_conversation
```

The program needs Foundry (`az login` + endpoint); the session round-trip is tested offline, and the live model round-trip is gated behind `AF_LIVE=1`.

---

Next: [step07 · Third-Party Session Storage](/blog/posts/maf-go-17-3rdparty-session-storage.html)
