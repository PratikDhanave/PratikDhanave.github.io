# Building Marketplace Split Payments and Connected Payouts

*Architecting platform balances, commission splits, delayed payouts, and negative-balance recovery without ever losing a cent.*

---

A marketplace takes one card charge from a buyer and turns it into money owed to several parties: the seller, the platform's commission, a tax authority, sometimes a shipping partner. The buyer sees a single line on their statement. Internally, that one settlement has to fan out into balanced ledger entries, sit in the right accounts until a payout schedule releases it, and survive refunds that arrive after the seller has already been paid. Getting this wrong doesn't produce a visual glitch — it produces money that is either double-counted or stranded. This post is about how to build that money-movement layer so the arithmetic is always closed.

## Two balance planes: platform vs connected accounts

The first design decision is where money lives before it reaches a seller's bank. You keep two conceptual planes. The **platform balance** is your own settlement account — every buyer charge lands here first, because the acquirer settles to *you*, not to the seller. The **connected-account balances** are per-seller sub-ledgers you maintain yourself; they are claims against the platform balance, not separate bank accounts.

This matters because the acquirer knows nothing about your sellers. You receive one net settlement per day (gross charges minus refunds minus scheme fees), and you are responsible for attributing slices of it. So a connected-account balance is a liability on your books: "we hold $X that we owe seller S." The invariant you defend is that the sum of all connected-account balances plus your own retained revenue equals the funds actually sitting in the platform's real bank account, minus money already paid out and still in flight.

Model each seller balance with at least three states, not one number:

- **Pending** — funds captured but inside the settlement/refund risk window.
- **Available** — cleared and eligible for the next payout run.
- **Reserved** — held back deliberately (rolling reserve, dispute cover).

Collapsing these into a single integer is the most common early mistake; you lose the ability to reason about *why* a balance can't be paid out yet.

## Splitting one charge into balanced entries

When a $100 charge succeeds, the split happens as a set of journal entries posted atomically. Think in double-entry terms: the buyer's payment is a credit into the platform's clearing account, and the offsetting debits allocate it across the parties. Every split must sum exactly to the captured amount — you validate this before committing, and reject the transaction if the components don't reconcile to the cent.

```
Buyer charge: $100.00 captured
        │
        ▼
┌───────────────────────────────────────────────┐
│ SPLIT ALLOCATION (must sum to 100.00)          │
│                                                │
│   seller_net        →  $84.00  (connected S)   │
│   platform_fee      →  $10.00  (revenue)       │
│   tax_withheld      →   $6.00  (tax liability) │
│                        ───────                 │
│                        $100.00  ✓ closed       │
└───────────────────────────────────────────────┘
        │
        ▼
   seller S pending balance += 84.00
   platform revenue         += 10.00
   tax liability account    +=  6.00
```

> **▸ [Open the interactive diagram](/blog/diagrams/fintech-marketplace-split-payments.html)** — pan, zoom, and trace every step (light/dark, self-contained).

Compute the split *before* you attempt the charge, store it alongside the payment intent, and treat it as the source of truth. Do not recompute percentages at capture time from a fee config that may have changed since the buyer checked out — a rate edit mid-flight will silently unbalance in-flight orders. Freeze the fee schedule version onto the order, the same way you'd freeze a currency rate.

Rounding is where cents leak. If your commission is a percentage, decide up front who absorbs the rounding remainder. A clean rule: compute the platform fee and tax with banker's rounding, then let the seller's net be the *residual* (`total − fee − tax`). That guarantees the sum closes exactly, because the residual is defined by subtraction rather than independently rounded.

## Delayed payouts and the schedule engine

Sellers are almost never paid instantly. You hold funds for a payout window — partly to cover refunds and disputes, partly because your own bank settlement clears on T+1 or T+2. A payout engine runs on a schedule (daily, weekly, or manual) and does three things per seller: sweep the *available* balance, subtract any *reserved* amount, and emit a single payout instruction to the seller's bank via ACH, SEPA, or a faster rail.

The engine must be idempotent per (seller, schedule-period). If a payout run crashes halfway, re-running it must not double-pay. Key each payout on a deterministic identifier — `payout:{seller}:{period}` — and make the balance decrement and the payout-record insert one atomic transaction. A payout is not "money sent," it's a state machine: `created → submitted → paid` or `→ failed → retryable`. Only move the balance out of the connected account when the payout reaches `paid`; before that it sits in an *in-transit* sub-state so a failed bank transfer flows the money back to *available* rather than vanishing.

## Negative balances: when refunds outrun payouts

The hard case. A seller sells $500 on Monday, gets paid out Tuesday, and on Wednesday a buyer refunds a $400 order. The refund debits the buyer's card from *your* platform balance, but the seller's connected balance is now near zero — you already paid them. The seller balance goes negative, and you are out of pocket until you recover it.

You cannot prevent this entirely, so you engineer for recovery:

- **Rolling reserve** — hold back a percentage of every payout (say 10% for 90 days) so there's a buffer to absorb late refunds before the balance goes negative.
- **Debit-first ordering** — always deduct refunds and chargebacks from *available* before touching *reserved*, and net new sales against a negative balance before any fresh payout.
- **Payout gating** — a seller with a negative balance is ineligible for payout until the balance is cured by new sales or an external top-up.
- **Recovery workflow** — if the balance stays negative past a threshold, trigger a collection process (debit a linked bank account, or write it off against reserves).

The ledger stays honest throughout: a negative connected balance is a *receivable* the platform holds against the seller, and it must show up as such in reconciliation, not as a mysterious hole in the platform account.

## Merchant-of-record vs facilitator: who owns the money

The regulatory shape of all this depends on one architectural choice. As a **payment facilitator**, you are a conduit — the seller is the merchant of record, funds are legally theirs, and you're moving money on their behalf. As **merchant of record (MoR)**, the platform *is* the seller to the buyer: you own the transaction, remit tax, and handle disputes, then pay the underlying seller as a supplier.

This is not cosmetic. MoR means tax liability, chargeback exposure, and refund obligation sit on the platform, so your ledger needs a full tax-liability account and dispute reserves. Facilitator means lighter tax handling but stricter KYC/onboarding duties on each connected account, because you're enabling *them* to accept money. Pick the model before you design the accounts — retrofitting tax remittance and dispute ownership onto a ledger that assumed pass-through is a painful migration. Encode the choice explicitly so every split, every payout, and every dispute entry knows which party owns the obligation.

Build the money layer around one non-negotiable rule: every charge, split, payout, refund, and reserve is a balanced double-entry event, and at any instant the connected balances plus retained revenue plus in-transit payouts reconcile exactly to the real bank position. If that identity holds, the marketplace can scale sellers, rails, and regions without the arithmetic ever drifting.
