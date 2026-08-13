# Inference Optimization

*Making an LLM system faster and cheaper without touching the weights — the levers an application engineer actually controls, from streaming and caching to token trimming, model routing, and Go's real superpower: concurrency with a rate limiter.*

---

"Inference optimization" sounds like something that happens on a GPU cluster you'll never see. Some of it does — quantization, distillation, better serving kernels — and we'll touch that at the end. But most of the speed and cost you can win in a real product comes from decisions in *your* code: what you send, how often you send it, which model you send it to, and how many calls you run at once. None of it requires retraining anything.

This post is about those levers, each with a concrete Go angle. We've built the pieces already — a chat client with streaming (post 4), token accounting (post 3), embeddings and cosine similarity (post 7), a from-scratch agent (posts 11–12). Inference optimization is mostly applying those pieces with discipline. The first rule, though, is the one everyone skips: **measure before you change anything.** You can't optimize a number you aren't looking at.

---

## Latency is two numbers, not one

When someone says a model is "slow," ask *which* slow. There are two distinct measurements, and they trade off against each other:

- **TTFT (time to first token)** — how long from sending the request until the first token comes back. This is what a user *feels* as responsiveness.
- **Total latency / throughput** — how long until the whole response is done, and how many tokens per second stream in between.

A model can have great TTFT and mediocre throughput, or vice versa. A short answer with a slow start feels laggy; a long answer that starts instantly and streams smoothly feels fast even if it takes longer overall. This is exactly why **streaming (post 4) is the single biggest perceived-latency win you can ship without changing a model.** The total time to generate 800 tokens is identical whether you stream or not — but streaming turns one long silence into a first word in a few hundred milliseconds and a steady flow after. Perceived latency collapses.

To optimize either number you have to measure both. With a streaming client, TTFT is the time to the first chunk and total is the time to the last:

```go
func Measure(ctx context.Context, client StreamingClient, req ChatRequest) (ttft, total time.Duration, err error) {
	start := time.Now()
	stream, err := client.Stream(ctx, req)
	if err != nil {
		return 0, 0, err
	}
	defer stream.Close()

	first := true
	for stream.Next() {
		if first {
			ttft = time.Since(start) // first token has arrived
			first = false
		}
		_ = stream.Chunk() // consume the token text
	}
	total = time.Since(start)
	return ttft, total, stream.Err()
}
```

Run that across a representative sample of prompts, not one lucky call. Record the distribution — the p50 and the p95 — because tail latency is what users complain about. Once you have those two numbers per route, every optimization below becomes a measurable before/after instead of a guess.

**The gotcha:** the biggest cheap win is almost never a clever micro-optimization — it's a smaller model that still passes your evals (post 13), or a cache hit that skips the call entirely. Engineers love shaving 50ms off serialization while a redundant call to an oversized model sits right next to it costing 2 seconds and ten times the money. Measure first, and spend your effort where the seconds actually are.

---

## Caching: the fastest call is the one you don't make

Every request you can avoid is 100% faster and 100% cheaper than the one you optimize. There are three caching layers worth knowing, in increasing order of cleverness and risk.

### Exact-match response cache

If the same request comes in twice, return the stored answer. "Same" means byte-identical inputs, so the key is a hash of everything that shapes the output — model, and every message.

```go
type ResponseCache struct {
	mu    sync.RWMutex
	store map[string]string
}

func NewResponseCache() *ResponseCache {
	return &ResponseCache{store: make(map[string]string)}
}

func cacheKey(req ChatRequest) string {
	h := sha256.New()
	fmt.Fprintf(h, "model=%s\n", req.Model)
	for _, m := range req.Messages {
		fmt.Fprintf(h, "%s: %s\n", m.Role, m.Content)
	}
	return hex.EncodeToString(h.Sum(nil))
}

func (c *ResponseCache) Get(key string) (string, bool) {
	c.mu.RLock()
	defer c.mu.RUnlock()
	v, ok := c.store[key]
	return v, ok
}

func (c *ResponseCache) Set(key, val string) {
	c.mu.Lock()
	defer c.mu.Unlock()
	c.store[key] = val
}
```

