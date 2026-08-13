# Production AI

*The last post in the series: what changes when the LLM system you built across posts 1-14 has to run for real — reliability, security, cost, observability, evaluation gates, and versioning, from a Go engineer's seat, with code where it earns its place.*

---

Across this series we built the whole stack from scratch in Go: a first raw model call (post 4), structured output and streaming (post 5), disciplined prompting (post 6), embeddings and a hand-rolled vector search (posts 7-8), retrieval-augmented generation (posts 9-10), a tool-using agent with memory and planning (posts 11-12), an evaluation harness (post 13), and inference optimization (post 14). Every one of those posts ended with something that *worked on my machine*.

Production is a different discipline. The model is now a remote dependency you don't control, invoked by real users, spending real money, over an untrusted network, with untrusted input flowing through your prompts. This post is about the concerns that only show up once the system is live — and where Go's standard library already gives you the tools to handle them. Nothing here is exotic; it's the same reliability engineering you'd apply to any network service, plus a few things that are specific to LLMs.

---

## 1. Reliability: the model call will fail

Post 4 called the model with a plain `context.Context`. In production that context is your first line of defense. A model endpoint is a network hop that can hang, rate-limit you, or return a 500 mid-stream. If you don't bound it, one slow upstream call ties up a goroutine, then a request, then your whole pool.

Every model call gets a deadline, and that deadline propagates:

```go
ctx, cancel := context.WithTimeout(r.Context(), 30*time.Second)
defer cancel()

resp, err := client.Complete(ctx, req)
```

Because you pass `r.Context()` in, a client that hangs up cancels the upstream model call too — no work continues for a user who has already left. This is the same `context` plumbing from post 4, now doing load-bearing work.

### Retries with backoff and jitter

