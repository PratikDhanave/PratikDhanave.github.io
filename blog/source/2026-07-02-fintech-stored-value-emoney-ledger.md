# Stored-Value and E-Money Wallet Ledgers

*Designing a closed-loop wallet from the ledger up: double-entry balances, the money lifecycle, safeguarding client funds 1:1, and the engineering that keeps top-ups, holds, and reconciliation honest.*

A stored-value wallet looks trivial from the outside. There is a number, the number goes up when you add money, and it goes down when you spend. Under that number sits one of the more unforgiving pieces of software you can build, because the number *is* the product. If it is wrong by a cent, you have not shipped a bug — you have either lost customer money or invented some. This post is about the ledger design and the money lifecycle behind a closed-loop wallet, and the engineering decisions that keep the balance trustworthy.

## The balance is not a column

The first instinct is to store `balance` as an integer on the account row and mutate it. Do not. A mutable balance field has no history, no explanation, and no way to answer "why is this number what it is?" when a customer or a regulator asks. Instead, the balance is *derived* from an append-only ledger of double-entry postings.

Every movement of value is recorded as balanced debits and credits across accounts. A wallet top-up is not "add 50 to the user"; it is a paired posting: **debit** the payment-gateway clearing account, **credit** the user's wallet account, both for the same amount, both stamped with the same transaction ID. The invariant is boring and absolute: for every transaction, the sum of debits equals the sum of credits. If it does not, the transaction is rejected before it is ever written. Because the ledger is append-only, you never edit a posting — you reverse it with an equal-and-opposite one. The current balance is `SUM(credits) - SUM(debits)` over the account, and it can always be rebuilt from zero.

## The money lifecycle

A single unit of value does not just sit in "balance." It moves through states, and each transition is a ledger event. Closed-loop wallets converge on the same shape: money is topped up, becomes available, may be reserved by a hold, is spent (captured), and finally settles — with refunds and withdrawals branching off the later phases.

```
  TOP-UP        AVAILABLE        HOLD          SPENT         SETTLED
 ┌────────┐   ┌──────────┐   ┌──────────┐   ┌────────┐   ┌──────────┐
 │ cleared│──▶│ spendable│──▶│ reserved │──▶│ capture│──▶│ reconciled│
 │  1:1   │   │ balance  │   │ (auth)   │   │ / debit│   │ to safeguard│
 └────────┘   └────┬─────┘   └──────────┘   └───┬────┘   └────┬─────┘
                   │ available = ledger − holds  │ refund      │ withdraw
                   ▼                             ▼             ▼
              (holds cut spendable,        ┌──────────┐  ┌──────────┐
               ledger unchanged)           │ REFUNDED │  │ WITHDRAWN│
                                           │ returned │  │ to bank  │
                                           └──────────┘  └──────────┘
```

> **▸ [Open the interactive diagram](/blog/diagrams/fintech-stored-value-emoney-ledger.html)** — pan, zoom, and trace the wallet balance lifecycle from top-up to settlement (light/dark, self-contained).

## Available balance vs ledger balance

The single most common source of wallet confusion — for users and engineers alike — is conflating two different numbers.

The **ledger balance** is the truth of the double-entry books: total credits minus total debits, settled money the wallet actually holds. The **available balance** is what the customer is allowed to spend right now. They differ by the sum of active holds:

```
available = ledger balance − Σ(active holds)
```

When a customer taps to pay, you do not immediately debit the ledger. You place a **hold** (an authorization) that reserves the amount. The ledger balance is unchanged — the money is still theirs — but the available balance drops so they cannot double-spend it. Only when the transaction captures does the hold convert into a real debit posting and the ledger balance moves. If the merchant never captures, the hold expires and the available balance heals back on its own. Modelling holds as first-class ledger objects with an expiry, rather than as ad-hoc subtractions, is what makes this correct under concurrency.

## Safeguarding: the money is not yours to lend

Here is the part that separates an e-money wallet from a bank account. When a customer tops up, that cash is **e-money** — a claim on the issuer — and the corresponding real money must be **safeguarded**: held 1:1 in a segregated account, typically at a bank or in low-risk liquid assets, and never lent out, invested for yield, or commingled with operating funds. If the issuer fails, safeguarded funds are ring-fenced so customers can be made whole.

This has a hard engineering consequence: the total of all customer wallet balances in your ledger must, at all times, be backed by an equal or greater balance in the safeguarding account. That is not a nightly nicety — it is the core solvency invariant:

```
Σ(customer wallet balances) ≤ balance in safeguarding account
```

Every top-up must land in safeguarding before — or atomically with — the wallet credit becoming spendable. Every withdrawal must leave safeguarding as the wallet is debited. The ledger and the bank must move together, and reconciliation exists to prove they did.

## Engineering the transitions

**Idempotent top-ups.** Payment webhooks are retried, duplicated, and delivered out of order. If a top-up handler is not idempotent, one payment becomes two credits and you have minted money. The fix is an idempotency key — the gateway's payment ID, or a client-supplied UUID — enforced by a unique constraint on the ledger transaction. The handler's contract becomes: "given this key, ensure exactly one matching transaction exists." A retry finds the existing row and returns the same result instead of writing a second one. Ledger writes for a single transaction must also be atomic: both legs of the double entry commit together or neither does.

**Idempotent holds and captures.** A hold, its capture, its release, and any refund are each keyed to the original authorization. Capturing an already-captured hold is a no-op that returns the prior result. Releasing an expired hold twice does not credit the customer twice. Because holds carry an expiry, a background sweep releases stale ones — and that sweep must itself be idempotent, because it will run concurrently with a late capture and the two must not both win.

**Reconciliation.** Reconciliation is the daily proof that the internal ledger and the external safeguarding account agree. You pull the bank statement, match each external movement to an internal transaction by reference, and assert that unmatched items on either side net to zero. Breaks — a top-up in the bank with no ledger entry, or vice versa — are surfaced immediately, because a persistent break is either a bug or the early signature of a solvency problem. The reconciliation job reads the ledger; it never fixes discrepancies by editing balances. Corrections flow back through the same double-entry postings as everything else, so the books stay explainable.

## Why the discipline pays off

A wallet built this way is auditable by construction. Any balance can be replayed from its postings; any discrepancy is a named ledger break, not a mystery; and the safeguarding invariant turns "are we solvent?" into a query you can run on demand rather than a quarterly hope. The lifecycle — top-up, available, hold, spend, settle, with refunds and withdrawals hanging off the end — is not incidental structure. It is the set of states in which money is allowed to exist, and every one of them is a balanced pair of entries in an append-only book.
