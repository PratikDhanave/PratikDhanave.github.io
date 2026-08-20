# Deployment and Serving: Traffic, SLOs, and Inline Guardrails

*A model that scores well in evaluation still has to serve real traffic within a latency budget, isolate tenants, plan for capacity, and enforce safety in the request path — and the guardrails have to be inline, not a filter someone can route around.*

Evaluation proves the system is good; deployment proves it can serve. This phase turns a validated system into one that handles real traffic with the reliability, latency, isolation, and capacity the use case demands — with safety enforced *in the request path*, not bolted on beside it. This post is Phase 5 of the roadmap.

## The reference architecture

Most production AI serving paths share a shape. A client's request enters through a gateway and orchestrator, passes through guardrails that validate input, reaches the model, which grounds itself via retrieval and acts via tools, and returns through guardrails that validate output — all observed end to end.

```text
Client ─▶ API Gateway ─▶ Guardrails ─▶ Foundation Model
                          (in + out)        │   │
                                    retrieve │   │ call
                                     context ▼   ▼ tools
                                    ┌──────────┐ ┌────────┐
                                    │Retrieval │ │ Tools  │
                                    │ (vector) │ │(APIs)  │
                                    └──────────┘ └────────┘
        (whole path: traces · cost · quality · drift telemetry)
```

> **▸ [Open the interactive diagram](/blog/handbook-diagrams/ai-production-reference-arch.html)** — pan, zoom, and trace every step (light/dark, self-contained).

The important property is that guardrails and observability wrap the *entire* path. Safety is a stage every request goes through, and every request emits telemetry — not an afterthought reachable only on the happy path.

## Serve within an SLO

Define service-level objectives the way you would for any production service — latency, availability, error rate — but account for AI-specific realities. Generation latency is variable and often dominated by output length; streaming responses improve perceived latency; and a cold model endpoint or a rate-limited provider can blow your tail latencies. Set objectives on the metrics users feel (time-to-first-token, end-to-end), measure the tail (p95/p99), and design fallbacks — a smaller model, a cached answer, a graceful degradation — for when a dependency is slow or down. An AI feature with no latency budget and no fallback is an outage waiting for its first traffic spike.

## Capacity and the reserved-throughput trap

Capacity planning for AI serving is different from ordinary web serving because inference is expensive and, for hosted models, rate-limited. Plan for peak concurrency against provider quotas, and know the consequence carried over from the development phase: custom fine-tuned models frequently require **reserved/provisioned throughput** to serve at all, which is a standing cost and a capacity commitment, not a pay-per-request convenience. This is one of the places the adaptation decision (compose versus fine-tune) shows up as an operational bill, and it should have been priced back in strategy.

## Guardrails must be inline

The control you cannot skip in this phase is **inline guardrails in the request path.** Input guardrails validate and screen requests before the model sees them (blocking prompt injection attempts, enforcing size and format limits, redacting sensitive data). Output guardrails validate what comes back before it reaches the user (schema conformance, grounding checks, content safety, PII leakage checks). "Inline" is the key word: a safety check that runs asynchronously after the response has already been sent to the user is not a guardrail, it is a report. Enforcement has to sit on the path, with the power to block or rewrite, even at the cost of a little latency.

## Isolation and safe rollout

Multi-tenant serving needs isolation so one tenant's load or data cannot affect another's — separate quotas, and strict separation of retrieved context and caches by tenant so PII and proprietary data never cross. And no new version should reach all users at once: deploy behind the progressive-delivery mechanisms that mature engineering already uses — canary releases, shadow traffic, and feature flags — so a regression the evals somehow missed is caught on a small slice and rolled back, not shipped to everyone. This ties directly into the next phase, where release engineering makes rollout automatic and reversible.

## Deployment topology choices

Match the serving topology to the requirement rather than defaulting. A hosted model API is fastest to stand up and scales without ops burden; self-hosting open weights can be cheaper at high steady utilization but carries infrastructure and operational cost; edge or on-device serving suits privacy-sensitive or offline cases at the cost of model size. There is no universal answer — the right topology follows from your latency, data-residency, cost, and utilization constraints, which is why the strategy and cost phases feed this decision.

## The gate and anti-patterns

Phase 5 is done when the system serves real traffic within defined SLOs, capacity is planned against provider quotas (including any reserved throughput for fine-tuned models), guardrails enforce input and output *inline* in the request path, tenants are isolated, and new versions roll out progressively with a tested rollback. Avoid the recurring failures: no latency budget or fallback; guardrails that run after the response is already out; a single big-bang deploy with no canary; and discovering the reserved-throughput cost of a fine-tuned model only after committing to it.

## Key takeaways

- Deployment turns a validated system into one that serves real traffic within reliability, latency, isolation, and capacity guarantees — with safety in the request path.
- The reference serving path is client → gateway → inline guardrails → model, with retrieval for grounding and tools for action, all wrapped in observability.
- Set SLOs on metrics users feel (time-to-first-token, end-to-end, tail latencies), and design fallbacks for slow or failed dependencies.
- Plan capacity against provider quotas and account for reserved/provisioned throughput that fine-tuned models often require — an operational cost that traces back to the adaptation decision.
- The non-skippable control is inline input/output guardrails with the power to block or rewrite; isolate tenants and roll out progressively (canary, shadow, flags) with tested rollback.

## Further reading

- [Production AI Reference Architecture (interactive diagram)](/blog/handbook-diagrams/ai-production-reference-arch.html)
- [AI Cost Optimization series](/blog/series/ai-cost-optimization/)
- [OWASP Top 10 for LLM Applications](https://genai.owasp.org/)
