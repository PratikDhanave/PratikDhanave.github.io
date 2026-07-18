# step05 · Structured Output

*How to make the agent return a typed Go struct instead of free-form prose, via a JSON schema derived from your type.*

---

## What this lesson demonstrates

Everything so far returned text. Real applications want *data*: a `PersonInfo`, not a paragraph about a person. This lesson asks the model to fill in a Go struct and shows the **two ways** the SDK exposes structured output:

1. **`agent.WithStructuredOutput(&v)`** — a *per-run* option. Hand it a pointer; when the run finishes the SDK has decoded the model's JSON into your value.
2. **`agent.WithResponseFormat(jsonformat.MustFor[T]())`** — wired once into `Config.RunOptions`, so *every* run is constrained to `T`'s JSON schema. The model streams raw JSON you unmarshal yourself.

## The core code

The struct *is* the schema — `json` tags become the field names the model must return. A generic helper decodes it per run:

```go
func runFor[T any](ctx context.Context, a *agent.Agent, message string, opts ...agent.Option) (T, error) {
	var v T
	opts = append(opts, agent.WithStructuredOutput(&v), agent.Stream(false))
	for _, err := range a.RunText(ctx, message, opts...) {
		if err != nil {
			return v, err
		}
	}
	return v, nil // decoded value is ready once the run is drained
}
```

## What to notice

- **Two altitudes for the same idea.** `WithStructuredOutput(&v)` is convenient at a single call site and decodes *for* you. `WithResponseFormat(...)` in `Config.RunOptions` bakes the constraint into the agent so every run returns JSON — but then *you* own the decoding, which is why `main` collects the streamed bytes and calls `json.Unmarshal`.
- **`RunOptions` are prepended to every run.** Anything you put there applies without repeating it at the call site — that is how the second agent gets its response format for free while still passing `Stream(true)` per call. The gotcha: you must still drain (range) the run before reading the decoded value.
- **Generics keep it reusable.** `runFor[T]` works for any output type — swap `PersonInfo` for a slice-bearing struct and nothing about the helper changes.

## How it maps to Azure AI Foundry

`jsonformat.MustFor[PersonInfo]()` reflects over the struct's `json` tags to build a JSON schema, which the SDK sends to Foundry as a `response_format = json_schema` constraint on the `/responses` call. The model is *told* to return exactly that shape — no prompt-engineering the format. The offline test `TestPersonInfoSchema` exercises `jsonformat.MustFor[PersonInfo]()` directly (asserting `Kind == "json"`, `Name == "PersonInfo"`, and a derived schema) — the exact call the response-format agent uses at runtime.

## Run it

```bash
go run ./tutorial/02-agents/agents/step05_structured_output
```

The same person prints twice — once decoded via `WithStructuredOutput`, once from streamed JSON you unmarshal. The program needs Foundry; the schema and decoding helpers are tested offline, and the live call is gated behind `AF_LIVE=1`.

---

Next: [step06 · Persisted Conversation](/blog/posts/maf-go-16-persisted-conversation.html)
