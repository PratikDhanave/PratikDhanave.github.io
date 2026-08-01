# Engineering a Two-Tier Retail CBDC: Ledger, Intermediaries, and Offline Payments

*Lay out a two-tier retail CBDC — central-bank ledger, intermediaries, retail wallets, and the offline mode that makes engineers nervous.*

Most of the retail central-bank digital currency (CBDC) discussion happens at the policy layer. As an engineer, the part that matters to me is the shape of the system: who holds the ledger, who touches the customer, and what happens when the network is gone. The design that keeps surfacing is a *two-tier* model, and once you draw it, the engineering constraints fall out almost mechanically.

The word "two-tier" is doing real work. Tier one is the central bank, which issues the currency and keeps the authoritative record of how much exists. Tier two is a set of regulated intermediaries — commercial banks and payment service providers — that onboard customers, run wallets, and handle day-to-day support. The central bank deliberately does not want a hundred million retail accounts and a support desk. It wants a wholesale ledger and a small number of accountable counterparties.

```
  TIER 1 (central bank)         TIER 2 (intermediaries)        RETAIL EDGE
  ┌──────────────┐   issue   ┌──────────────┐   distribute  ┌──────────────┐
  │ Central Bank │──────────▶│ Core Ledger  │──────────────▶│ Bank / PSP   │
  └──────────────┘  / redeem └──────┬───────┘               └──────┬───────┘
                                    │                               │ provision
                                    │ reconcile                     ▼
                              ┌─────┴──────┐                 ┌──────────────┐
                              │ Settlement │◀── deferred ────│ Retail Wallet│
                              │  / Recon   │     sync        └──────┬───────┘
                              └────────────┘                        │ online / offline
                                                             ┌──────▼───────┐
                                                             │  Merchant    │
                                                             └──────────────┘
```

> **▸ [Open the interactive diagram](/blog/diagrams/fintech-cbdc-two-tier-architecture.html)** — pan, zoom, and trace every step (light/dark, self-contained).

## What the central-bank ledger actually stores

The Tier 1 ledger is the smallest, most conservative component in the whole system, and it should stay that way. Its job is to record claims on the central bank, and every unit of retail CBDC in circulation is a direct liability of the central bank — not of the intermediary that happens to be servicing the wallet. That single property is the reason people care about CBDC at all: it removes the intermediary's balance sheet from the risk equation.

Because it is a direct liability, the ledger cannot be a black box that only the central bank can reason about. I model it as an append-only record of issuance and redemption events, plus a running position per intermediary. Note the granularity: at the wholesale tier I track balances *per intermediary*, not per end user. The retail-level ledger — which wallet holds which token — lives one tier down, or is split so that no single party sees both the identity and the full transaction graph. This split is a privacy decision with direct schema consequences, and it is easier to get right at design time than to retrofit.

Two operations dominate: **issue** (mint against a commercial-bank reserve debit) and **redeem** (burn and credit reserves back). Everything else is movement that nets to zero at this tier. If your Tier 1 ledger is doing anything more complicated than that, some Tier 2 responsibility has leaked upward.

## Intermediaries do the hard, boring work

Tier 2 is where the engineering effort concentrates, because this is where the messy real world lives. Intermediaries run KYC and onboarding, issue wallets, enforce holding limits, field disputes, and translate between the CBDC rails and the account-based world customers already know.

Holding limits deserve a mention because they are a systemic control implemented in ordinary application code. A retail CBDC that pays no interest and has no cap could, in a crisis, drain deposits out of commercial banks and into the central bank overnight — the digital equivalent of a bank run at fibre speed. The usual mitigation is a per-wallet cap plus a "waterfall": funds above the cap automatically sweep to a linked commercial bank account. That waterfall is a Tier 2 feature. It has to be idempotent, it has to be observable, and it has to fail closed, because a bug there is a monetary-policy incident, not just a customer complaint.

The intermediary also owns the customer relationship end to end. When a wallet is lost, the recovery flow, the identity re-verification, and the balance restoration are all Tier 2 problems. The central bank should never be paged because someone dropped their phone.

## The wallet and the online payment

At the retail edge, a payment between two wallets is conceptually simple: decrement the payer, increment the payee, and make the two happen atomically. When both parties are online, the intermediaries mediate the transfer and the position updates propagate up to the ledger on the usual settlement cadence. There is nothing exotic here — it looks like any well-built account-to-account transfer, with the important difference that the value being moved is a central-bank liability rather than commercial-bank money.

The interesting design questions are about *what the payer's device is allowed to assert*. In the online case, not much: the intermediary is the source of truth and can reject an overdraft. The device is a thin client. That comfortable assumption is exactly what breaks in offline mode.

## Offline payments and the double-spend problem

Offline capability is the headline feature and the hardest engineering problem in the entire design. The requirement is that two people can exchange value with no connectivity — a phone-to-phone transfer on a train, in a disaster zone, in a rural area with no signal. The instant you allow that, you have handed the payer's device the authority to move money without a central check, and you have re-created the double-spend problem that ledgers exist to prevent.

The realistic answer is hardware. Each wallet carries a **secure element** — a tamper-resistant chip that holds keys and an offline balance the host application cannot forge. An offline transfer is a signed message between two secure elements: the payer's element decrements its own counter and produces a cryptographic proof, and the payee's element verifies the signature and increments. The device operating system never sees the keys.

This bounds the risk rather than eliminating it. A compromised secure element can double-spend until it reconnects and gets caught, so the design leans on limits and windows:

```
offline balance ── loaded from online balance, capped (e.g. small value)
     │
     ├─ pay offline ── SE signs, decrements counter, emits proof
     │        (bounded: max N offline txns, max value, max time offline)
     │
     └─ reconnect ── replay proofs to intermediary ── reconcile to ledger
                       │
                       └─ conflict? ── flag device, freeze, investigate
```

Small caps, a limited number of consecutive offline transactions, and a maximum offline duration together keep the blast radius of any single compromised element tiny. The design decision is explicit: you are trading absolute prevention for detectable, bounded fraud. For a physical-cash replacement, that is the same trade society already accepts with banknotes.

## Reconciliation is where correctness is proven

Offline transactions are promissory until they sync. When a device reconnects, it replays its queue of signed proofs to its intermediary, which forwards net positions up to the Tier 1 ledger. Reconciliation is therefore not a background nicety — it is the step where the system finally proves that no money was created or destroyed.

Two properties matter most. First, **replay must be idempotent**: the same offline proof can arrive twice — from a retried sync, or from both counterparties uploading the same transaction — and it must apply exactly once. I key on a per-element monotonic counter so duplicates collapse. Second, **conflicts must be loud**. If a secure element's proofs imply it spent value it never held, that is a compromise signal; the correct response is to freeze the element and investigate, not to silently drop the transaction.

If I were building this, the things I would watch in production are unglamorous: the offline-to-online sync lag distribution, the rate of reconciliation conflicts per device cohort, and whether the holding-limit waterfall ever double-sweeps. The cryptography is the part everyone reviews; the state machine around reconnection and settlement is the part that actually decides whether the money is right.

None of this is speculative architecture for its own sake. Draw the two tiers, put the ledger where liabilities belong, push the customer-facing complexity down to accountable intermediaries, and treat the offline path as a bounded-risk hardware problem rather than a distributed-consensus fantasy — and the retail CBDC stops looking like a research topic and starts looking like a system you could actually operate.
