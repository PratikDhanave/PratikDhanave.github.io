# Production on the NVIDIA Stack

*Running an NVIDIA-stack LLM system in production from a Go engineer's seat — the hosted-versus-self-hosted decision, reliability with timeouts and retries and fallback, cost and throughput, observability with Prometheus, security, and a checklist to ship against.*

---

The previous seven posts built a working system: a Go client calling NIM ([post 2](/blog/posts/nvidia-go-02-calling-nim-from-go.html)), tool calling ([post 3](/blog/posts/nvidia-go-03-tool-calling.html)), NeMo Retriever embeddings and reranking ([post 4](/blog/posts/nvidia-go-04-embeddings-and-reranking.html)), RAG ([post 5](/blog/posts/nvidia-go-05-rag-on-the-nvidia-stack.html)), NeMo Guardrails at the HTTP boundary ([post 6](/blog/posts/nvidia-go-06-guardrails-with-nemo-guardrails.html)), and a self-hosted NIM optimized with TensorRT-LLM ([post 7](/blog/posts/nvidia-go-07-self-hosting-and-optimization.html)). Every piece worked on a laptop. Production is a different question: what happens when NVIDIA rate-limits you, when a GPU box falls over at 2am, when a bill arrives, or when someone tries to jailbreak the retrieval layer?

This finale is the operations view. There is still no NVIDIA Go SDK — everything is REST — and that turns out to be an advantage, because the reliability, cost, and observability tooling you need already lives in the Go standard library and a couple of well-known packages.

---

## Hosted or self-hosted — and the case for both

The first decision is where inference runs, and it comes down to three axes.

- **Cost.** The hosted API Catalog is per-token: you pay for what you send and receive, and idle time costs nothing. A self-hosted NIM is **GPU-hours**: you rent or own the hardware and pay whether it's busy or not. Below some sustained request volume the API is cheaper; above it, amortizing a GPU wins.
- **Control.** Self-hosting pins the model version, the container tag, and the TensorRT-LLM engine build ([post 7](/blog/posts/nvidia-go-07-self-hosting-and-optimization.html)). The hosted catalog can rotate models and capacity underneath you.
- **Data.** If prompts carry regulated data that can't leave your network, self-hosting inside a private subnet is the answer. The hosted catalog means your text transits NVIDIA's service.

The honest answer for most teams is **hybrid**: run steady-state traffic on a self-hosted NIM you've sized for your median load, and burst overflow to the API Catalog when you exceed it. Both speak the same OpenAI-compatible contract, so in Go this is just two `Client` values pointed at two base URLs — the same struct from [post 2](/blog/posts/nvidia-go-02-calling-nim-from-go.html):

```go
selfHosted := nim.NewWithBaseURL("http://nim.internal:8000/v1", "") // network-scoped, no key
hosted, _ := nim.New()                                              // API Catalog, nvapi- key
```

**The gotcha:** pin your model id *and* your container tag. Deploying `nim:latest` — or leaving a model id unversioned — means the behavior of your system can change on a `docker pull` you didn't intend, with no code change to blame. Prompts that passed evaluation last week can regress silently. Pin an explicit tag, and treat a version bump as a deploy that goes through the same testing as any other.

---

## Reliability: timeouts, retries, health, and fallback

A production caller assumes every dependency will fail and makes the failure survivable.

### Timeouts and cancellation

This is settled from [post 2](/blog/posts/nvidia-go-02-calling-nim-from-go.html): a coarse `http.Client.Timeout` backstop, and a per-call `context.WithTimeout` you control. Because the request is built with `http.NewRequestWithContext`, cancelling the context tears down the in-flight request instead of leaking a goroutine blocked on a slow generation.

### Retries with exponential backoff and jitter

A `429` (rate limited) or a `5xx` is usually transient. Retry it — but not immediately, and not in lockstep with every other client, or you build a thundering herd. Exponential backoff spaces attempts out; jitter de-synchronizes them.

