# Building a Revenue Recognition Engine

*How to turn contracts into performance obligations, recognition schedules, and ledger journals — and why billing is never the same event as revenue.*

---

The single most common accounting bug in a young fintech or SaaS platform is treating an invoice as revenue. You charge a customer $1,200 for an annual plan, cash lands, and someone books $1,200 of revenue on day one. Under accrual accounting and the ASC 606 / IFRS 15 standards, that is wrong: you have earned one twelfth of it, and the remaining eleven twelfths are a liability you owe the customer in future service. A revenue recognition engine is the system that keeps those two facts — cash collected and revenue earned — permanently separate and reconcilable.

This post is about the engineering of that engine: the data model, the recognition run, and the ledger postings. It is not accounting advice; it is how to build software that a controller can trust.

## Billing and revenue are two different clocks

The core mental model is that a contract drives two independent event streams:

- **Billing events** happen when you have the *right to invoice* — a signup, a renewal, a usage rollup at month end. They move cash and create receivables.
- **Recognition events** happen when you have *satisfied a performance obligation* — delivered a day of service, shipped a unit, completed a milestone. They move revenue.

These clocks almost never tick together. You can bill annually but recognize daily. You can deliver first (recognizing) and bill in arrears. The engine's whole job is to hold the gap between them on the balance sheet: unearned billings sit in **deferred revenue** (a liability), and earned-but-unbilled work sits in **unbilled receivable** (an asset called a contract asset). Get this separation right and everything else is bookkeeping.

## The five-step model as a pipeline

ASC 606 defines five steps, and they map cleanly onto a data pipeline. Each stage is a pure transformation over the contract, which makes the whole thing testable and replayable.

```
 Contract          Obligations         Allocation          Schedule            Recognition
   line            (distinct POs)      (by standalone      (period-by-         run -> ledger
   items      -->   identified    -->   selling price) -->  period plan)  -->   journals
                                                                                    |
                                       deferred revenue  <-- billing events         |
                                       liability drawn down as revenue is recognized +
```

> **▸ [Open the interactive diagram](/blog/diagrams/fintech-revenue-recognition-engine.html)** — pan, zoom, and trace every step (light/dark, self-contained).

Walking the stages:

1. **Identify the contract.** The unit of work. One agreement, possibly many line items.
2. **Identify performance obligations (POs).** Each distinct promise is its own PO with its own recognition pattern. A bundle of "platform license + onboarding + support" is three POs, not one, if the customer could benefit from each separately.
3. **Determine the transaction price.** The total consideration, adjusted for discounts, refunds, and variable components.
4. **Allocate price to obligations** by their **standalone selling price** (SSP). If you sell the bundle for $1,000 but the parts list at $600 / $200 / $400, you allocate proportionally to the $1,200 total, not by the discounted sticker.
5. **Recognize revenue** as each PO is satisfied — either *at a point in time* (a one-off delivery) or *over time* (ratably across a service period).

The output of steps 1–4 is a static artifact: a **recognition schedule**, a table of `(obligation_id, period, amount)` rows that sums back to the allocated price. Step 5 is a recurring job that reads the schedule and posts journals.

## Modeling the schedule

The schedule is the heart of the engine, and it should be computed once and stored, not derived on the fly every time someone opens a report. A minimal shape:

```python
from dataclasses import dataclass
from datetime import date
from decimal import Decimal

@dataclass(frozen=True)
class ScheduleEntry:
    obligation_id: str
    period_start: date      # e.g. first of the month
    amount: Decimal         # in minor units, integer-safe
    recognized: bool = False

def ratable_schedule(obligation_id, total, start, months) -> list[ScheduleEntry]:
    # Even split with the rounding remainder pushed into the final period,
    # so the schedule always sums back to `total` — no lost cents.
    base = total // months
    entries = []
    for i in range(months):
        amt = base if i < months - 1 else total - base * (months - 1)
        entries.append(ScheduleEntry(obligation_id, add_months(start, i), amt))
    return entries
```

Two engineering rules matter more than the accounting nuance:

- **Work in integer minor units.** Never let floating point near a revenue schedule. A `Decimal` or integer cents representation is the only acceptable type; the sum-back invariant (`sum(entries) == total`) must hold exactly.
- **Push the rounding remainder deterministically.** Twelve into $1,200 is clean, but $1,000 over 3 months is 333 / 333 / 334. Decide once (usually last period absorbs the remainder) and encode it, so re-running the calculation is idempotent.

## The recognition run

Recognition is a scheduled job — typically nightly — that asks a single question: *for every open schedule entry with a period on or before today, has it already been recognized?* If not, recognize it and mark it. That "mark it" step is what makes the job safe to run twice.

```python
def run_recognition(as_of: date, ledger):
    due = fetch_unrecognized_entries(up_to=as_of)   # recognized == False, period <= as_of
    for entry in due:
        journal = build_recognition_journal(entry)   # deterministic from entry
        ledger.post(journal, idempotency_key=f"rec:{entry.obligation_id}:{entry.period_start}")
        mark_recognized(entry)
```

Three properties make this production-grade:

- **Idempotent per entry.** The idempotency key is derived from the obligation and period, so a crashed-and-retried run, or a re-run after a bug fix, cannot double-book revenue. The ledger rejects the duplicate key.
- **Replayable.** Because the schedule is stored and journals are deterministic functions of schedule entries, you can rebuild a period's revenue from scratch. This is what lets you fix a bug in the allocation logic and re-recognize cleanly.
- **As-of aware.** Passing `as_of` explicitly (rather than reading the wall clock) means you can run catch-up recognition for a missed day, or reproduce what the books *should* have said on any past date.

## Ledger postings and deferred-revenue drawdown

Every recognition event is a balanced, double-entry journal. When you billed the customer, you posted:

```
Dr  Cash / AR            1200
    Cr  Deferred Revenue      1200   (a liability: you owe service)
```

Each recognition run then *draws down* that liability into earned revenue:

```
Dr  Deferred Revenue     100
    Cr  Revenue               100    (one month satisfied)
```

After twelve runs the deferred-revenue balance for that contract is zero and cumulative revenue is $1,200 — the two clocks have finally converged. The invariant a controller will check is that, at any instant, **deferred revenue equals the sum of all unrecognized schedule entries**. If it doesn't, the engine and the ledger have diverged and something posted out of band.

When recognition leads billing instead, the mirror applies: you credit revenue and debit a **contract asset** (unbilled receivable), which the later invoice clears. Same machinery, opposite starting liability.

## The edge cases that decide the design

The happy path above is easy. The reasons rev-rec engines are hard are all in the changes:

- **Contract modifications.** A mid-term upgrade either creates a new contract (prospective) or reallocates the remaining price across the changed obligations. Your schedule model needs versioning so a modification supersedes future entries without rewriting recognized history.
- **Variable consideration.** Usage-based fees, rebates, and refund estimates change the transaction price after the fact. Model these as revised schedules with a true-up journal for the already-recognized delta, never by editing posted periods.
- **Early termination and refunds.** Reverse the remaining deferred balance and stop the schedule; do not claw back already-earned revenue.

The common thread: **treat recognized periods as immutable and express every change as a new forward-looking schedule plus an adjusting journal.** That single discipline — append, never mutate — is what keeps the engine auditable, replayable, and trustworthy when a controller comes asking why last quarter's number moved.
