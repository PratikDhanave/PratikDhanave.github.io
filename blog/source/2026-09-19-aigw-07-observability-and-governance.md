# Observability and Governance

*You can't manage what you can't see, and AI systems are unusually hard to see into — non-deterministic outputs, per-token costs, quality that's a matter of degree. Because every model call flows through the gateway, it's the one place you can observe all of it: what was called, what it cost, how long it took, and whether it was allowed. This post is about turning the gateway into your AI system's source of truth and its governance point.*

The previous posts made the gateway control *how* calls are served; this one makes it *visible and governed*. Observability (logging, tracing, metrics, cost) and governance (guardrails, access, audit, policy) both depend on the same fact: all traffic passes through one point. That's what lets the gateway be the single source of truth for AI usage and the single place to enforce policy.

## Observability: the gateway as source of truth

Because every call passes through the gateway, it can capture a complete record of your AI usage that no per-app instrumentation could assemble. The core signals (echoing the observability-engineering fundamentals — metrics, logs, traces):

- **Metrics** — request rate, error rate (by type: 429s, timeouts, provider errors), latency (percentiles, not averages — LLM latency is highly variable), token throughput, cache hit rate, and **cost** (the LLM-specific metric that matters enormously). These per-model, per-app, per-key metrics tell you what your AI system is doing at a glance.
- **Logging** — a record of each call: which model, the request (or a reference to it), the response, tokens used, cost, latency, outcome. This is the raw material for debugging, analysis, and audit. (With the privacy caveat below.)
- **Tracing** — propagate a trace context so a model call is connected to the larger request it's part of (which user action, which agent step), making it possible to follow one logical operation across services and into the model call — the same distributed-tracing idea, extended to LLM calls.

The distinctive, high-value signal is **cost observability.** LLM cost is per-token and varies wildly by request, so "what are we spending, on what, by whom?" is a question most organizations can't answer — unless a gateway meters every call. The gateway computes and attributes cost per call, per model, per team, giving you the cost visibility that makes right-sizing (post 3), budgets (post 6), and FinOps possible. This alone justifies many gateway deployments.

## Governance: one place to enforce policy

The same choke point that enables observation enables *control*. Governance is applying organizational policy to AI usage, centrally:

- **Access control** — who (which app, team, user) can use which models. Not every team should reach every model (cost, capability, data-sensitivity reasons); the gateway enforces model-level access per consumer.
- **Guardrails** — the gateway is the natural place to apply input/output guardrails (content moderation, PII detection/redaction, injection screening — the whole guardrails discipline) uniformly to *all* traffic, rather than hoping each app implements them. One integration point protects everything.
- **Data governance** — controlling what data is allowed to be sent to which providers (e.g. blocking sensitive data from external providers, or routing regulated workloads only to approved/self-hosted models). The gateway can inspect and enforce this at the boundary.
- **Audit trail** — a complete, central log of who called what, when, and what came back — essential for compliance, incident investigation, and accountability. Because it's the choke point, the gateway's log is authoritative.

Governance at the gateway is powerful for the same reason everything else in this series is: **enforced centrally, it actually holds.** Guardrails or access rules implemented per-app are inconsistent and skippable; implemented at the gateway, they apply to every call by construction — no app can bypass the policy because no app can bypass the gateway. This is "policy as code, enforced not persuaded" (the recurring theme from the CI/CD and guardrails series) at the AI-infrastructure layer.

## The privacy and PII responsibility

Centralizing observation creates a serious responsibility that must be named: **the gateway sees, and often logs, every prompt and response** — which frequently contain sensitive user data. That makes the gateway's logs a high-value, high-risk data store:
- **Log deliberately.** Decide what to log (full prompts/responses vs. metadata + references), because logging everything can capture PII, secrets, and confidential content at scale.
- **Protect and control the logs.** Access controls, retention limits, and redaction of sensitive fields — the log is now a compliance-relevant asset.
- **Redact PII** in transit and in logs where required, and honor data-residency and retention rules.

This is the flip side of the choke-point power: concentrating visibility concentrates risk. The gateway's observability is invaluable, but its logs must be treated with the same seriousness as any store of sensitive customer data — which is itself something the gateway's governance features (redaction, access control) can help enforce.

## Why this completes the gateway

Observability and governance are what turn the gateway from an operational convenience into an organizational control plane. Performance features (routing, caching, reliability) make AI calls *work well*; observability and governance make them *accountable and safe*. Together they mean the gateway can answer the questions leadership actually asks — what are we spending, is it safe, who's using what, can we prove it — from one authoritative point. Everything in the series has built toward this: a single layer through which all AI traffic flows, made fast and reliable and cheap, and now visible and governed. The final post assembles it into a complete architecture and covers building versus buying it.

## Key takeaways

- The gateway sees **every call**, making it the **source of truth** for AI usage: metrics (rate, errors by type, latency *percentiles*, token throughput, cache-hit rate, and **cost**), per-call logging, and **tracing** that connects model calls to the larger operations they serve.
- **Cost observability** is the distinctive high-value signal — LLM cost is per-token and wildly variable, so "what are we spending, on what, by whom?" is unanswerable without a gateway metering and attributing every call; it's what makes right-sizing, budgets, and FinOps possible.
- The choke point also enables **governance**: model-level **access control** per consumer, **guardrails** (moderation/PII/injection) applied uniformly to all traffic, **data governance** (what data goes to which providers), and an authoritative **audit trail** — all enforceable because no app can bypass the gateway.
- Governance at the gateway **actually holds** ("enforced, not persuaded") — per-app policy is inconsistent and skippable; gateway policy applies to every call by construction.
- Centralizing visibility **concentrates risk**: the gateway sees/logs every prompt and response (often PII/secrets), so log deliberately (metadata vs. full content), protect and retention-limit the logs, and redact sensitive data — its logs are a compliance-relevant, high-value store.

## Further reading

- [OpenTelemetry — observability framework](https://opentelemetry.io/docs/)
- [LiteLLM — logging and observability](https://docs.litellm.ai/)