```go
package retry

import (
	"context"
	"errors"
	"math/rand"
	"time"
)

// Retryable marks an error the caller decided is worth retrying (429, 5xx,
// or a transport error). Non-retryable errors (400, 401, 404) return immediately.
type Retryable struct{ Err error }

func (r Retryable) Error() string { return r.Err.Error() }
func (r Retryable) Unwrap() error { return r.Err }

// Do runs fn up to maxAttempts times, backing off exponentially with full
// jitter between attempts. It stops early on a non-retryable error or a
// cancelled context.
func Do(ctx context.Context, maxAttempts int, base, cap time.Duration, fn func() error) error {
	var lastErr error
	for attempt := 0; attempt < maxAttempts; attempt++ {
		if err := fn(); err != nil {
			var r Retryable
			if !errors.As(err, &r) {
				return err // permanent — don't waste attempts
			}
			lastErr = err

			// backoff = min(cap, base * 2^attempt), then full jitter in [0, backoff].
			backoff := float64(base) * float64(int64(1)<<attempt)
			if backoff > float64(cap) {
				backoff = float64(cap)
			}
			sleep := time.Duration(rand.Int63n(int64(backoff) + 1))

			select {
			case <-time.After(sleep):
			case <-ctx.Done():
				return ctx.Err()
			}
			continue
		}
		return nil
	}
	return lastErr
}
```

The caller decides what's retryable by wrapping the classified error. Building on the `statusError` helper from [post 2](/blog/posts/nvidia-go-02-calling-nim-from-go.html), a `429` or `503` becomes a `retry.Retryable`; a `400` or `401` does not — retrying a malformed request or a bad key just wastes attempts.

### A readiness probe before you route

[Post 7](/blog/posts/nvidia-go-07-self-hosting-and-optimization.html) covered the NIM health endpoints. In production you probe *before* sending real traffic, so a warming or crashed container is removed from rotation rather than absorbing requests it can't serve. NIM exposes a readiness endpoint; a tiny probe suffices:

```go
// Ready reports whether a NIM endpoint is accepting inference requests.
func Ready(ctx context.Context, hc *http.Client, baseURL string) bool {
	// baseURL includes /v1; the health route sits at the server root.
	root := strings.TrimSuffix(baseURL, "/v1")
	req, err := http.NewRequestWithContext(ctx, http.MethodGet, root+"/v1/health/ready", nil)
	if err != nil {
		return false
	}
	resp, err := hc.Do(req)
	if err != nil {
		return false
	}
	defer resp.Body.Close()
	return resp.StatusCode == http.StatusOK
}
```

### Graceful fallback, the Go way

The hybrid model earns its keep here. If the self-hosted NIM is down or unready, fall back to the hosted catalog; if both fail, serve a cached or canned answer rather than a 500. Go's concurrency makes a fan-out-with-fallback clean — race the primary against a delayed backup and take whichever answers first:

```go
type result struct {
	resp *nim.ChatResponse
	err  error
}

// ChatWithFallback tries primary; if it errors or is slow, the hosted backup
// answers instead. The first success wins; the loser's context is cancelled.
func ChatWithFallback(ctx context.Context, primary, backup *nim.Client, req nim.ChatRequest) (*nim.ChatResponse, error) {
	ctx, cancel := context.WithCancel(ctx)
	defer cancel()

	ch := make(chan result, 2)
	go func() {
		resp, err := primary.Chat(ctx, req)
		ch <- result{resp, err}
	}()
	go func() {
		// Give the primary a head start so the backup only spends money on real trouble.
		select {
		case <-time.After(750 * time.Millisecond):
		case <-ctx.Done():
			return
		}
		resp, err := backup.Chat(ctx, req)
		ch <- result{resp, err}
	}()

	var lastErr error
	for i := 0; i < 2; i++ {
		r := <-ch
		if r.err == nil {
			return r.resp, nil // cancel() fires via defer, tearing down the loser
		}
		lastErr = r.err
	}
	return nil, lastErr // both failed — caller serves a cached/canned reply
}
```

**The gotcha:** a fallback path that is never exercised fails exactly when you finally need it. The head-start timer means the backup almost never runs in normal operation, which is precisely why it rots. Test it deliberately: point the primary at a dead address in staging, add a periodic synthetic request that forces the fallback, and alert if the fallback rate is either zero (untested) or high (primary degrading).

---

## Cost and throughput

You cannot manage what you don't count.

### Token accounting

Every non-streaming response carries a `usage` object ([post 2](/blog/posts/nvidia-go-02-calling-nim-from-go.html)) with `prompt_tokens`, `completion_tokens`, and `total_tokens`. On the hosted catalog those tokens *are* the bill, so record them per request and aggregate per tenant or feature. On streaming responses, request usage in the final chunk if the endpoint supports it, or estimate from the emitted text — but prefer the server's count when you have it.

### Client-side rate limiting

Hosted endpoints enforce rate limits. Fire a naive burst of parallel goroutines and you convert throughput into a wall of `429`s. Limit yourself *before* the network with a real token-bucket limiter — `golang.org/x/time/rate` is the standard tool:

