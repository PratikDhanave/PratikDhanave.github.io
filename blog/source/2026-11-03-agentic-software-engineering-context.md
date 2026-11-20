# Agentic Software Engineering in Go: Context Engineering

*The foundation that makes everything else work*

---

## The Problem: Unconstrained Agent Behavior

An LLM with no constraints generates its statistical baseline — the most probable code given its training distribution. That baseline is almost never your code: it logs with `fmt.Println`, skips the health endpoint, ignores graceful shutdown, and has never heard of your team's conventions, because they weren't in the prompt.

**Context engineering** is the discipline of deliberately designing what the agent knows. The claim this post makes — constrained agents produce operable code, unconstrained agents produce tutorials — is testable, so instead of asserting it, let's run it.

## The Experiment, For Real

Same model (qwen3.6 via Ollama), same system prompt, same request: *"Write a basic HTTP server in Go that listens on port 8080 and returns Hello, World! for the root path."* The only variable: the closed-loop run appends one ADR, formatted exactly as the factory's context engine renders context.

**Open-loop output** (16.7s, 549 tokens) — verbatim, and it compiles:

```go
package main

import (
	"fmt"
	"net/http"
)

func handler(w http.ResponseWriter, r *http.Request) {
	fmt.Fprintf(w, "Hello, World!")
}

func main() {
	http.HandleFunc("/", handler)
	fmt.Println("Server running on :8080")
	if err := http.ListenAndServe(":8080", nil); err != nil {
		fmt.Printf("Server failed to start: %v\n", err)
	}
}
```

Perfectly correct, and operationally useless: `fmt.Println` logging no aggregator can parse, no health endpoint for a load balancer to probe, and a server that dies mid-request on every deploy.

**The ADR** injected for the closed-loop run:

```markdown
# ADR-002: HTTP Service Standards - APPROVED

## The Absolute Constraint
- Services MUST log with log/slog in JSON (slog.NewJSONHandler), never
  fmt.Println or log.Printf
- Services MUST expose GET /health returning 200 and {"status":"ok"} as JSON
- Services MUST shut down gracefully on SIGINT/SIGTERM via
  http.Server.Shutdown with a timeout
- Handlers MUST log method, path, and remote address for every request
```

**Closed-loop output** (59.4s, 3,958 tokens) — excerpted from the verbatim artifact, which also compiles:

```go
logger := slog.New(slog.NewJSONHandler(os.Stdout, nil))
slog.SetDefault(logger)

// Health check endpoint as per ADR-002
mux.HandleFunc("/health", healthHandler)

loggingMiddleware := func(next http.Handler) http.Handler {
	return http.HandlerFunc(func(w http.ResponseWriter, r *http.Request) {
		slog.InfoContext(r.Context(), "Request received",
			"method", r.Method,
			"path", r.URL.Path,
			"remote_addr", r.RemoteAddr,
		)
		next.ServeHTTP(w, r)
	})
}

// ... server started in a goroutine, then:
sigChan := make(chan os.Signal, 1)
signal.Notify(sigChan, syscall.SIGINT, syscall.SIGTERM)
<-sigChan

ctx, cancel := context.WithTimeout(context.Background(), 5*time.Second)
defer cancel()
if err := server.Shutdown(ctx); err != nil { ... }
```

Every constraint satisfied — JSON logging, `/health`, signal-driven graceful shutdown, per-request logging via middleware. The model even wrote `// Health check endpoint as per ADR-002` in its comments: the ADR didn't just constrain the output, it entered the artifact's *reasoning trail*.

Two honest observations the tidy version of this story omits. The closed-loop run took 3.5× longer and 7× the tokens — context buys compliance with latency and budget, which is why the factory caps context per provider rather than shoveling everything in. And one run is a demonstration, not a benchmark; the direction of the effect is unmistakable here, but the magnitude varies run to run.

## The ADR Pattern

ADRs work as agent context because they're already the right shape: a decision, the reasoning, and — the part that does the work — an **Absolute Constraint** section written in MUST/MUST NOT language that survives being pasted into a prompt. Write the constraint section as if a very literal junior engineer will follow it exactly, because that is precisely what will happen.

## The Context Engine

`pkg/context` turns the repository into the agent's working set. Three loaders walk the tree and tag what they find with a priority — ADRs outrank specs, specs outrank code patterns:

```text
$ ./asf context
Loaded 37 context items:

=== docs/ADR-001-Example.md [adr] (priority: 100, ~98 tokens) ===
# ADR-001: Example Decision - APPROVED
...
=== docs/ARCHITECTURE.md [adr] (priority: 100, ~2082 tokens) ===
...
```

That's real output, and it shows a real wart worth learning from: the ADR loader globs all of `docs/*.md`, so `ARCHITECTURE.md` and `API.md` are riding along as priority-100 "ADRs." Harmless here, but it illustrates the failure mode of context engineering — **unintentional context**. What the agent reads, it obeys; a stale doc in the context path is an instruction you didn't mean to give. Curate the directories the engine walks as deliberately as you curate the ADRs themselves.

`FormatForAgent` renders the items into the prompt block the harness appends to every spec (the `=== path [category] (priority: N) ===` headers above are its format), and the factory enforces a provider-aware budget — about 24K characters for local models, 400K for large-context cloud models — so a small context window gets the highest-priority items rather than a truncated dump of everything.

The budget creates the discipline's central trade-off: context you include crowds out context you can't. The [case study](/blog/posts/agentic-software-engineering-case-study.html) hits this exactly — the model hallucinated a `jwt/v5` API that two lines of dependency documentation in context would have prevented, but those lines were never written, and at a 24K budget the library's real docs don't fit incidentally. When generation fails on a knowable fact, the cheapest fix in the whole system is usually a few lines of context.

## Open Loop vs. Closed Loop, Summarized

The experiment above is the whole argument: same model, same ask, and the difference between a tutorial artifact and an operable service was one well-written constraint document. Context is also the discipline with the best cost profile — ADRs are written once and constrain every future generation, while prompt fixes are paid per attempt.

The [next post](/blog/posts/agentic-software-engineering-specs.html) covers the second input to every generation: replacing the English ask itself with a machine-readable specification.

---

*Both generated artifacts in this post are verbatim, compiled outputs from a single real session (qwen3.6 via Ollama); timings and token counts are measured. Engine output is from the companion factory codebase (Go 1.23+).*
