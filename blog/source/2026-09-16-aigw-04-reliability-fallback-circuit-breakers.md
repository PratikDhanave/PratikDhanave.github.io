# Reliability: Fallback, Retries, and Circuit Breakers

*Model providers go down, rate-limit you, and time out — regularly. If your application calls one provider directly, its reliability is capped at that provider's. An AI gateway breaks that ceiling: because it can route across providers, a failure on one becomes a transparent retry on another. This post covers the reliability patterns that turn provider outages into non-events.*

Routing and load balancing (previous post) set up the capacity to fail over across. This post uses it: retries, fallback across providers, and circuit breakers, so a provider problem doesn't become your outage. These are classic distributed-systems reliability patterns, applied to the specific failure modes of model APIs — which fail *often* enough that reliability engineering isn't optional.

## The failure modes of model APIs

Model provider calls fail in characteristic ways, more often than most backend dependencies:
- **Rate limiting (429)** — you exceeded a per-key request or token limit. Extremely common at scale.
- **Timeouts and slow responses** — generation latency is variable and occasionally very high; a call can hang far past your budget.
- **Transient errors (5xx)** — provider-side overload or hiccups, often recoverable on retry.
- **Outages** — a provider or a specific model is degraded or down for a stretch.
- **Content/validation errors (4xx)** — a bad request; *not* recoverable by retrying unchanged (like the retryable-vs-terminal distinction in API error design).

The key insight: **model APIs fail frequently enough that reliability must be engineered, not hoped for.** A direct-call app inherits every one of these failures raw. The gateway's job is to absorb the recoverable ones so applications rarely see them.

## The request flow with reliability built in

Here's how a request moves through a reliability-aware gateway — cache first, route to a primary, fail over on trouble, then meter and return:

```
 Application        AI Gateway        Cache   Primary    Fallback   Observability
     │  POST /chat     │                │         │          │            │
     │────────────────▶│  semantic lookup                                 │
     │                 │───────────────▶│                                  │
     │                 │◀── miss ───────│                                  │
     │                 │  route (within budget)                            │
     │                 │─────────────────────────▶│  timeout / 503        │
     │                 │◀── error ────────────────│                        │
     │                 │  failover (circuit open)  │                       │
     │                 │─────────────────────────────────────▶│ completion │
     │                 │◀── completion ────────────────────────│           │
     │                 │  store response ──▶ cache;  log+cost+trace ──────▶│
     │◀── 200 ─────────│                                                    │
```

> **▸ [Open the interactive sequence diagram](/blog/handbook-diagrams/ai-gateway-request-flow.html)** — pan, zoom, and trace every message (light/dark, self-contained).

The application sent one request and got one response. Behind that, the gateway checked the cache, tried the primary provider, absorbed its failure, and transparently completed on a fallback — none of which the app had to know about. That transparency is the whole point of putting reliability in the gateway.

## Retries with backoff

The first line of defense against *transient* failures is **retrying** — but retrying correctly:
- **Only retry retryable failures** — timeouts, 429s, and 5xx are worth retrying; 4xx validation errors are not (they'll fail identically). Retrying a terminal error just wastes time and money.
- **Use exponential backoff with jitter** — wait progressively longer between attempts, with randomness, so you don't hammer a struggling provider or create a synchronized retry stampede across many clients. (The same backoff discipline from distributed systems and API design.)
- **Bound the retries** — a maximum attempt count and an overall deadline, so a doomed request fails fast rather than retrying forever and blowing your latency budget.
- **Respect `Retry-After`** — when a provider tells you how long to wait (on a 429), honor it.

Retries handle the blips. But retrying the *same* provider doesn't help when that provider is genuinely down — which is where fallback comes in.

## Fallback across providers

**Fallback** is the gateway's superpower that a direct call can never have: when the primary model/provider fails (after retries), route the *same request* to a *different* provider or model. Because the unified API (post 2) makes providers interchangeable, the gateway can send the identical request to an alternate and return its result — and the application never knows the primary was down.

This is what breaks the reliability ceiling. A direct-call app's uptime equals its one provider's uptime. A gateway with fallback across two independent providers has *combined* availability far higher, because both must be down simultaneously to fail. Fallback chains (primary → secondary → tertiary, possibly a cheaper or self-hosted model as last resort) turn provider outages into slightly-degraded-at-worst service. Two design notes: order the chain by preference (quality/cost), and be aware that a fallback model may behave slightly differently — acceptable degradation, but know it's happening.

## Circuit breakers

Retrying and failing over on *every* request to a *dead* provider is wasteful — you pay the timeout latency each time before failing over. The **circuit breaker** pattern (from distributed systems) fixes this: track a provider's recent failures, and when they cross a threshold, "open the circuit" — stop sending requests to that provider entirely for a cooldown period, failing over immediately instead of trying-then-timing-out. After the cooldown, "half-open" — send a trial request; if it succeeds, close the circuit and resume; if not, stay open.

The circuit breaker turns "try the dead provider, wait for timeout, then fail over" (slow, repeated on every request) into "provider is known-down, fail over instantly" (fast). It's what makes fallback *efficient* during a sustained outage rather than paying the failure cost on every call. Combined with health-aware load balancing (post 3), it lets the gateway route traffic away from a struggling backend automatically and route it back when it recovers.

## The gateway's own reliability

One honest caveat that echoes post 1: the gateway now sits in the critical path of every model call, so **its own reliability is paramount** — all this failover is worthless if the gateway itself is a single point of failure. A production gateway must be run highly available (redundant instances, health checks, no single choke that can take everything down). You've concentrated reliability logic in one place, which is powerful, but it means that place must be more reliable than anything behind it. Engineering the gateway's own uptime is the price of the reliability it provides.

## Key takeaways

- Model APIs fail **frequently** (429 rate limits, timeouts, 5xx overload, outages, plus non-retryable 4xx) — a direct-call app's reliability is capped at its one provider's, so reliability must be *engineered* at the gateway.
- **Retry** only retryable failures (timeouts/429/5xx, not 4xx), with **exponential backoff + jitter**, bounded attempts/deadline, and respect for `Retry-After` — retries handle transient blips.
- **Fallback across providers** is the gateway's superpower (enabled by the unified API): on primary failure, send the *same request* to a different provider transparently — breaking the single-provider reliability ceiling, since both must be down at once to fail.
- **Circuit breakers** stop hammering a dead provider — after a failure threshold, "open" and fail over *instantly* (skip the timeout), then "half-open" a trial before resuming — making fallback efficient during sustained outages.
- The gateway now sits in **every** call's critical path, so its **own high availability is paramount** — all this failover is moot if the gateway itself is a single point of failure; engineering its uptime is the price of the reliability it provides.

## Further reading

- [Martin Fowler — CircuitBreaker](https://martinfowler.com/bliki/CircuitBreaker.html)
- [Circuit breaker design pattern — overview](https://en.wikipedia.org/wiki/Circuit_breaker_design_pattern)
