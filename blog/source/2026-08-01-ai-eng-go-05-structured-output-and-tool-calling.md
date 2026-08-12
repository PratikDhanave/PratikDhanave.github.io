# Structured Output and Tool Calling

*From-scratch Go for the two mechanisms that turn an LLM from a text generator into a component you can wire into real software — schema-constrained JSON and function calling — both spoken over the same OpenAI-compatible chat JSON.*

---

In post 4 we called an LLM the way most tutorials stop: send a prompt, read the assistant's prose reply, print it. That is fine when a human reads the answer. It falls apart the moment your Go program has to *act* on the answer. `resp.Choices[0].Message.Content` is a `string`, and a string is exactly the wrong shape to feed into a database write, a switch statement, or a downstream API. You end up writing regexes to scrape a number out of a sentence, and the model breaks you the first time it adds "Sure, here's the total: **$42.00**." around it.

This post is about getting output you can *rely on* — machine-readable, typed, validated. There are two mechanisms, and the whole point of this post is that **they are the same idea wearing two hats**: constrain the model to emit JSON your Go code can decode and act on. The first, **structured output**, asks the model to fill in a shape you define. The second, **tool calling**, lets the model ask *you* to run a function and hand back the result. Both ride the same OpenAI-compatible chat JSON we already speak from post 4, so we build on the hand-rolled `net/http` client, not a vendor SDK.

We will keep one hard rule throughout: **the wire is JSON typed by a schema, but the model is not bound by your types.** It can still return malformed or schema-violating JSON. So every decode is defensive, and every structured call gets a validate-and-retry loop.

---

## The shared foundation: our post-4 client

Everything below assumes the small chat client from post 4. As a refresher, the request and response envelopes look like this — plain structs over `encoding/json`, no framework:

```go
type Message struct {
	Role       string     `json:"role"`
	Content    string     `json:"content,omitempty"`
	ToolCalls  []ToolCall `json:"tool_calls,omitempty"`
	ToolCallID string     `json:"tool_call_id,omitempty"` // set on role:"tool" replies
	Name       string     `json:"name,omitempty"`
}

type ChatRequest struct {
	Model          string          `json:"model"`
	Messages       []Message       `json:"messages"`
	Tools          []Tool          `json:"tools,omitempty"`
	ResponseFormat *ResponseFormat `json:"response_format,omitempty"`
}

type ChatResponse struct {
	Choices []struct {
		Message      Message `json:"message"`
		FinishReason string  `json:"finish_reason"`
	} `json:"choices"`
}
```

Assume a method `client.Complete(ctx, ChatRequest) (ChatResponse, error)` that marshals the request, POSTs it, and unmarshals the reply — exactly what we wrote last time. The new fields (`Tools`, `ResponseFormat`, `ToolCalls`, `ToolCallID`) are all `omitempty`, so a plain chat call serializes identically to post 4. We are extending the envelope, not replacing it.

---

## Structured output, attempt one: just ask for JSON

The lowest-tech approach is to ask, in the prompt, for JSON and nothing else. Define the Go shape you want first, because the struct *is* your contract:

```go
type Invoice struct {
	Vendor   string  `json:"vendor"`
	Total    float64 `json:"total"`
	Currency string  `json:"currency"`
	DueDate  string  `json:"due_date"` // ISO 8601, e.g. "2026-09-01"
}
```

Then instruct the model to produce that shape:

```go
sys := `Extract the invoice fields. Respond with ONLY a JSON object, no prose, no
markdown fences, matching exactly:
{"vendor": string, "total": number, "currency": string, "due_date": "YYYY-MM-DD"}`

resp, err := client.Complete(ctx, ChatRequest{
	Model: "gpt-4o-mini",
	Messages: []Message{
		{Role: "system", Content: sys},
		{Role: "user", Content: rawInvoiceText},
	},
})
```

This works often enough to be tempting and fails often enough to hurt. The model may wrap the JSON in ```` ```json ```` fences, prepend "Here is the extracted data:", or emit a trailing comma. You are back to scraping text.

**The gotcha:** prompting for JSON is a *request*, not a *guarantee*. Never `json.Unmarshal` the raw content directly and assume success. At minimum, strip markdown fences and locate the outermost `{...}` before decoding — and even then, treat a decode error as an expected branch, not a panic. Prompt-only JSON is the fallback for models or endpoints that lack a real structured-output mode, not the default.

---

## Structured output, attempt two: response_format

Most OpenAI-compatible endpoints expose a `response_format` field that *constrains* the decoder rather than merely asking politely. Two modes matter:

- `{"type": "json_object"}` — the model is guaranteed to emit syntactically valid JSON (some object), but not any *particular* shape.
- `{"type": "json_schema", ...}` — you attach a JSON Schema and the model's output is constrained to match it. This is the strong version.

Here are the Go types for the schema mode:

```go
type ResponseFormat struct {
	Type       string      `json:"type"`                  // "json_schema"
	JSONSchema *JSONSchema `json:"json_schema,omitempty"`
}

