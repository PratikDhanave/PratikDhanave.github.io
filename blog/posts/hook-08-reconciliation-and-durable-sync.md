<!-- Markdown version for AI agents and readers. Canonical: https://pratikdhanave.com/blog/posts/hook-08-reconciliation-and-durable-sync.html -->

# Reconciliation and Durable Sync — The Backstop That Makes Webhooks Trustworthy

*Everything in this series hardened the event path — and post 1's contract still stands: delivery is not guaranteed, eventually. Endpoints stay down past retry horizons, subscriptions get misconfigured, providers have incidents too, and events from before your integration existed never arrive at all. The final discipline accepts this and closes the loop: periodic reconciliation against the source of truth, convergence-oriented sync design, and the backfill machinery that makes "we missed a week" a procedure instead of a crisis. This is what turns a webhook integration into a synchronization system.*

This closing post is where the series' reframe — webhooks as state synchronization over an unreliable channel ([post 1](/blog/posts/hook-01-why-webhooks-are-hard.html)) — pays off in architecture: the event path for latency, the reconciliation path for truth, by design rather than apology.

## Reconciliation: the slow loop that catches everything

The pattern is the billing world's reconciliation ([bill-08](/blog/posts/bill-08-revenue-integrity.html)) applied to integration state: on a schedule, compare your replicated state against the provider's API and converge the differences.

- **Sweep by modification time.** The workhorse: periodically list resources changed since the last sweep (minus an overlap margin for clock skew) and version-gated-upsert each (post 3's machinery, reused verbatim — reconciliation is just fetch-on-event without the event). A resource the sweep finds changed but no event touched is a **missed delivery, now healed** — and counted, because that count is the event path's true reliability metric, measured rather than assumed.
- **Detect deletions deliberately.** Modified-since sweeps can't see deletions (deleted things stop appearing). If deletions matter, you need full-set comparison (paged ID listing against local IDs) at a slower cadence, or a provider deletion feed — choose per resource type by how much a ghost record costs.
- **Tier the cadences.** Hot, money-adjacent resources reconcile hourly; warm state daily; full-set deletion sweeps weekly. The cost is API read quota (post 6's amplification discussion); the dial is per-type cadence, not whether.
- **Reconcile within the grace reality.** A sweep racing in-flight events will briefly disagree with itself; version gates make this harmless (older write loses), which is precisely why reconciliation *requires* the version discipline rather than merely benefiting from it.

## Backfill: history as a first-class operation

Three moments demand replaying the past at bulk: **day one** (the integration starts mid-history — initial sync is a paged walk of current state, after webhooks are already flowing so the gap between snapshot and live stream self-heals via version gates); **after an incident** (yours or theirs — re-sweep the affected window, or bulk-redeliver if the provider offers it, post 7); and **after a logic fix** (your handler was wrong for a month; the events were fine — re-derive from stored raw events, post 5's persisted intake paying out, or re-fetch the affected set). The engineering requirements are the same trio each time: bounded, resumable batches (checkpointed cursors, not one heroic loop); throttling that respects both sides' rate limits; and idempotent application so backfill can overlap live traffic — which, after post 3, it already can. Teams that treat backfill as a built, tested procedure change their whole relationship with webhook risk: missed events stop being feared because *recovery is rehearsed*.

## Durable sync: the end-state architecture

Assemble the series and the destination architecture names itself — a **sync engine** per integrated provider: the durable intake (post 5) feeding version-gated, idempotent upserts (post 3) through fetch-on-event (post 6), beside a tiered reconciliation loop and rehearsed backfill, with the missed-event counter as its honesty meter. Events make it fast; reconciliation makes it true; backfill makes it recoverable. Each layer covers the one above: a dropped event is caught by the sweep, a sweep gap by the full-set pass, a logic error by replay from raw intake. The emotional shift is the real deliverable — webhook integrations stop being anxious best-effort listeners and become boring replication systems with known convergence bounds ("every resource correct within an hour, always"), which is what the business actually wanted when someone said "just add the webhook."

The takeaway: webhooks need a backstop because non-delivery is in the contract — so build the **slow loop**: modified-since sweeps with version-gated upserts (healing and *counting* missed deliveries), deliberate deletion detection, tiered cadences priced in API quota; and make **backfill** a rehearsed, resumable, throttled, idempotent procedure for day-one, post-incident, and post-fix replays. The end state is a sync engine where events provide latency, reconciliation provides truth, and replay provides recovery — layered coverage with measurable convergence. That's the series' closing promise: not webhooks that never fail, but synchronization that doesn't care when they do.

## Key takeaways

- Reconciliation = **fetch-on-event without the event**: modified-since sweeps (with overlap margin) through the same version-gated upserts; healed differences are **missed deliveries, counted** — your event path's real SLO.
- **Deletions need their own detection** (full-set compare or deletion feeds) — modified-since is structurally blind to them.
- **Tier cadences** by resource temperature; the cost is read quota, the dial is per-type frequency.
- **Backfill is a rehearsed procedure** — checkpointed batches, bilateral throttling, idempotent overlap with live traffic — for day-one sync, incident windows, and logic-fix replays (raw intake storage pays off here).
- End state: a **sync engine** — events for latency, reconciliation for truth, replay for recovery — with convergence bounds you can state out loud.

## Further reading

- [Change data capture — the discipline of propagating state changes between systems](https://en.wikipedia.org/wiki/Change_data_capture)
- [Eventual consistency — the convergence model durable sync delivers](https://en.wikipedia.org/wiki/Eventual_consistency)

---

Author: Pratik Dhanave (https://pratikdhanave.com) | Published: 2026-11-04
Canonical: https://pratikdhanave.com/blog/posts/hook-08-reconciliation-and-durable-sync.html
Attribution: please link the canonical URL when citing or quoting this post.
