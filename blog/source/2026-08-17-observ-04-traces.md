# Traces

*When a request touches ten services and comes back slow, metrics tell you it's slow and logs tell you what each service did — but neither shows you the one thing you need: where, along that journey, the time actually went. Distributed tracing is the pillar built for exactly this, following a single request across every service it touches and showing you the whole path at once.*

Metrics detect; logs detail. But in a distributed system, the question that stumps both is *where*: a request flows through many services, and when it's slow or fails, you need to see its *entire journey* to find the culprit. **Distributed tracing** is the pillar built for this — it's the connective tissue that shows a single request's path across services, which metrics (aggregated) and logs (per-service, disconnected) can't. This post covers spans, traces, context propagation, and why tracing is what makes distributed systems debuggable.

## The problem traces solve

Picture a request that enters your API gateway, calls an auth service, then an orders service, which calls a database and a payment service, which calls an external provider. It comes back slow. Metrics say "p99 latency is up." Logs from each service say what that service did. But neither answers: *which* of those services (or calls) consumed the time? Was it the database query, the payment provider, or the network between two hops?

With only metrics and logs, you're stuck correlating timestamps across services by hand — tedious, error-prone, and often impossible when clocks differ and requests interleave. **Tracing solves this directly** by following *one specific request* through *all* the services it touches and recording how long each step took, as a single connected picture. It turns "somewhere in these ten services, time was lost" into "the payment service's call to the external provider took 4 of the 4.3 seconds." That localization — *where* across a distributed system — is what tracing uniquely provides.

## Spans and traces

Tracing has two core concepts:

- **Span** — a single unit of work: one operation in one service (a database query, an HTTP call, a function). A span records its name, start time, duration, and metadata (attributes), plus its status (ok/error). A span answers "this operation took this long and did this."
- **Trace** — the *whole* collection of spans for a single request, linked together into a tree that shows the request's complete journey. Spans have parent-child relationships (this service call spawned that database query), so the trace reconstructs the full call hierarchy and timing.

```text
Trace (one request):
  [────────────── API gateway (4.3s) ──────────────]
    [── auth (0.1s) ──]
    [──────────── orders service (4.1s) ────────────]
       [─ db query (0.2s) ─]
       [──────── payment service (3.8s) ────────]
          [──── external provider call (3.7s) ────]  ← the culprit
```

Read that trace and the answer jumps out: the external provider call took 3.7 of the 4.3 seconds. This **waterfall view** — spans laid out by time, nested by parent-child — is tracing's signature, and it makes latency problems visually obvious in a way no metric or log can. A trace shows you *where the time went* and *where a failure occurred* across the entire distributed path, at a glance.

## Context propagation: the key mechanism

The magic that connects spans across service boundaries into one trace is **context propagation**, and it's the concept that makes tracing work (and the one to get right). When a request starts, it gets a unique **trace ID**. As the request flows from service to service, that trace ID — plus the current span's ID (to establish parent-child) — must be **passed along** with every call, so each service's spans attach to the *same* trace:

```text
Service A starts trace (trace_id=abc), creates span, and when calling
Service B, INJECTS the context (trace_id=abc, parent_span_id) into the
request headers → Service B EXTRACTS it, creates its span as a child of A's
→ all spans share trace_id=abc → they assemble into one trace
```

- Context is propagated by **injecting** trace identifiers into outgoing requests (typically HTTP headers, following a standard like **W3C Trace Context**) and **extracting** them from incoming requests.
- Every service in the path must propagate the context, or the trace *breaks* — a service that drops the context starts a disconnected trace, and you lose the connection across that gap.

This is why context propagation is the linchpin: tracing only works if the context flows unbroken through *every* hop. A standard format (W3C Trace Context) ensures services (and different vendors' tools) agree on how to pass it, which is part of why OpenTelemetry (next post) matters — it standardizes propagation so traces span heterogeneous systems.

## Traces plus logs plus metrics: correlation

Tracing's real power multiplies when you *connect* it to the other pillars via the trace ID — the correlation the first post argued observability really needs:

- **Traces ↔ logs** — include the `trace_id` in every log line (the structured-logging point from the last post), and you can jump from a span straight to the logs emitted during it. You see not just *that* the payment span was slow, but the log lines *within* it explaining why.
- **Traces ↔ metrics** — a spiking latency metric can lead you to *example traces* from that spike, so you go from "p99 is up" to a concrete slow request to inspect.

This is the connected-telemetry vision: metrics detect the problem, traces localize *where* across services, and logs (linked by trace ID) reveal *what* happened at that spot — one investigation flowing across all three, joined by the trace ID. The trace ID is the thread that stitches the pillars together, which is why propagating it and putting it in logs is so valuable.

## Sampling: the cost reality

Tracing every request in a high-volume system produces enormous data (each request is many spans), so tracing uses **sampling** — recording a subset of traces rather than all:

- **Head-based sampling** decides at the start whether to trace a request (e.g. keep 1%); simple, but may miss the rare failing request.
- **Tail-based sampling** decides *after* seeing the whole trace (e.g. keep all traces that errored or were slow, sample the rest); catches the interesting ones but is more complex to run.

The trade-off is cost vs. coverage: you can't afford to keep every trace, but you don't want to miss the ones that matter. A common approach keeps all error/slow traces and samples the normal ones — so the traces you actually need for debugging are there, without the full firehose. Sampling is a necessary part of tracing at scale, and choosing it well means always capturing the anomalies.

## Traces as the distributed debugger

Tracing is what makes distributed systems *debuggable*: it restores the "follow the execution" ability you lose when a request spans many services, showing the whole path, the timing of each step, and where failures occur — the *where* that metrics and logs can't give. Combined with the other pillars via the trace ID, it's the centerpiece of investigating a distributed system. But instrumenting three pillars consistently, propagating context across services, and avoiding vendor lock-in is a lot — which is exactly what the next post's subject, OpenTelemetry, exists to solve.

## Key takeaways

- Distributed tracing follows a single request across every service it touches, answering the question metrics and logs can't in a distributed system: *where* along the journey did the time go or the failure occur.
- A span is one unit of work (an operation, with duration/status/attributes); a trace is all the spans for one request linked into a parent-child tree, shown as a waterfall that makes latency culprits visually obvious.
- Context propagation is the linchpin: a trace ID (plus parent span ID) is injected into outgoing calls and extracted from incoming ones (via a standard like W3C Trace Context) so spans across services join one trace — any service that drops the context breaks the trace.
- The trace ID stitches the pillars together: put it in structured logs (jump span → its logs) and link it from metrics (spike → example traces), enabling one investigation to flow metric → trace → log.
- Tracing every request is too costly at scale, so use sampling (head-based upfront, or tail-based keeping all error/slow traces) to capture the anomalies you need without the full firehose.

## Further reading

- [Logs (previous post)](/blog/posts/observ-03-logs.html)
- [OpenTelemetry — traces](https://opentelemetry.io/docs/concepts/signals/traces/)
- [Distributed Systems from First Principles series](/blog/series/distributed-systems-from-first-principles/)
