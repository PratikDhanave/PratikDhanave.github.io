# step08 · Observability (OpenTelemetry)

*How to turn every agent run into an OpenTelemetry span with the SDK's otelprovider middleware.*

---

## What this lesson demonstrates

Same Joker agent as `step01`, but the middleware in the `Config` is now `otelprovider.NewMiddleware(...)` — the framework's built-in OpenTelemetry instrumentation. It opens a span around each run, tags it with `gen_ai.*` attributes (agent name, provider, operation), records any error onto the span, and closes it when the run finishes. Point it at any OTel backend and you get distributed traces for free.

## The core code

Observability is just another middleware slotted into `Config.Middlewares`, and it emits to whatever `TracerProvider` is globally registered:

```go
rec := newSpanRecorder()
otellib.SetTracerProvider(rec)

a := newJoker(demo.Endpoint(), demo.Model(), cred,
	otelprovider.NewMiddleware(otelprovider.MiddlewareConfig{}))

// each run — collected or streamed — produces one invoke_agent span
resp, err := a.RunText(ctx, "Tell me a joke about a pirate.").Collect()
```

## What to notice

- **Observability is just another middleware.** `otelprovider.NewMiddleware(...)` slots into `agent.Config.Middlewares` exactly like the logger in `step01`. Instrumentation is wiring, not a rewrite — the agent's core logic never changes.
- **Spans go wherever the global TracerProvider points.** The middleware calls `otel.Tracer(...)` under the hood, so whatever you register with `otel.SetTracerProvider(...)` receives every span. The gotcha: forget to register a provider and the spans go to the no-op default and vanish silently.
- **Both call styles produce one span.** The one-shot `.Collect()` run and the streamed `agent.Stream(true)` run each create exactly one `invoke_agent` span — observability doesn't care which style you use.

## How it maps to Azure AI Foundry

The `gen_ai.*` attributes the middleware sets follow OpenTelemetry's semantic conventions for generative-AI, so traces from a Foundry-backed agent line up with the rest of your observability stack. In production you register the OTel SDK's `TracerProvider` pointed at Jaeger, an OTLP collector, or a console exporter — and the middleware code is unchanged. This port swaps that exporter for a tiny in-process `spanRecorder` (built only from the core OTel API pinned in the tutorial's `go.mod`), so the lesson stays offline; the concept — one middleware turns runs into spans — is identical. The offline tests drive the OTel API exactly as the middleware does and assert a finished span was captured with its name, attributes, and error status intact.

## Run it

```bash
go run ./tutorial/02-agents/agents/step08_observability
```

You'll see two jokes then a `===== captured spans =====` block. The program needs Foundry; the span-capture tests run offline, and the live call is gated behind `AF_LIVE=1`.

---

Next: [step09 · Dependency Injection](/blog/posts/maf-go-19-dependency-injection.html)