type JSONSchema struct {
	Name   string                 `json:"name"`
	Strict bool                   `json:"strict"`
	Schema map[string]interface{} `json:"schema"`
}
```

And the schema for our `Invoice` struct, written by hand as a Go map so it marshals to exactly the JSON Schema the API expects:

```go
invoiceSchema := map[string]interface{}{
	"type": "object",
	"properties": map[string]interface{}{
		"vendor":   map[string]interface{}{"type": "string"},
		"total":    map[string]interface{}{"type": "number"},
		"currency": map[string]interface{}{"type": "string"},
		"due_date": map[string]interface{}{"type": "string"},
	},
	"required":             []string{"vendor", "total", "currency", "due_date"},
	"additionalProperties": false,
}

req := ChatRequest{
	Model:    "gpt-4o-mini",
	Messages: []Message{{Role: "user", Content: rawInvoiceText}},
	ResponseFormat: &ResponseFormat{
		Type: "json_schema",
		JSONSchema: &JSONSchema{Name: "invoice", Strict: true, Schema: invoiceSchema},
	},
}
```

With `strict: true` and `additionalProperties: false`, a compliant endpoint returns JSON that decodes cleanly into `Invoice`. Writing the schema by hand keeps you honest about what "required" means and avoids pulling in a reflection library — but for larger structs you can generate the map from `reflect` once and reuse it.

**The gotcha:** `json_schema` support is provider- and model-specific. Older or self-hosted endpoints may accept only `json_object`, or silently ignore `response_format` entirely and return prose. Don't assume the field did anything — the very next section validates the result regardless of which mode produced it. Structured mode narrows the failure rate; it does not eliminate it.

---

## Decode defensively, then validate, then retry

This is the part most write-ups skip, and it is the part that makes structured output production-grade. Even with `strict: true`, you can get a `total` of `-1`, an empty `vendor`, or a `due_date` of `"next Tuesday"`. Schema conformance is not the same as *semantic* validity. So we separate three concerns: **decode** (is it valid JSON of the right shape?), **validate** (do the values make sense?), and **retry** (feed the error back and let the model fix it).

```go
func validateInvoice(inv Invoice) error {
	if strings.TrimSpace(inv.Vendor) == "" {
		return errors.New("vendor is empty")
	}
	if inv.Total <= 0 {
		return fmt.Errorf("total must be positive, got %v", inv.Total)
	}
	if _, err := time.Parse("2006-01-02", inv.DueDate); err != nil {
		return fmt.Errorf("due_date %q is not YYYY-MM-DD", inv.DueDate)
	}
	return nil
}
```

Now the loop. We give the model a bounded number of attempts; on each failure we append the model's bad answer *and* a user message describing what was wrong, so the next attempt is a correction rather than a blind retry:

```go
func extractInvoice(ctx context.Context, c *Client, text string) (Invoice, error) {
	msgs := []Message{{Role: "user", Content: text}}

	const maxAttempts = 3
	for attempt := 1; attempt <= maxAttempts; attempt++ {
		resp, err := c.Complete(ctx, ChatRequest{
			Model: "gpt-4o-mini", Messages: msgs,
			ResponseFormat: &ResponseFormat{
				Type:       "json_schema",
				JSONSchema: &JSONSchema{Name: "invoice", Strict: true, Schema: invoiceSchema},
			},
		})
		if err != nil {
			return Invoice{}, err // transport error: don't burn a retry
		}
		content := resp.Choices[0].Message.Content

		var inv Invoice
		decodeErr := json.Unmarshal([]byte(content), &inv)
		if decodeErr == nil {
			decodeErr = validateInvoice(inv)
		}
		if decodeErr == nil {
			return inv, nil // success
		}

		// Feed the failure back for the next attempt.
		msgs = append(msgs,
			Message{Role: "assistant", Content: content},
			Message{Role: "user", Content: "That response was invalid: " +
				decodeErr.Error() + ". Return corrected JSON only."})
	}
	return Invoice{}, fmt.Errorf("no valid invoice after %d attempts", maxAttempts)
}
```

Note the two error paths are treated differently. A transport error (`err`) means the HTTP call itself failed — retrying inside this loop would just hammer a broken endpoint, so we return immediately and let the caller's own retry/backoff decide. A *content* error (`decodeErr`) means the model answered but got it wrong, which is exactly what the correction loop is for.

**The gotcha:** the retry budget must be *bounded*. An unbounded "loop until valid" can spin forever against a model that keeps making the same mistake, running up cost and latency with nothing to show. Three attempts is a reasonable default; past that, fail loudly and let a human or a fallback handle it. Also: keep the successfully-decoded value even if validation later fails — you want the error message to reference real values ("got -1"), which is what makes the correction prompt effective.

---

## Tool calling: the model asks you to run code

Structured output makes the model fill in a shape. Tool calling flips the direction: you tell the model what functions exist, and it decides to *call* one, handing you typed arguments. You run the real Go function and hand the result back. It is structured output pointed at your codebase.

The request carries a `tools` array. Each tool is a name, a description, and a JSON-Schema description of its parameters — the same schema machinery as above:

```go
type Tool struct {
	Type     string       `json:"type"` // always "function"
	Function ToolFunction `json:"function"`
}

