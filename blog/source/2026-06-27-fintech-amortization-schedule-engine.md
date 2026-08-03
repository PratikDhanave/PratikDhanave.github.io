# Building a Deterministic Amortization Schedule Engine
*Computing loan amortization you can reproduce to the cent — annuity math, day-count conventions, the per-installment principal/interest split, and prepayment recomputation.*

An amortization schedule looks like a solved problem. You learned the EMI formula in school, a spreadsheet can render one in thirty seconds, and every lending product ships one. Then you put it behind an API that a borrower, a collections team, a regulator, and an accounting system all read from — and the schedule becomes one of the least forgiving pieces of code in the stack. Two runs of the same loan must produce byte-identical rows. A prepayment in month 14 must not silently move a cent in month 3. And the final installment must close the balance to exactly zero.

This post treats the schedule engine as what it actually is: a deterministic function from loan terms to a table of installments, with a small set of invariants that must hold on every path.

## The engine is a pure function

Start by drawing a hard boundary. The core computation takes terms in, produces a schedule out, and touches nothing else — no clock, no database, no random rounding mode inherited from the runtime. Everything that varies (today's date, the interest rate feed, prepayment events) is passed in as an explicit argument so the same inputs always yield the same rows.

```
 Loan Terms ─┐
             ├─►  Installment  ─►  P/I Split  ─►  Schedule ─►  Prepayment
 Day-Count ──┘        calc                          table          event
                                                      ▲              │
                                                      └── Recompute ──┘
```

> **▸ [Open the interactive diagram](/blog/diagrams/fintech-amortization-schedule-engine.html)** — pan, zoom, and trace every step (light/dark, self-contained).

Everything downstream of that boundary — statements, ledger accruals, delinquency buckets — consumes the schedule as data. If the engine is a pure function, you can snapshot a schedule, replay it in a test, and diff two versions of the code against a golden fixture. If it quietly reads `now()` or a live rate somewhere in the middle, you lose all of that, and you will spend a quarter chasing "the numbers don't match" tickets.

## Two formulas, and knowing which you sold

There are two amortization styles, and mixing them up is a compliance incident, not a rounding quirk.

**Equated installments (annuity / EMI).** Every period the borrower pays the same total. The classic closed form for the level payment is:

```python
def emi(principal_minor: int, rate_per_period: Decimal, n: int) -> int:
    if rate_per_period == 0:
        return round_half_even(Decimal(principal_minor) / n)
    r = rate_per_period
    factor = (1 + r) ** n
    payment = Decimal(principal_minor) * r * factor / (factor - 1)
    return round_half_even(payment)
```

**Reducing-balance with fixed principal.** The principal component is constant (`principal / n`), interest is charged on the outstanding balance, so the *total* installment falls over the life of the loan. Common in some commercial and auto products.

The formula you pick changes every downstream number — total interest, the APR you must disclose, the payoff amount on any given day. Store the amortization method as a first-class field on the loan, never as an implicit consequence of which code branch ran.

Note that `principal_minor` is an integer count of minor units (paise, cents). Amortization multiplies and divides balances thousands of times; doing that in binary floating point accumulates error that eventually shows up as a non-zero final balance. Work in integer minor units and a `Decimal` for the periodic rate, and choose one rounding mode — half-even is the usual pick to avoid a systematic bias toward the lender.

## Day-count decides the interest, not the formula

The period rate above hides the second landmine. Interest for a period is `outstanding × annual_rate × (days_in_period / days_in_year)`, and both the numerator and denominator depend on a **day-count convention** that is part of the contract:

- **30/360** — every month is 30 days, every year 360. Clean, common in mortgages, and the reason a "monthly" schedule can ignore actual calendar lengths.
- **ACT/365F** — actual elapsed days over a fixed 365. February is genuinely shorter than March.
- **ACT/360** — actual days over 360, which quietly inflates the effective annual rate; standard in some money-market and commercial lending.
- **ACT/ACT** — actual over the actual length of the year, leap years included.

A loan booked at "12% per annum, monthly" pays a different amount under 30/360 than under ACT/365F, and the gap widens across February and December. Make the convention an input to the day-count function and unit-test each one against hand-computed values. Do not let "12% / 12" be hardcoded as the monthly rate; that *is* a convention (30/360-flavoured), and pretending it isn't will bite you the first time a product uses actual days.

## Splitting each installment

With the payment amount and the period interest in hand, the per-installment split is a short, strict loop. For each period: compute interest on the current balance, take the rest of the payment as principal, and decrement the balance.

```python
def schedule(principal_minor, payment, periods, day_count):
    balance = principal_minor
    rows = []
    for i, period in enumerate(periods):
        interest = round_half_even(
            balance * annual_rate * day_count.fraction(period)
        )
        principal = payment - interest
        if i == len(periods) - 1:          # final period closes the loan
            principal = balance
            payment_i = principal + interest
        else:
            payment_i = payment
        balance -= principal
        rows.append(Row(period, payment_i, principal, interest, balance))
    return rows
```

The subtle line is the final period. Because every prior row was rounded, the sum of principal components will be off from the original principal by a few minor units. Rather than let that error leak into a residual balance, the last installment is forced to repay exactly the remaining balance and its payment is derived from that. This is the standard "true-up on the last row" technique, and it is what guarantees the closing invariant: **sum of principal components equals the original principal, and the final balance is exactly zero.**

Two more invariants belong in the same test: interest is never negative, and principal never exceeds the outstanding balance. If your period rate is high relative to the payment (a very short-tenor, high-rate loan), the naive formula can produce a negative-amortizing row where interest exceeds the payment. The engine should reject that at construction time, not emit a schedule where the balance grows.

## Prepayment: recompute, never patch

The moment a borrower pays extra principal, the temptation is to reach into the stored schedule and edit a few rows. Resist it. A prepayment is a new input; the correct response is to re-run the pure function from the event date forward.

There are two contractual outcomes, and the borrower's agreement dictates which:

- **Reduce tenor** — keep the installment the same, apply the extra principal to the balance, and the loan simply ends earlier. You recompute how many periods remain.
- **Reduce installment** — keep the number of periods, recompute a new (lower) level payment on the reduced balance for the remaining term.

```
outstanding after month 14
        │
   extra principal ── applied ──► new balance
        │
        ├─ reduce tenor  → same EMI, fewer rows
        └─ reduce EMI    → new EMI, same end date
```

Structurally, you split the schedule at the event's effective date: rows before it are frozen (they already happened and were posted to the ledger), and everything from the event forward is regenerated by calling the same `schedule()` function with the reduced balance and the chosen strategy. Rate changes mid-loan are handled identically — a rate change is just another event that recomputes the tail. Because the tail is recomputed rather than hand-edited, the closing invariants hold automatically on the new schedule, and you keep a clean audit trail: version N of the schedule, the event, version N+1.

## What to actually test

The determinism promise is only real if you enforce it. Three test families cover most of the risk. First, **golden fixtures**: a handful of loans (annuity and reducing-balance, each day-count convention) with schedules computed by hand or a trusted reference, diffed row-for-row. Second, **invariant property tests**: for randomly generated terms, assert the principal sums back to the original, the final balance is zero, and no row negatively amortizes. Third, **event replay**: apply a prepayment or rate change, then confirm the frozen prefix is unchanged and the recomputed tail still closes to zero.

An amortization engine is not hard because the math is deep. It is hard because dozens of small decisions — minor units, rounding mode, day-count, the final-row true-up, recompute-versus-patch — each have a correct answer, and every one of them is visible to someone who will notice a one-cent discrepancy. Pin them down as explicit inputs and invariants, and the schedule becomes what it should be: boring, reproducible, and correct on every path.
