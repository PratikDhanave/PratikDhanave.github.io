# Pricing, Rating, and Billing Engines

*How a rating engine turns raw usage and transactions into charges — and why the hard part is making that transformation deterministic, replayable, and idempotent.*

---

## The transformation nobody sees

Every metered product hides the same machine. Somewhere between "the customer did a thing" and "the customer owes money" sits a pipeline that converts events into currency. It reads usage, applies a price, groups the results, produces an invoice, and posts the fees to a ledger. When it works, no one thinks about it. When it drifts by a fraction of a cent per transaction across ten million transactions, someone in finance stops trusting the whole platform.

The mistake most teams make is treating this as one big billing service. It is not one thing. It is three distinct concerns that happen to share a data path: **pricing** (the rules), **rating** (applying the rules to events), and **billing** (assembling and posting the result). Keeping them separate is the single most important design decision, because each has a different failure mode and a different rate of change.

## Pricing: configuration, not code

Pricing is the catalog of rules. It answers "what does one unit cost?" and it changes constantly — sales negotiates a custom rate, marketing launches a promo, a new tier ships. If any of that requires a deploy, you have already lost.

Common plan shapes, all of which a rating engine must express as data rather than branches in code:

- **Flat** — a fixed fee per period regardless of usage.
- **Per-transaction / per-unit** — a price multiplied by a count.
- **Basis points (bps)** — a fraction of transaction value, the standard for payments; 30 bps of a $100 charge is $0.30.
- **Tiered** — different unit prices for different bands, where each band is priced at its own rate (first 1,000 at one price, the next 9,000 cheaper).
- **Volume** — the *entire* quantity is priced at the rate for the band it lands in. Tiered and volume look identical until the numbers cross a boundary, and confusing them is a classic billing bug.

The rule I hold to: pricing plans are **versioned data**. A plan is immutable once a customer is attached to it; a change produces a new version. That way a charge can always name the exact plan version that produced it, and a dispute six months later is answerable instead of a guess.

## Rating: the deterministic core

Rating is where an event meets a plan and becomes a charge. This is the component that most deserves to be treated like a pure function:

```
rate(usage_event, plan_version) -> rate_event
```

Given the same event and the same plan version, it must produce the same priced line every single time — no wall-clock reads, no "current" plan lookup, no randomness. Determinism is not academic. It is what makes the system **replayable**: if you find a rating bug, you re-run the rater over the original events and regenerate the charges, and you can prove the new numbers because the inputs never moved.

That is why the output is a stream of **rate events** — append-only priced lines, not mutable balances. You never edit a rate event. A correction is a new event. The append-only log is the audit trail, the replay source, and the aggregation input all at once.

Idempotency lives here too. Usage arrives at-least-once — queues retry, clients resend, a webhook fires twice. If rating each duplicate produced a duplicate charge, revenue would inflate on every retry. The fix is a deterministic idempotency key per rate event, derived from the source event's identity and the plan version. Re-rating the same usage overwrites the same rate-event slot instead of appending a second charge.

The dataflow, end to end:

```
   SOURCES        RATE         AGGREGATE       INVOICE        POST
 ┌─────────┐
 │ Usage   │──metered──┐
 │ Events  │           │
 └─────────┘        ┌──▼──────┐   ┌──────────┐
                    │ Rating  │──►│  Rate    │
 ┌─────────┐        │ Engine  │   │  Events  │
 │ Pricing │─rate──►│ (pure)  │   │(append-  │
 │ Plans   │  cards └─────────┘   │  only)   │
 └─────────┘                      └────┬─────┘
                                       │ replayable read
                                  ┌────▼──────┐
                                  │Aggregator │
                                  │per acct / │
                                  │  period   │
                                  └────┬──────┘
                                       │ period charges
                                  ┌────▼──────┐    ┌─────────┐
                     ┌─adjust────►│  Invoice  │───►│ Invoice │
                     │            │  Builder  │    │(document)│
              ┌──────┴───┐        │(idempotent)│   └─────────┘
              │ Promos & │        └────┬──────┘
              │Discounts │             │ fee postings
              └──────────┘        ┌────▼──────┐
                                  │  Ledger   │
                                  │(double-   │
                                  │  entry)   │
                                  └───────────┘
```

> **▸ [Open the interactive diagram](/blog/diagrams/fintech-pricing-rating-billing-engine.html)** — usage and pricing plans rated into rate events, aggregated per period, then invoiced and posted to the ledger.

## Aggregation and invoicing

Rate events are fine-grained — one per transaction. Nobody wants an invoice with two million lines. The **aggregator** groups priced lines by account and billing period and rolls them into summarized charges. Because it reads from the append-only log, aggregation is itself replayable: re-run it and you get the same totals.

The **invoice builder** is the billing run. It takes the period's aggregated charges, applies discounts and promos, and assembles a customer-facing invoice. Two engineering constraints matter here.

First, **idempotency at the run level**. A billing run for account *A*, period *2026-07* must produce exactly one invoice no matter how many times it fires. Key the run on `(account, period)` and make re-runs a no-op — or, better, a reconciliation that detects drift. Cron double-fires, operators re-trigger, and a partially failed run gets retried; none of that can mint a second invoice.

Second, **proration**. Customers upgrade mid-cycle, cancel on the 14th, or switch plans. Proration splits a period at the boundary and prices each fragment against the plan version in force during that fragment. Because plans are versioned and rating is deterministic, proration is just rating over two shorter intervals — not a special code path bolted on.

## Discounts, disputes, and posting to the ledger

Discounts and promos enter the invoice builder as explicit **adjustments**, never as edits to rate events. A 20%-off promo is a separate adjustment line referencing the charges it discounts. This keeps the original priced amounts intact and the discount auditable — you can always see gross, the adjustment, and net.

Disputes and corrections follow the same rule. You do not delete a charge; you post an **adjustment** — a credit, a refund line, a reversal — that references the original. The invoice's history becomes a stack of immutable facts, which is exactly what an auditor or a reconciliation job needs.

Finally, the invoice's fees post to the **ledger** as double-entry postings. The ledger is the financial source of truth, and it is append-only too: a posting is never mutated in place. A dispute becomes a reversing pair of entries, not a rewrite. When rating, aggregation, invoicing, and posting are all append-only and replayable, the whole pipeline has one property that finance cares about more than any feature — you can always explain how a number came to be.

## What to separate, and why

If you take one thing from this: **keep pricing config out of the rating runtime**. The rater is a stable, deterministic function you rarely change. Pricing plans, promos, and discounts are data that changes daily. When they live apart, sales can ship a custom rate and marketing can launch a promo without touching the code that turns events into money — and the code that turns events into money stays boring, replayable, and correct.
