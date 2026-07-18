# step06 · Persisted Conversations

*How to serialize an agent.Session to disk and resume it later, so a follow-up prompt still remembers earlier turns across a process restart.*

---

## What this lesson demonstrates

An `agent.Session` is the memory of one conversation — and because it serializes with `encoding/json`, you can persist it between runs or process restarts and hand it back to the agent later. This lesson does exactly that: ask a joke with a session, marshal the session to a file, read it back, and ask a follow-up that only makes sense if the history survived the round-trip through disk.

## Save and load are just JSON

The persistence is deliberately unremarkable — that's the point:

```go
func saveSession(session *agent.Session, path string) error {
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
	var session agent.Session
	if err := json.Unmarshal(data, &session); err != nil {
		return nil, err
	}
	return &session, nil
}
```

`main` runs turn 1 on a fresh session, writes it to a temp file, reads it straight back into a `resumed` session, and continues the conversation on `resumed` with `agent.WithSession(resumed)`. The follow-up ("tell the same joke in the voice of a pirate") only works because the history rode along through JSON.

## What to notice

The whole persistence story is **`json.Marshal(session)`** — no custom serializer, no provider-specific export. `agent.Session` is a plain serializable value, so "save to a database between requests" is the same code as "write to a file," just with the destination swapped. The temp-file round-trip in `main` is a stand-in for that database.

The gotcha to internalize: this Foundry session is **client-side** (contrast with the server-conversation lesson). Persisting it means persisting the *transcript itself*, so on resume the history is replayed into the model — that's why the "same joke" reference resolves. A server-conversation session would instead persist just the conversation ID and rely on the service to still hold the history.

Because it's pure JSON, the offline test round-trips a `Session` through disk and back with no model at all, proving the persistence half of the lesson end to end alongside the usual fake-credential wiring assertion.

## How it maps to the Agent Framework

Serializable sessions are how the Go SDK supports **stateless services**: a request handler loads the session for a user, runs a turn, saves it, and returns — nothing lives in process memory between requests. The `json`-marshalable `Session` is the contract that makes that pattern work uniformly, and it's the same abstraction workflows later checkpoint and rehydrate.

## Run it

```bash
go run ./tutorial/02-agents/providers/foundry/step06_persisted_conversations
```

The disk round-trip test runs offline; the two live turns are gated behind `AF_LIVE=1` with `az login` and `FOUNDRY_PROJECT_ENDPOINT`.

---

Next: [step07 · Observability](/blog/posts/maf-go-46-observability.html)