```go
import "golang.org/x/time/rate"

// Allow, say, 10 requests/second with a burst of 20.
limiter := rate.NewLimiter(rate.Limit(10), 20)

func (c *RateLimitedClient) Chat(ctx context.Context, req nim.ChatRequest) (*nim.ChatResponse, error) {
	if err := c.limiter.Wait(ctx); err != nil { // blocks until a token frees up or ctx dies
		return nil, err
	}
	return c.inner.Chat(ctx, req)
}
```

`Wait` blocks politely until a token is available or the context is cancelled, so a spike queues instead of hammering the API. Pair the client-side limiter with the retry helper above: the limiter prevents most `429`s, and backoff absorbs the ones that slip through when the server's limit is stricter than your estimate.

### The self-hosted cost model is different

A self-hosted NIM does not bill per token — it bills in **GPU-hours**, whether the card is busy or idle. That inverts the optimization target. On the hosted catalog you minimize tokens; self-hosted, you maximize *utilization* so the fixed GPU cost is spread across the most requests. Batching (which TensorRT-LLM and Triton do for you — [post 7](/blog/posts/nvidia-go-07-self-hosting-and-optimization.html)) is what turns a half-idle GPU into a saturated one.

**The gotcha:** an idle self-hosted GPU is pure loss, and a saturated one drops latency as requests queue. There is a real sweet spot between them, and you find it with the Prometheus metrics below — not by guessing. Capacity-plan against measured queue depth and utilization, and autoscale (or shift burst traffic to the hosted catalog) before the queue turns into timeouts.

---

## Observability

You want three things visible: what the server is doing, what your Go service is doing, and where a single request spent its time.

### Scrape the server's Prometheus metrics

Self-hosted NIM and Triton both expose a Prometheus metrics endpoint. Triton publishes it on port `8002` at `/metrics`; NIM surfaces inference metrics the same way. Point a Prometheus scraper at it and you get GPU utilization, request latency histograms, and — critically for the cost model — inference queue depth. Those are the numbers that tell you whether to scale up (queue growing) or down (GPU idle).

### Emit your own metrics and logs from Go

The server metrics stop at the model. Everything around it — retrieval, reranking, guardrails, retries, fallback — lives in your Go process, and only you can measure it. Use structured logging (`log/slog` is in the standard library) and the Prometheus Go client:

```go
import (
	"log/slog"
	"github.com/prometheus/client_golang/prometheus"
)

var latency = prometheus.NewHistogramVec(prometheus.HistogramOpts{
	Name:    "llm_request_seconds",
	Help:    "End-to-end LLM request latency.",
	Buckets: prometheus.DefBuckets,
}, []string{"route", "outcome"})

func (s *Service) handle(ctx context.Context, req nim.ChatRequest) (*nim.ChatResponse, error) {
	start := time.Now()
	resp, err := s.chat.Chat(ctx, req)
	outcome := "ok"
	if err != nil {
		outcome = "error"
	}
	latency.WithLabelValues("chat", outcome).Observe(time.Since(start).Seconds())

	logger := slog.With("route", "chat", "model", req.Model)
	if err != nil {
		logger.Error("chat failed", "err", err, "latency_ms", time.Since(start).Milliseconds())
		return nil, err
	}
	logger.Info("chat ok",
		"latency_ms", time.Since(start).Milliseconds(),
		"prompt_tokens", resp.Usage.PromptTokens,
		"completion_tokens", resp.Usage.CompletionTokens,
	)
	return resp, nil
}
```

A histogram gives you latency percentiles (p50/p95/p99) rather than a misleading average, and the token fields on each log line reconcile against the bill.

### Trace a request across the stack

A RAG answer is a pipeline: embed the query → retrieve → rerank → guardrails → generate. When it's slow, you need to know *which* hop. Propagate a request id (or an OpenTelemetry trace) through the `context.Context` and stamp it on every log line and span, so one slow reranker call is visible instead of hidden inside an aggregate latency number.

---

## Security

Three surfaces need attention, and RAG plus tools plus guardrails widened all of them.

