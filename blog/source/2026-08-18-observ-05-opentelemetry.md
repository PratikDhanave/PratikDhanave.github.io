# OpenTelemetry

*Before OpenTelemetry, instrumenting a system meant picking a vendor and wiring their proprietary agent into all your code — and switching vendors meant re-instrumenting everything. OpenTelemetry ended that: one open, vendor-neutral standard for producing metrics, logs, and traces, so you instrument once and send the data anywhere. It's become the default way to make systems observable.*

The last three posts covered the pillars; this one covers the standard that unifies them. **OpenTelemetry (OTel)** is the open, vendor-neutral framework for generating and collecting telemetry — metrics, logs, and traces — with a single set of APIs and tools. It matters because it solves the two problems the pillars posts kept hinting at: consistent instrumentation across a heterogeneous system, and freedom from vendor lock-in. This post covers what OTel is, its architecture, and why it became the industry default.

## The problem OTel solves

Before a standard, observability was a mess of proprietary, incompatible tooling:

- **Vendor lock-in** — each observability vendor had its own agent, SDK, and data format. Instrumenting your code with Vendor A's library meant your telemetry was tied to Vendor A, and switching to Vendor B meant *re-instrumenting your entire codebase*. The instrumentation — the expensive, invasive part — was captive to the vendor.
- **Inconsistency** — different languages, services, and libraries used different tools and conventions, so telemetry didn't line up across a polyglot system. Correlating (the trace-ID-across-services idea) was hard when each service spoke a different telemetry dialect.
- **Duplicated effort** — every vendor and community reinvented instrumentation for the same common libraries and frameworks.

**OpenTelemetry** fixes this by being a *single, open, vendor-neutral standard* for telemetry, backed broadly across the industry (a CNCF project). You instrument your code *once* against OTel's APIs, and you can send that telemetry to *any* backend that supports OTel — swapping observability vendors becomes a configuration change, not a re-instrumentation project. That decoupling of *instrumentation* from *backend* is OTel's core value.

## What OpenTelemetry provides

OTel is a set of components that together cover producing and shipping telemetry:

- **APIs and SDKs** — language-specific libraries to instrument your code: create spans (traces), record metrics, and emit logs, using consistent concepts across every language. You write against the *API*; the *SDK* implements it.
- **A unified data model and semantic conventions** — standard definitions for what telemetry looks like and *how to name things* (e.g. conventions for HTTP attributes, service names). This is subtly crucial: consistent naming across services and languages is what makes telemetry correlatable and dashboards portable.
- **The OpenTelemetry Protocol (OTLP)** — a standard wire format for transmitting telemetry, so producers and backends interoperate.
- **The Collector** — a standalone service that receives, processes, and exports telemetry (below).
- **Auto-instrumentation** — for many popular languages and frameworks, OTel can instrument common libraries (web frameworks, HTTP clients, databases) *automatically*, giving you traces and metrics with little or no code change — a big head start on coverage.

Critically, OTel covers **all three pillars in one framework** with a shared context, so a single trace ID flows through traces and into logs and links to metrics — the correlated telemetry the first post argued for, built into the standard rather than bolted on.

## The architecture: instrument, collect, export

OTel's data flow separates *producing* telemetry from *shipping* it, which is what enables the vendor neutrality:

```text
  Your services (instrumented with OTel SDK / auto-instrumentation)
        │  emit metrics, logs, traces via OTLP
        ▼
  OpenTelemetry Collector
        │  receive → process (batch, filter, sample, enrich) → export
        ▼
  Any backend(s): metrics store, log store, tracing backend, vendor platform
```

- **Instrumentation** in your services produces telemetry (via SDK or auto-instrumentation) and sends it, typically to the Collector, over OTLP.
- **The Collector** is a vendor-neutral pipeline that *receives* telemetry, *processes* it (batching, filtering, sampling, adding metadata, redacting sensitive fields), and *exports* it to one or more backends. It's the decoupling point: your code sends to the Collector, and the Collector decides where the data goes — so changing backends means reconfiguring the Collector, not touching your code.
- **Backends** are where telemetry is stored, queried, and visualized — could be open-source tools, a commercial platform, or several at once. OTel is deliberately *not* a backend; it standardizes producing and shipping telemetry and leaves storage/visualization to whatever you choose.

This separation is the whole point: the invasive, code-level part (instrumentation) is standardized and vendor-neutral, and the swappable part (backend) is decoupled behind the Collector. You own your instrumentation; you rent your backend, replaceably.

## Why OpenTelemetry won

OTel became the industry default for concrete reasons worth understanding:

- **It ends lock-in.** Instrument once, send anywhere — the single biggest reason to adopt it. Your instrumentation investment is protected regardless of which vendor you use now or later.
- **It's the industry standard.** Broad backing means libraries, frameworks, and observability platforms converge on OTel, so instrumentation and integrations are increasingly available out of the box.
- **It unifies the pillars.** One framework, one context, all three signals correlated — rather than three separate tools you must stitch together.
- **Auto-instrumentation lowers the cost** of getting started — meaningful coverage with little code, then add custom instrumentation where you need domain-specific detail.
- **It's future-proof** — building on the open standard means you're not betting on one vendor's survival or pricing.

The practical guidance is straightforward: **use OpenTelemetry for new instrumentation.** It's the standard, it prevents lock-in, it covers all three pillars with correlation built in, and it decouples your code from your backend. Whatever observability backend you choose (or change to), instrument with OTel so that choice stays yours. With telemetry being produced and collected in a standard way, the remaining question is how to turn it into *reliability* and *action* — SLOs and alerting, the next posts.

## Key takeaways

- OpenTelemetry is an open, vendor-neutral standard for producing and collecting metrics, logs, and traces — you instrument once against its APIs and can send the telemetry to any compatible backend, ending the lock-in where switching vendors meant re-instrumenting everything.
- It provides language APIs/SDKs, a unified data model with semantic conventions (consistent naming that makes telemetry correlatable), the OTLP wire protocol, the Collector, and auto-instrumentation for common frameworks — covering all three pillars with a shared context.
- Its architecture separates producing telemetry (instrumentation in your services) from shipping it (the Collector receives, processes, and exports to backends), so the invasive code-level part is standardized and the swappable backend is decoupled — change backends by reconfiguring the Collector, not your code.
- OTel deliberately isn't a backend; it standardizes generation and transport and leaves storage/visualization to whatever tools you choose (open-source or commercial, one or many).
- It won because it ends lock-in, is the broadly-backed industry standard, unifies the pillars with built-in correlation, lowers the cost of coverage via auto-instrumentation, and is future-proof — so instrument new systems with OTel by default.

## Further reading

- [Traces (previous post)](/blog/posts/observ-04-traces.html)
- [OpenTelemetry documentation](https://opentelemetry.io/docs/)
- [What observability is — the correlated-telemetry goal](/blog/posts/observ-01-what-is-observability.html)
