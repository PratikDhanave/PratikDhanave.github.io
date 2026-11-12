# Building the Provider Platform — Fan-Out, Endpoint Health, and the Art of Delivering to Strangers

*The moment your product offers webhooks, you've signed up to run a delivery platform: fan-out to thousands of endpoints you don't control, operated by teams of wildly varying competence, every one of them capable of being slow, down, or misconfigured — without letting any of them degrade the others or your own system. This post is the provider's view: the architecture, the per-endpoint health machinery, and the policy decisions that separate a webhook feature from a webhook platform.*

Posts [2](/blog/posts/hook-02-delivery-semantics.html)–[6](/blog/posts/hook-06-thin-events-fat-events.html) equipped the receiver; this post crosses the table. It's worth reading even if you never provide webhooks — nothing improves your receiving like understanding what the delivery fleet on the other side is managing around you.

## The delivery pipeline

The provider architecture mirrors the receiver's (post 5) at larger scale: **capture** — domain events emit onto an internal stream at the moment of state change, with the transactional-outbox discipline ensuring an event is recorded iff the state change committed (no ghost events, no silent gaps); **match** — subscriptions filter the stream per endpoint (customers subscribe to event types; coarse filters here save entire delivery volumes downstream); **fan-out** — one domain event becomes N delivery jobs, each an independent unit with its own retry state, signed (post 4) at delivery time per endpoint secret; **deliver** — worker fleets execute jobs with tight timeouts, no redirects, and the SSRF containment post 4 specified. The load-bearing property is **per-endpoint isolation**: every endpoint gets its own logical queue and retry budget, because the alternative — a shared queue — lets one big customer's dead endpoint consume the fleet's capacity and delay everyone's deliveries. One slow stranger must cost only themselves.

## Endpoint health: the actuarial core

Operating deliveries to strangers is actuarial work — classifying endpoints by observed behavior and adjusting treatment:

- **Health scoring** per endpoint: success rate, latency distribution, consecutive-failure streaks. Healthy endpoints get full throughput; degrading ones get backoff (post 2's machinery, applied per destination).
- **Suspension policy** — the decision nobody wants to automate but must: an endpoint failing for days, burning retry capacity with no sign of life, eventually gets *disabled*. The policy's shape matters more than its thresholds: warn early (email at hours-of-failure, not after disabling), disable visibly (dashboard banner, notification with re-enable path), and retain the missed events for redelivery (below). Silent disabling is how providers convert their customer's outage into their customer's data loss — and their own support escalation.
- **Misbehavior classes** beyond downness: endpoints that answer 200 instantly and process nothing (the "ack-everything" anti-receiver — undetectable, which is why it's the receiver's sin, not yours to fix), endpoints that time out at exactly your limit (tighten with jitterless patience), and endpoints behind corporate proxies that eat bodies (document, shrug).

## The platform features that separate good from adequate

The difference between "we POST JSON" and a platform receivers trust is a short feature list, each item earning disproportionate goodwill: **delivery logs** customers can see (per-event attempt history, response codes, bodies-on-failure — self-service debugging that eliminates half of webhook support tickets); **manual and bulk redelivery** (the companion to suspension retention: "replay everything since Tuesday" turns receiver incidents into receiver non-events — and assumes their idempotency, which your docs should preach, post 3); **test and sandbox tooling** (fire synthetic events on demand, per [Testing at Scale](/blog/series/testing-at-scale/)'s environments chapter); **secret rotation with overlap** (dual-signing windows, post 4); and **an event-feed fallback** (the cursor-paged pull API post 6 praised — offering it beside push costs little and gives integrators the reconciliation primitive post 8 will demand anyway). Underneath all of it: your own observability per post 5's dashboard, aggregated per endpoint *and* per event type, because "deliveries are slow" is a different incident than "one customer's endpoint is dying."

The takeaway: providing webhooks is running a delivery platform — **outbox-captured events, per-endpoint filtered fan-out, signed deliveries through contained workers, and above all per-endpoint isolation** so strangers' failures stay their own. Operate endpoints actuarially: health scores, per-destination backoff, and a **suspension policy that warns early, disables visibly, and retains for redelivery**. The trust-earning features are known: visible delivery logs, bulk replay, test events, rotation overlap, and a pull-feed fallback. Build those and receivers can hold up their half of the contract this series keeps describing; skip them and every integration inherits your gaps as their incidents.

## Key takeaways

- Pipeline: **capture (transactional outbox) → match (subscription filters) → fan-out (per-endpoint jobs, signed per secret) → deliver (contained workers)** — with per-endpoint queues/budgets as the non-negotiable isolation property.
- Treat endpoints **actuarially**: health scoring, per-destination backoff, misbehavior classes — one slow stranger costs only themselves.
- **Suspension done right**: warn early, disable visibly with a re-enable path, retain missed events for redelivery — silent disabling converts customer outages into data loss.
- The platform short-list that buys trust: **delivery logs, bulk redelivery, test events, secret-rotation overlap, and a cursor-paged event feed** beside push.
- Observe per endpoint *and* per event type — fleet-wide slowness and one dying destination are different incidents.

## Further reading

- [Rate limiting — the pressure-control discipline fan-out depends on](https://en.wikipedia.org/wiki/Rate_limiting)
- [Multitenancy — isolating tenants who share your infrastructure](https://en.wikipedia.org/wiki/Multitenancy)
