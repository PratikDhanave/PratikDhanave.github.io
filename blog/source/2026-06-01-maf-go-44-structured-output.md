# step05 · Structured Output

*How to make the model return a typed Go struct instead of prose — hand RunText a pointer, get back populated fields.*

---

## What this lesson demonstrates

Instead of collecting the model's answer as free text and parsing it yourself, this lesson asks for **typed data**. You pass `RunText` a pointer to a Go struct via `agent.WithStructuredOutput(&v)`. The framework asks the model to emit JSON matching that shape, then unmarshals the reply straight into your struct — so you get a `PersonInfo{Name, Age, Occupation}` back, not a paragraph.

## The target struct and the run

The struct's `json` tags do double duty: they're the schema the framework hands the model, and they drive unmarshaling the reply:

```go
type PersonInfo struct {
	Name       string `json:"name"`
	Age        int    `json:"age"`
	Occupation string `json:"occupation"`
}

var person PersonInfo
_, err = a.RunText(
	context.Background(),
	"Please provide information about John Smith, who is a 35-year-old software engineer.",
	agent.WithStructuredOutput(&person),
	agent.Stream(false),
).Collect()
```

After `Collect` returns, `person.Name`, `person.Age`, and `person.Occupation` are populated. No `json.Unmarshal` in your code — the framework did it.

## What to notice

Two options travel together here. `WithStructuredOutput` needs a **pointer** (`&person`) because the framework writes the parsed result back into it. And `agent.Stream(false)` is deliberate: **structured output is non-streaming** — the framework needs the *whole* JSON reply before it can parse it into your struct, so streaming token-by-token wouldn't make sense. Passing a value instead of a pointer, or leaving streaming on, is the classic mistake.

The `int` field is a nice tell that this is more than string formatting: the model is being asked to produce a JSON number, and it lands in a Go `int` directly. Get the types right and the framework enforces them; the schema is derived from your struct, so the model is constrained toward valid output rather than left to freeform.

A `runLogger` middleware rides along (the same local stand-in used across these lessons), and the offline test proves it's a transparent pass-through while asserting the agent's wiring with a fake credential — no network.

## How it maps to the Agent Framework

`WithStructuredOutput` is the Go SDK's structured-output mechanism, and it's provider-portable: the same option works against Foundry, OpenAI, or Anthropic, with each provider mapping it onto its own JSON-schema / response-format feature. On Foundry's Responses API it becomes a structured response request. This is the primitive you reach for whenever an agent's output feeds another system — extraction, classification, form-filling — rather than a human reader.

## Run it

```bash
go run ./tutorial/02-agents/providers/foundry/step05_structured_output
```

Tests run offline with a fake credential; the live extraction call is gated behind `AF_LIVE=1` with `az login` and `FOUNDRY_PROJECT_ENDPOINT`.

---

Next: [step06 · Persisted Conversations](/blog/posts/maf-go-45-persisted-conversations.html)