type ToolFunction struct {
	Name        string                 `json:"name"`
	Description string                 `json:"description"`
	Parameters  map[string]interface{} `json:"parameters"`
}
```

Let's expose one concrete tool: a currency converter backed by a fixed rate table (real Go, no fabricated service):

```go
var rates = map[string]float64{"USD": 1.0, "EUR": 1.08, "GBP": 1.27, "INR": 0.012}

// The actual Go function the model's call will drive.
func convertCurrency(amount float64, from, to string) (float64, error) {
	rf, okF := rates[from]
	rt, okT := rates[to]
	if !okF || !okT {
		return 0, fmt.Errorf("unsupported currency pair %s->%s", from, to)
	}
	return amount * rf / rt, nil
}

var convertTool = Tool{
	Type: "function",
	Function: ToolFunction{
		Name:        "convert_currency",
		Description: "Convert an amount between USD, EUR, GBP and INR.",
		Parameters: map[string]interface{}{
			"type": "object",
			"properties": map[string]interface{}{
				"amount": map[string]interface{}{"type": "number"},
				"from":   map[string]interface{}{"type": "string", "enum": []string{"USD", "EUR", "GBP", "INR"}},
				"to":     map[string]interface{}{"type": "string", "enum": []string{"USD", "EUR", "GBP", "INR"}},
			},
			"required": []string{"amount", "from", "to"},
		},
	},
}
```

When the model decides to use it, the response comes back not as prose but with `finish_reason: "tool_calls"` and a `tool_calls` array on the message:

```json
{
  "choices": [{
    "finish_reason": "tool_calls",
    "message": {
      "role": "assistant",
      "content": null,
      "tool_calls": [{
        "id": "call_a1b2c3",
        "type": "function",
        "function": {
          "name": "convert_currency",
          "arguments": "{\"amount\": 100, \"from\": \"EUR\", \"to\": \"USD\"}"
        }
      }]
    }
  }]
}
```

Look closely at `arguments`. It is a JSON **string**, not a JSON object — a string whose *contents* are JSON. Our Go types reflect that exactly:

```go
type ToolCall struct {
	ID       string `json:"id"`
	Type     string `json:"type"`
	Function struct {
		Name      string `json:"name"`
		Arguments string `json:"arguments"` // JSON encoded as a string
	} `json:"function"`
}
```

**The gotcha:** `arguments` arrives as a *string you must unmarshal a second time*, not a `map` you can index. `tc.Function.Arguments["amount"]` does not compile — the field is a `string`. You `json.Unmarshal([]byte(tc.Function.Arguments), &args)` into a typed struct, and that decode can fail exactly like any other model output. The model can hallucinate an argument name, omit a required field, or pass a string where you wanted a number. Decode into a struct and check, never trust it blindly.

---

## The full round-trip loop

One tool call is rarely the whole story. The model might call `convert_currency`, read the result, then call it again for a second pair, then finally answer in prose. So the driver is a **loop**: call the model, and while the reply contains tool calls, execute each one, append its result as a new message, and call again. You exit only when the model returns prose (`finish_reason` is not `tool_calls`).

```go
func runWithTools(ctx context.Context, c *Client, userMsg string) (string, error) {
	msgs := []Message{{Role: "user", Content: userMsg}}

	const maxTurns = 8 // hard ceiling so a misbehaving model can't loop forever
	for turn := 0; turn < maxTurns; turn++ {
		resp, err := c.Complete(ctx, ChatRequest{
			Model: "gpt-4o-mini", Messages: msgs, Tools: []Tool{convertTool},
		})
		if err != nil {
			return "", err
		}
		reply := resp.Choices[0].Message
		msgs = append(msgs, reply) // the assistant turn (with its tool_calls) stays in history

		if len(reply.ToolCalls) == 0 {
			return reply.Content, nil // model answered in prose — we're done
		}

		// Execute every requested call and append one tool-result message per call.
		for _, tc := range reply.ToolCalls {
			result := dispatchTool(tc)
			msgs = append(msgs, Message{
				Role:       "tool",
				ToolCallID: tc.ID, // ties the result to the specific call
				Name:       tc.Function.Name,
				Content:    result,
			})
		}
	}
	return "", fmt.Errorf("tool loop exceeded %d turns", maxTurns)
}
```

`dispatchTool` is where the string-arguments decode and the real function call live. Crucially, a tool *error* is not a Go error you return up the stack — it is a result you hand back to the model, which can then apologize or try different arguments:

```go
func dispatchTool(tc ToolCall) string {
	switch tc.Function.Name {
	case "convert_currency":
		var args struct {
			Amount float64 `json:"amount"`
			From   string  `json:"from"`
			To     string  `json:"to"`
		}
		if err := json.Unmarshal([]byte(tc.Function.Arguments), &args); err != nil {
			return fmt.Sprintf(`{"error": "could not parse arguments: %s"}`, err)
		}
		out, err := convertCurrency(args.Amount, args.From, args.To)
		if err != nil {
			return fmt.Sprintf(`{"error": %q}`, err.Error())
		}
		return fmt.Sprintf(`{"result": %.2f}`, out)
	default:
		return fmt.Sprintf(`{"error": "unknown tool %q"}`, tc.Function.Name)
	}
}
```

**The gotcha:** two things must be exact or the loop silently breaks. First, the assistant message *with its `tool_calls`* must go back into `msgs` before you append the results — the API rejects a `tool` message that answers a call it never saw. Second, each tool result is its **own message** with `role: "tool"` and a `tool_call_id` matching the `id` the model sent. If the model made three calls in one turn, you append three tool messages, each tagged with its own id. Mismatch the ids and the model can't tell which result answers which call. And keep the `maxTurns` ceiling: without it, a model that loops on a failing tool will spin until your context window or your budget runs out.

---

## The two mechanisms, side by side

| | Structured output | Tool calling |
|---|---|---|
| Who initiates | You demand a shape | Model requests a function |
| On the wire | `response_format` + schema | `tools` array + schema |
| Model's reply | JSON in `content` | `tool_calls` array |
| Your job | Decode + validate the JSON | Decode args, run func, return result |
| Loop? | Retry on invalid | Loop while tool calls present |
| Shared idea | Constrain the model to emit JSON your Go code can act on | ← same |

Both are the same move: attach a JSON Schema, get back JSON, decode into a Go struct, and *never trust it until you have checked it*. Structured output is a one-shot fill-in-the-shape; tool calling is a conversation where the shape is "which function, with what arguments." Once you see them as one idea, the defensive-decoding discipline transfers directly from one to the other.

---

## Key takeaways

- **A string is the wrong output type for software.** Structured output and tool calling both exist to get you typed, machine-readable JSON instead of prose you have to scrape.
- **Prefer `response_format` json_schema over prompt-only JSON**, but know it is provider-dependent and still fallible — validate regardless of which mode produced the bytes.
- **Decode, validate, retry — bounded.** Schema conformance is not semantic validity; run a real `validate` step and feed failures back into a capped correction loop.
- **Tool `arguments` is a JSON string, not a map.** Unmarshal it a second time into a typed struct, and treat that decode as fallible.
- **Tool calling is a loop, not a call.** Append the assistant's `tool_calls` turn, then one `role:"tool"` message per call tagged with its `tool_call_id`, and iterate until the model answers in prose — with a hard turn ceiling.
- **The two mechanisms are one idea:** constrain the model to emit JSON your Go code can act on, and never act on it blindly.

Next in the series we build on this loop to assemble a small agent — the same tool round-trip, plus memory and a planning step, so the model can string several tools together toward a goal.

---

## Further reading

- [OpenAI — Structured Outputs guide](https://platform.openai.com/docs/guides/structured-outputs)
- [OpenAI — Function calling guide](https://platform.openai.com/docs/guides/function-calling)
- [Anthropic — Tool use (function calling)](https://docs.anthropic.com/en/docs/build-with-claude/tool-use)
- [Anthropic — Increase output consistency with JSON](https://docs.anthropic.com/en/docs/test-and-evaluate/strengthen-guardrails/increase-consistency)
- [Go — `encoding/json` package documentation](https://pkg.go.dev/encoding/json)
- [JSON Schema — specification and reference](https://json-schema.org/understanding-json-schema/)
