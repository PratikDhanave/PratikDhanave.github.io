# Calling an LLM from Go

*Make your first model call from scratch with net/http and encoding/json — the chat/messages API shape, a typed client with a Bearer key and context timeout, robust error handling, and server-sent-event streaming — no framework required.*

---

Most "get started" guides hand you an SDK and a one-liner. That is fine until something breaks — a 429 you don't understand, a streamed response that never terminates, a timeout that hangs a request forever. This post takes the opposite route: we call a large language model from Go using nothing but the standard library. By the end you will have a typed client you understand top to bottom, because you built every layer of it. Once you know the shape of the request and response, adopting an official SDK is a convenience, not a mystery.

We target an **OpenAI-compatible chat completions endpoint**, because that request/response shape is the closest thing the industry has to a lingua franca — dozens of providers and local runtimes (llama.cpp, vLLM, Ollama's compatibility layer, Together, Groq, and OpenAI itself) speak it. The field names below are the real, generic ones; point the base URL and model at whatever provider you use.

---

## The chat API is a list of messages with roles

Before any Go, understand the data model. A chat request is not a single prompt string — it is an ordered **list of messages**, each tagged with a `role`:

- **`system`** — standing instructions that set behavior and tone. Usually one, first.
- **`user`** — what the human said.
- **`assistant`** — what the model said on previous turns.

To hold a conversation you resend the whole list every call — the endpoint is stateless, so *you* own the history. A three-turn chat looks like this on the wire:

```json
{
  "model": "gpt-4o-mini",
  "messages": [
    {"role": "system", "content": "You are a terse Go tutor."},
    {"role": "user", "content": "What does a nil map do on write?"},
    {"role": "assistant", "content": "It panics. Reads return the zero value."},
    {"role": "user", "content": "And on read?"}
  ],
  "temperature": 0.7,
  "max_tokens": 512
}
```

The knobs that matter most: **`temperature`** (0 = deterministic-ish and focused, higher = more varied), **`max_tokens`** (a ceiling on the *response* length, not the whole conversation), and **`model`** (which model to run). The response comes back as a list of **`choices`** — usually one — each carrying a `message` with the assistant's `role` and `content`, plus a `finish_reason` and a top-level **`usage`** block counting tokens:

```json
{
  "id": "chatcmpl-abc123",
  "choices": [
    {
      "index": 0,
      "message": {"role": "assistant", "content": "It returns the value type's zero value."},
      "finish_reason": "stop"
    }
  ],
  "usage": {"prompt_tokens": 42, "completion_tokens": 9, "total_tokens": 51}
}
```

`finish_reason` is worth reading: `stop` means the model finished naturally, `length` means it hit `max_tokens` and got cut off mid-thought. Token counts in `usage` are what you are billed on and what you budget against a context window.

---

## Modeling the request and response as Go structs

Now the Go. We mirror that JSON with typed structs and let `encoding/json` do the marshaling. The struct tags carry the wire names; Go field names stay idiomatic.

```go
package llm

type Message struct {
	Role    string `json:"role"`
	Content string `json:"content"`
}

type ChatRequest struct {
	Model       string    `json:"model"`
	Messages    []Message `json:"messages"`
	Temperature float64   `json:"temperature,omitempty"`
	MaxTokens   int       `json:"max_tokens,omitempty"`
	Stream      bool      `json:"stream,omitempty"`
}

type Usage struct {
	PromptTokens     int `json:"prompt_tokens"`
	CompletionTokens int `json:"completion_tokens"`
	TotalTokens      int `json:"total_tokens"`
}

type Choice struct {
	Index        int     `json:"index"`
	Message      Message `json:"message"`
	FinishReason string  `json:"finish_reason"`
}

type ChatResponse struct {
	ID      string   `json:"id"`
	Choices []Choice `json:"choices"`
	Usage   Usage    `json:"usage"`
}
```

**The gotcha:** the `,omitempty` on `Temperature` is subtle. A `float64` zero value is `0.0`, which `omitempty` treats as empty and *drops from the JSON* — so you can never send `temperature: 0` this way. If deterministic output matters, make the field a `*float64` (a nil pointer omits, a pointer to `0` sends `0`) or drop `omitempty` and always send an explicit value. The same trap applies to any numeric knob whose meaningful value is zero.

---

## A typed client: Bearer key, context, decode

The client holds a base URL, an API key read from the environment, and — importantly — a *shared* `*http.Client` so connections get reused across calls rather than leaking a new transport each time.

```go
package llm

import (
	"bytes"
	"context"
	"encoding/json"
	"fmt"
	"io"
	"net/http"
	"os"
	"time"
)

type Client struct {
	BaseURL    string
	APIKey     string
	Model      string
	HTTPClient *http.Client
}

func NewClient() (*Client, error) {
	key := os.Getenv("LLM_API_KEY")
	if key == "" {
		return nil, fmt.Errorf("LLM_API_KEY is not set")
	}
	return &Client{
		BaseURL:    "https://api.openai.com/v1",
		APIKey:     key,
		Model:      "gpt-4o-mini",
		HTTPClient: &http.Client{Timeout: 60 * time.Second},
	}, nil
}
```

Reading the key from an environment variable — never a string literal — keeps credentials out of source control and CI logs. Now the call itself. Note that we take a `context.Context` as the first argument: that is the Go convention for anything that does I/O, and it lets the caller cancel a slow request or bound it with a deadline.

```go
func (c *Client) Chat(ctx context.Context, messages []Message) (*ChatResponse, error) {
	reqBody := ChatRequest{
		Model:       c.Model,
		Messages:    messages,
		Temperature: 0.7,
		MaxTokens:   512,
	}
	payload, err := json.Marshal(reqBody)
	if err != nil {
		return nil, fmt.Errorf("marshal request: %w", err)
	}

	req, err := http.NewRequestWithContext(ctx, http.MethodPost,
		c.BaseURL+"/chat/completions", bytes.NewReader(payload))
	if err != nil {
		return nil, fmt.Errorf("build request: %w", err)
	}
	req.Header.Set("Content-Type", "application/json")
	req.Header.Set("Authorization", "Bearer "+c.APIKey)

	resp, err := c.HTTPClient.Do(req)
	if err != nil {
		return nil, fmt.Errorf("send request: %w", err)
	}
	defer resp.Body.Close()

	body, err := io.ReadAll(resp.Body)
	if err != nil {
		return nil, fmt.Errorf("read body: %w", err)
	}
	if resp.StatusCode != http.StatusOK {
		return nil, fmt.Errorf("api error %d: %s", resp.StatusCode, body)
	}

	var out ChatResponse
	if err := json.Unmarshal(body, &out); err != nil {
		return nil, fmt.Errorf("decode response: %w", err)
	}
	return &out, nil
}
```

Two details earn their place. `http.NewRequestWithContext` is what actually wires cancellation into the transport — a plain `http.NewRequest` ignores your context entirely. And reading the full body *before* checking the status lets us surface the provider's error JSON (which explains *why* it failed) instead of a bare status code. A tiny caller ties it together:

```go
func main() {
	c, err := llm.NewClient()
	if err != nil {
		log.Fatal(err)
	}
	ctx, cancel := context.WithTimeout(context.Background(), 30*time.Second)
	defer cancel()

	resp, err := c.Chat(ctx, []llm.Message{
		{Role: "system", Content: "You are a terse Go tutor."},
		{Role: "user", Content: "Explain a nil channel in one sentence."},
	})
	if err != nil {
		log.Fatal(err)
	}
	fmt.Println(resp.Choices[0].Message.Content)
	fmt.Printf("tokens: %d in, %d out\n",
		resp.Usage.PromptTokens, resp.Usage.CompletionTokens)
}
```

**The gotcha:** the `context.WithTimeout` on the caller and the `Timeout` on the `http.Client` are *different* clocks. The client timeout is a blunt per-call cap; the context deadline can be tighter or shared across several operations, and it is the only one that lets you cancel *early* from elsewhere. When both are set the shorter one wins — set the context deadline to what the caller actually needs and keep the client timeout as a generous backstop. Always `defer resp.Body.Close()`, and always drain or close the body even on the error path, or you leak connections from the pool.

---

## Errors, rate limits, and retries with backoff

Real endpoints fail in ways worth distinguishing. A `400` means your request is malformed — retrying is pointless. A `401` means a bad key — also terminal. A `429` means rate-limited, and a `500`/`502`/`503` means the provider hiccuped — both are worth retrying *after a delay*. The delay is the important part: hammering a rate-limited endpoint immediately just extends the throttle.

The right strategy is **exponential backoff with jitter** — wait longer after each failure, plus a small random offset so a fleet of clients doesn't retry in lockstep. On a `429` the provider often sends a `Retry-After` header telling you exactly how long to wait; honor it when present. Sketching the retry decision (keeping the transport code from above):

```go
func retryable(status int) bool {
	return status == http.StatusTooManyRequests || // 429
		status >= 500 // provider-side failures
}

func backoff(attempt int) time.Duration {
	base := time.Duration(1<<attempt) * time.Second        // 1s, 2s, 4s, ...
	jitter := time.Duration(rand.Int63n(int64(250 * time.Millisecond)))
	return base + jitter
}
```

You would wrap `Chat` in a loop that tries a few times, sleeps `backoff(attempt)` between retryable failures (or the `Retry-After` value), and returns immediately on success or a non-retryable status. Two rules keep it honest: **cap the attempts** (three or four — infinite retries turn a blip into an outage), and **respect the context** by selecting on `ctx.Done()` while you sleep, so a cancelled request stops waiting instead of finishing its backoff.

---

## Streaming with server-sent events

For anything a human reads, waiting for the full completion feels sluggish. Streaming fixes that: set `"stream": true` and the model pushes tokens as it generates them. The transport is **server-sent events (SSE)** — a long-lived HTTP response where the body is a text stream of lines, each event prefixed with `data: `. A streamed chat response is a sequence of these:

```
data: {"choices":[{"delta":{"role":"assistant"},"index":0}]}

data: {"choices":[{"delta":{"content":"It "},"index":0}]}

data: {"choices":[{"delta":{"content":"panics."},"index":0}]}

data: [DONE]
```

Three things differ from the non-streaming shape. The payload carries a **`delta`** (the *incremental* piece) instead of a full `message`; events are separated by blank lines; and the stream ends with a literal sentinel line, `data: [DONE]`, which is **not JSON** — you must special-case it before decoding.

Go's `bufio.Scanner` reads the body line by line without buffering the whole response, which is exactly what streaming demands. We strip the `data: ` prefix, stop at the sentinel, decode each remaining line as a delta chunk, and hand each token to a callback.

```go
type streamChunk struct {
	Choices []struct {
		Delta struct {
			Content string `json:"content"`
		} `json:"delta"`
		FinishReason string `json:"finish_reason"`
	} `json:"choices"`
}

func (c *Client) ChatStream(ctx context.Context, messages []Message, onToken func(string)) error {
	reqBody := ChatRequest{Model: c.Model, Messages: messages, Stream: true}
	payload, err := json.Marshal(reqBody)
	if err != nil {
		return fmt.Errorf("marshal request: %w", err)
	}

	req, err := http.NewRequestWithContext(ctx, http.MethodPost,
		c.BaseURL+"/chat/completions", bytes.NewReader(payload))
	if err != nil {
		return fmt.Errorf("build request: %w", err)
	}
	req.Header.Set("Content-Type", "application/json")
	req.Header.Set("Authorization", "Bearer "+c.APIKey)
	req.Header.Set("Accept", "text/event-stream")

	resp, err := c.HTTPClient.Do(req)
	if err != nil {
		return fmt.Errorf("send request: %w", err)
	}
	defer resp.Body.Close()
	if resp.StatusCode != http.StatusOK {
		body, _ := io.ReadAll(resp.Body)
		return fmt.Errorf("api error %d: %s", resp.StatusCode, body)
	}

	scanner := bufio.NewScanner(resp.Body)
	scanner.Buffer(make([]byte, 0, 64*1024), 1024*1024) // room for long lines
	for scanner.Scan() {
		line := scanner.Text()
		if !strings.HasPrefix(line, "data: ") {
			continue // skip blank separators and any comment/keepalive lines
		}
		data := strings.TrimPrefix(line, "data: ")
		if data == "[DONE]" {
			break
		}
		var chunk streamChunk
		if err := json.Unmarshal([]byte(data), &chunk); err != nil {
			return fmt.Errorf("decode chunk: %w", err)
		}
		if len(chunk.Choices) > 0 {
			onToken(chunk.Choices[0].Delta.Content)
		}
	}
	return scanner.Err()
}
```

Printing tokens as they land is now a two-liner:

```go
err := c.ChatStream(ctx, msgs, func(tok string) {
	fmt.Print(tok)
	os.Stdout.Sync()
})
```

**The gotcha:** `bufio.Scanner` has a default maximum token size of 64 KB per line and returns `bufio.ErrTooLong` if a single SSE `data:` line exceeds it — which large chunks can. The `scanner.Buffer(...)` call above raises that ceiling; without it a long line silently ends your loop with an error you must check via `scanner.Err()`. Also note the sentinel check *must* come before `json.Unmarshal` — `[DONE]` is not valid JSON and will error every time if you try to decode it. Finally, don't forget to accumulate the deltas yourself if you need the full text; the stream never resends the complete message.

---

## When to reach for an official SDK

Everything above is deliberately hand-rolled so the mechanics are visible. In production you'll often prefer a maintained SDK that tracks provider changes, handles retries and streaming, and gives you typed helpers for tool calls and structured output. Well-known Go options include **`openai-go`** for OpenAI-compatible endpoints, **`anthropic-sdk-go`** for the Anthropic Messages API, and **`google.golang.org/genai`** for Gemini. Their exact method names and option types differ, so check each project's own docs and examples rather than assuming — but the request/response shape you now understand maps cleanly onto all of them.

| Concern | Standard library approach |
|---|---|
| Transport | `net/http` with a shared `*http.Client` |
| Auth | `Authorization: Bearer <key>` header from an env var |
| Cancellation | `http.NewRequestWithContext` + `context.WithTimeout` |
| Encoding | `encoding/json` structs with wire-name tags |
| Zero-valued knobs | `*float64` or drop `,omitempty` |
| Streaming | `bufio.Scanner` over SSE, split on `data: `, stop at `[DONE]` |
| Reliability | classify status, backoff + jitter, honor `Retry-After` |

---

## Key takeaways

- **The chat API is a stateless list of role-tagged messages.** You own the history and resend it every call; the response is a list of `choices` plus a `usage` token count.
- **A typed Go client is four small pieces** — request/response structs, a Bearer header from an env var, a context-aware `http.Request`, and a JSON decode. No framework needed.
- **Mind `omitempty` on numeric fields.** It silently drops legitimate zero values like `temperature: 0`; use a pointer or send the value explicitly.
- **Retry only what's retryable.** 429 and 5xx with exponential backoff and jitter; honor `Retry-After`; cap attempts; respect the context while you wait.
- **Streaming is SSE parsed line by line.** Read with `bufio.Scanner`, strip `data: `, break on `[DONE]` before decoding, and raise the scanner buffer for long chunks.
- **SDKs are a convenience, not magic.** Once the wire shape is clear, `openai-go`, `anthropic-sdk-go`, and `google.golang.org/genai` are just ergonomic wrappers over the same request and response.

---

## Further reading

- [OpenAI API reference — Chat Completions](https://platform.openai.com/docs/api-reference/chat) — the request/response fields and streaming format this post mirrors.
- [Anthropic API reference — Messages](https://docs.anthropic.com/en/api/messages) — the same message-list concept with provider-specific field names.
- [Go `net/http` package documentation](https://pkg.go.dev/net/http) — `Client`, `NewRequestWithContext`, and header handling.
- [Go `encoding/json` package documentation](https://pkg.go.dev/encoding/json) — struct tags, `omitempty` semantics, `Marshal`/`Unmarshal`.
- [Go `bufio` package documentation](https://pkg.go.dev/bufio) — `Scanner`, `Buffer`, and the default token-size limit.