An `sync.RWMutex` guarding a map is fine to start; swap in Redis when you need it to survive restarts or be shared across instances. This wins big on repeated prompts — FAQ-style lookups, retries, the same document summarized twice.

**The gotcha:** caching a non-deterministic model's output is fine *as long as the key captures everything that varies*. If you cache by prompt text alone but vary `temperature`, or inject a changing system prompt or retrieved context, two "identical" prompts can legitimately need different answers — and you'll serve a stale one. Put every input that affects the output into the key, or don't cache that route.

### Semantic cache

Exact match misses "What's your refund policy?" versus "How do I get a refund?" — same intent, different bytes. A *semantic* cache reuses the embeddings and cosine similarity from post 7: embed the incoming query, compare it to embeddings of past queries, and if one is close enough, return that cached answer.

```go
type semanticEntry struct {
	embedding []float32
	answer    string
}

type SemanticCache struct {
	mu        sync.RWMutex
	entries   []semanticEntry
	embed     func(context.Context, string) ([]float32, error)
	threshold float32 // e.g. 0.92 — tune this carefully
}

func (c *SemanticCache) Lookup(ctx context.Context, query string) (string, bool, error) {
	qv, err := c.embed(ctx, query)
	if err != nil {
		return "", false, err
	}
	c.mu.RLock()
	defer c.mu.RUnlock()

	best, bestScore := "", float32(-1)
	for _, e := range c.entries {
		if s := cosine(qv, e.embedding); s > bestScore { // cosine from post 7
			best, bestScore = e.answer, s
		}
	}
	if bestScore >= c.threshold {
		return best, true, nil
	}
	return "", false, nil
}
```

**The gotcha:** a semantic cache trades correctness for speed, and the trade is not free. "How do I *cancel* my subscription?" and "How do I *change* my subscription?" are embedding-neighbors but need opposite answers — a near-miss above the threshold will confidently serve the wrong one. The threshold is a dial between hit rate and wrong answers, and there is no setting that gives you both. Use semantic caching only where a slightly-off answer is recoverable, keep the threshold conservative, and never point it at anything where a wrong hit is dangerous.

### Provider prompt caching

Most hosted providers offer **prompt caching**: if many requests share a long identical prefix — a big system prompt, a fixed few-shot block, a retrieved document — the provider caches the processed prefix so it isn't recomputed every call. Cache *reads* are dramatically cheaper than fresh input tokens (often around a tenth of the price) and lower latency, while the initial cache *write* costs slightly more than a normal call. It's a prefix match, so anything that changes the prefix — a timestamp in the system prompt, a reordered tool list — invalidates it. Structure your prompt with stable content first and the per-request part last. The exact way you enable it (a header, a flag on a content block) differs by provider and SDK, so reach for their docs rather than assume a specific call — but the shape of the win is universal: pay to process the shared prefix once, ride it cheaply for every request after.

---

## Cut the tokens, cut the bill

Tokens are the currency of both cost and latency (post 3): you pay per input token, per output token, and generation time scales with how many tokens the model has to emit. So the most direct optimization is to move fewer of them.

- **Trim the prompt.** Verbose system prompts, redundant instructions, and stale conversation history all cost tokens every single turn. In an agent loop that resends history each call, this compounds — tie it back to the compaction discipline from post 12.
- **Prune few-shot examples.** Five examples rarely beat two well-chosen ones. Drop the ones that aren't earning their tokens.
- **Cap `max_tokens`.** If you need a one-word classification, don't leave room for an essay. A tight output cap bounds both cost and worst-case latency.
- **Ask for less.** "Reply with just the category name" produces fewer output tokens than "explain your reasoning and then give the category." Output tokens are usually the more expensive kind, so shortening the *answer* often matters more than shortening the *prompt*.

None of this touches the model. It's editing, and it's the highest-leverage editing you'll do.

---

## Right-size the model, then route

The costliest habit in LLM engineering is sending every request to the strongest model out of caution. Most requests don't need it.

