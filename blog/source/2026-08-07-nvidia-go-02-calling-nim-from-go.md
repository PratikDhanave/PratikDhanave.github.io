# Calling NIM from Go

*Building a small, typed Go client for NVIDIA NIM over its OpenAI-compatible REST API — request and response structs, robust error handling, SSE streaming, and one base-URL switch that moves you from the hosted catalog to a self-hosted microservice.*

---

NVIDIA does not ship a Go SDK. That sounds like a gap until you notice what NIM (NVIDIA Inference Microservices) actually exposes: an **OpenAI-compatible REST API**. The hosted API Catalog at `https://integrate.api.nvidia.com/v1` and a NIM container you run yourself both speak the same HTTP dialect — `POST /chat/completions` with a JSON body, a Bearer token, and either a single JSON response or a Server-Sent Events stream. That means the whole client is `net/http` and `encoding/json`. No dependencies, no code generation, no wrapper library to keep in sync.

This post builds that client from scratch. We'll define the request and response structs, read the key from the environment, run a request under a `context.Context` deadline, handle the error paths the docs warn about, then add streaming with `bufio.Scanner`. The payoff at the end is a one-line change: point the same code at the hosted catalog or at your own GPU box.

---

## The shape of the API

Before writing any Go, it helps to name exactly what we're talking to. The request is an OpenAI-shaped chat-completions body:

```json
{
  "model": "meta/llama-3.1-8b-instruct",
  "messages": [
    {"role": "system", "content": "You are a terse assistant."},
    {"role": "user", "content": "Name three moons of Saturn."}
  ],
  "temperature": 0.2,
  "max_tokens": 256,
  "stream": false
}
```

The non-streaming response carries the answer in `choices[].message.content` and token accounting in `usage`:

```json
{
  "choices": [
    {"index": 0, "message": {"role": "assistant", "content": "Titan, Enceladus, Mimas."}}
  ],
  "usage": {"prompt_tokens": 24, "completion_tokens": 9, "total_tokens": 33}
}
```

