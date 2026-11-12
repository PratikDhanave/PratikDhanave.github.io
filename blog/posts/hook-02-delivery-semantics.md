<!-- Markdown version for AI agents and readers. Canonical: https://pratikdhanave.com/blog/posts/hook-02-delivery-semantics.html -->

# Delivery Semantics — At-Least-Once, Retries, and the Exactly-Once Myth

*Every delivery guarantee is a bet about failure, and webhook systems inherit the oldest result in distributed messaging: between two parties over an unreliable channel, you can deliver at-most-once or at-least-once, but exactly-once delivery is not on the menu — only exactly-once effect, manufactured by the receiver. This post builds that result from first principles and derives the retry machinery both sides need: schedules, backoff, jitter, and the acknowledgment discipline that makes them work.*

Post [1](/blog/posts/hook-01-why-webhooks-are-hard.html) stated the contract; this post explains why it reads that way — the semantics layer everything else in the series stands on.

## The two-generals shape of a POST

A webhook delivery is one question: did the receiver process this event? The provider knows only what the HTTP response tells it — and the response can be lost independently of the processing. Four outcomes matter: delivered-and-acked (fine), undelivered (timeout, connection refused — fine, retry), delivered-but-the-ack-was-lost (receiver processed; provider saw a timeout), and delivered-but-processing-failed-after-ack (receiver acked, then crashed). The third outcome forces the fundamental choice. **Retry** on ambiguity and the receiver sometimes sees duplicates: at-least-once. **Don't retry** on ambiguity and the receiver sometimes misses events: at-most-once. There is no third option, because the channel can always eat the acknowledgment — that's the two-generals problem in miniature. Providers choose at-least-once because missed events corrupt silently while duplicates corrupt loudly — and loud corruption can be engineered away (post 3) while silent loss can only be reconciled later (post 8).

"Exactly-once delivery" claims always decompose, on inspection, into at-least-once delivery plus receiver-side deduplication — exactly-once *processing*, built where it can only be built: at the effect. That's post 3's whole subject; this post's job is to make the retry side worth consuming.

## Retry schedules: pressure management, not politeness

Given at-least-once, retries are the mechanism, and their design is pressure management across two independently operated systems:

- **Exponential backoff** — because failures are temporally correlated: the receiver that just failed is probably still failing. Immediate retries convert one failure into a self-inflicted load test on a struggling endpoint; doubling intervals (seconds → minutes → hours) probe recovery without piling on.
- **Jitter** — because synchronized retries re-create the outage they're responding to. A provider whose deliveries to a big receiver all failed at 12:00 must not retry them all at 12:01; randomizing within the backoff window spreads the thundering herd. (The same logic the receiver's own outbound retries need.)
- **A bounded horizon with a declared end** — schedules that stretch over ~days cover realistic incident lengths; beyond that, retention costs and staleness make redelivery pointless. What matters is that the horizon is *published* and the end state is *visible*: dead-lettered on the provider side, surfaced in a dashboard, recoverable by redelivery request or reconciliation.
- **Per-endpoint isolation** — one receiver's outage must not consume the delivery capacity of others; queues and retry budgets partition per destination. This is the provider-side architecture of post 7, but receivers should *assume* it: your outage is burning your own budget, and recovery order on return is not promised — another reason ordering assumptions (post 3) die here.

## The receiver's half of the semantics

Delivery semantics are bilateral, and the receiver controls more than it thinks. **Acknowledge delivery, not processing**: return 200 the moment the event is durably *accepted* (post 5's queue), not after business logic completes — this shrinks the ambiguity window that creates duplicates, and keeps you inside the provider's timeout regardless of processing cost. **Be deliberate with status codes**: 2xx means accepted (no retry); 5xx and timeouts mean retry; 4xx conventionally means *don't* retry — so returning 400 on a transient internal error quietly converts a recoverable failure into permanent event loss, one of the most common self-inflicted webhook wounds. **Fail loudly into the retry window**: when your intake is genuinely down, being *down* (connection refused) is better than being *wrong* (200 with a dropped event) — the provider's retry machinery is your safety net, but only if you let it see failure.

The takeaway: a webhook POST is the two-generals problem in miniature — the acknowledgment can always be lost, so the only honest choices are at-most-once (silent loss) or **at-least-once (loud duplicates)**, and providers rightly choose loud. Exactly-once exists only as receiver-manufactured *effect*. The retry machinery that makes at-least-once livable is pressure engineering — exponential backoff against correlated failure, jitter against thundering herds, bounded published horizons with visible dead-letter ends, per-endpoint isolation — and the receiver completes the semantics by acking on durable acceptance, using status codes as the protocol they are, and failing visibly into the retry window rather than invisibly out of it.

## Key takeaways

- The ack can always be lost → **at-least-once or at-most-once; exactly-once delivery is a myth** — only exactly-once *effect*, built by the receiver (post 3).
- Providers choose duplicates over loss because **loud corruption is engineerable, silent loss is only reconcilable**.
- Retry design = **backoff** (correlated failures), **jitter** (herd prevention), **bounded, published horizon** with a visible dead-letter end, **per-endpoint isolation** — and no recovery-order promises.
- Receiver semantics: **ack on durable acceptance** (not processing), honor the status-code protocol (4xx = no retry — never 400 a transient error), and when down, be *visibly* down so the retry net catches you.

## Further reading

- [Exponential backoff — spacing retries against correlated failure](https://en.wikipedia.org/wiki/Exponential_backoff)
- [Two Generals' Problem — why the acknowledgment can never be certain](https://en.wikipedia.org/wiki/Two_Generals%27_Problem)

---

Author: Pratik Dhanave (https://pratikdhanave.com) | Published: 2026-10-29
Canonical: https://pratikdhanave.com/blog/posts/hook-02-delivery-semantics.html
Attribution: please link the canonical URL when citing or quoting this post.
