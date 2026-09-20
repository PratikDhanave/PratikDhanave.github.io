# Why You Need an AI Gateway

*The moment your application talks to more than one model — or one model but seriously — you accumulate a pile of cross-cutting concerns: provider APIs that differ, outages you must survive, costs you must control, calls you must log. An AI gateway is the single control point that handles all of it, sitting between your applications and every model provider. This series builds one from first principles.*

If you've wired an app directly to a model provider's SDK, it works — until you need a second provider, or the first one has an outage, or finance asks what you're spending, or you need to know why a response was bad. Each of those is a cross-cutting concern that doesn't belong scattered across every service. An **AI gateway** consolidates them into one layer. This opening post makes the case for that layer and shows its shape.

## The problem: direct provider calls don't scale organizationally

Calling a provider SDK directly from each application is fine for one app and one model. It stops being fine fast:

- **Every app reimplements the same plumbing** — retries, timeouts, error handling, logging, key management — copied and drifting across services.
- **Providers have different APIs** — switching from one to another, or using several, means each app speaks multiple dialects and is coupled to specific vendors.
- **No central control** — no one place to enforce spending limits, apply rate limits, rotate keys, or add a guardrail. Policy lives nowhere and everywhere.
- **No central visibility** — cost, latency, and errors are smeared across apps, so "what are we spending on AI, and where?" has no answer.
- **Outages hit every app independently** — when a provider degrades, each app fails on its own, and failover (if it exists) is reinvented per service.

These aren't model problems; they're *infrastructure* problems — exactly the kind that, in the REST world, gave rise to the **API gateway**. The AI gateway is the same idea applied to model calls: pull the cross-cutting concerns out of every application and into one shared layer.

## What an AI gateway is

An **AI gateway** is a service that sits between your applications and your model providers, through which all model calls flow. Applications call the gateway with a single, consistent API; the gateway handles routing to providers, reliability, caching, rate limiting, observability, and governance, then returns the result.

Here's the shape:

```
 Applications                 AI Gateway                        Model Providers
 (agents,      one request   ┌──────────────────────────┐       ┌──────────────┐
  chatbots, ───────────────▶ │  Unified API  →  Router   │ ────▶ │ OpenAI       │
  backends)                  │    ├─ Cache (exact/sem.)  │       │ Anthropic    │
                             │    ├─ Rate limiter/budget │       │ Google Vertex│
                             │    ├─ Fallback / retry     │       │ Self-hosted  │
                             │    └─ Observability        │       │ (vLLM)       │
                             └──────────────────────────┘       └──────────────┘
```

> **▸ [Open the interactive architecture diagram](/blog/handbook-diagrams/ai-gateway-reference-arch.html)** — pan, zoom, and trace every path (light/dark, self-contained).

The essential idea: **one choke point.** Because every model call passes through the gateway, it's the natural place to put anything that should apply to *all* model calls — which turns out to be almost every operational concern.

## What the choke point buys you

Concentrating model traffic through one layer is what makes each capability possible (each is a post in this series):

- **A unified API** (post 2) — apps speak one interface; the gateway translates to each provider. Swap models without touching app code.
- **Routing and load balancing** (post 3) — send each request to the right model, and spread load across providers and API keys.
- **Reliability** (post 4) — retries, fallback to another provider, and circuit breakers, so a provider outage doesn't become your outage.
- **Caching** (post 5) — exact and *semantic* caching to cut cost and latency on repeated queries.
- **Rate limiting and budgets** (post 6) — quotas and spend controls per team/app/key, enforced in one place.
- **Observability and governance** (post 7) — central logging, tracing, cost metering, and a single point to apply guardrails and policy.

None of these are possible when calls go direct, because there's no shared layer to host them. The gateway *is* that layer, and every capability is a consequence of routing traffic through one point.

## The trade-offs, honestly

An AI gateway is not free, and a clear-eyed view includes the costs:
- **It's another hop.** The gateway adds a network hop and a component in the critical path, so it must be fast and highly available — if it's down, *everything* is down. A gateway concentrates risk as well as control, which is why reliability (its own uptime) matters intensely.
- **It's infrastructure to run.** Whether you build or adopt one (post 8), it's a service to deploy, scale, secure, and operate.
- **It can become a bottleneck** if poorly designed — the same centralization that gives control can throttle throughput if it's not built for the load.

The judgment: for a single app calling one model, a gateway is overkill — call the provider directly. The gateway earns its place as you scale to *multiple apps, multiple models, real spend, and real reliability requirements* — which is exactly when the cross-cutting concerns above become painful. Most serious LLM deployments reach that point, which is why the gateway pattern has become standard infrastructure (tools like LiteLLM, and provider/cloud gateway offerings, exist precisely to fill this role).

The mental model to carry through the series: an AI gateway is the API-gateway pattern for model calls — one control point that turns a pile of scattered cross-cutting concerns into shared, centrally-managed infrastructure. Everything ahead is a capability that becomes possible once all your model traffic flows through one place.

## Key takeaways

- Calling provider SDKs directly is fine for one app + one model, but doesn't scale *organizationally*: every app reimplements plumbing, speaks multiple provider dialects, and there's no central control, visibility, or failover.
- An **AI gateway** sits between your applications and all model providers as a **single choke point** through which every model call flows — the API-gateway pattern applied to model calls.
- The choke point is what makes each capability possible: **unified API, routing/load-balancing, reliability (fallback/circuit breakers), caching, rate-limits/budgets, and observability/governance** — none achievable when calls go direct, because there's no shared layer to host them.
- **Trade-offs**: it's another hop in the critical path (must be fast + highly available — if it's down, everything is), infrastructure to operate, and a potential bottleneck if poorly built — it concentrates risk along with control.
- Use direct calls for a single app/model; the gateway **earns its place at scale** — multiple apps, multiple models, real spend, and real reliability needs — which is why it's become standard LLM infrastructure.

## Further reading

- [LiteLLM — call 100+ LLMs with one interface](https://docs.litellm.ai/)
- [API gateway — pattern overview](https://en.wikipedia.org/wiki/API_gateway)
- [Martin Fowler — the Gateway pattern](https://martinfowler.com/articles/gateway-pattern.html)
