# Routing and Load Balancing

*Once every model call flows through one place, that place can make an intelligent decision on every request: which model should serve this, and through which of your capacity? Routing picks the right model for the task; load balancing spreads traffic across providers and keys so no single limit or outage bottlenecks you. Together they turn the gateway from a passthrough into a control plane.*

The unified API lets apps name a model; routing and load balancing let the *gateway* decide how that name is fulfilled. This post covers both — choosing the target model per request, and distributing load across the capacity behind it — because this is where the gateway starts actively managing traffic rather than just translating it.

## Routing: choosing the model per request

**Routing** is the gateway deciding *which model* handles a given request. The app might name a specific model, or name a logical alias (`"default"`, `"cheap"`, `"reasoning"`) that the gateway resolves by policy. Common routing strategies:

- **Explicit** — the app names the exact model; the gateway just honors it. The baseline.
- **Alias / policy-based** — the app names a role (`"summarizer"`) and the gateway maps it to a concrete model per current policy, so you can change which model backs a role centrally without touching apps.
- **Capability-based** — route by what the request needs: a request with images goes to a multimodal model; one needing tool calling goes to a model that supports it.
- **Cost/latency-aware** — route simple requests to a cheap, fast model and hard ones to a strong, expensive model (model "right-sizing"). Some setups even use a small model to *classify* difficulty and route accordingly.
- **Quality/experiment** — send a fraction of traffic to a candidate model (A/B) to compare quality before switching.

Routing is where a lot of an AI system's cost and quality is won or lost: sending every request to the most powerful model is simple but wasteful; routing each request to the *cheapest model that can do it well* can cut cost dramatically at equal quality. The gateway is the natural home for this logic because it sees every request and can change routing policy in one place, for all apps.

## Load balancing: spreading traffic across capacity

**Load balancing** is distributing requests across *multiple backends for the same model* — multiple API keys, multiple provider accounts/regions, or multiple deployments of a self-hosted model. Where routing chooses *which model*, load balancing chooses *which instance of that model's capacity* serves the call.

Why it matters for LLMs specifically:
- **Provider rate limits are per-key/account.** A single API key has request and token-per-minute limits. Spreading load across multiple keys/accounts multiplies your effective throughput ceiling — often the difference between hitting rate-limit errors constantly and not.
- **Capacity is finite and uneven.** Providers have their own capacity constraints; distributing across providers/regions smooths spikes and avoids overloading one.
- **It sets up failover.** Balancing across backends is the foundation for reliability (next post) — if you're already spreading across several, routing away from a failing one is natural.

Common strategies mirror classic load balancing — round-robin, weighted (send more to cheaper/faster backends), and least-loaded — plus LLM-specific twists like balancing by *token* throughput (since limits are often token-based, not just request-based) and respecting each backend's distinct rate limits.

## Routing + load balancing together

The two compose into the gateway's traffic-management layer, and it's worth seeing how they stack:

1. **Route** decides the model (or model tier) for the request — by explicit name, alias, capability, or cost/latency policy.
2. **Load balance** picks which backend/key/deployment of that model actually serves it — spreading across capacity and respecting rate limits.

So a request for the `"reasoning"` alias might route to a strong model, then load-balance across three API keys for that model to stay under per-key limits. The app said one word; the gateway made two decisions to fulfill it well. This layered decision — *what model*, then *which capacity* — is the essence of the gateway as a control plane: it's actively optimizing every request for cost, capability, and throughput, invisibly to the caller.

## Practical considerations

A few realities shape good routing/balancing:
- **Routing state and stickiness.** Mostly LLM calls are stateless, so you can route each freely — but if you rely on provider-side conversation state or prompt caching, you may want stickiness to the same backend to benefit from it. Know which model your setup assumes.
- **Health-aware balancing.** Balance away from backends that are erroring or slow (feeding into circuit breaking, next post) — a backend at its rate limit or degraded should get less traffic automatically.
- **Cost/latency visibility drives routing.** Good routing decisions depend on knowing each model's cost and latency, which comes from the observability layer (post 7) — routing and observability reinforce each other.
- **Keep policy central and declarative.** Express routing rules as configuration in the gateway, not logic scattered in apps, so you can retune the whole system's cost/quality/throughput trade-offs in one place.

The takeaway: routing and load balancing are what make the gateway *earn* its position in the path. It's not just translating calls (post 2) — it's deciding, per request, the best model and the best capacity to serve it, optimizing cost, capability, and throughput across your entire fleet of apps from one control point. That active management sets up the reliability layer next: once you're spreading across models and backends, surviving a provider outage becomes a routing decision.

## Key takeaways

- **Routing** chooses *which model* serves each request — explicit, alias/policy-based, capability-based, cost/latency-aware ("right-sizing"), or experiment/A-B — and is where much of an AI system's cost and quality is won (route to the cheapest model that does the job well, not always the most powerful).
- **Load balancing** spreads traffic across *multiple backends for the same model* (keys, accounts, regions, self-hosted deployments) — crucial for LLMs because rate limits are per-key/account, so spreading multiplies effective throughput and avoids constant rate-limit errors.
- They **compose**: route decides the model/tier, then load-balance picks which capacity/key serves it — a layered "what model, then which capacity" decision that makes the gateway an active control plane, invisible to the caller.
- LLM-specific twists: balance by **token throughput** (not just requests), respect each backend's distinct rate limits, and consider **stickiness** if you rely on provider-side state or prompt caching.
- Keep routing **health-aware** (steer away from erroring/slow backends — feeds circuit breaking) and **policy central/declarative** (config in the gateway, not app logic) so you retune cost/quality/throughput in one place; routing decisions depend on observability's cost/latency data.

## Further reading

- [LiteLLM — routing and load balancing](https://docs.litellm.ai/)
- [Rate limiting — overview](https://en.wikipedia.org/wiki/Rate_limiting)
