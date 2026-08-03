# Modeling Card Chargebacks as a State Machine

*Modeling the full card dispute lifecycle with reason codes, evidence deadlines, representment, arbitration, and provisional-credit ledger entries at every transition.*

Most teams first meet chargebacks as a support ticket: money left the merchant account, a cardholder complained, and someone has to gather receipts. That framing is where dispute systems go wrong. A dispute is not a ticket. It is a regulated, deadline-driven negotiation between an issuer and an acquirer, with a scheme sitting in the middle enforcing timers. If you model it as anything other than a state machine, you will miss deadlines, double-post ledger entries, and lose funds you could have kept.

This post walks through how to model the card dispute lifecycle explicitly: the states, the transitions that reason codes and deadlines trigger, and the ledger movements that must accompany each transition so your books never lie about who is holding the money.

## Why a state machine, not a workflow

A workflow describes what a person does next. A state machine describes what the system *is*, and constrains what can happen from here. Disputes need the second model because the scheme, not your code, owns the clock. When an issuer files a chargeback, a representment window opens — commonly 30 to 45 days depending on network and reason code. Miss it and you forfeit by default, regardless of how strong your evidence was. The scheme does not care that your ops queue was backed up.

Encoding this as explicit states buys three things. First, every state carries exactly one active deadline timer, so "what is about to expire" is a query, not a spreadsheet. Second, transitions are the only place money moves, which gives you a single choke point to enforce double-entry correctness. Third, illegal moves become impossible by construction: you cannot represent a case that is already in arbitration, and the type system says so.

The core lifecycle looks like this. Each box is a state; each arrow is a transition guarded by an event and a deadline.

```
  first_chargeback ──accept──▶ accepted (loss)
        │
        │ submit evidence (T+30d)
        ▼
   representment ──issuer accepts──▶ won
        │
        │ issuer re-files (pre-arb)
        ▼
   pre_arbitration ──merchant accepts──▶ lost
        │
        │ escalate (T+30d)
        ▼
    arbitration ──scheme ruling──▶ won │ lost
```

> **▸ [Open the interactive diagram](/blog/diagrams/fintech-chargeback-dispute-state-machine.html)** — pan, zoom, and trace every step (light/dark, self-contained).

Notice that `won` and `lost` are terminal and can be reached from several stages. That is deliberate: a dispute can end early at any negotiation round. The machine's job is to make every exit explicit and every exit's ledger effect correct.

## States and their invariants

Model states, not statuses. A status is a label; a state has invariants the system enforces.

- **`retrieval` / `first_chargeback`** — the entry state. A retrieval request is informational (the issuer wants the transaction record); a first chargeback is a real debit. On entry to `first_chargeback`, funds are pulled from the merchant. The invariant: a provisional reservation exists against the merchant balance.
- **`representment`** — the merchant has contested and submitted evidence. Invariant: evidence artifacts are attached and a submission deadline was met. The disputed amount is still reserved.
- **`pre_arbitration`** — the issuer rejected the representment and re-filed, usually with new information. Invariant: this is a second issuer challenge, distinct from the first, with its own deadline.
- **`arbitration`** — one side escalated to the scheme for a binding ruling. Invariant: a filing fee is committed, and the loser typically pays it.
- **`won` / `lost` / `accepted`** — terminal. Invariant: no reservation remains; the disputed amount has been definitively released back to the merchant or paid to the cardholder.

The state should carry the reason code, the network, the disputed amount, the current deadline, and a monotonic revision counter. The reason code matters because it changes both the evidence you need and the deadline you get; a fraud reason code (cardholder says "I never authorized this") demands different proof than a "goods not received" code, and the networks assign different representment windows to each.

## Deadlines as first-class timer state

Every non-terminal state has exactly one governing deadline. The cleanest implementation is to store `deadline_at` on the state itself and drive transitions from a single timer sweep rather than scattering `setTimeout` logic across services.

```
on enter(state):
    deadline_at = now + window_for(network, reason_code, state)
    schedule_check(case_id, deadline_at)

on timer_fire(case_id):
    case = load(case_id)
    if case.state == representment and no_evidence_submitted:
        transition(case, to=lost, cause="representment_deadline_missed")
```

The subtlety: the timer must be idempotent and race-safe against a human action landing at the same moment. Load the case, check the state and revision inside a transaction, and only transition if nothing changed underneath you. If an analyst submitted evidence one second before the sweep, the revision counter moved and the auto-loss is a no-op. This is the same optimistic-concurrency discipline you would use anywhere money is at stake, applied to the deadline itself.

## Ledger entries at every transition

Here is the part teams underestimate: the dispute state machine is also a ledger driver, and the two must move together atomically. If the state changes but the ledger does not — or vice versa — you have money that exists in one system and not the other.

Use a reservation model rather than moving cash directly. When a chargeback lands, you do not debit the merchant's settlement account outright; you post a **provisional debit** against a dispute-holding account. That keeps the disputed amount visible and reversible.

| Transition | Ledger effect |
|---|---|
| enter `first_chargeback` | provisional debit: merchant → dispute-hold |
| enter `won` | reverse reservation: dispute-hold → merchant |
| enter `lost` / `accepted` | finalize: dispute-hold → issuer settlement |
| enter `arbitration` | commit filing-fee reservation |
| arbitration ruling | release fee to winner, charge loser |

Every one of these postings must be part of the same atomic unit as the state transition, keyed by an idempotency token derived from `(case_id, revision, transition)`. Replay the same scheme notification twice — which networks *will* do — and the second attempt hits the same idempotency key and is a no-op. Without that key, a duplicate `first_chargeback` notification debits the merchant twice, and you will find it only during month-end reconciliation, long after the money moved.

## Reconciliation and the invariant that saves you

The single invariant worth asserting continuously: the balance of every dispute-hold account equals the sum of disputed amounts across all non-terminal cases. If a case is `representment` for 120 units, the hold account must carry exactly that reservation. Run this check on a schedule; any drift means a transition posted a ledger entry it should not have, or skipped one it should have.

This invariant is what turns a pile of edge cases — duplicate notifications, deadline races, partial-amount disputes — into something you can trust. The state machine makes transitions explicit, the reservation model makes money movements reversible, and the reconciliation check makes both auditable. Build the dispute engine in that order and the "chargeback support ticket" becomes a system you can reason about instead of a source of quiet losses.
