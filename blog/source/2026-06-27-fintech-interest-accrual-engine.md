# Building a Daily Interest Accrual Engine

*How to compute interest that earns every day, tracks the accrued-but-unbilled balance, survives mid-period rate changes, and posts to the ledger with idempotent replay-safe jobs.*

---

Interest is deceptively simple until you have to book it. The math on a whiteboard is one line — balance times rate times time — but a production accrual engine has to answer harder questions. What did this account earn *yesterday*, specifically, and not a cent more? If the nightly job crashed halfway and re-ran, did we double-count? When the rate changed on the fifteenth, did the first half of the month accrue at the old rate and the second half at the new one? And when the billing cycle closes, how much accrued interest do we capitalize versus carry forward?

An accrual engine is the system that turns a balance and a rate into a stream of tiny, dated, ledger-posted amounts. The design goal is not clever math. It is determinism: the same inputs must always produce the same accrual, so a run can be replayed, audited, and reconciled. This post walks through how to build one.

## Accrual is a daily event, not a monthly formula

The instinct is to compute interest once per billing cycle: take the balance, multiply by the monthly rate, post it. That falls apart the moment anything moves mid-cycle — a payment, a drawdown, a rate change. The balance is not constant across the month, so a single multiplication is wrong.

The correct model is to accrue **once per day** against that day's balance. Each daily accrual is a small, independent, dated fact:

```
accrual(day) = principal_balance(day) * daily_rate(day)
```

where the daily rate comes from the annual rate and a **day-count convention** — the rule that decides how many days are in a year for interest purposes:

- **Actual/365 fixed** — divide the annual rate by 365 every day.
- **Actual/360** — divide by 360; each day is worth slightly more (common in money markets).
- **30/360** — pretend every month has 30 days and every year 360, smoothing February and 31-day months.

The convention is a business input, not a detail. A/360 on the same nominal rate yields about 1.4% more interest per year than A/365, so it must be explicit and stored per product, never hardcoded.

```
 Balance      Day-count      Daily         Accrued-but-      Billing        Ledger
 snapshot --> convention --> accrual   --> unbilled      --> cutoff     --> journal
 (per day)    (rate/N)       amount        sub-ledger        capitalize      (Dr/Cr)
                                              ^                  |
                                              +---- carried -----+
                                                   forward
```

> **▸ [Open the interactive diagram](/blog/diagrams/fintech-interest-accrual-engine.html)** — pan, zoom, and trace every step (light/dark, self-contained).

Reading left to right: a dated balance snapshot meets a day-count convention to produce one day's accrual; that amount lands in an accrued-but-unbilled sub-ledger, accumulating day after day until the billing cutoff sweeps it into a capitalization event and a ledger journal. The whole engine is that loop, run once per account per day.

## Simple versus compound: what the balance includes

The single decision that changes the shape of the engine is whether accrued interest itself earns interest.

Under **simple interest**, the daily accrual is always computed on the *principal* balance. Accrued interest sits in its own bucket and does not feed back into the base.

Under **compound interest**, at some frequency the accrued interest is *capitalized* — folded into the principal — so future accruals are computed on principal plus previously-accrued interest. Compounding frequency (daily, monthly, at billing) is the knob:

```python
from decimal import Decimal

def daily_accrual(principal: int, annual_rate: Decimal, day_count: int) -> int:
    # principal in minor units (cents); returns accrual in minor units, rounded
    daily_rate = annual_rate / day_count
    return int((Decimal(principal) * daily_rate).quantize(Decimal("1")))
```

Two rules that are non-negotiable. First, **work in integer minor units**. Interest schedules and floating point do not mix; use integer cents or `Decimal`, never `float`. Second, **round each daily accrual deterministically** to the currency's smallest unit and carry the rounding decision consistently. Sub-cent fractions that you keep in memory but never post will silently diverge the engine from the ledger.

## The accrued-but-unbilled sub-ledger

