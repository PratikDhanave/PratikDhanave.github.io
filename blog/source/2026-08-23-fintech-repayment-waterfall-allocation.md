# Repayment Waterfalls: Allocating a Payment

*How a single loan payment is split across fees, interest, and principal — and why the engine that does it has to be deterministic, auditable, and safe to run twice.*

A borrower sends one number: an amount and a date. Behind that number, a lending system has to answer a surprisingly hard question — *which obligations does this money pay, and in what order?* The answer is the **repayment waterfall**: an ordered set of buckets a payment fills from the top down until it runs out. Get the order wrong and you overcharge interest, misreport delinquency, or fail an audit. This post walks through the domain rules and then the engineering shape of an allocation engine you can trust.

## The buckets and the order

A loan at any moment owes several distinct things. A typical consumer-loan waterfall clears them in this order:

1. **Fees and penalties** — late fees, returned-payment charges, other assessed costs.
2. **Accrued interest** — interest that has accumulated since the last posting.
3. **Principal** — the outstanding balance itself.

The payment fills bucket 1 to the brim, then bucket 2, then bucket 3. Whatever remains after bucket 3 is a surplus (more on that later).

The critical thing an engineer must internalize: **the order is a policy, not a constant.** It varies by product and by regulation. Some mortgage products and many regulators require *principal-first* or *interest-first* ordering for certain payment types; some jurisdictions forbid applying a payment to fees before the past-due principal that generated them. Student loans, credit cards, and auto loans each have their own conventions. So the waterfall must be **configurable data**, not an `if` ladder buried in code. Model it as an ordered list of bucket definitions attached to the product, versioned, and effective-dated — so you can prove which rules applied to a payment made two years ago.

## Partial payments and the past-due dimension

Real payments rarely land exactly on the total due. Two cases dominate.

**The payment is short.** It fills the top buckets and stops mid-waterfall. The buckets it never reached stay unpaid, and the loan carries that shortfall forward. A short payment does not "fail" — it partially satisfies the obligation and the remainder ages.

This is where a second axis appears: **time**. A delinquent loan doesn't owe one lump of interest; it owes interest and principal for *each past-due period*. When a partial payment arrives, you generally settle the **oldest past-due period first**, then move forward. So allocation is really two-dimensional: within a period you walk the bucket order, and across periods you walk oldest-to-newest. A payment that covers one full month of arrears on a two-months-behind loan advances the delinquency clock by exactly one period — it does not cure the account.

**The payment is long.** After principal is satisfied, money is left over. That surplus doesn't vanish. Depending on product rules it becomes an **advance** (prepaid future installments, reducing the next amount due) or lands in a **suspense** account (held unallocated until it's large enough to cover a full obligation, or until instructed). Silently absorbing an overpayment into principal is a common and costly bug — it changes the amortization schedule the borrower agreed to.

## Allocation drives status and accrual

Allocation is not bookkeeping that happens *after* the important decisions — it *is* the important decision. Two downstream systems read its output directly:

- **Delinquency status.** Whether the oldest past-due period is now fully cleared determines if the account moves from "past due" back to "current," stays delinquent, or rolls to a worse bucket. That status feeds credit reporting, collections queues, and fee assessment.
- **Interest accrual.** Interest accrues on the *outstanding principal*. The moment a payment reduces principal, the daily accrual amount changes going forward. Allocate principal a day late and every subsequent interest calculation is wrong.

Because these consequences are irreversible-feeling to a borrower (a misreported late payment is real harm), the allocation engine has to be *correct*, *explainable*, and *replayable*.

## The engineering shape

Here is the flow the allocation engine runs for every payment. The main path is the happy case; the branches are the partial and overpayment rules.

```
 payment in
     |
     v
 [ idempotent post ]   <-- dedup on payment key (exactly once)
     |
     v
 +---------------- waterfall (ordered, per period) ----------------+
 |  fees/penalty  -->  accrued interest  -->  principal            |
 +----------------------------------------------------------------+
     |                    |                          |
  funds short?       (continue)                 surplus?
     |                                               |
     v                                               v
 [ partial pay ]                              [ overpayment ]
  oldest due first                            advance / suspense
     |                                               |
     v                                               v
 [ post ledger entries ] ---------------> [ status + accrual update ]
       (immutable)                         current / past due
```

> **▸ [Open the interactive diagram](/blog/diagrams/fintech-repayment-waterfall-allocation.html)** — the same repayment waterfall as an explorable workflow, with the partial-payment and overpayment branches highlighted.

Three properties make this engine trustworthy.

**Deterministic.** Given the same loan state, the same payment, and the same effective-dated waterfall configuration, the engine must produce the same split every time. That means no wall-clock reads inside the allocation math (pass the value date in), no floating-point money (use integer minor units or a decimal type), and a fixed rounding rule applied at defined points. Determinism is what lets you *replay* a payment during a dispute and get byte-identical results.

**Auditable.** Every allocation writes **immutable ledger entries** — one line per bucket touched, each naming the period it applied to, the amount, and the balance after. You never mutate a prior entry; corrections are new, reversing entries. The ledger is the source of truth, and the running balances are derived from it. When someone asks "why did $40 go to fees?", the answer is a row, not a guess.

**Idempotent.** Payment posting is a distributed-systems problem: webhooks retry, batch files get reprocessed, users double-click. Attach an **idempotency key** to each payment (the processor's payment ID, or a hash of file-line + amount + date). Before allocating, check whether that key has already been posted; if so, return the *original* result rather than allocating again. Do the dedup check and the ledger write in the same transaction so a crash between them can't create a duplicate. "Exactly once" here means: the money moves at most once, and a replay is a safe no-op.

## Putting it together

The engine's contract is small and strict: take a `(loan snapshot, payment, effective-dated config)` and return an ordered list of ledger entries plus a new status — as a **pure function**, with idempotency and persistence wrapped around it as a thin, transactional shell. Keeping the allocation math pure is what makes it unit-testable against the tricky cases: the payment that exactly clears one period, the one cent short of curing, the overpayment that spans two future installments, the payment applied under a since-changed waterfall order.

A repayment waterfall looks like arithmetic. It is really a policy engine whose every output is a promise to a borrower and a line in a regulatory report. Treat the ordering as versioned configuration, make the core deterministic and pure, write immutable ledger entries, and guard posting with an idempotency key — and "split this payment" becomes a decision you can explain, reproduce, and defend years later.
