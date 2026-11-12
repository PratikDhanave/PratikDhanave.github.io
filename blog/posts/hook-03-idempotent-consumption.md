<!-- Markdown version for AI agents and readers. Canonical: https://pratikdhanave.com/blog/posts/hook-03-idempotent-consumption.html -->

# Idempotent Consumption — Manufacturing Exactly-Once at the Receiver

*Post 2 ended with the only honest promise available: at-least-once delivery, duplicates included. This post builds the receiver that makes duplicates harmless and disorder survivable — the dedup store, the effect-level idempotency that outranks it, and the versioned-state techniques that let events arrive in any order and still converge on the truth. This is where "exactly-once" actually gets manufactured.*

The techniques here are the webhook-shaped versions of old friends from the [Fintech Engineering Handbook](/blog/series/the-fintech-engineering-handbook/)'s idempotency chapter and [distributed systems](/blog/series/distributed-systems-from-first-principles/) generally — applied at the integration boundary where you control only one side.

## Layer one: event-ID deduplication

Every well-designed webhook event carries a unique event ID, and the first defense is the obvious one: keep a store of processed IDs; on arrival, attempt to record the ID; if it already exists, acknowledge and stop. Three details separate the robust version from the naive one. **The check must be an atomic claim** — a read-then-process-then-write sequence has a race where two concurrent deliveries of the same event both pass the read; the correct shape is an atomic insert-if-absent (unique constraint, conditional put) that exactly one delivery wins. **Claim at the right moment** — claim-then-process risks a crash after claim leaving the event marked done but unprocessed; the stricter pattern claims *within the same transaction as the effect* (next section) or records the claim only on completion while tolerating the resulting re-execution window. **Retention is part of the contract** — dedup entries can expire only after the provider's published retry horizon (post 2) plus your reconciliation window; expiring them in hours to save storage reopens the duplicate door exactly when late retries walk through it.

## Layer two: idempotent effects — the stronger property

Event-ID dedup treats delivery as the thing to make unique. The deeper discipline makes the *effect* idempotent, so even a redelivery that slips the dedup net (or a replay you trigger deliberately during recovery — post 8) lands harmlessly:

- **Natural idempotency by shape** — prefer absolute operations: "set subscription to canceled" re-applies harmlessly; "decrement seat count" doesn't. Where the domain forces relative operations, attach the event ID to the effect (the ledger-entry pattern: one entry per event ID, enforced by constraint).
- **Transactional outcome recording** — process the event and record its ID *in the same local transaction* as the state change. Crash before commit: clean retry. Crash after: dedup catches the redelivery. This small pattern is the actual exactly-once machine.
- **Idempotent downstream calls** — your handler often triggers further side effects (emails, API calls, charges). Each needs its own idempotency key derived from the event ID, or you've deduplicated the entry and duplicated the exit.

## Layer three: surviving disorder

Unordered delivery (post 1) means `customer.updated` can arrive before `customer.created`, or two updates can arrive reversed. Ordering recovery has a toolkit, chosen by how much the payload can be trusted:

- **Version-stamped state** — the best providers put a version/sequence (or at least a resource-level `updated_at`) on every event; the receiver applies an event only if its version exceeds the stored one. Stale arrivals are acknowledged and dropped — convergence without ordering.
- **Fetch-on-event** — when payloads can't carry trustworthy versions, treat the event as a *doorbell*: on any change event, fetch the resource's current state from the API and upsert. Duplicates and disorder both collapse into "fetch again, converge again." (This is post 6's thin-event pattern arriving early, because it solves ordering as a side effect.)
- **Parking for prerequisites** — the update-before-create case: park events whose referenced resource doesn't exist yet (short-delay requeue), and let the create — or a fetch — release them. Bounded parking with escalation, not infinite patience.
- **Last-write-wins honesty** — upserting raw payloads by arrival order is acceptable only when overwriting newer state with older is genuinely tolerable; name the choice rather than discovering it in a data-quality incident.

One concurrency note spans all three layers: process events for the *same resource* serially (partition your workers by resource ID — post 5's queue makes this natural), because most "ordering bugs" are actually two handlers interleaving on one aggregate.

The takeaway: the receiver manufactures exactly-once in layers — **atomic event-ID claims** with retention outliving the retry horizon, **idempotent effects** (absolute operations, the effect-plus-ID-in-one-transaction pattern, idempotency keys on every downstream call) as the stronger guarantee beneath, and **disorder survival** via version-stamped applies, fetch-on-event convergence, bounded parking for prerequisites, and per-resource serialization. Dedup is the door lock; idempotent effects are the vault; together they turn the provider's loose promises into your strict ones.

## Key takeaways

- Event-ID dedup must be an **atomic insert-if-absent claim** (never read-check-write), with **retention ≥ retry horizon + reconciliation window**.
- The stronger property is **idempotent effect**: absolute state-setting over relative mutation, the **same-transaction record-and-effect** pattern as the real exactly-once machine, and derived idempotency keys on every downstream side effect.
- Disorder toolkit by trust level: **version-gated applies** → **fetch-on-event** (doorbell pattern — solves duplicates and ordering at once) → **bounded parking** for missing prerequisites → *named* last-write-wins where truly tolerable.
- Serialize per resource (partition workers by resource ID) — most ordering bugs are interleaved handlers on one aggregate, not provider disorder.

## Further reading

- [Idempotence — the property that makes retries and replays safe](https://en.wikipedia.org/wiki/Idempotence)
- [Race condition — the concurrent-delivery bug the atomic claim prevents](https://en.wikipedia.org/wiki/Race_condition)

---

Author: Pratik Dhanave (https://pratikdhanave.com) | Published: 2026-10-30
Canonical: https://pratikdhanave.com/blog/posts/hook-03-idempotent-consumption.html
Attribution: please link the canonical URL when citing or quoting this post.