The `model` value is a string you pick from the catalog. `"meta/llama-3.1-8b-instruct"` is used throughout as an **example** — check [build.nvidia.com](https://build.nvidia.com) for the identifiers currently available to you, since the catalog changes over time.

**The gotcha:** the base URL already ends in `/v1`, and you append `/chat/completions` yourself. So the full endpoint is `https://integrate.api.nvidia.com/v1/chat/completions`. Get the join wrong — a doubled `/v1`, a missing slash — and the server answers with a bare `404`, not a message explaining what you did. Store the base URL *with* `/v1` and let the client add the path; more on this below.

---

## Request and response structs

Map the JSON directly to Go types. The `omitempty` tags matter: they keep optional fields out of the wire body when you leave them at their zero value.

```go
package nim

// Message is one turn in the conversation.
type Message struct {
	Role    string `json:"role"`    // "system", "user", or "assistant"
	Content string `json:"content"`
}

// ChatRequest is the body sent to POST {baseURL}/chat/completions.
type ChatRequest struct {
	Model       string    `json:"model"`
	Messages    []Message `json:"messages"`
	Temperature float64   `json:"temperature,omitempty"`
	MaxTokens   int       `json:"max_tokens,omitempty"`
	Stream      bool      `json:"stream,omitempty"`
}

// Usage reports token accounting for a completion.
type Usage struct {
	PromptTokens     int `json:"prompt_tokens"`
	CompletionTokens int `json:"completion_tokens"`
	TotalTokens      int `json:"total_tokens"`
}

// Choice is one candidate completion. Message is populated on a
// non-streaming response; Delta carries incremental text when streaming.
type Choice struct {
	Index   int     `json:"index"`
	Message Message `json:"message"`
	Delta   Message `json:"delta"`
}

// ChatResponse is the decoded non-streaming reply.
type ChatResponse struct {
	Choices []Choice `json:"choices"`
	Usage   Usage    `json:"usage"`
}
```

Reusing `Message` for `Delta` works because the streaming chunk's `delta` object has the same `role`/`content` fields — only `content` is usually present per chunk, which decodes cleanly into an otherwise-zero `Message`.

---

## The client: key from the environment, one shared http.Client

Two rules drive the constructor. First, the API key is a secret — it comes from an environment variable, never a literal in source. Second, you want **one** `*http.Client` shared across requests so Go can pool and reuse TCP connections; constructing a fresh client per call throws that away.

```go
package nim

import (
	"fmt"
	"net/http"
	"os"
	"time"
)

// Client talks to a NIM chat-completions endpoint.
type Client struct {
	baseURL string       // includes the trailing /v1, e.g. https://integrate.api.nvidia.com/v1
	apiKey  string       // may be empty for a network-scoped self-hosted NIM
	http    *http.Client // shared; reuses connections
}

// New builds a client for the hosted API Catalog, reading the key from
// NVIDIA_API_KEY. The key looks like "nvapi-...".
func New() (*Client, error) {
	key := os.Getenv("NVIDIA_API_KEY")
	if key == "" {
		return nil, fmt.Errorf("NVIDIA_API_KEY is not set")
	}
	return NewWithBaseURL("https://integrate.api.nvidia.com/v1", key), nil
}

// NewWithBaseURL targets any NIM endpoint. Pass an empty key for a
// self-hosted NIM that relies on network scoping instead of a token.
func NewWithBaseURL(baseURL, apiKey string) *Client {
	return &Client{
		baseURL: baseURL,
		apiKey:  apiKey,
		http:    &http.Client{Timeout: 60 * time.Second},
	}
}
```

**The gotcha:** keep the key in an environment variable or a secret store — a committed `nvapi-...` key is a leaked credential that anyone with repo access can spend against your account. A **self-hosted** NIM is the exception: when it's reachable only inside a private network it may require no key at all, so the client has to tolerate an empty `apiKey` and simply skip the `Authorization` header. `New()` insists on a key because it targets the public hosted catalog, where a missing key is always a mistake; `NewWithBaseURL` stays permissive for the self-hosted case.

---

## One request, decoded — with real error handling

Here's the core call. It builds the JSON body, attaches the context, sets the headers, checks the status *before* trusting the body, and surfaces the provider's error text when something goes wrong.

```go
package nim

import (
	"bytes"
	"context"
	"encoding/json"
	"fmt"
	"io"
	"net/http"
)

// Chat sends a non-streaming completion request and returns the decoded reply.
func (c *Client) Chat(ctx context.Context, req ChatRequest) (*ChatResponse, error) {
	req.Stream = false

	body, err := json.Marshal(req)
	if err != nil {
		return nil, fmt.Errorf("marshal request: %w", err)
	}

	url := c.baseURL + "/chat/completions"
	httpReq, err := http.NewRequestWithContext(ctx, http.MethodPost, url, bytes.NewReader(body))
	if err != nil {
		return nil, fmt.Errorf("build request: %w", err)
	}
	httpReq.Header.Set("Content-Type", "application/json")
	httpReq.Header.Set("Accept", "application/json")
	if c.apiKey != "" {
		httpReq.Header.Set("Authorization", "Bearer "+c.apiKey)
	}

	resp, err := c.http.Do(httpReq)
	if err != nil {
		return nil, fmt.Errorf("do request: %w", err)
	}
	defer resp.Body.Close()

	if resp.StatusCode != http.StatusOK {
		return nil, statusError(resp)
	}

	var out ChatResponse
	if err := json.NewDecoder(resp.Body).Decode(&out); err != nil {
		return nil, fmt.Errorf("decode response: %w", err)
	}
	if len(out.Choices) == 0 {
		return nil, fmt.Errorf("response contained no choices")
	}
	return &out, nil
}
```

The error path deserves its own helper. When the server returns a non-200, the response body usually holds a JSON error object that says *why* — an unknown model id, a malformed body, an expired key. Discarding it and returning "status 400" wastes the most useful diagnostic you have. The `429` (rate-limited) case is worth naming explicitly so callers can decide to back off and retry.

```go
package nim

import (
	"fmt"
	"io"
	"net/http"
)

// statusError reads the provider's error body and wraps it with the status.
func statusError(resp *http.Response) error {
	b, _ := io.ReadAll(io.LimitReader(resp.Body, 4<<10)) // cap the read; error bodies are small
	if resp.StatusCode == http.StatusTooManyRequests {
		return fmt.Errorf("rate limited (429): %s", string(b))
	}
	return fmt.Errorf("nim returned %d: %s", resp.StatusCode, string(b))
}
```

Calling it end to end:

```go
package main

import (
	"context"
	"fmt"
	"log"
	"time"

	"example.com/nim"
)

func main() {
	client, err := nim.New()
	if err != nil {
		log.Fatal(err)
	}

	ctx, cancel := context.WithTimeout(context.Background(), 30*time.Second)
	defer cancel()

	resp, err := client.Chat(ctx, nim.ChatRequest{
		Model: "meta/llama-3.1-8b-instruct", // example id — verify against the catalog
		Messages: []nim.Message{
			{Role: "system", Content: "You are a terse assistant."},
			{Role: "user", Content: "Name three moons of Saturn."},
		},
		Temperature: 0.2,
		MaxTokens:   256,
	})
	if err != nil {
		log.Fatal(err)
	}

	fmt.Println(resp.Choices[0].Message.Content)
	fmt.Printf("tokens: prompt=%d completion=%d total=%d\n",
		resp.Usage.PromptTokens, resp.Usage.CompletionTokens, resp.Usage.TotalTokens)
}
```

Note the two-layer timeout: the `http.Client.Timeout` is a coarse backstop for the whole exchange, while `context.WithTimeout` is the per-call deadline you actually control. Because we used `http.NewRequestWithContext`, cancelling the context — a deadline, or a user closing a connection — tears down the in-flight request immediately instead of leaking it.

---

## Streaming with SSE

For a chat UI you want tokens as they arrive, not a 20-second wait for the whole paragraph. Set `stream: true` and NIM answers with **Server-Sent Events**: a stream of lines, each data line prefixed with `data: `, carrying one JSON chunk whose `choices[].delta.content` holds the next slice of text. The stream ends with a literal `data: [DONE]` sentinel.

```go
package nim

import (
	"bufio"
	"context"
	"encoding/json"
	"fmt"
	"net/http"
	"strings"
)

// ChatStream sends a streaming request and calls onDelta for each text chunk
// as it arrives. It returns once the server sends [DONE] or the stream ends.
func (c *Client) ChatStream(ctx context.Context, req ChatRequest, onDelta func(string)) error {
	req.Stream = true

	body, err := json.Marshal(req)
	if err != nil {
		return fmt.Errorf("marshal request: %w", err)
	}

	url := c.baseURL + "/chat/completions"
	httpReq, err := http.NewRequestWithContext(ctx, http.MethodPost, url, strings.NewReader(string(body)))
	if err != nil {
		return fmt.Errorf("build request: %w", err)
	}
	httpReq.Header.Set("Content-Type", "application/json")
	httpReq.Header.Set("Accept", "text/event-stream")
	if c.apiKey != "" {
		httpReq.Header.Set("Authorization", "Bearer "+c.apiKey)
	}

	resp, err := c.http.Do(httpReq)
	if err != nil {
		return fmt.Errorf("do request: %w", err)
	}
	defer resp.Body.Close()

	if resp.StatusCode != http.StatusOK {
		return statusError(resp)
	}

	scanner := bufio.NewScanner(resp.Body)
	// Raise the line cap: a single SSE chunk can exceed the 64KB default.
	scanner.Buffer(make([]byte, 0, 64<<10), 1<<20)

	for scanner.Scan() {
		line := scanner.Text()
		if line == "" {
			continue // SSE separates events with blank lines
		}
		if !strings.HasPrefix(line, "data: ") {
			continue // ignore comments and other SSE fields
		}
		payload := strings.TrimPrefix(line, "data: ")

		if payload == "[DONE]" {
			return nil // terminal sentinel — NOT JSON, must be caught first
		}

		var chunk ChatResponse
		if err := json.Unmarshal([]byte(payload), &chunk); err != nil {
			return fmt.Errorf("decode chunk: %w", err)
		}
		if len(chunk.Choices) > 0 {
			if text := chunk.Choices[0].Delta.Content; text != "" {
				onDelta(text)
			}
		}
	}

	if err := scanner.Err(); err != nil {
		return fmt.Errorf("read stream: %w", err)
	}
	return nil
}
```

Driving it prints the answer token by token:

```go
err = client.ChatStream(ctx, nim.ChatRequest{
	Model: "meta/llama-3.1-8b-instruct",
	Messages: []nim.Message{
		{Role: "user", Content: "Write a haiku about garbage collection."},
	},
	MaxTokens: 128,
}, func(delta string) {
	fmt.Print(delta) // append to stdout as chunks land
})
if err != nil {
	log.Fatal(err)
}
fmt.Println()
```

**The gotcha:** `[DONE]` is **not JSON**. If you feed it straight into `json.Unmarshal` it fails, and if your error handling aborts the stream on the first unmarshal error you'll turn every clean finish into a spurious failure. Special-case the sentinel *before* you attempt to decode.

**The gotcha:** `bufio.Scanner` caps a single token (line) at **64KB by default** and returns `bufio.ErrTooLong` past that. A long SSE chunk — a big code block, a verbose tool call — can blow through 64KB and silently truncate your stream unless you raise the limit with `scanner.Buffer(...)`. And always check `scanner.Err()` after the loop: `Scan()` returning `false` means *either* clean EOF *or* an error, and only `scanner.Err()` tells you which.

---

## The portability payoff

Everything above targeted `https://integrate.api.nvidia.com/v1`. Now suppose you deploy a NIM container on your own GPU host. It exposes the **same paths** — `POST /v1/chat/completions`, the same body, the same SSE stream — on your host and port. Moving between them is a single constructor argument:

```go
// Hosted API Catalog:
client, _ := nim.New()

// Self-hosted NIM on your network (no key required if network-scoped):
client := nim.NewWithBaseURL("http://nim.internal:8000/v1", "")
```

Nothing else changes. The structs, the streaming parser, the error handling, the token accounting — all identical, because both endpoints implement the same OpenAI-compatible contract. That is the quiet advantage of NIM not having a bespoke Go SDK: there's no vendor abstraction to unlearn when you move from a hosted trial to production on your own hardware. You wrote plain HTTP, and plain HTTP travels.

| Concern | Hosted catalog | Self-hosted NIM |
|---|---|---|
| Base URL | `https://integrate.api.nvidia.com/v1` | `http://your-host:port/v1` |
| Auth | `Authorization: Bearer nvapi-...` | often none (network-scoped) |
| Paths | `/chat/completions` | `/chat/completions` (identical) |
| Body & response shape | OpenAI-compatible | OpenAI-compatible (identical) |
| Go client code | same | same |

---

## Key takeaways

- **No Go SDK is a feature here.** NIM speaks an OpenAI-compatible REST API, so `net/http` + `encoding/json` is the whole client — one that works unchanged against the hosted catalog and a self-hosted container.
- **The base URL owns `/v1`; you append `/chat/completions`.** Botch the join and you get a bare `404`. Store the base with `/v1` and let the client add the path.
- **Check the status before the body, and surface the provider's error text.** A `429` means back off; a `400` usually explains itself in the JSON error body you'd otherwise throw away.
- **Streaming is SSE, and `[DONE]` is not JSON.** Strip the `data: ` prefix, catch the sentinel before decoding, and raise `bufio.Scanner`'s 64KB buffer so long chunks don't truncate — then check `scanner.Err()`.
- **Keep the key in the environment.** The hosted catalog needs `nvapi-...` as a Bearer token; a network-scoped self-hosted NIM may need no key at all, so let the client tolerate an empty one.

---

## Further reading

- [NVIDIA NIM for LLMs — API reference](https://docs.nvidia.com/nim/large-language-models/latest/api-reference.html) — the chat-completions endpoint, request/response fields, and streaming behavior.
- [build.nvidia.com](https://build.nvidia.com) — the API Catalog: current model ids, and where you generate an `nvapi-...` key.
- [Go `net/http` package](https://pkg.go.dev/net/http) — `Client`, `NewRequestWithContext`, and connection reuse.
- [Go `encoding/json` package](https://pkg.go.dev/encoding/json) — `Marshal`, `Unmarshal`, and `Decoder`.
- [Go `bufio` package](https://pkg.go.dev/bufio) — `Scanner`, its default token limit, and `Buffer`.