Between billing cycles, interest has been *earned* but not yet *billed* to the customer. That money is real — it is an asset you can report — but it is not yet part of the customer's statement balance. It lives in a dedicated **accrued interest receivable** sub-ledger.

This separation is the accrual analogue of keeping cash and revenue apart. Two balances move on different clocks:

- **Accrued-but-unbilled** grows a little every day as the daily job runs.
- **Billed balance** jumps once per cycle when the cutoff capitalizes the accrued amount onto the statement.

At the billing cutoff, the engine sweeps the accrued sub-ledger: the accumulated interest is capitalized (added to the customer's principal or moved to a billed-interest line), the sub-ledger resets to zero, and a fresh cycle begins. Between cutoffs, the invariant a controller checks is that **the accrued-interest sub-ledger balance equals the sum of all daily accruals posted since the last capitalization**. If those two numbers disagree, a day was double-posted or dropped.

## Idempotent daily jobs and replay safety

The accrual job runs nightly across millions of accounts. It *will* crash, retry, and occasionally run twice for the same date. The engine has to make that a non-event.

The technique is the same discipline that makes any financial job safe: derive a natural idempotency key from the business fact, and let the ledger reject duplicates.

```python
def run_accrual(as_of: date, ledger):
    for account in accounts_active_on(as_of):
        balance = balance_snapshot(account, as_of)      # deterministic for a past date
        rate    = effective_rate(account, as_of)        # from the rate timeline
        amount  = daily_accrual(balance, rate, account.day_count)
        ledger.post(
            accrual_journal(account, as_of, amount),
            idempotency_key=f"accrual:{account.id}:{as_of.isoformat()}",
        )
```

Three properties make this production-grade. It is **idempotent per account per day** — the key is the account plus the date, so a re-run cannot double-book; the ledger silently discards the repeat. It is **as-of aware** — the job reads `as_of` explicitly, not the wall clock, so a missed night is backfilled by re-running that date, and any past day reproduces exactly. And it is **replayable** — because the accrual is a pure function of a dated balance and a dated rate, you can rebuild an account's whole accrual history to verify the books. That is why balance snapshots and the rate timeline must both be queryable *as of a date*, never just "current."

## Rate changes mid-period

Rates move: a promotional rate expires, a variable rate tracks a benchmark, a repricing event lands on the tenth. Because the engine already accrues per day and reads an *effective rate as of that day*, a mid-period change needs no special case — it is just two different `daily_rate` values on two different days.

The requirement this pushes onto the data model is a **rate timeline**: a set of `(effective_from, rate)` intervals per account, not a single mutable `current_rate` field. The engine resolves the rate for a given day by finding the interval covering it.

```
Rate timeline:   3.5% ────────┐
                              1.5% (promo ends)
                 |────────────|───────────────────|
 Day:            1 ....... 14  15 ............... 30

 Accrual:  days 1–14 at 3.5%/N,  days 15–30 at 1.5%/N,  summed = month's interest
```

Modeling rate history as an append-only timeline (rather than overwriting a field) is what lets recomputation stay correct. If a rate is later found to have been entered wrong, you correct the timeline and *replay* the affected date range; every daily accrual in that window recomputes deterministically and posts a true-up for the delta. You never edit a posted accrual — you append a correcting one, exactly as you would in the ledger itself.

## The discipline that ties it together

Every hard part of an accrual engine dissolves into the same rule: **make each day's interest an immutable, dated, deterministically-derived fact, and express every change as a new fact rather than a mutation of an old one.**

Daily granularity handles mid-cycle balance and rate moves for free. Integer minor units and fixed rounding keep the engine and ledger bit-for-bit reconcilable. A per-account-per-day idempotency key makes the nightly job safe to crash and retry. An as-of-queryable balance and rate timeline make the whole history replayable. Get those four disciplines right and interest — the thing that quietly compounds every wrong assumption — becomes the most boringly auditable number in the system. That is exactly what you want it to be.
