# Observability in Practice

*Knowing the pillars is not the same as having an observable system. In practice, observability is built incrementally, costs real money you have to manage, and only pays off if the whole team treats telemetry as part of building software — not something added after the outage. This closing post turns the concepts into a way of working.*

The series has covered the pillars, OpenTelemetry, SLOs, and alerting. This final post is about *doing* it: how to instrument a system without boiling the ocean, how to manage the very real cost, and how to build the culture that makes observability actually used. Because the failure mode isn't usually *not knowing* about metrics, logs, and traces — it's having them and still flying blind during an incident, because they weren't built in, correlated, or trusted. This post is how to avoid that.

## Instrument incrementally, starting where it hurts

You don't make a system observable in one heroic project — you build it up, prioritizing by value:

- **Start with the golden signals.** Instrument the RED metrics (rate, errors, duration) for your key services first — they give the most insight per effort and cover the user-facing health that matters most (the metrics post). This alone transforms "we have no idea" into "we can see service health."
- **Add tracing across service boundaries next.** For a distributed system, tracing (with propagated context) is what makes incidents debuggable, so instrument the request paths that span services — especially the critical user journeys.
- **Make logs structured and correlated.** Convert logs to structured format and include the trace ID, so logs link to traces (the logs and traces posts). This is often a high-value, moderate-effort upgrade to logging you already have.
- **Lean on OpenTelemetry and auto-instrumentation.** Use OTel (previous post) so instrumentation is standard and portable, and use auto-instrumentation to get broad coverage of common frameworks cheaply before writing custom instrumentation.
- **Prioritize the critical paths.** Instrument the flows that matter to users and the business first (checkout, login, core features), not everything uniformly. Coverage follows importance.

The principle: incremental, value-ordered instrumentation — golden-signal metrics, then cross-service traces, then correlated structured logs, on the paths that matter most — beats a stalled attempt to instrument everything perfectly at once.

## Correlate, or you've wasted the effort

The recurring warning from the first post, now as practice: **the pillars must connect, or you have three disconnected data stores and still can't investigate.** The concrete requirements:

- **Propagate trace context everywhere** so traces are unbroken across services (the traces post) — a single gap loses the thread.
- **Put the trace ID in every log line** so you can pivot from a trace to its logs and back (the logs post).
- **Link metrics to example traces** so a spiking metric leads to a concrete request to inspect.
- **Use consistent naming (OTel semantic conventions)** so telemetry from different services and languages lines up.

The test of whether you have observability (vs. just telemetry) is whether, during an incident, you can *fluidly follow an investigation* — metric spike → example trace → the logs within it → the root cause — without hitting a wall where the data doesn't connect. If you can't make that pivot, the correlation work isn't done, no matter how much telemetry you're collecting. Correlation is what turns three pillars into observability.

## Manage the cost deliberately

Observability is not free, and its cost can become surprisingly large — sometimes rivaling infrastructure spend — so cost management is part of doing it well, not an afterthought:

- **Logs and traces are the expensive pillars** (volume-driven), metrics the cheap one (aggregated). Spend accordingly.
- **Control log volume** — appropriate levels, sample very high-volume logs, set retention limits, and don't log noise (the logs post). "Log everything forever" is a real budget line.
- **Sample traces** — keep all error/slow traces, sample the rest (the traces post), so you capture the anomalies without the full firehose.
- **Guard metric cardinality** — the number-one metrics cost explosion (the metrics post): no unbounded labels (user IDs, request IDs), which belong in logs/traces instead.
- **Match retention to value** — keep detailed data for the recent window where you'd investigate, aggregate or drop older data. You rarely need per-request traces from six months ago.

The discipline mirrors the AI cost series: observability spend should be *deliberate*, sized to the value it provides, not accumulated by default. Uncontrolled cardinality and unbounded log/trace retention are how observability bills quietly balloon.

## Build the culture, not just the tooling

The deepest determinant of whether observability works is cultural, not technical — the tools are necessary but not sufficient:

- **Instrument as you build, not after the outage.** Observability designed in — spans, metrics, and structured logs added as features are written — is far better than telemetry retrofitted in a panic. Treat instrumentation as part of "done," like tests. A feature that ships without telemetry is a feature you can't operate.
- **Whoever builds it, operates it (or at least instruments it).** When developers share responsibility for running their services, they instrument them well, because they'll be the ones investigating at 3 a.m. Observability thrives when building and operating aren't fully separated.
- **Use it routinely, not just in fires.** Teams that look at their telemetry regularly — reviewing SLOs, watching trends, checking traces during development — catch problems early and keep the telemetry trustworthy. Observability used only during incidents atrophies.
- **Blameless learning.** Postmortems that ask "what did our observability fail to show us, and how do we fix that?" continuously improve both the system and its instrumentation (the alerting post's loop).
- **Trust through low noise.** Keep alerts real and dashboards meaningful (the alerting post), because observability people don't trust is observability they don't use.

Tooling gives you the *capability*; culture determines whether it's *realized*. A team with modest tooling that instruments as it builds, correlates its telemetry, and uses it daily is far more observable than one with expensive tools and no discipline.

## The series in one arc

Observability, end to end: it's the capability to understand and investigate a system you can't fully see — especially in the novel failures monitoring never anticipated (post one). You build it from **metrics** (efficient detection, percentiles, watch cardinality), **logs** (structured, correlated, no secrets), and **traces** (the distributed *where*, via propagated context), unified by **OpenTelemetry** (instrument once, vendor-neutral, correlated). You turn that telemetry into **reliability management** with SLIs/SLOs/error budgets, and into **response** with symptom- and burn-rate-based alerting that respects the humans on call. And you make it real in practice by instrumenting incrementally on the paths that matter, correlating the pillars so investigations flow, managing cost deliberately, and — above all — building a culture that instruments as it builds and uses telemetry every day. Do that, and when your system fails in a way no one predicted, you'll be able to ask it what happened and get an answer.

## Key takeaways

- Instrument incrementally by value: golden-signal RED metrics for key services first, then cross-service tracing, then structured correlated logs — leaning on OpenTelemetry and auto-instrumentation, prioritizing critical user paths over uniform coverage.
- Correlation is the test of real observability: propagate trace context everywhere, put the trace ID in every log, link metrics to example traces, and use consistent naming — so during an incident you can fluidly pivot metric → trace → log → root cause; if you can't, the work isn't done.
- Manage cost deliberately: logs and traces are the expensive (volume-driven) pillars and metrics the cheap one — control log volume/retention, sample traces (keeping anomalies), guard metric cardinality, and match retention to value.
- Culture determines success more than tooling: instrument as you build (telemetry is part of "done"), have builders share operation, use telemetry routinely not just in fires, run blameless postmortems that improve instrumentation, and keep noise low so people trust it.
- Observability is the end-to-end capability — pillars → OpenTelemetry → SLOs → alerting → practice — to interrogate a system you can't fully see, so that when it fails unpredictably you can ask it what happened and get an answer.

## Further reading

- [Alerting (previous post)](/blog/posts/observ-07-alerting.html)
- [What observability is — start of the series](/blog/posts/observ-01-what-is-observability.html)
- [OpenTelemetry documentation](https://opentelemetry.io/docs/)
