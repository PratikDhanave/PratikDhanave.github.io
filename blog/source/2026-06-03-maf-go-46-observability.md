# step07 · Observability

*How one middleware wraps every agent run in an OpenTelemetry span tagged with gen_ai.* attributes — the same one-line hook you use for logging.*

---

## What this lesson demonstrates

This lesson makes an agent **traceable**. The SDK ships `otelprovider.NewMiddleware`, a middleware that opens an OpenTelemetry *span* around every run and tags it with `gen_ai.*` attributes (operation, provider, agent id/name). You wire it into the agent's `Config` and every `RunText` becomes a traced span — the exact same middleware hook you'd use for logging, guardrails, or retries.

## Wiring the tracing middleware

The span middleware goes into `Config.Middlewares`, and **order matters**:

```go
Config: agent.Config{
	Name: "Joker",
	Middlewares: []agent.Middleware{
		// Order matters: the tracing span wraps everything downstream,
		// including the logger and the model call it eventually reaches.
		otelprovider.NewMiddleware(otelprovider.MiddlewareConfig{}),
		runLogger(),
	},
},
```

Listing the tracer first means its span encloses the logger and, ultimately, the model call — so the span's duration reflects the whole run. In `main`, one line makes the spans land somewhere visible: `otel.SetTracerProvider(rec.provider())`. The middleware calls `otel.Tracer(...)`, which resolves to whatever global provider is installed.

## What to notice

The middleware traces **both** run shapes identically. A one-shot `RunText(...).Collect()` opens a span, runs to completion, and ends it before `Collect` returns. A streaming `RunText(..., agent.Stream(true))` opens the same kind of span but keeps it **open until the last update is yielded** — so a streamed run's span still measures the full stream, not just the first token. That's why the recorder must be safe for concurrent use: the streaming path may yield from another goroutine.

The instructive port detail: the real OpenTelemetry *SDK* exporter isn't on this tutorial module's dependency graph, so the lesson installs a tiny in-memory `TracerProvider` built only from the core OTel *API*. The trick is embedding the no-op implementations (`noop.Tracer`, `noop.Span`) — which satisfy each interface's unexported embedded marker — and overriding just the two or three methods that matter (`Start`, `IsRecording`, `SetStatus`). Everything else stays a safe no-op. In production you'd swap in `stdouttrace` + `sdktrace` and export to Jaeger or OTLP; the middleware wiring is unchanged.

Because the middleware only depends on the OTel *API*, the offline test drives it against a fake in-process span recorder — no provider, no network — and asserts a span was opened with the agent's name.

## How it maps to Foundry and the Agent Framework

`otelprovider` is the SDK's observability provider, and it's model-agnostic: the `gen_ai.*` semantic conventions it emits are the same whether the run hits Foundry, OpenAI, or Anthropic. Because it's *just a middleware*, tracing composes with everything else in `Config.Middlewares` — you add observability without touching the agent's logic.

## Run it

```bash
go run ./tutorial/02-agents/providers/foundry/step07_observability
```

The tracing test runs offline against the fake recorder; the live model calls are gated behind `AF_LIVE=1` with `az login` and `FOUNDRY_PROJECT_ENDPOINT`.

---

Next: [09 · MCP Client as Tools (Foundry)](/blog/posts/maf-go-47-mcp-client-as-tools.html)