**Model selection** is the first cut: use the smallest model that passes your eval suite (post 13) for the task. If a small model scores as well as a large one on your actual test cases, the large one is pure waste — more money, more latency, no benefit. Eval is what makes this a decision instead of a gamble.

**Routing** goes further: classify each request and send easy ones to a cheap model, hard ones to a strong one.

```go
type Router struct {
	cheap  Client
	strong Client
}

func (r *Router) Route(ctx context.Context, prompt string) (string, error) {
	client := r.cheap
	if isHard(prompt) {
		client = r.strong
	}
	resp, err := client.Complete(ctx, ChatRequest{
		Messages: []Message{{Role: "user", Content: prompt}},
	})
	if err != nil {
		return "", err
	}
	return resp.Text, nil
}
```

`isHard` can be as simple as a length or keyword heuristic, or as involved as a cheap classifier call. The point is that most traffic flows to the cheap path.

**Cascades** are routing without an up-front decision: try the cheap model first, and escalate only when its answer looks weak. You need a confidence signal — often the cheap model returning a structured result (post 5) with a self-reported confidence field, or a validator that checks the output.

```go
func (r *Router) Cascade(ctx context.Context, prompt string) (string, error) {
	resp, err := r.cheap.Complete(ctx, ChatRequest{
		Messages: []Message{{Role: "user", Content: prompt}},
	})
	if err != nil {
		return "", err
	}
	if confident(resp) {
		return resp.Text, nil // cheap path was enough
	}
	strong, err := r.strong.Complete(ctx, ChatRequest{
		Messages: []Message{{Role: "user", Content: prompt}},
	})
	if err != nil {
		return resp.Text, nil // strong path failed — fall back to the cheap answer
	}
	return strong.Text, nil
}
```

A cascade pays two calls on hard queries but one cheap call on the easy majority. Whether it wins depends on your traffic mix — measure the blended cost against always using the strong model.

| Strategy | When it fits | Cost shape |
|---|---|---|
| Model selection | One task type, uniform difficulty | Flat — smallest model that passes eval |
| Routing | Mixed difficulty, cheap to classify up front | Cheap path for most, strong for the hard slice |
| Cascade | Hard to classify up front, cheap confidence signal | One cheap call usually; two on escalation |

---

## Concurrency: Go's home turf

Here's where Go earns its place in the stack. Model calls are almost entirely I/O-bound waiting on a network round trip — the ideal workload for goroutines. If you have 500 independent prompts to run, running them one at a time is leaving nearly all your throughput on the floor.

But you can't just fire 500 goroutines at a provider. You'll get rate-limited (HTTP 429), and now you've converted a latency problem into an error-handling problem. The right shape is a **bounded worker pool** with a **rate limiter**. Two real packages do the heavy lifting: `golang.org/x/sync/errgroup` bounds concurrency and collects the first error, and `golang.org/x/time/rate` is a token-bucket limiter that paces requests to a rate the provider tolerates.

```go
import (
	"context"

	"golang.org/x/sync/errgroup"
	"golang.org/x/time/rate"
)

// CompleteMany runs prompts concurrently, capped at maxConcurrent in flight
// and rps requests per second.
func CompleteMany(ctx context.Context, client Client, prompts []string, maxConcurrent int, rps float64) ([]string, error) {
	results := make([]string, len(prompts))
	limiter := rate.NewLimiter(rate.Limit(rps), 1)

	g, ctx := errgroup.WithContext(ctx)
	g.SetLimit(maxConcurrent) // at most this many goroutines active at once

	for i, prompt := range prompts {
		i, prompt := i, prompt // capture per iteration (unneeded as of Go 1.22)
		g.Go(func() error {
			if err := limiter.Wait(ctx); err != nil {
				return err // context cancelled while waiting for a token
			}
			resp, err := client.Complete(ctx, ChatRequest{
				Messages: []Message{{Role: "user", Content: prompt}},
			})
			if err != nil {
				return err
			}
			results[i] = resp.Text
			return nil
		})
	}
	if err := g.Wait(); err != nil {
		return nil, err
	}
	return results, nil
}
```

