# Merchant Settlement and Payout: Acquirer Funding
*How a captured card transaction turns into money in a merchant's bank account — batching, gross-to-net fees, reserves, adjustments, and the T+N funding file.*

A cardholder taps, the terminal shows "approved," and the merchant assumes the money is theirs. It isn't — not yet. Authorization only reserves funds; **capture** flags the transaction for collection; and **settlement** is the multi-day pipeline that actually moves money from the card networks, through the acquirer, and into the merchant's account. The gap between the amount on the receipt and the amount that lands in the bank is where most of an acquirer's engineering — and most of a merchant's confusion — lives.

This post walks the settlement pipeline as an engineer would build it: how captures are batched, how gross becomes net, why a slice is held back in reserve, how disputes claw money back, and how the final payout is reconciled against the transactions that produced it.

## The pipeline at a glance

```
  Sources          Batch          Compute            Settle             Payout
  -------          -----          -------            ------             ------
 Captured   ====>  Batch   ====> Gross-to-Net ====> Settlement  ====>  Merchant
   Txns            Cutoff        (fee engine)         Ledger           Payout
                     ^                |                 ^  |          (T+2 file)
 Fee ----------------+           holdback |             |  |
 Schedules                                v             |  +---> Reconciliation
                                    Rolling Reserve     |         (captures
 Chargebacks ------------------------------------------>+          vs payout)
 (dispute debits)
```

> **▸ [Open the interactive diagram](/blog/diagrams/fintech-merchant-settlement-payout.html)** — the settlement pipeline from captured card transactions to the merchant funding file.

## The batch and the cutoff

Card settlement is a **batch** system by nature. Captured transactions accumulate throughout the day, and at a fixed **cutoff** — say 22:00 in the acquirer's processing timezone — everything since the last cutoff is closed into a settlement batch. Transactions captured after the cutoff roll into the next day's batch. That single design choice explains most "why did my payout land a day later than I expected" tickets.

Engineering-wise, the cutoff must be **deterministic and idempotent**. If the batch job runs twice, it must not double-count. The usual pattern is a monotonic batch identifier plus a status column on each capture (`captured → batched → settled → funded`), advanced only by a state machine that refuses illegal transitions. Late-arriving captures, reversals, and partial captures all have to be resolved *before* the cutoff snapshot is taken, because once a batch is closed it is treated as immutable — corrections happen as new adjustment entries, never as edits to a closed batch.

## Gross to net: where the money shrinks

The receipt shows the **gross** amount. The merchant is funded the **net**. Three deductions sit between them, and computing them correctly per transaction is the heart of the fee engine:

- **Interchange** — paid to the card-issuing bank. It is not one number; it is a matrix keyed by card type (debit, credit, rewards, commercial), transaction channel (card-present, e-commerce, keyed), merchant category code, and region. A single acquirer may resolve hundreds of interchange categories.
- **Scheme fees** — paid to the card network for switching and assessment. Smaller than interchange, but numerous and easy to miscount.
- **Acquirer markup** — the acquirer's own margin, structured as interchange-plus (a fixed markup over pass-through cost) or as blended/tiered pricing.

The fee engine joins each captured transaction against the merchant's **fee schedule** — the per-merchant contract of rates — and produces line items: `gross − interchange − scheme − markup = net`. The engineering discipline here is precision and auditability. Money math runs in integer minor units (cents), never floats. Every deduction is stored as its own ledger line with the rule and rate that produced it, so a merchant statement can later be reconstructed line by line. Rounding is defined once, at a documented step, and applied consistently — a half-cent rounded the wrong way, multiplied across millions of transactions, becomes a real reconciliation break.

## Rolling reserves and risk holdbacks

Acquirers carry the liability for chargebacks that a merchant cannot cover. A merchant that ships goods weeks after payment, or suddenly goes insolvent, is a credit risk to the acquirer. The mitigation is a **rolling reserve**: a percentage of settled volume (commonly 5–10%) is withheld from each payout and parked in a reserve balance, then released on a schedule — for example, funds held for 90 days and released on a rolling basis thereafter.

In the pipeline this is a **branch off the compute stage**, not part of the main funding flow. The gross-to-net result splits: the reserve portion posts to a reserve balance account, and only the remainder flows toward the funding file. Two properties matter for correctness. First, the reserve is its own ledgered account — you must always be able to answer "how much of this merchant's money are we holding, and when does each tranche release." Second, **release is time-driven, not batch-driven**: today's payout may include a reserve tranche held back 90 days ago, so the release schedule is a separate scheduled process that injects credits back into the funding computation when tranches mature.

## Chargebacks and adjustments

Not all money flows toward the merchant. **Chargebacks** — disputes initiated by the cardholder — pull money back, and along with refunds, fee corrections, and reversals they form the **adjustment** stream. Adjustments post to the settlement ledger as debits against the merchant, netted into the same payout cycle.

The key engineering rule is that adjustments are **additive ledger entries, never mutations** of the original transaction. A chargeback on a transaction that already settled last week does not rewrite last week's batch; it posts a new debit dated today. This keeps every batch immutable and every balance explainable as a sum of entries. When a merchant's adjustments in a cycle exceed their sales, the net payout goes negative and the balance is either drawn from the reserve or carried as a debt — an edge case the funding logic must handle explicitly rather than clamping silently to zero.

## The funding file and the T+N payout

Once the ledger holds settled net, minus reserve, plus or minus adjustments, the acquirer produces a **funding file** — the instruction set that moves money to merchants. In practice this is a batch of payout instructions handed to a bank rail (ACH, SEPA, or wire), keyed by the merchant's settlement account. The delay is the familiar **T+N**: T+1 or T+2 is typical, reflecting network settlement timing plus the acquirer's own risk and processing windows.

The funding file is the moment of truth, so it is generated transactionally: the ledger entries that feed a payout are marked `funded` in the same commit that emits the instruction, so a retry can never pay a merchant twice. Each payout carries a settlement reference that the merchant can match against their statement, closing the loop between what they sold and what they received.

## Reconciliation: proving the payout

The final engineering obligation is **reconciliation** — proving that every unit of money is accounted for. Two ties matter. The **downward** tie: each payout must decompose exactly into the captured transactions, fees, reserve movements, and adjustments that produced it — `sum(captures) − fees − reserve + releases − adjustments = payout`, to the cent. The **outward** tie: the acquirer's own settlement received from the card networks must match what it collected from cardholders and paid to merchants, so the acquirer is never silently short or long.

Reconciliation reads the immutable ledger rather than live state, which is exactly why immutability and per-line fee entries were worth the effort upstream. When a tie fails, the break is **quarantined** — the affected merchant or transaction is held out of the funding file rather than shipping a wrong payout — and flagged for investigation. A settlement system is judged less by how fast it pays and more by whether every cent it pays can be explained. Get the ledger right, and the payout, the reserve release, and the reconciliation all fall out of the same source of truth.
