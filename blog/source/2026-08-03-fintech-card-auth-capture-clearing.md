# Card Authorization, Capture, and Clearing: One Transaction, Three Money States

*How to model the card payment as a two-phase auth-then-capture flow plus a clearing tail — handling incremental auths, partial captures, reversals, expiry, and the auth-vs-settled reconciliation that trips up every ledger.*

---

## One purchase, three different truths about the money

A card payment feels atomic to the shopper: tap, approved, done. Inside a payment platform it is nothing of the sort. A single purchase moves through at least three distinct money states, and each one answers a different question.

- **Authorization** answers *"does the cardholder have the funds and is this transaction allowed right now?"* It places a hold. No money moves.
- **Capture** answers *"how much do we actually intend to collect?"* It converts some or all of that hold into an amount owed.
- **Clearing and settlement** answer *"when does the money physically arrive?"* The scheme moves funds between the issuer and the acquirer, usually a day or more later.

The classic engineering mistake is collapsing these into a single boolean `paid`. The moment you support anything real — shipping delays, partial fulfilment, tips added after the fact, order edits, expired holds — that boolean lies. The authorized amount and the settled amount routinely differ, and your ledger has to survive the gap between them. The right model is an explicit state machine where each transition is an event you can store, replay, and reconcile.

## The state machine, drawn out

Here is the lifecycle a card transaction actually travels. The top rail is the happy path; the branches are the states most first attempts forget to model.

```
                 incremental auth (raise hold)
                 ┌────────────┐
                 v            │
  [Authorized] ──┴──> [Captured] ──> [Cleared] ──> [Settled]
      │  │                 ^
      │  │  partial capture │ (residual hold released)
      │  └──────────────────┘
      │
      ├──> [Auth Reversed]   (voided before capture)
      │
      └──> [Expired]         (hold aged out, no capture)
```

> **▸ [Open the interactive diagram](/blog/diagrams/fintech-card-auth-capture-clearing.html)** — pan, zoom, and trace every step (light/dark, self-contained).

Two properties make this tractable to build. First, transitions are **event-sourced**: `authorized`, `incremental_auth`, `captured`, `reversed`, `expired`, `cleared`, `settled` are append-only facts, and the current state is a fold over them. Second, every transition carries an **amount and a currency**, because the number changes as you go. The authorized amount is a ceiling, not a commitment.

## Incremental auths and partial captures

The interesting states live between authorization and capture, and they exist because the final price is often unknown at auth time.

**Incremental authorization** raises an existing hold. A hotel authorizes an estimate at check-in, then bumps it as the guest orders room service; a fuel pump authorizes a nominal amount, then adjusts to the litres actually dispensed. Each increment references the original authorization and adds to the held total. You are not creating a second transaction — you are amending one, and your model needs a stable authorization identifier that all increments and captures point back to.

**Partial capture** collects less than what was authorized. Ship two of three items today and you capture two items' worth; the remaining hold should be released rather than left dangling against the customer's available balance. Some acquirers auto-release the residual on first capture, others require an explicit reversal for the difference — you cannot assume, you have to encode the behaviour per acquirer.

A minimal state fold makes the invariants obvious:

```python
def fold(events):
    state = {"authorized": 0, "captured": 0, "status": "none"}
    for e in events:
        if e.type == "authorized":
            state["authorized"] = e.amount
            state["status"] = "authorized"
        elif e.type == "incremental_auth":
            state["authorized"] += e.amount
        elif e.type == "captured":
            state["captured"] += e.amount
            state["status"] = "captured"
        elif e.type in ("reversed", "expired"):
            state["status"] = e.type
    # invariant: you may never capture more than you hold
    assert state["captured"] <= state["authorized"]
    return state
```

That single assertion — captured never exceeds authorized — is the backbone control. If it can ever fail, you have a bug that leaks money or overcharges a cardholder.

## Reversals, expiry, and the holds you must release

Authorizations are not free to leave lying around. A hold reduces the cardholder's available balance whether or not you ever capture it, so unresolved auths generate support tickets and, at scale, real customer harm.

**Auth reversal (void)** cancels a hold before any capture — the order was cancelled, fraud was flagged, the basket was abandoned at the last step. A reversal should release the *full* remaining hold and move the transaction to a terminal `Auth Reversed` state.

**Expiry** is the silent one. Every authorization has an issuer-defined lifetime — often around seven days, shorter for some card types and merchant categories. If you have not captured by then, the issuer drops the hold regardless of your records. The danger: your system still believes it can capture. Attempting to settle an expired auth gets rejected or, worse, forces a fresh authorization the cardholder never expects. Model expiry as a first-class timed transition, run a sweeper that fires it, and never capture against an auth past its window without re-authorizing.

## Clearing, settlement, and reconciling two amounts

Once captured, the transaction enters clearing. The acquirer batches captures and submits them to the scheme; the scheme moves funds and produces settlement records. This is where the **authorized amount and the settled amount finally reconcile** — and where they are allowed to differ.

They differ legitimately all the time: you authorized 100, captured 80, and 80 settles. You authorized in one currency and settle in another after conversion. A tip pushed the capture *above* the original auth within the scheme's tolerance. Your reconciliation job matches on the authorization identifier and classifies each break:

- **Matched** — captured equals settled. Post to the ledger, close it out.
- **Tolerance drift** — settled within an allowed delta of captured (rounding, FX, permitted tip). Accept and record the delta.
- **Amount break** — settled diverges beyond tolerance. Flag for investigation.
- **Missing** — captured but never settled by the expected value date, or settled with no matching capture. Age it and route to an exception queue.

The ledger discipline that keeps this honest: an authorization posts to a **memo/hold account**, never to revenue. Only capture creates a receivable, and only settlement realizes cash. If your books recognize revenue at auth time, every reversal and every partial capture becomes a painful correcting entry. Separate the accounts and the state machine maps cleanly onto double-entry postings.

## What to hold onto

Model the card transaction as an explicit, event-sourced state machine, not a `paid` flag. Keep a stable authorization identifier that increments and captures reference. Enforce the *captured ≤ authorized* invariant as a hard control. Treat expiry as a timed transition with a sweeper, and always release residual holds on partial capture and reversal. Finally, reconcile authorized against settled per transaction, allow a tolerance band, and only recognize cash at settlement. Get those five things right and the messy real-world cases — hotels, fuel, tips, split shipments, cancellations — stop being special cases and become ordinary transitions on a state machine you already trust.