`g.SetLimit(maxConcurrent)` caps how many calls are in flight; `limiter.Wait(ctx)` blocks each goroutine until the bucket has a token, smoothing the request rate. Because `errgroup.WithContext` cancels the shared context on the first error, a failure stops the fleet cleanly instead of letting the rest pile into a wall of 429s. Each goroutine writes to its own index in `results`, so no extra locking is needed — a common Go pattern that beginners often over-guard with a mutex.

**The gotcha:** parallelizing without a rate limiter doesn't speed anything up — it just converts latency into 429s. The provider throttles you, your retries add load, and total wall-clock time can end up *worse* than running serially. The limiter isn't optional garnish; it's the thing that makes concurrency actually pay off. Set the rate below your provider's documented limit and leave headroom for retries.

For large offline jobs where latency doesn't matter — nightly re-summarization, backfilling embeddings — many providers also offer a **batch API**: you submit a file of thousands of requests and collect results within a window (often up to a day) at a steep discount, commonly around half the normal price. It's the opposite trade from the worker pool above: you give up immediacy to buy throughput and savings. Reach for batch APIs when the work isn't time-sensitive, and the concurrent worker pool when it is.

---

## The levers you don't control (but should know)

Server-side, providers run their own optimizations: **quantized** models (weights stored at lower precision for faster, cheaper inference) and **distilled** models (a smaller model trained to imitate a larger one). You don't operate these — but they're often exactly what a provider's "small" or "fast" tier *is*. That's why model selection and routing work: the cheap tier is frequently a quantized or distilled version tuned for speed. Knowing this reframes the choice — picking the cheap model isn't settling for less, it's picking a model someone already optimized for the easy majority of your traffic. Confirm the fit with your evals and move on.

---

## Key takeaways

- **Measure two latencies.** TTFT is what users feel; total latency and throughput are what they wait for. Optimize the one that matters for your UX, and always measure before and after.
- **Streaming is the cheapest perceived-latency win.** It doesn't change total time, but it turns one long silence into an instant first token (post 4).
- **The fastest call is the one you skip.** Exact-match caching is safe and free wins; semantic caching is powerful but trades correctness for speed — keep the threshold conservative; provider prompt caching cuts the cost of a shared prefix.
- **Tokens are the cost and latency driver.** Trim prompts, prune few-shot, cap `max_tokens`, ask for shorter answers (post 3, post 12).
- **Right-size then route.** Use the smallest model that passes eval (post 13); route easy queries cheap and hard ones strong; cascade when confidence is checkable.
- **Concurrency is Go's edge — with a limiter.** A bounded worker pool over `errgroup` plus a `rate` token bucket runs many calls at once without turning latency into 429s. Batch APIs handle the offline bulk at a discount.
- **Measure first, optimize second.** The biggest win is usually a smaller model or a cache hit, not a micro-optimization.

---

## Further reading

- [NVIDIA — Mastering LLM Techniques: Inference Optimization](https://developer.nvidia.com/blog/mastering-llm-techniques-inference-optimization/) — a solid primary on the latency metrics (TTFT, inter-token latency, throughput) this post builds on.
- [Go `golang.org/x/sync/errgroup` package documentation](https://pkg.go.dev/golang.org/x/sync/errgroup) — bounded concurrency with `SetLimit` and first-error propagation.
- [Go `golang.org/x/time/rate` package documentation](https://pkg.go.dev/golang.org/x/time/rate) — the token-bucket limiter used above.
- [Anthropic — Streaming Messages](https://docs.claude.com/en/docs/build-with-claude/streaming) — how token-by-token streaming works over the wire.
- [Anthropic — Prompt caching](https://docs.claude.com/en/docs/build-with-claude/prompt-caching) — a concrete example of the provider prompt-caching feature described above.
- [Anthropic — Message Batches](https://docs.claude.com/en/docs/build-with-claude/batch-processing) — a representative batch API for offline jobs at a discount.
