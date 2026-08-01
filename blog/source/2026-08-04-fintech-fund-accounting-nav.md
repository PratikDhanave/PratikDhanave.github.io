# Fund Accounting and NAV Calculation

*How a fund turns positions, prices, cash, and accruals into one defensible number every day — and the controls that keep it honest.*

A fund publishes a single price each day: its Net Asset Value per share. Investors buy and redeem at that number, performance is measured against it, and fees are struck from it. One number, once a day. It sounds like a rounding exercise. It is not. Behind that number sits a pipeline that reconciles trades, values thousands of instruments, accrues income and expenses to the correct day, and passes through hard controls before anyone is allowed to publish it. Get it wrong and you have mispriced every subscription and redemption that traded on it — a real, compensable error, not a cosmetic one.

This post walks the daily striking pipeline the way an engineer would build it: inputs, valuation, the NAV formula, and the controls that decide whether today's number ships.

## Why "one number a day" is deceptively hard

NAV is a point-in-time snapshot of ownership. It answers: if the fund liquidated at today's marks and settled every obligation, what is each share worth? The difficulty is that the snapshot must be *complete and consistent as of a specific cutoff*. Every trade that belongs to today must be captured; every price must reflect the same valuation point; every accrual must land on the right calendar day. A missing dividend, a stale price, or a trade booked to the wrong date does not produce a visibly broken NAV — it produces a plausible-looking wrong one. That is the whole problem: the failure mode is silent.

## The input pipeline

Four independent feeds converge before valuation can run.

**Positions (the book of record).** Position keeping is the running ledger of what the fund holds. It starts from yesterday's closing positions and applies today's activity: trades (buys and sells, with quantity, price, and settlement date), corporate actions (splits, dividends, mergers, spin-offs), and any transfers. Corporate actions are the sharp edge here — a 2-for-1 split doubles the quantity and halves the reference price on the ex-date, and if your book applies it a day late, every downstream value is wrong. Positions must reconcile against the custodian's records; unexplained breaks block the strike.

**Prices (valuation inputs).** Each instrument needs a mark as of the fund's valuation point. Liquid equities take the official close from their primary exchange. Bonds often use evaluated prices from a pricing vendor. Derivatives may be modeled. The pricing feed is never assumed complete — every position must have a price, and every price must be fresh.

**Cash.** Cash and cash-equivalent balances, plus known receivables and payables (unsettled trades, pending subscriptions and redemptions), feed directly into assets and liabilities.

**Accruals.** Income and expenses rarely arrive on clean daily boundaries, so they are accrued. Interest accrues daily on fixed-income holdings; dividends accrue from the ex-date. On the expense side, the management fee, custody, audit, and administration costs are accrued daily so the NAV each day carries its fair share rather than lurching on the day an invoice is paid. Management-fee amortization is the canonical case: an annual fee is spread across the year's valuation days so no single day absorbs it.

```
   Positions ─┐
   Prices ────┤
   Cash ──────┼──▶ Valuation ──▶ NAV Calc ──▶ Tolerance ──▶ Sign-off ──▶ Publish
   Accruals ──┘     Engine        (A−L)/Sh      Check       (four-eyes)
                                                   │
                                                   └─(breach)─▶ Investigate
```

> **▸ [Open the interactive diagram](/blog/diagrams/fintech-fund-accounting-nav.html)** — the daily NAV striking pipeline: input feeds converging through valuation and the NAV calculation, then the tolerance and four-eyes control gate before publish.

## Valuation policies

Marking to market is easy when there is a market. The policies exist for when there is not.

**Stale-price detection.** A price that has not moved for several sessions, or is older than the valuation point, is treated as suspect. Automated checks flag prices exceeding a day-over-day move threshold or an age threshold, routing them to a human rather than trusting them blindly.

**Fair-value policy.** When a market price is unavailable or no longer representative — a halted stock, a bond that hasn't traded, a foreign market closed at the valuation point while material news broke — the fund applies a documented fair-value methodology instead of the last printed price. This is deliberately governed: fair value is a judgment, it is logged, and it is reviewed. The engineering job is to make the fair-valued instruments *explicit* in the pipeline, never a silent substitution.

## The NAV formula and share classes

Once every position is valued and every accrual is posted, the arithmetic is simple:

**NAV = (Total Assets − Total Liabilities) / Shares Outstanding**

Total assets are the market value of all holdings plus cash plus accrued income and receivables. Total liabilities are payables plus accrued expenses (including the accrued management fee). Shares outstanding is the share count *as of the same cutoff* — this is why subscription and redemption processing must be synchronized with the strike.

Most funds run multiple share classes over one pool of assets. Each class shares the investment portfolio but carries its own fee schedule and its own shares outstanding, so each strikes its own NAV per share. The engine values the common pool once, then allocates income, expenses, and class-specific fees down to each class before dividing. A currency-hedged class adds its own hedge P&L on top. The pool is shared; the per-share numbers are not.

## Controls: tolerance, four-eyes, and error correction

A computed NAV is a candidate, not a published price.

**Tolerance / variance checks.** The first gate compares today's NAV to a modeled expectation — typically prior-day NAV adjusted for the day's market moves. If the fund's NAV per share oscillates more than a set tolerance (say, beyond an expected band given benchmark movement), the strike halts for investigation. Oscillation checks catch the whole class of silent errors: a fat-fingered price, a missed corporate action, a dropped accrual usually shows up as an unexpected jump.

**Four-eyes sign-off.** A NAV that passes tolerance still requires a second qualified reviewer, independent of whoever ran the strike, to approve it before publication. The maker computes; the checker confirms the inputs reconciled, the exceptions were resolved, and the number is defensible. Only after sign-off is the NAV published to transfer agents, portals, and pricing services.

**NAV error correction.** When a wrong NAV does ship, there is a formal process: quantify the error (often as basis points of NAV), determine whether it breaches a materiality threshold, and if so, correct the price and compensate investors who transacted at the wrong number and the fund itself. This is why the upstream controls earn their cost — the downstream remediation is expensive and reportable.

## Pitfalls

- **Stale and fair value.** Trusting a last price that no longer means anything. If it doesn't move, prove it should.
- **Timing and cutoff.** A trade or a subscription booked to the wrong side of the cutoff shifts value between days and between the fund and its investors.
- **Missed accruals.** A forgotten daily accrual makes NAV drift smoothly wrong, then jump when reality catches up — the hardest error to spot because there is no single bad number.
- **Corporate-action timing.** Applying a split, dividend, or merger on the wrong date. The event is known; the date is the trap.

## Contrast with a general ledger

A general ledger records what *happened* — it is transaction-history-driven, double-entry, and reconciles debits to credits over a reporting period. Fund accounting for NAV is *valuation-driven and point-in-time*: its job is not to tell the story of the period but to answer "what is a share worth right now, at this cutoff." The GL is the audited historical record; the daily NAV is a fresh mark-to-market snapshot struck under a deadline. They reconcile to each other, but they answer different questions and run on different clocks.

## What to remember

NAV is one number, but it is the tip of a reconciled, valued, accrued, and controlled pipeline. Build it so the silent failures — stale prices, missed accruals, mis-dated corporate actions — surface as loud exceptions. Make fair value explicit, make the tolerance check unmissable, and never let a number reach investors without a second set of eyes. The arithmetic is trivial; the discipline is the product.
