# Payment Orchestration: Routing One Charge Across Many PSPs

*Route a payment across multiple providers to maximize auth rate, with health-aware routing, failover, and normalized webhooks.*

---

## Why one PSP is never enough

The first version of any checkout talks to a single payment service provider. It works until it doesn't: a regional issuer starts declining more of your traffic, your PSP has a bad afternoon, or your blended cost creeps up because every transaction pays the same fee regardless of card type. At scale, a one-point drop in authorization rate is real revenue, and a single provider is a single point of failure you cannot hedge.

The fix is an orchestration layer that sits between your checkout and several PSPs. Your application stops thinking about "Stripe" or "Adyen" and starts thinking about a payment *intent*: an amount, a currency, a payment method, and a set of constraints. The orchestrator decides which provider actually runs the charge, retries a decline against a second provider when that is safe, and hands your application one consistent event stream no matter who processed the money.

This post is about how you build that layer without turning it into a fragile pile of if-statements.

## The shape of the system

At the center is a stateless router fed by two data sources: a set of routing rules and a live health signal per provider. The router picks a provider, an adapter translates the intent into that provider's API, and the outcome flows back through a normalization layer that turns every provider's vocabulary into yours.

```
                         ┌────────────────────┐
   checkout ──intent──▶  │   Orchestrator     │
                         │  (validate + idem)  │
                         └─────────┬──────────┘
                                   ▼
                         ┌────────────────────┐   reads    ┌──────────────┐
                         │   Routing Engine   │ ◀────────  │ rules + health│
                         │ cost / auth / health│            └──────────────┘
                         └───┬──────┬──────┬───┘
                    ┌────────┘      │      └────────┐
                    ▼               ▼               ▼
                ┌───────┐       ┌───────┐       ┌───────┐
                │ PSP A │       │ PSP B │       │ PSP C │
                └───┬───┘       └───┬───┘       └───┬───┘
                    └──── decline? failover ───────┘
                                   ▼
                         ┌────────────────────┐
                         │  Normalization +   │──▶ unified webhooks
                         │   webhook fan-out  │
                         └────────────────────┘
```

> **▸ [Open the interactive diagram](/blog/diagrams/fintech-payment-orchestration-routing.html)** — pan, zoom, and trace every step (light/dark, self-contained).

The orchestrator itself does three boring but critical things before routing: it validates the intent, it enforces idempotency, and it persists the attempt. Idempotency is the piece juniors skip and seniors lose sleep over — every intent carries a client-supplied key, and every provider call carries a derived key so a network timeout never becomes a double charge.

## Deciding where the money goes

The routing engine is where the value lives, and it is worth keeping it small and explainable. Think of it as a scoring function, not a decision tree. Each candidate provider gets a score, and the highest score wins. The inputs are usually the same three concerns:

- **Cost.** Interchange plus provider markup varies by card type, region, and volume tier. A debit card in one market may be cheapest on PSP A; a premium credit card on PSP B.
- **Expected auth rate.** Providers and issuer combinations have measurably different approval odds. You learn this from your own history, bucketed by BIN range, method, and amount band.
- **Health.** A provider that is timing out or degraded should score near zero regardless of how cheap it is.

A first cut can be a plain weighted sum:

```python
def score(provider, intent, stats):
    if not provider.healthy:
        return 0.0
    auth = stats.auth_rate(provider, intent.bin, intent.method)
    cost = provider.cost_for(intent)          # lower is better
    return (W_AUTH * auth) - (W_COST * cost)

def choose(providers, intent, stats):
    ranked = sorted(providers, key=lambda p: score(p, intent, stats),
                    reverse=True)
    return [p for p in ranked if score(p, intent, stats) > 0]
```

Note that `choose` returns an ordered *list*, not one provider. That ordering is your failover sequence, computed once, up front. Keeping the weights in config rather than code lets a payments analyst tune behavior without a deploy, and returning a ranked list keeps routing and failover as one coherent decision instead of two systems that can disagree.

## Health-aware routing without flapping

The health signal is what separates a real orchestrator from a load balancer. You want to route away from a degraded provider quickly, but you do not want a couple of unlucky declines to yank all traffic off a healthy one. That is a classic circuit-breaker problem.

Track a rolling window per provider — success rate, latency, and error class over the last N seconds. When the error rate crosses a threshold, the breaker opens and the provider's health score drops to zero, so the router simply stops selecting it. After a cooldown, the breaker goes half-open: you let a trickle of traffic through, and if it succeeds you close the breaker and restore full weight. The key discipline is to distinguish *soft* declines (issuer said no — this is normal business, not a provider fault) from *hard* failures (timeouts, 5xx, malformed responses). Only hard failures should move the health needle. Counting normal declines as failures will trip your breakers during a perfectly healthy fraud spike.

## Failover that does not double-charge

When a provider returns a retryable decline or a hard failure, the orchestrator walks to the next provider in the ranked list. The rule that makes this safe: **only retry declines that are provider-attributable or explicitly retryable.** An "insufficient funds" or "do not honor" is the issuer's final answer — retrying it on another PSP wastes money, annoys the issuer, and can look like card testing. A timeout, a gateway error, or a "try again" soft decline is fair game.

```
attempt on PSP A ──▶ hard fail / retryable ──▶ attempt on PSP B ──▶ success
                └──▶ issuer hard decline ─────────────────────────▶ stop, report decline
```

Two guardrails keep failover honest. First, a per-intent attempt budget — cap it at two or three providers so a bad night doesn't turn one checkout into a fan-out storm. Second, that derived idempotency key per provider attempt, so if PSP A actually captured the payment but the response was lost to a timeout, retrying on PSP B and later reconciling A won't leave you having charged twice. Reconciliation, not optimism, is what catches the ambiguous cases.

## One event stream out of many

Every PSP has its own webhook schema, its own decline code taxonomy, and its own idea of what an event even is. If you let those differences leak into your application, every downstream consumer — ledger, emails, analytics, fraud — has to know about all of them. The normalization layer is the anti-corruption boundary.

Each provider adapter maps inbound webhooks to a canonical internal event: `payment.authorized`, `payment.captured`, `payment.failed`, `payment.refunded`, with a normalized decline reason drawn from your own enum rather than the raw provider code. You verify the provider's signature at the adapter, dedupe on the provider event id (webhooks are at-least-once, so you *will* get duplicates), correlate back to the original intent, and only then emit your internal event. Downstream systems subscribe to your vocabulary and never learn a provider's.

That single normalized stream is also what makes the whole orchestrator observable. Because every attempt and every outcome is expressed in one schema, auth rate by provider, failover frequency, and blended cost fall out of the same event log you already keep — which is exactly the data the routing engine needs to get smarter next quarter. The loop closes on itself: normalized events feed the stats that feed the scores that choose the next route.

## Where to start

Do not build all of this on day one. Start with two providers, a static priority order, and clean normalization — that alone buys you failover and one event stream. Add the scoring function once you have enough of your own outcome data to trust it, and add circuit breakers the first time a provider has a bad day. The architecture above is the destination; the value shows up long before you arrive.
