# Multi-Currency Accounting and FX Revaluation

*How to keep books in more than one currency — transaction-date versus settlement-date rates, unrealized and realized FX gain/loss, and the period-end revaluation run that keeps the balance sheet honest.*

The first time a ledger touches a second currency, a comfortable assumption quietly breaks. When every balance is in one currency, a balance is just the sum of its postings. Add a foreign currency and that sum stops meaning anything on its own: a balance of `100 EUR` is not a number you can add to a `USD` trial balance, and it is not a fixed amount of value either — it drifts against your reporting currency every day the market moves. Multi-currency accounting is the discipline of holding *two* numbers for every foreign amount and being explicit about when each one is allowed to change.

This post is about the engineering of that discipline: how amounts are stored, which exchange rate applies at which moment, and how the period-end revaluation job turns market movement into real journal entries without corrupting the underlying ledger.

## Every foreign amount carries two currencies

Pick one currency as the **functional currency** — the unit the entity actually keeps its books and reports its results in. Everything else is a **transaction currency**. The rule that keeps the whole system sane: a foreign posting stores *both* the original transaction amount and its functional-currency equivalent, plus the rate used to convert between them.

```
Posting on a EUR receivable, functional currency = USD
+------------------+-------------+----------+------------------+
| field            | value       | ccy      | note             |
+------------------+-------------+----------+------------------+
| txn_amount       |    100.00   | EUR      | original         |
| fx_rate          |    1.08     | EUR->USD | rate at booking  |
| functional_amount|    108.00   | USD      | txn * rate       |
| rate_date        | 2026-08-01  |          | which day's rate |
+------------------+-------------+----------+------------------+
```

> **▸ [Open the interactive diagram](/blog/diagrams/fintech-multi-currency-revaluation.html)** — pan, zoom, and trace every step (light/dark, self-contained).

The `functional_amount` is what participates in your double-entry invariant. Postings still sum to zero *in the functional currency* — that is the number the balance sheet and P&L are built from. The `txn_amount` is retained so you never lose the original economic fact: the customer owes exactly 100 EUR, not "whatever 108 USD happens to be worth later."

Store both as signed integers in minor units, per currency, and store the rate as an exact rational or a fixed-scale decimal — never a float. The conversion `txn_amount * rate` must round deterministically (round-half-even at the functional currency's minor-unit scale) so that re-deriving the functional amount from the same inputs always yields the same cents. Reconciliation depends on that determinism.

## Which rate, and which date

The rate is not one number; it is a time series, and picking the wrong point on it is the most common multi-currency bug. Three dates matter, and they are frequently different:

- **Transaction date** — when the economic event occurs (invoice raised, trade booked). The functional amount is fixed here and, for the *original* posting, never changes again.
- **Reporting/period-end date** — the closing date at which open foreign balances are re-measured. This is where revaluation happens.
- **Settlement date** — when cash actually moves and the position closes. The rate here determines the *realized* result.

A receivable booked on the transaction date, revalued at each period-end while it sits open, and finally settled on the settlement date will touch the rate curve at three points. The gap between booking rate and settlement rate is real economic gain or loss; the job of the accounting system is to recognize it in the right periods rather than in one lump at the end.

Rates also come in flavours — you generally hold foreign *asset* balances at a rate you could sell them at and *liability* balances at a rate you would buy at — but for the mechanics below a single closing rate per currency pair is enough to reason about.

## Unrealized gain/loss: revaluing an open position

While a foreign balance is still open, its functional value is stale — it reflects the booking rate, not today's rate. Revaluation is the process of re-measuring open foreign monetary balances at the current closing rate and booking the difference as an **unrealized** FX gain or loss.

Consider that 100 EUR receivable booked at 1.08 (108 USD). At month-end the rate is 1.11. The receivable is now worth 111 USD, but the books still say 108. That 3 USD is unrealized gain — the cash has not moved, so nothing is *realized*, but the balance sheet must show the current value:

```
Month-end revaluation, EUR receivable 100.00
  carrying value (booked):   108.00 USD   @ 1.08
  current value (closing):   111.00 USD   @ 1.11
  delta (unrealized):        + 3.00 USD

Journal:
  DR  AR - EUR (functional adj)    3.00
  CR  Unrealized FX gain (P&L)     3.00
```

Two engineering rules make this safe. First, **revaluation only ever adjusts the functional amount** — the `txn_amount` (100 EUR) is untouched, because the entity is still owed exactly 100 EUR. Second, the adjustment posts to a *separate* revaluation contra line, not the original posting. The original booking is immutable history; the revaluation is a new, dated, reversible journal on top of it. That separation is what lets you unwind or re-run a revaluation without rewriting the ledger.

## The period-end revaluation run

Operationally this is a batch job with a strict shape. It snapshots open balances at a cutoff, fetches the closing rate, computes deltas, and posts one revaluation journal per currency exposure.

```python
def revalue(period_end: date, functional: str) -> list[Journal]:
    journals = []
    for acct, ccy, txn_bal, func_carry in open_foreign_balances(period_end):
        rate = closing_rate(ccy, functional, period_end)   # deterministic lookup
        current = to_minor_units(txn_bal * rate, functional)  # round-half-even
        delta = current - func_carry
        if delta == 0:
            continue
        gl = "unrealized_fx_gain" if delta > 0 else "unrealized_fx_loss"
        journals.append(Journal(
            date=period_end,
            reversing=True,                 # backs out on day 1 of next period
            lines=[Line(acct, func_delta=delta),
                   Line(gl,   func_delta=-delta)],
            idempotency_key=f"reval:{acct}:{ccy}:{period_end}",
        ))
    return journals
```

Two properties earn their keep. The job is **idempotent**: keyed on account, currency, and period, a re-run produces the same journal and posts it at most once, so a failed run can be retried without double-counting. And the entries are **reversing**: an unrealized adjustment is a snapshot of an open position, so it is automatically backed out at the start of the next period. Otherwise last month's unrealized gain and this month's would stack and the balance would drift. Reverse-then-remeasure keeps each period's revaluation self-contained.

## Realization: closing the position on settlement

When the foreign balance finally settles, the difference between the booking rate and the settlement rate becomes **realized** — cash has moved, the position is closed, and the gain or loss is now a fact rather than a mark.

Say the 100 EUR is collected when the rate is 1.10, converting to 110 USD of cash. The receivable was booked at 108. The 2 USD difference is realized gain. Crucially, any *unrealized* revaluation still sitting against that receivable is reversed as part of the same close, so the same movement is never counted twice:

```
Settlement of EUR 100.00 receivable @ 1.10
  DR  Cash                     110.00
  CR  AR - EUR (clear @ book)  108.00
  CR  Realized FX gain           2.00
  (prior unrealized reval on this AR reverses out)
```

The realized/unrealized split is the whole point of the exercise. Unrealized movement tells you what the open book is worth right now; realized movement tells you what you actually earned or lost when positions closed. Keeping them on distinct P&L lines — and keeping revaluation journals reversible and idempotent on top of an immutable base ledger — is what lets a multi-currency system report an honest balance sheet on any date without ever mutating the original economic record.
