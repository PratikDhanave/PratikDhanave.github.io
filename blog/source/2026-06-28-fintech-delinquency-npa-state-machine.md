# Delinquency as a State Machine: DPD Buckets, SMA, and NPA Classification

*Model days-past-due transitions, SMA/NPA classification, provisioning triggers, and cure logic as one deterministic engine driven by time and repayment events.*

A loan does not turn "bad" the instant a borrower misses a payment. It ages. Teams that treat delinquency as a nightly report — a query that scans balances and prints a number — end up with classification that drifts, provisions that are wrong at month-end close, and a collections queue nobody trusts. The durable design is a state machine: every account carries an explicit delinquency state, transitions are driven by exactly two inputs (the passage of time and repayment events), and every transition has deterministic, auditable side effects on the ledger.

This post models that machine end to end: the days-past-due clock that advances it, the bucket boundaries that name each state, the classification rules that tag an account as standard, special-mention, or non-performing, and the cure logic that walks it back.

## The DPD clock is the spine

Days-past-due (DPD) is the number of calendar days since the *oldest unpaid* installment's due date. Not the days since the last payment — the days since the oldest dollar still owed. That distinction is the single most common source of misclassification. A borrower who pays this month's installment while last month's is still outstanding has *not* reset the clock; the oldest arrears keep ageing.

```
Due dates:   D1 ──── D2 ──── D3 ──── D4 ──────► today
             │       │       │
paid:        paid    unpaid  unpaid
                     ▲
                     └─ oldest unpaid → DPD counts from HERE (D2),
                        even though a later installment (D4) was paid
```

> **▸ [Open the interactive diagram](/blog/diagrams/fintech-delinquency-npa-state-machine.html)** — pan, zoom, and trace every step (light/dark, self-contained).

Compute DPD from the amortization schedule, never from a counter you increment nightly. An incrementing counter cannot be replayed, and it drifts permanently the first time a batch job is skipped, double-runs, or lands out of order. Deriving DPD from the schedule and a snapshot of what has been paid makes the whole engine a pure function of `(schedule, payments, as_of_date)`:

```python
def days_past_due(schedule, payments, as_of):
    paid = allocate_payments(schedule, payments)  # oldest-first waterfall
    oldest_unpaid = next(
        (inst for inst in schedule
         if inst.due_date <= as_of and paid[inst.id] < inst.amount),
        None,
    )
    if oldest_unpaid is None:
        return 0                       # nothing overdue → Current
    return (as_of - oldest_unpaid.due_date).days
```

The payment waterfall matters: allocate receipts oldest-installment-first (and, within an installment, in your fees/interest/principal order) so that a partial payment can retire the oldest bucket and genuinely reduce DPD rather than paying down a future installment.

## Buckets name the states

DPD is continuous; the state machine is discrete. You collapse the DPD integer into named buckets, and those buckets are your states. A common structure separates *special mention* (early warning, still standard) from *non-performing*:

| State | DPD range | Classification |
|-------|-----------|----------------|
| Current | 0 | Standard |
| SMA-0 | 1–30 | Standard, watch |
| SMA-1 | 31–60 | Standard, special mention |
| SMA-2 | 61–90 | Standard, special mention |
| NPA (sub-standard) | 90+ | Non-performing |

The 90-day boundary is the one that carries weight: crossing it flips the asset from performing to non-performing, which changes provisioning, interest recognition (you typically stop accruing interest to income and move to a suspense treatment), and regulatory reporting. Encode the boundaries as data, not as branching code — a single ordered table of `(lower, upper, state, classification, provision_rate)` rows — so that when policy changes a threshold you edit a row, not a function.

## Roll-forward, roll-back, and the cure edge

Two forces move an account. Time rolls it *forward*: with no qualifying payment, DPD grows and the account steps Current → SMA-0 → SMA-1 → SMA-2 → NPA. Repayment rolls it *back*, and the roll-back rules are where correctness is won or lost.

The key rule: a payment reduces DPD only by how much of the *oldest* arrears it clears. Paying one installment's worth when three are overdue moves DPD from, say, 75 to 45 — SMA-2 down to SMA-1 — but does not cure the account. Full **cure** (return to Current) requires clearing *all* overdue principal and interest so that no unpaid installment predates today.

```
                 time, no payment
   Current ─────────────────────────────► NPA (90+ DPD)
      ▲                                      │
      │  cure: ALL arrears cleared           │ workout / restructure
      └──────────────────────────────────────┘
```

Two subtleties bite teams here. First, many policies impose a **cure period** on non-performing accounts: an NPA does not upgrade to standard on a single payment: it must stay current for a defined window before the classification is restored, to prevent "evergreening" through a token payment. Model that as an intermediate `Cured (probation)` state, not a direct NPA → Current edge. Second, a **restructure** (a renegotiated schedule) is its own transition with its own classification treatment — it is not a cure, and conflating the two understates risk.

## Provisioning is a side effect of transitions

The state is not just a label; each state carries a provision rate, and *every transition emits a balanced ledger entry* that trues up the loan-loss provision to the new state's requirement. Standard assets provision a small general reserve; special-mention more; non-performing a materially higher rate that escalates the longer the asset stays impaired.

Make the provision movement a function of the transition, not an absolute recomputed blindly:

```
on transition(from_state, to_state, exposure):
    target   = provision_rate[to_state] * exposure
    current  = provision_balance(loan)
    delta    = target - current
    post_journal(
        debit  = "P&L: provision expense" if delta > 0 else "P&L: provision writeback",
        credit = "Balance sheet: loan-loss provision",
        amount = abs(delta),
        memo   = f"{from_state}->{to_state} @ DPD={dpd}",
    )
```

Because the journal is derived from the delta between the old and new provision balance, a roll-back (cure) naturally produces a *write-back* entry, and the ledger always reflects the current classification without double-counting. Every posting carries the transition and DPD in its memo, which is what makes the month-end provision number defensible in an audit.

## Idempotency and replay-safety

The classification job runs daily and must be safe to re-run. Key each run by `(loan_id, as_of_date)` and make the job recompute state from the schedule and payment history rather than mutating a prior state in place. Reprocessing the same `as_of_date` twice must produce the same state and must not post the provision journal twice — guard the ledger posting with the same `(loan_id, as_of_date, transition)` idempotency key.

This design gives you three properties that a nightly-counter approach cannot: you can **backfill** a corrected payment and have every downstream state and provision recompute deterministically; you can **replay** an entire portfolio as-of any historical date for reporting or dispute resolution; and you can **prove** any single account's classification is a pure function of inputs a reviewer can inspect. Delinquency stops being an opaque number on a dashboard and becomes a transparent, reproducible state — which is exactly what a regulator, an auditor, and your own on-call engineer each need it to be.