- **Keys belong in a secret manager, not source.** Two different keys are in play: the `nvapi-` key for the hosted API Catalog, and the **NGC API key** used to pull NIM containers and model artifacts from NVIDIA's registry ([post 7](/blog/posts/nvidia-go-07-self-hosting-and-optimization.html)). Both are credentials; both go in a secret store (Vault, cloud secret manager, Kubernetes secrets) and reach the process as environment variables at runtime — never committed, never baked into an image layer.
- **The injection surface grew.** Retrieval ([post 5](/blog/posts/nvidia-go-05-rag-on-the-nvidia-stack.html)) means untrusted document text now flows into the prompt, and tools ([post 3](/blog/posts/nvidia-go-03-tool-calling.html)) mean the model can trigger actions. Prompt injection hidden in a retrieved passage can try to hijack tool use. NeMo Guardrails at the boundary ([post 6](/blog/posts/nvidia-go-06-guardrails-with-nemo-guardrails.html)) is your input/output filter, but keep defense in depth: validate tool arguments in Go before executing, and never let the model's output alone authorize a side effect.
- **Network-scope the self-hosted endpoint.** A NIM with no API key is fine *only* because it's unreachable from outside a private subnet. Put it behind a firewall or service mesh, restrict ingress to your application's identity, and don't expose port 8000 to the internet on the assumption that "nobody knows the address."

---

## Production checklist

| Area | Ship-blocking item |
|---|---|
| Versioning | Model id and container tag pinned; no `latest`. |
| Timeouts | Per-call `context.WithTimeout` on every request; `http.Client.Timeout` backstop. |
| Retries | Backoff + full jitter on 429/5xx only; no retry on 4xx. |
| Rate limiting | Client-side `x/time/rate` limiter sized under the endpoint's published limit. |
| Health | Readiness probe gates routing; unready instances removed from rotation. |
| Fallback | Hybrid fallback path exists *and* is exercised by a synthetic test. |
| Cost | `usage` tokens logged per request; self-hosted GPU utilization tracked. |
| Metrics | Latency percentiles, error rate, tokens emitted; Prometheus scrape of NIM/Triton. |
| Tracing | Request id propagated through embed → retrieve → rerank → guardrails → generate. |
| Secrets | `nvapi-` and NGC keys in a secret manager; not in source or image layers. |
| Guardrails | Input/output filtering live; tool arguments validated in Go before execution. |
| Network | Self-hosted endpoint firewalled to the app's identity, not public. |

---

## The series arc

Eight posts, one throughline. We opened with a hosted call to the API Catalog, gave the model tools, added retrieval and reranking with NeMo Retriever, assembled those into RAG, wrapped the whole thing in NeMo Guardrails, moved it onto self-hosted NIM and optimized it with TensorRT-LLM, and now hardened it for production. The remarkable part is how little the Go changed across all of that. Because NIM speaks an **OpenAI-compatible REST surface** — the same paths, the same request and response shapes, hosted or self-hosted — the client written in [post 2](/blog/posts/nvidia-go-02-calling-nim-from-go.html) survived every step. No Go SDK meant no vendor abstraction to relearn: `net/http`, `encoding/json`, `context`, and a couple of standard packages carried a laptop demo all the way to a production system.

---

## Key takeaways

- **Hosted is per-token, self-hosted is per-GPU-hour.** The crossover is a volume question; hybrid — steady on self-hosted, burst to hosted — gets both, and in Go it's two base URLs.
- **Assume failure and make it survivable.** Context deadlines, backoff-with-jitter retries on 429/5xx only, a readiness probe before routing, and a *tested* fallback path.
- **Count tokens and watch utilization.** Hosted cost is in the `usage` field; self-hosted cost is idle-versus-saturated GPU time you read off Prometheus.
- **Observability is server plus service plus trace.** Scrape NIM/Triton metrics, emit your own latency percentiles and token counts, and trace one request across the whole pipeline.
- **Security widened with RAG, tools, and guardrails.** Keys in a secret manager, injection defense in depth, and a network-scoped self-hosted endpoint.
- **The OpenAI-compatible surface kept the Go stable.** One HTTP client, eight posts, laptop to production.

---

## Further reading

- [NVIDIA NIM for LLMs — observability](https://docs.nvidia.com/nim/large-language-models/latest/observability.html) — the Prometheus metrics NIM exposes and how to scrape them.
- [Triton Inference Server — metrics](https://docs.nvidia.com/deeplearning/triton-inference-server/user-guide/docs/user_guide/metrics.html) — GPU utilization, latency, and queue-depth metrics on the metrics port.
- [NVIDIA NIM for LLMs — configuration](https://docs.nvidia.com/nim/large-language-models/latest/configuration.html) — the environment variables and `NGC_API_KEY` used to run and pull a NIM.
- [`golang.org/x/time/rate`](https://pkg.go.dev/golang.org/x/time/rate) — the token-bucket limiter for client-side rate limiting.
- [Prometheus Go client](https://pkg.go.dev/github.com/prometheus/client_golang/prometheus) — histograms and counters for emitting your own service metrics.
- [Go `log/slog` package](https://pkg.go.dev/log/slog) — structured logging in the standard library.
