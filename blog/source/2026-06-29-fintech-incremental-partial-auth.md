# Authorization Holds: Incremental, Partial, and Estimated Auth
*Why "authorize then capture" is a lie, and how to model a hold that grows, shrinks, expires, and reconciles against a moving available balance.*

Most payment tutorials teach a tidy two-step dance: authorize the exact amount, then capture it. Real money movement is messier. A pump does not know how much fuel you will draw. A hotel does not know whether you will raid the minibar. A prepaid card may not hold the full ticket. So the network gives us a richer vocabulary of holds — estimated, incremental, and partial — and an engineer's real job is to model the *lifecycle* of a hold as it drifts away from the number you first reserved.

This post walks through that lifecycle from the ledger's point of view: what each auth type reserves, how the hold interacts with available balance, and how you reconcile the hold against the eventual capture without double-counting a cardholder's money.

## The three shapes of an authorization

An authorization is a promise, not a transfer. It reserves funds on the cardholder's account and reduces their **available balance**, but no money moves until capture (clearing). The three shapes differ in how confident you are about the amount.

- **Estimated / pre-authorization.** You reserve a plausible amount before the final total is known. A hotel reserves nightly rate times nights plus a cushion; a fuel merchant reserves a flat "status check" amount at the pump. The reservation is deliberately approximate.
- **Incremental authorization.** You extend an *existing* hold as the obligation grows. The bar tab crosses the initial reserve, so you add to the same authorization rather than opening a second one. Crucially, an increment references the original auth — it is not a new, independent hold.
- **Partial approval.** The issuer approves *less* than you asked for because that is all the account can fund — common on prepaid and some debit balances. You requested 100; the issuer says "approved for 62, the rest is on you." Your terminal must be ready to split tender.

Estimated and incremental are about *when* you know the amount. Partial approval is about *whether the money is even there*. Conflating them is the first bug most systems ship.

## Modeling the hold as a state machine

Treat every hold as an object with its own lifecycle, distinct from the order or the payment intent that owns it. The rail below is the happy path with the two branches that actually generate ledger events: excess reversal after capture, and expiry of a hold that is never captured.

```
                AUTHORIZATION HOLD LIFECYCLE

  [Auth Request] --> [Auth Hold] --> [Incremental] --> [Captured] --> [Cleared]
   estimated amt     funds reserved   hold extended     final amt      settled
                                          |                 |
                                          v                 v
                                      [Expired]         [Reversal]
                                      hold aged out     excess released
                                                            |
                                                            v
                                                        [Released]
                                                        balance freed

  held -> incremental: same auth id, higher amount, new expiry clock
  captured < hold:     reverse the delta, restore available balance
  never captured:      issuer auto-expires the hold after N days
```

> **▸ [Open the interactive diagram](/blog/diagrams/fintech-incremental-partial-auth.html)** — the authorization-hold lifecycle: estimated pre-auth, incremental extension, capture, excess reversal, and expiry.

The states worth naming explicitly in your schema:

- `HELD` — funds reserved, amount `authorized_amount`, with an `expires_at`.
- `INCREMENTED` — still held, but `authorized_amount` has grown; keep an audit trail of each increment.
- `CAPTURED` — a `captured_amount` has been claimed; may be less than, equal to, or (rarely, with tip-on-capture rules) more than the hold.
- `REVERSED` / `RELEASED` — the unused portion is given back.
- `EXPIRED` — the issuer released the hold because no capture arrived in time.

The single most important invariant: **the hold amount and the captured amount are different numbers that must be reconciled.** If your data model stores only one "amount" field, you have already lost.

## Available balance is the number that actually matters

Cardholders do not feel your database rows; they feel their available balance. Every hold you place, extend, or release moves that number. So the ledger view of a hold is really a running effect on available funds:

```
available = ledger_balance - sum(open_holds) - sum(pending_captures)
```

An **estimated auth** subtracts the reserved amount immediately. An **incremental auth** subtracts only the delta — the amount you added — because the original reserve is already counted. This is where naive implementations double-charge available balance: they place a *new* hold for the full running total instead of incrementing the old one, and the cardholder suddenly sees twice the tab locked up.

The reverse mistake happens at capture. Suppose you held 150 (estimated) and captured 120. The 30 excess does not evaporate on its own in your books. Until you post a **reversal** for the delta, your ledger still shows 150 tied up. The cardholder's issuer may release it on their side per network timers, but *your* reconciliation will drift unless you emit the reversal event yourself.

A clean rule of thumb per event:

- On **hold**: `available -= authorized_amount`
- On **increment**: `available -= delta`  (never the new total)
- On **capture**: move `captured_amount` from held to settled; `available` unchanged by the capture itself
- On **reversal**: `available += (authorized_amount - captured_amount)`
- On **expiry**: `available += remaining_hold`

## Partial approval: split tender, not a smaller hold

Partial approval is a different branch because it changes *who owes the remainder*. The issuer approves what the balance allows and returns the approved amount plus an indicator that it is partial. Your system now has an obligation shortfall.

The lifecycle fork looks like this. You request an auth for the full amount. The response is `APPROVED` but for a lesser sum. You either (a) collect the difference on another tender — a second card, cash, a wallet — or (b) reverse the partial approval entirely because a split is not allowed for this order. There is no "try to hold the rest on the same card"; the account already told you the money is not there.

Two engineering consequences fall out of this:

1. **Idempotency and reversal on abandonment.** If the customer cannot cover the remainder, you must reverse the partial approval promptly, or you have locked up the little balance they had. Treat the partial hold as provisional until the full tender is assembled.
2. **Prepaid balances are a moving target.** The available amount can change between your balance inquiry and your auth. Design for the auth itself to be the source of truth — the approved amount in the response — not a balance check you did a moment earlier.

## Reconciling holds against capture and expiry

The end game is making three numbers agree: what you held, what you captured, and what the cardholder's available balance reflects. The hard cases are all timing.

**Capture under the hold.** Capture 120 against a 150 hold, then reverse 30. If you skip the reversal, the cardholder waits days for issuer-side expiry to free their money — a real support-ticket generator even though your capture was correct.

**Capture after expiry.** Holds do not live forever; issuers release them after a network-defined window (often several days, longer for travel). If your capture arrives after the hold expired, it may still clear as a "force capture" against the account — but with no guaranteed funds behind it. That is the quiet risk of long-lived estimated auths: the hold protects you only inside its window.

**Incremental resets the clock.** Each valid incremental authorization typically refreshes the expiry, which is exactly why open tabs extend rather than re-auth: it keeps the hold alive and the reserve accurate in one call.

Model each of these as explicit events with their own timestamps and amounts. A hold is not a boolean flag on a payment — it is an append-only sequence of `authorized`, `incremented`, `captured`, `reversed`, and `expired` records whose running sum must always equal the effect you claim on available balance. Store the sequence, reconcile against it nightly, and the messy reality of estimated, incremental, and partial auth becomes something you can actually reason about.

## Takeaways

- Authorize-then-capture is the exception, not the rule; hotels, fuel, rentals, and tabs all reserve an *approximate* amount first.
- Store the hold amount and the captured amount as separate, reconcilable numbers — never one field.
- Increment the delta, never re-hold the running total, or you double-lock available balance.
- Always emit your own reversal for the hold-minus-capture excess; do not wait for issuer-side expiry.
- Treat a partial approval as split tender with a provisional hold, and reverse it fast if the remainder cannot be collected.
