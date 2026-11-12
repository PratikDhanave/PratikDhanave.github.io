<!-- Markdown version for AI agents and readers. Canonical: https://pratikdhanave.com/blog/posts/hook-01-why-webhooks-are-hard.html -->

# Why Webhooks Are Hard — The Contract Nobody Reads

*Webhooks look like the easiest integration pattern in software: the provider POSTs you JSON when something happens. Then production arrives — events show up twice, out of order, late, or not at all; a deploy drops an hour of deliveries; a signature check fails silently — and the team discovers that webhooks are a distributed system whose other half they don't control. This series is the missing engineering discipline for both sides of that contract.*

Webhooks are how the SaaS economy synchronizes — payments, deployments, messages, signatures, tickets all propagate between companies as HTTP callbacks. The pattern's reputation for flakiness is really a reputation for *unread contracts*: the delivery semantics are published, loose, and almost universally designed against as if they were strict. This opening post states the real contract and maps the discipline the rest of the series builds.

## The real contract

Strip any provider's webhook documentation to its load-bearing clauses and the same contract emerges:

- **At-least-once, not exactly-once.** The provider retries until your endpoint acknowledges. Network timeouts after your successful processing mean redelivery — so *duplicates are a certainty of the design*, not a provider defect. (The deeper reasons live in post 2.)
- **Ordering is not promised.** Retries, parallel delivery workers, and multiple event sources mean the `updated` event can arrive before the `created` one. Systems assuming sequence are betting against the documentation.
- **Delivery is not guaranteed, eventually.** Retry schedules end. An endpoint down past the window (a long incident, an expired certificate, a forgotten URL migration) misses events *permanently* — which is why reconciliation (post 8) is part of webhook architecture, not an admission of defeat.
- **Your latency is their problem, so it becomes yours.** Slow handlers back up provider queues; providers respond with timeouts, suspensions, and disabled endpoints. The receiving architecture (post 5) exists largely to answer in milliseconds regardless of processing cost.
- **The payload is a point-in-time claim.** By the time an event arrives — or is retried a day later — the resource may have changed again. Treating stale payloads as current truth is the subtle corruption source; post 6's thin-event pattern is the systematic answer.

None of these clauses is hidden. Engineering against the contract-as-written, rather than the contract-as-wished, is essentially the whole discipline.

## Why the contract can't be stricter

The temptation is to blame providers; the physics says otherwise. Exactly-once delivery across independently operated systems over HTTP would require distributed transactions between strangers; ordered delivery would serialize throughput through per-recipient bottlenecks and let one slow consumer brake a fleet; guaranteed delivery would mean unbounded retention for endpoints that may never return. Every provider lands on the same trade — at-least-once, unordered, bounded retention — because it's the one that scales across millions of endpoints they don't operate. The consequence for receivers is liberating once accepted: **the provider delivers possibilities; your system establishes truth.** Idempotency (post 3), verification (post 4), durable intake (post 5), fetch-on-event (post 6), and reconciliation (post 8) are how.

## The series map

The discipline splits by role. **Receiving well** — post 2 (delivery semantics and retries, the theory under the contract), post 3 (idempotent consumption and ordering recovery), post 4 (security: signatures, replay, SSRF), post 5 (the durable intake architecture: queue-behind-endpoint, DLQs, poison events). **Choosing shapes** — post 6 (thin vs fat events, fetch-on-event, events vs polling). **Providing well** — post 7 (building the delivery platform: fan-out, per-endpoint health, suspension policy — the view from the other side, which makes anyone a better receiver). **Closing the loop** — post 8 (reconciliation and durable sync: the backstop that turns webhooks from a hope into a guarantee). The connective theme is the one this post earns: webhooks are not notifications; they're *replicated state synchronization over an unreliable channel*, and every pattern in the series is a standard distributed-systems answer wearing integration clothes.

The takeaway: the webhook contract — at-least-once, unordered, bounded-retention, latency-sensitive, point-in-time payloads — is loose by necessity, not negligence; exactly-once and ordering don't survive contact with millions of independently operated endpoints. The failure pattern is designing against the contract you wish existed. The discipline is accepting that **the provider delivers possibilities and the receiver establishes truth** — through idempotency, verification, durable intake, fetch-on-event, and reconciliation — which is exactly the map this series walks.

## Key takeaways

- The real contract everywhere: **at-least-once** (duplicates are design, not defect), **unordered**, **bounded retries** (missed means missed — reconciliation required), **answer fast or get suspended**, **payloads are point-in-time claims**.
- The contract can't be stricter at scale: exactly-once needs distributed transactions between strangers; ordering serializes fleets behind slow consumers; guarantees need unbounded retention.
- Governing reframe: webhooks are **state synchronization over an unreliable channel** — receiver-side truth-establishment is the job, and every technique is a distributed-systems classic applied to integration.
- Series map: receive (semantics, idempotency, security, intake architecture) → shape (thin vs fat) → provide (the platform side) → close the loop (reconciliation and durable sync).

## Further reading

- [Webhook — the callback pattern itself](https://en.wikipedia.org/wiki/Webhook)
- [Event-driven architecture — the paradigm webhooks extend across company boundaries](https://en.wikipedia.org/wiki/Event-driven_architecture)

---

Author: Pratik Dhanave (https://pratikdhanave.com) | Published: 2026-10-28
Canonical: https://pratikdhanave.com/blog/posts/hook-01-why-webhooks-are-hard.html
Attribution: please link the canonical URL when citing or quoting this post.