Transient failures — a 429 rate-limit, a 503, a dropped connection — are not bugs; they are the normal weather of a shared API. The fix is to retry, but naively retrying immediately just amplifies the storm. You want *exponential backoff* (wait longer each attempt) with *jitter* (randomize the wait so a thousand clients don't retry in lockstep).

```go
// retryable reports whether an error is worth trying again.
func retryable(err error, status int) bool {
    if errors.Is(err, context.DeadlineExceeded) || errors.Is(err, context.Canceled) {
        return false // caller gave up or timed out; don't burn attempts
    }
    return status == 429 || status == 503 || (status >= 500 && status < 600) || err != nil
}

// withRetry retries fn up to maxAttempts with exponential backoff + jitter.
func withRetry(ctx context.Context, maxAttempts int, fn func() (int, error)) error {
    var lastErr error
    for attempt := 0; attempt < maxAttempts; attempt++ {
        status, err := fn()
        if err == nil && status < 400 {
            return nil
        }
        lastErr = err
        if !retryable(err, status) {
            return err
        }
        // 0.5s, 1s, 2s, 4s ... capped, then a random 0-1x jitter on top.
        base := time.Duration(1<<attempt) * 500 * time.Millisecond
        if base > 30*time.Second {
            base = 30 * time.Second
        }
        wait := base/2 + time.Duration(rand.Int63n(int64(base/2)))
        select {
        case <-time.After(wait):
        case <-ctx.Done():
            return ctx.Err()
        }
    }
    return fmt.Errorf("gave up after %d attempts: %w", maxAttempts, lastErr)
}
```

Two details matter more than the arithmetic. First, the wait respects the context — if the caller's deadline fires while you're sleeping, you abandon the retry instead of blocking. Second, you only retry things that *can* succeed on a second try: a 429 or 503, yes; a 400 (malformed request) or a context cancellation, never. Retrying a deterministic failure just wastes the user's time and your budget. If the provider sends a `Retry-After` header, honor it over your own backoff.

**The gotcha:** without token and cost observability (section 3), a retry loop wrapped around an agent loop (post 11) is a compounding hazard. An agent that retries a failing tool call, inside a planning loop that retries the whole step, inside your HTTP handler that retries the request, can multiply one user action into dozens of billed model calls. Cap attempts at *every* layer and count them.

### Circuit breakers and graceful degradation

Retries handle a blip. They make a sustained outage *worse* — every request piles more load onto a provider that's already down. A circuit breaker fixes that: after N consecutive failures, "open" the circuit and fail fast for a cooling-off window instead of trying at all, then let a single probe request test whether the provider has recovered.

When the circuit is open, you don't have to return an error to the user. You *degrade gracefully*:

```go
answer, err := breaker.Do(ctx, func() (string, error) {
    return callPrimaryModel(ctx, prompt)
})
if err != nil {
    // Fallbacks, in order of preference:
    if cached, ok := cache.Get(promptKey); ok {
        return cached, nil            // 1. a recent cached answer
    }
    if alt, err2 := callFallbackModel(ctx, prompt); err2 == nil {
        return alt, nil               // 2. a smaller/alternate model
    }
    return cannedResponse, nil        // 3. an honest "try again shortly"
}
```

A fallback to a smaller model, a cached answer, or an honest canned message keeps the product usable when the primary provider is having a bad day. The worst outcome is a spinner that never resolves.

---

## 2. Security and safety: the prompt is an attack surface

The single biggest mindset shift for production LLMs is this: **anything that reaches the model as text is untrusted input, including text your own system retrieved.**

### Prompt injection, widened by RAG and tools

Post 6 introduced prompt injection — a user writing "ignore your instructions and…". In a bare chatbot the injection can only come from the user. The moment you add RAG (post 9) or tools (post 11), the attack surface widens dramatically: a retrieved document, a web page an agent fetched, a row in a database, or a tool's output can *all* carry instructions the model will happily follow. An attacker who can get a poisoned paragraph into your knowledge base has, in effect, gotten text into your system prompt.

**The gotcha:** treat retrieved content as untrusted data, never as instructions. Keep it structurally separated from your directives — put documents inside a clearly delimited block and tell the model, in the trusted system prompt, that everything in that block is reference material to be quoted, not commands to be obeyed. Structural separation is not a cryptographic boundary; it raises the cost of an attack, it doesn't eliminate it. The durable defenses live *outside* the prompt.

### Least privilege for tools

Post 11's agent could call functions. In production, assume the model can be talked into calling any tool with any arguments — because a good enough injection will. So the security boundary cannot be the prompt; it has to be the tool implementation itself.

```go
func (t *DeleteRecordTool) Call(ctx context.Context, args Args) (string, error) {
    user := UserFromContext(ctx)
    if !user.Can("record:delete", args.RecordID) {
        return "", ErrForbidden // the tool enforces authz, not the prompt
    }
    // scoped, audited, reversible where possible
    return t.store.SoftDelete(ctx, args.RecordID, user.ID)
}
```

A tool an agent can call should have exactly the authority a well-behaved call needs and no more: scoped to the current user, read-only where read-only will do, rate-limited, and audit-logged. If a tool can wire money or delete data, put a human approval step in front of it. The rule is the same one from operating-system design — least privilege — applied to model-invoked functions.

### Output validation, PII, and secrets

Three more layers that are cheap to add and expensive to omit:

- **Validate output before it acts.** If the model returns JSON (post 5), unmarshal it into a strict struct and reject anything that doesn't fit *before* you act on it. If it returns SQL or code, never execute it directly against production. The model's output is a suggestion, not a command.
- **Handle PII deliberately.** Decide what personal data is allowed to leave your boundary for the provider, redact what isn't, and know your provider's data-retention terms. Moderation and safety classifiers — the provider's, or your own — belong as a *layer* around the model on both input and output, not as a line in the prompt.
- **Keep secrets out of code.** API keys come from the environment or a secret manager, never a committed file. This is table stakes, and it's a one-liner in Go:

```go
apiKey := os.Getenv("MODEL_API_KEY")
if apiKey == "" {
    log.Fatal("MODEL_API_KEY not set") // fail loudly at startup, not per request
}
```

---

## 3. Cost control and observability: you can't fix what you can't see

An LLM system fails differently from a normal service. It rarely throws — it returns a confident, wrong, or expensive answer with a 200 status. Your metrics dashboard will look green while users are unhappy and the bill climbs. Observability for AI has to capture *what the model did*, not just *whether the call returned*.

### Track tokens and cost per request

Post 3 taught that tokens are the unit of both latency and billing, and post 14 optimized around them. In production you turn that into a number attached to every request. The provider returns token counts in its response; capture them, price them, and log them:

```go
type Usage struct {
    PromptTokens     int
    CompletionTokens int
}

func costUSD(u Usage, inPer1M, outPer1M float64) float64 {
    return float64(u.PromptTokens)/1e6*inPer1M +
        float64(u.CompletionTokens)/1e6*outPer1M
}
```

Use your provider's published per-token prices for `inPer1M`/`outPer1M` — don't hard-code a number that will drift. Aggregate cost per user, per feature, and per endpoint so a runaway agent loop shows up as a line on a graph the day it starts, not as a shock on the invoice at month's end.

### Structured logging and tracing

Log every model interaction as structured data — Go's standard `log/slog` is enough — so you can actually query it later:

```go
slog.InfoContext(ctx, "model_call",
    "request_id", reqID,
    "model", modelVersion,   // the pinned version, not "latest" (section 5)
    "prompt_tokens", usage.PromptTokens,
    "completion_tokens", usage.CompletionTokens,
    "cost_usd", costUSD(usage, inPrice, outPrice),
    "latency_ms", time.Since(start).Milliseconds(),
    "retrieved_doc_ids", docIDs, // which chunks RAG fed the model
    "tool_calls", toolNames,     // which tools the agent invoked
)
```

The goal is to **log enough to debug a bad answer**. When a user reports a wrong reply, you want to reconstruct exactly what happened: which prompt, which retrieved chunks, which tool calls, which model version, and what came back. A single `request_id` threaded through the context lets you trace one request across the RAG lookup, each agent step, and every model call — the LLM equivalent of a distributed trace. (Be careful logging raw prompts and responses when they can contain PII; redact or hash where policy requires.)

### Metrics, dashboards, and alerts

Beyond logs, expose aggregate metrics: latency percentiles (p50/p95/p99 — averages hide the tail that hurts users), error rate, retry rate, circuit-breaker state, and cost per hour. Wire alerts on the ones that signal trouble: cost spiking, error rate climbing, p99 latency past your SLO. OpenTelemetry has a mature Go SDK if you want traces and metrics to flow into standard tooling rather than rolling your own.

---

## 4. Evaluation in CI/CD: catch regressions before users do

Post 13 built an evaluation set — inputs paired with graded expectations. In production that eval set becomes a *gate*. Before any change to a prompt, a model, a retrieval parameter, or the code around them ships, run the eval suite and block the deploy if quality drops below threshold. In Go this is just a test that runs your graders:

```go
func TestAnswerQualityGate(t *testing.T) {
    results := runEvalSuite(context.Background(), evalSet)
    if results.PassRate < 0.90 {
        t.Fatalf("quality gate failed: pass rate %.2f < 0.90", results.PassRate)
    }
}
```

**The gotcha:** an eval gate in CI is the only thing that reliably catches quality regressions *before* users do. Unit tests confirm the code runs; they say nothing about whether the answers got worse. A one-line prompt tweak that fixes one case and quietly breaks ten will pass every conventional test and fail your users — unless the eval suite is standing in the deploy path.

Two techniques carry this into production, where the eval set can't cover everything:

- **Canary and shadow deploys.** Route a small slice of live traffic to the new version (canary) and watch its metrics before promoting. Or run the new version *in shadow* — it processes real requests but its output isn't served, only compared — so you see how a change behaves on real traffic with zero user risk.
- **Online evaluation and feedback signals.** Sample production traffic and grade it continuously (an LLM-as-judge from post 13, or human review). Capture user feedback — thumbs up/down, edits, retries, abandonment — as a quality signal. This is how you detect *drift*: the slow degradation that offline evals never see because the world changed, not your code.

---

## 5. Versioning: prompts, models, and data are all artifacts

The subtlest production failure is the one where you changed *nothing* and the system got worse. It happens because three of your most important inputs are not in your codebase by default.

**Pin your model version.** Providers ship a moving `latest` alias and periodically point it at a new snapshot. If you call `latest`, your behavior changes the day they update it — new refusals, different formatting, a shifted tone — with no deploy on your side and no line in your changelog. Pin an explicit, dated model version, treat an upgrade as a deliberate change, and run it through the eval gate before you adopt it.

**The gotcha:** pinning the model version is not optional hygiene — it's the difference between a system you can reason about and one that regresses overnight. "Latest" silently changing under you can tank your eval scores while every one of your tests still passes, because the thing that changed was never in your repo.

Version the other two artifacts the same way:

- **Prompts** are code. Keep them in version control, review changes, and log which prompt version produced each response so you can correlate a quality dip with a specific edit.
- **Datasets** — your RAG corpus and your eval set — are versioned artifacts too. When retrieval quality shifts, you want to know whether the corpus changed. When eval scores move, you want to know it was a real regression and not a quietly edited test set.

---

## 6. A production checklist

| Concern | Minimum bar for production | Series link |
|---|---|---|
| Timeouts | Every model call bounded by a `context` deadline that propagates | Post 4 |
| Retries | Backoff + jitter on 429/5xx only; capped at every layer | This post |
| Degradation | Circuit breaker + fallback model / cache / canned reply | This post |
| Injection | Retrieved & tool content treated as untrusted; structurally separated | Posts 6, 9 |
| Tool authority | Least privilege, scoped, audited; human gate on dangerous actions | Post 11 |
| Output safety | Strict validation before acting; moderation as a layer; PII policy | Post 5 |
| Secrets | Keys from env / secret manager; fail loudly if missing | This post |
| Cost | Token + USD tracked per request, per user, per feature | Posts 3, 14 |
| Observability | Structured logs + request-id tracing across RAG → agent → model | This post |
| Metrics | Latency percentiles, error/retry rate, cost; alerts on each | This post |
| Eval gate | Regression gate in CI blocks deploys below threshold | Post 13 |
| Rollout | Canary or shadow before full promotion | This post |
| Online eval | Sampled production grading + user feedback for drift | Post 13 |
| Versioning | Model pinned; prompts and datasets under version control | This post |

Treat it as a starting point, not a compliance form — the right bar depends on what your system can do if it misbehaves. A summarizer needs less than an agent that can move money.

---

## Key takeaways

- **The model is an unreliable remote dependency.** Bound it with a context deadline, retry only what can succeed with backoff and jitter, and degrade gracefully behind a circuit breaker instead of hanging.
- **Every text that reaches the model is untrusted — including your own retrieved documents.** RAG and tools widen the injection surface; the real defenses are least-privilege tools, output validation, and moderation layers, not clever prompt wording.
- **Observe what the model did, not just whether it returned.** Track tokens and cost per request, log enough to reconstruct any bad answer, and trace one request across RAG and agent steps.
- **An eval gate in CI is your regression seatbelt.** It's the only check that catches quality dropping before users report it; pair it with canary/shadow rollout and online eval for drift.
- **Pin your model version and version your prompts and data.** "Latest" changes under you; the system you can't reproduce is the system you can't debug.

Fifteen posts ago we made a single call to a model and printed the reply. From that one call we added structure, retrieval, memory, planning, evaluation, and optimization — and in this post, the scaffolding that lets all of it survive contact with real users, real money, and real adversaries. That scaffolding is not glamorous, and almost none of it is AI-specific: it's the ordinary reliability, security, and observability engineering that Go was built for, pointed at a new kind of dependency.

Where to go next depends on what you want to build. Take the from-scratch agent from posts 11-12 and give it the production treatment here. Swap the hand-rolled vector search of post 8 for a real vector database and re-run your eval gate to prove the answers held. Or go deeper on any one pillar — evaluation and observability, in particular, are entire disciplines. The point of building each piece from scratch was never that you'd ship the hand-rolled version; it was that you'd understand the managed one well enough to run it in production without fear. That understanding is the whole series. Now go ship something.

---

## Further reading

- [OWASP Top 10 for LLM Applications](https://owasp.org/www-project-top-10-for-large-language-model-applications/) — the canonical catalog of LLM-specific risks, including prompt injection, insecure output handling, and excessive agency.
- [OWASP LLM Prompt Injection Prevention Cheat Sheet](https://cheatsheetseries.owasp.org/cheatsheets/LLM_Prompt_Injection_Prevention_Cheat_Sheet.html) — concrete mitigations for the injection surface that RAG and tools widen.
- [Go `context` package documentation](https://pkg.go.dev/context) — deadlines, cancellation, and propagation, the foundation of reliable model calls.
- [Go `log/slog` package documentation](https://pkg.go.dev/log/slog) — the standard library's structured logging, enough for production LLM observability.
- [OpenTelemetry Go SDK](https://opentelemetry.io/docs/languages/go/) — distributed tracing and metrics for threading a request through RAG and agent steps.
- [Google SRE Book — Handling Overload](https://sre.google/sre-book/handling-overload/) — retries, load shedding, and graceful degradation, the reliability patterns behind this post.
