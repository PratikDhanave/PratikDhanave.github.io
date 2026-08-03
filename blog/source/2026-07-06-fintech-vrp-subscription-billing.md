# Variable Recurring Payments and Metered Billing as a Mandate Lifecycle

*Model variable recurring payments and metered/subscription billing with proration, treating the mandate — not the retry loop — as the object that actually has state.*

Most subscription-billing code starts from the wrong object. It centres on the invoice, or worse, on the retry counter, and everything else hangs off that. The result is a system where nobody can answer a simple question — "is this customer currently authorised to be charged, and up to how much?" — without joining four tables and guessing. The durable model puts the **mandate** at the centre. A variable recurring payment (VRP) mandate is a standing, revocable authorisation that says: *you may pull from my account, up to this ceiling, at this cadence, until I cancel.* Everything else — metering, invoicing, the charge, retries, proration — is a side effect of where that mandate sits in its lifecycle.

This post models VRP-backed metered billing as one state machine and keeps it deliberately separate from the retry logic that people tend to conflate it with. Retry is a small sub-behaviour of a single charge; the mandate lifecycle is the spine.

## The mandate is the authorisation, not the schedule

A fixed direct-debit mandate authorises a *known* amount on a *known* date. A VRP mandate authorises a *bounded* amount within a *window*. The bound is the whole point: the customer consents to "up to £200 per calendar month across at most 30 payments," and the paying institution enforces that ceiling on every pull. That enforcement lives on the mandate, so your billing engine must carry it as first-class state, not as a config value it hopes is still accurate.

```
Mandate parameters (enforced on every charge)
┌─────────────────────────────────────────────┐
│ max_amount_per_period   £200 / calendar month │
│ max_per_transaction     £80                   │
│ period_window           2026-08-01 .. 08-31   │
│ consumed_this_period    £142   ← running tally │
│ headroom                £58    ← what's left   │
└─────────────────────────────────────────────┘
```

> **▸ [Open the interactive diagram](/blog/diagrams/fintech-vrp-subscription-billing.html)** — pan, zoom, and trace every step (light/dark, self-contained).

The `consumed_this_period` and `headroom` fields are not derived on the fly from a `SUM()` over payments — they are maintained as the mandate transitions, because the ceiling check has to be atomic with the charge. Two concurrent charges that each individually fit under headroom but together breach it is the classic race, and you close it by decrementing headroom under the same lock that authorises the pull.

## Metering feeds the amount; it does not drive the cycle

Metered billing means the charge amount is unknown until the period closes. You accumulate usage events — API calls, seat-days, gigabytes — into a per-mandate, per-period counter. The mistake is letting each usage event nudge the billing state machine. It should not. Usage accumulation is a high-frequency append; the mandate cycle ticks at most once per billing period. Keep them decoupled:

```python
def record_usage(mandate_id, period, quantity, unit, event_id):
    # idempotent append — the mandate state does NOT move here
    ledger.upsert(
        key=(mandate_id, period, event_id),   # dedupe replays
        quantity=quantity,
        unit=unit,
    )
```

When the period closes, you *rate* the accumulated usage — apply the price book, tiers, and any included allowance — to produce a single invoice amount. Only then does the mandate move from metering into the invoiced state. Rating is a pure function of `(usage_ledger, price_book, period)`, which means you can re-rate a disputed period without touching the mandate at all.

## Proration is a boundary event, not a special case

Proration shows up whenever the billing period and the entitlement period disagree: a mid-cycle upgrade, a plan change on day 12, a cancellation partway through. The clean model treats every such change as *closing the current sub-period and opening a new one*, then rating each sub-period on its own terms.

```
Plan change on day 12 of a 30-day month:

|<--- Standard (days 1-11) --->|<------- Pro (days 12-30) ------->|
       11/30 x £30  = £11.00          19/30 x £50  = £31.67
                              invoice = £42.67
```

The reason to model it as two rated sub-periods rather than one adjusted line is auditability: each sub-period carries its own plan, rate, and day-count, so the invoice explains itself. A single "prorated adjustment" line that nets to £42.67 is impossible to defend when a customer queries it. Proration is arithmetic on closed windows, not a branch buried in the charge path.

## The lifecycle: active, metered, invoiced, charged, paid

Now the states line up. A mandate that has been authorised sits **active**. As a period runs it is **metered** — usage accruing, no money moving. At period close it becomes **invoiced** — a concrete amount now exists and has been checked against mandate headroom. The engine then **charges**, and on success the period is **paid**; the mandate resets its per-period tally and returns to active for the next cycle.

Two branches leave that happy path, and they are genuinely different. A **failed** charge is *recoverable*: it drops into a retry (dunning) sub-flow — a bounded schedule of re-attempts with backoff — and a successful retry rejoins the main path at charged. This is the only place retry logic belongs, and it is subordinate to a single charge, not a property of the mandate. A **cancelled** mandate is *terminal*: the customer (or the bank) revoked authorisation, and no further pull is legal regardless of headroom. Once cancelled, a mandate never re-enters the cycle; a returning customer gets a *new* mandate with a fresh consent record.

```
active ──► metered ──► invoiced ──► charge ──► paid ──┐
              ▲                        │              │
              └──── next period ───────┘              │
                                       │(fails)       │
                                    retry/dunning     │
   cancelled  ◄─── revoked, at any state ─────────────┘
```

Modelling failed-as-recoverable and cancelled-as-terminal separately is what keeps the machine honest. Collapsing them — treating a hard cancellation as "just another failure" — is how systems end up pulling from accounts whose consent was withdrawn, which is both a reconciliation nightmare and a compliance breach.

## Why the mandate-centric model pays off

Three properties fall out for free once the mandate is the stateful object. First, **the authorisation question is always answerable**: current state plus headroom tell you, in one row, whether a charge is legal right now. Second, **retries stay contained**: because retry is a sub-flow of a charge and not a mandate state, an exhausted retry schedule can escalate to dunning or cancellation without special-casing the rest of the engine. Third, **every money movement is idempotent and replayable**: charges are keyed by `(mandate_id, period)`, usage by `(mandate_id, period, event_id)`, so re-running a billing job double-charges nobody and a corrected usage event re-rates cleanly.

The through-line is the same one that makes any billing system trustworthy: separate the thing that has *state* (the mandate) from the things that are *events* (usage, invoices, charge attempts). Get that boundary right and proration becomes arithmetic, metering becomes an append log, and retries become a small local loop — instead of three tangled concerns fighting over a single overloaded status column.
