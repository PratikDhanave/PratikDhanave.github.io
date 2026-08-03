# Engineering Escrow: Conditional Hold and Release with Double-Entry Safety

*How to build escrow and conditional hold/release — segregated ledger accounts, release conditions and approvals, partial releases, and expiry auto-refund that never strand money.*

Escrow looks deceptively simple from a product brief: hold a buyer's money until a condition is met, then pay the seller. Engineers who reach for a boolean `is_released` column and a nullable `released_at` timestamp discover the truth during the first audit — escrow is not a status flag on a payment row, it is a small ledger with its own invariants. The money physically exists somewhere the whole time, and that "somewhere" has to be a real account you can reconcile against your bank.

This post walks through how to model escrow as segregated ledger accounts, drive it with a hold/release state machine, and handle the messy exits: partial releases, disputes, and expiry auto-refunds — all while keeping double-entry balanced at every transition.

## Escrow is a segregated account, not a flag

The first architectural decision is where held funds live. A held amount is not the buyer's money anymore, and it is not yet the seller's. It is a liability you owe to whichever party the condition resolves toward. That means it deserves its own ledger account, segregated per escrow agreement (or at least per program, with a sub-ledger keyed by agreement).

Concretely, you open an `escrow_liability` account and move money into it with a balanced journal entry. Nothing about escrow should ever be a single-sided update.

```
Deposit (buyer funds $100 into escrow #A17)
  DR  buyer_clearing         100.00   (cash you received settles here)
  CR  escrow_liability:A17   100.00   (you now owe this to someone)

Release (condition met, pay seller $100)
  DR  escrow_liability:A17   100.00   (obligation discharged)
  CR  seller_payable:S9       100.00   (now owed to the seller's payout)
```

> **▸ [Open the interactive diagram](/blog/diagrams/fintech-escrow-hold-release.html)** — pan, zoom, and trace every step (light/dark, self-contained).

Two properties fall out of this model immediately. First, the escrow balance is always the sum of its journal lines — there is no separate "amount held" field to drift out of sync. Second, at any instant `SUM(escrow_liability:*)` across all agreements must equal the balance in the real segregated bank account holding customer funds. That equality is your daily reconciliation check, and it is the single most important control escrow gives you.

## The hold/release state machine

Escrow money moves through a small, well-defined set of states. Modeling those states explicitly — rather than inferring them from timestamps — is what keeps the system auditable.

- **Deposited** — funds received into buyer clearing, journal posted, agreement created.
- **Held in escrow** — the steady state; money sits in the segregated liability account.
- **Condition check** — a decision point triggered by an event: buyer approval, delivery confirmation, an oracle, or a timer.
- **Releasing** — the transition is posting balanced entries toward the beneficiary.
- **Released** — terminal success; the obligation is discharged.

Two exit branches leave that happy path at the condition check — the waiting state where you evaluate whether to pay out. A **dispute** freezes the check and hands off to an arbitration process. An **expiry** fires when the release condition is never met inside the agreed window, triggering an auto-refund back to the buyer. Each of those branches is itself a balanced journal entry — a dispute resolution and an expiry refund both credit a payout account and debit the escrow liability, they just point at different beneficiaries.

The important design rule: transitions between these states are the *only* places money moves, and every transition emits exactly one balanced journal entry. If you find yourself writing code that changes a balance outside a state transition, you have a bug waiting to happen.

## Partial releases without losing the plot

Real escrow rarely resolves all-or-nothing. A milestone project releases 30% now and 70% on completion; a marketplace releases the item price to the seller but holds a returns reserve. Partial releases are where naive implementations break, because the "is it released?" boolean has no answer.

The ledger model handles this for free: a partial release is just a journal entry for part of the balance. The escrow account's remaining balance *is* the remaining held amount. You never track "released so far" separately — you sum the postings.

The one rule you must enforce is that you cannot release more than is held. That is an invariant check against the current escrow balance at posting time, executed inside the same transaction that writes the journal lines:

```python
def release(agreement_id, amount, beneficiary, idem_key):
    with ledger.transaction() as tx:
        held = tx.balance(f"escrow_liability:{agreement_id}")
        if amount > held:
            raise InsufficientEscrow(agreement_id, requested=amount, held=held)
        tx.post(idempotency_key=idem_key, lines=[
            Line(f"escrow_liability:{agreement_id}", debit=amount),
            Line(f"{beneficiary}_payable",            credit=amount),
        ])
```

Note the `idempotency_key`. Release requests arrive over networks that retry. Keying each posting on a caller-supplied idempotency key means a retried release is a no-op that returns the original result, rather than paying the seller twice. This is not optional — a duplicate release is real money leaving the building.

## Expiry and auto-refund

Every escrow needs a deadline, because unresolved held funds are both a liability on your books and, in many jurisdictions, subject to unclaimed-property rules. The clean design is a scheduled sweep that finds agreements past their expiry with a non-zero balance and posts a refund to the original funding source.

```
Expiry auto-refund (window elapsed, condition never met)
  DR  escrow_liability:A17   100.00
  CR  buyer_refund_payable    100.00
```

The subtlety is racing against a genuine last-second release. Guard the expiry sweep with the same state machine: only an agreement still awaiting its condition transitions to `expired`. If a release grabbed the row and moved it to `releasing` first, the expiry job sees the new state and skips it. Optimistic locking on the agreement's state column — or simply selecting `FOR UPDATE` inside the sweep transaction — closes the window. Make the refund posting idempotent on the agreement id and the expiry date so a re-run of the sweep cannot double-refund.

## Invariants worth testing

Escrow is a place to be paranoid, because the failure mode is stranded or duplicated customer money. The tests that earn their keep are the invariant tests, not the happy-path ones.

- **Conservation**: for any agreement, deposits equal releases plus refunds plus current held balance. No money appears or disappears.
- **Non-negative balance**: an escrow account can never go below zero; the release guard is exercised with a release larger than the held amount.
- **Bank equality**: total escrow liability equals the segregated bank balance — run this as a reconciliation job, not just a unit test.
- **Idempotent transitions**: replay every state transition with the same idempotency key and assert the ledger is unchanged after the first application.
- **Exit exclusivity**: an agreement cannot be both released and refunded; drive a dispute and an expiry at the same instant and assert exactly one wins.

Build escrow as a ledger with a state machine on top, make every transition a balanced and idempotent posting, and reconcile the total against a real segregated account daily. Do that, and the hard questions — "where is this customer's money right now?" — always have a single, provable answer.
