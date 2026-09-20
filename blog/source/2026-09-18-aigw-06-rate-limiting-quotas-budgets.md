# Rate Limiting, Quotas, and Budgets

*Nothing concentrates the mind like a surprise five-figure AI bill from one runaway loop, or one team's traffic spike exhausting the rate limit everyone shares. Because every model call flows through the gateway, it's the one place you can enforce limits and budgets that actually hold — protecting your spend, your providers' rate limits, and fairness across teams. This post is about spending control as a first-class gateway capability.*

The gateway sees and mediates all model traffic, which makes it the only place spend and rate controls can be enforced comprehensively. This post covers rate limiting (protecting throughput), quotas and budgets (protecting spend), and how the gateway turns "we hope nobody blows the budget" into "the budget is enforced." For LLM systems, where a single bug can burn real money fast, this is not optional governance — it's cost survival.

## Why limits belong at the gateway

Rate limits and budgets enforced *inside each application* are unreliable: each app enforces its own, they don't see each other, and nothing stops a new or misbehaving app from ignoring them. Enforced at the *gateway*, they're comprehensive and unavoidable — every call passes through, so every call is subject to the limit, and no app can route around it. This is the same choke-point logic as the rest of the series: centralize the concern where all traffic converges, and it becomes enforceable rather than aspirational.

Two distinct things need controlling, and it's worth separating them:
- **Rate** — how *fast* requests flow (requests or tokens per unit time). Protects throughput and your providers' rate limits.
- **Spend** — how *much* is consumed in total (cost over a period). Protects your budget.

They're related but different: you can be within your rate limit and still blow your monthly budget, or under budget but hammering a provider's per-minute limit. Good gateways control both.

## Rate limiting

**Rate limiting** caps the frequency of requests — per API key, per user, per team, or globally. Its purposes at the gateway:
- **Stay under provider limits** — providers impose per-key request-and-token-per-minute limits; the gateway rate-limits (and load-balances, post 3) to stay under them and avoid 429 storms.
- **Fairness across consumers** — prevent one app or user from monopolizing shared capacity and starving others. Per-consumer limits ensure a noisy tenant can't degrade everyone.
- **Abuse and runaway protection** — a bug that loops, or a malicious caller, is capped before it does real damage.

LLM rate limiting has a token-shaped twist: because providers limit *tokens* per minute (not just requests), and requests vary enormously in token count, the gateway often limits on **tokens**, not just request count — a few huge requests can exhaust a token-per-minute limit that a request-count limit would miss. Classic algorithms (token bucket, sliding window) apply, adapted to count tokens. The gateway enforces these per-key/user/team so limits are both respected upstream (providers) and fair downstream (your consumers).

## Quotas and budgets

Where rate limiting controls *speed*, **quotas and budgets** control *total consumption* — the spend dimension, which for LLMs is where the scary numbers live:
- **Budgets** — a maximum spend per period (per team, app, key, or user) per day/week/month. When a consumer approaches or hits its budget, the gateway can alert, throttle, or block further calls. This is the direct defense against the runaway-cost nightmare: a bug that would burn thousands hits its budget and stops.
- **Quotas** — a cap on usage units (tokens or requests) over a period, similar in spirit to budgets but counted in usage rather than dollars.
- **Per-consumer allocation** — because the gateway attributes every call to a key/team (it's the choke point), it can enforce *different* budgets for different teams and give each its own allocation — real chargeback and cost governance, impossible without central mediation.

The transformative capability here is **enforced, attributed spend control.** Without a gateway, AI spend is often a single undifferentiated bill you discover after the fact, with no way to attribute or cap it. With gateway budgets, spend is *pre-emptively* limited per consumer and *attributed* to who spent it — turning AI cost from an uncontrolled, after-the-fact surprise into a governed, allocated, capped resource. For finance and platform teams, this is frequently the single most valuable thing a gateway provides.

## Enforcement behavior: throttle, degrade, or block

When a limit or budget is hit, the gateway needs a defined behavior, and the choice matters:
- **Throttle** — slow the consumer (queue or delay) rather than hard-fail, smoothing spikes.
- **Block** — reject calls (a clear rate-limit/quota error) once the limit is reached — the safe default for hard budgets.
- **Degrade** — route to a cheaper model when a budget is nearly exhausted, preserving service at lower cost (a nice pattern combining this with routing, post 3).
- **Alert** — warn (at, say, 80% of budget) before enforcing, so humans can react before service is cut.

Pick behavior per limit and per stakes: a soft warning at 80% and a hard block at 100% for a budget; throttling for rate limits to smooth bursts; degrade-to-cheaper for graceful cost control. Make the enforcement *response* clear to callers (a proper error with the reason, like the API error-design principles) so apps can handle it, not just mysteriously fail.

## Tying it together

Rate limiting, quotas, and budgets make the gateway the enforcement point for *how much* and *how fast* — the governance counterpart to the reliability and caching that control *how well* and *how cheaply*. All of it depends on the gateway's position: because every call is mediated and attributed at one point, limits are enforceable and spend is attributable, which is simply not achievable with direct provider calls. This is where the gateway stops being merely a performance/reliability layer and becomes a genuine *control plane* for AI usage across the organization — protecting the budget, the providers, and fairness, all from one place. And it depends on knowing usage and cost per call, which comes from the observability layer — the subject of the next post.

## Key takeaways

- Limits enforced **inside each app** are unreliable (apps don't see each other, new/misbehaving apps ignore them); enforced at the **gateway** they're comprehensive and unavoidable — every call is subject to them and none can route around.
- Separate two concerns: **rate** (how *fast* — requests/tokens per unit time, protecting throughput and providers' per-key limits) and **spend** (how *much* total — protecting budget); you can violate either while respecting the other.
- **Rate limiting** stays under provider limits, ensures fairness across consumers, and caps runaway/abuse — and for LLMs often limits on **tokens** not just request count (a few huge requests exhaust token-per-minute limits).
- **Quotas and budgets** cap total consumption per team/app/key/user and can alert/throttle/block near the limit — the direct defense against runaway-cost surprises; because the gateway attributes every call, it enables **per-consumer budgets and chargeback**, turning AI spend from an after-the-fact undifferentiated bill into a governed, attributed, capped resource.
- Define **enforcement behavior** per limit (throttle to smooth, block for hard budgets, degrade-to-cheaper-model, alert at 80%) with clear errors to callers — this is what makes the gateway a genuine **control plane** for AI usage, dependent on its choke-point position and on observability's per-call cost data.

## Further reading

- [Rate limiting — overview](https://en.wikipedia.org/wiki/Rate_limiting)
- [LiteLLM — budgets and rate limits](https://docs.litellm.ai/)
