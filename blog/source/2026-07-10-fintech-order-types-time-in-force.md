# Order Types and Time-in-Force as a Lifecycle

*Modeling limit/market/stop and GTC/IOC/FOK semantics as a lifecycle instead of a pile of flags.*

Most order-management bugs I have chased were not matching-engine bugs. They were state bugs. An order that reported `Filled` but still had resting quantity on the book. A cancel that "succeeded" on an order that had already expired. A partial fill that leaked through as a full fill because the code branched on a boolean instead of a state. The root cause is almost always the same: the order was modeled as a bag of mutable fields — `quantity`, `filledQty`, `status`, `isActive`, `expireAt` — and the transitions between those fields were implied by scattered `if` statements rather than declared in one place.

The fix is to treat an order as an explicit state machine. Order type decides where the order *enters* the machine and how aggressively it seeks a fill. Time-in-force (TIF) decides how long it is allowed to *stay* in the machine before the venue forces it out. Once you draw those two forces on the same lifecycle, a lot of ambiguity disappears.

## The rail: New to Filled

The happy path is a single directed rail. An order is submitted (`New`), clears pre-trade risk and validation (`Accepted`), rests on the book as a live resting order (`Working`), begins matching (`Partially Filled`), and completes (`Filled`). Every other outcome is a branch off that rail into a terminal state.

```
New ──▶ Accepted ──▶ Working ──▶ Partially Filled ──▶ Filled
                        │                │
                        ▼ DAY / GTC end  ▼ cancel remainder
                     Expired          Canceled
```

> **▸ [Open the interactive diagram](/blog/diagrams/fintech-order-types-time-in-force.html)** — pan, zoom, and trace every step (light/dark, self-contained).

Two properties of this rail matter more than the boxes themselves. First, `Partially Filled` is still an *active* state — the order is open, it has done work, and it can still be canceled, expired, or completed. Treating a partial as "almost filled" is where double-fill bugs are born. Second, the terminal states never re-enter the rail. Once an order is `Filled`, `Canceled`, or `Expired`, no event can revive it. That single invariant kills an entire class of race conditions where a late cancel or a late fill mutates a closed order.

## Order type: where you enter and how hard you push

Order type is not a separate lifecycle. It is a modifier on how the order traverses the one above.

- A **market** order enters and is expected to match immediately against the best available liquidity. In practice it barely rests — it goes `Accepted` and then straight into `Partially Filled`/`Filled` within the same matching cycle. If it cannot be fully satisfied, TIF decides what happens to the remainder.
- A **limit** order carries a price constraint. If the book cannot fill it at its limit or better, it becomes a genuine `Working` resting order and waits. This is the order type most exposed to TIF, because "waits" is exactly what TIF governs.
- A **stop** (or stop-limit) order is a two-phase order. It sits in a triggered/untriggered condition off-book until the market touches its stop price, at which point it *becomes* a market or limit order and enters the rail above. Model the trigger as a guard on the `Accepted → Working` edge, not as its own status, or you will end up reconciling two half-lifecycles.

The engineering point: you do not need a distinct status enum per order type. You need one lifecycle plus a small set of guards that decide *which edges are reachable* for a given type.

## Time-in-force: the clock on a resting order

TIF is what turns a resting order into a terminal one without a fill. It is the timer and the kill-switch attached to the `Working` and `Partially Filled` states.

- **GTC (Good-Til-Canceled)** rests until it is filled or explicitly canceled. In real venues it is not truly infinite — brokers and exchanges impose an age cap (often 90 days), after which the order is `Expired`, not `Canceled`. Encode that cap; do not assume "forever."
- **DAY** rests until the session close and is then `Expired` by the venue's end-of-day sweep. This is a scheduled transition, not an event-driven one — your engine needs a deterministic session-close job that moves every open DAY order to `Expired` atomically.
- **IOC (Immediate-Or-Cancel)** fills whatever it can *right now* and cancels the remainder. It never becomes a durable `Working` order; any unfilled quantity goes to `Canceled` in the same cycle.
- **FOK (Fill-Or-Kill)** is all-or-nothing: if the full quantity cannot be matched immediately, the entire order is `Canceled` with zero fills.

Notice how cleanly this maps to two terminal branches. `Expired` is "the market never completed this and the clock ran out." `Canceled` is "someone or some rule pulled it" — a user cancel, or the automatic remainder-kill of IOC/FOK. Different cause, different terminal state, and downstream reconciliation should be able to tell them apart from the state alone.

## Enforce transitions in one place

The reliability payoff comes from making illegal transitions unrepresentable. Instead of mutating a status field wherever a fill or cancel arrives, route every mutation through a single transition guard that owns the legal edges.

```go
var legal = map[State][]State{
    New:      {Accepted, Rejected},
    Accepted: {Working, Filled, Canceled}, // market/IOC may skip Working
    Working:  {PartiallyFilled, Filled, Canceled, Expired},
    PartiallyFilled: {Filled, Canceled, Expired},
    // terminal states have no outgoing edges
}

func (o *Order) transition(to State) error {
    if isTerminal(o.State) {
        return fmt.Errorf("order %s is terminal (%s); ignoring %s",
            o.ID, o.State, to)
    }
    for _, ok := range legal[o.State] {
        if ok == to {
            o.State = to
            return nil
        }
    }
    return fmt.Errorf("illegal transition %s -> %s", o.State, to)
}
```

Two things fall out of this shape for free. A cancel arriving for an already-terminal order returns a clean, idempotent no-op instead of corrupting state — which is exactly what you want, because cancels and fills race constantly. And because terminal states have no outgoing edges, a late fill on a canceled order is rejected at the guard rather than silently over-filling the client.

## What the engine must guarantee

A correct order lifecycle comes down to a few invariants that are easy to state and worth asserting in tests:

- **Conservation of quantity.** At every state, `filled + resting + terminated == original`. If a partial fill does not decrement resting by exactly the matched quantity, you have a leak.
- **Terminal is final.** No event moves an order out of `Filled`, `Canceled`, or `Expired`. Assert it in the guard, not just in review.
- **TIF is authoritative over resting time.** DAY and GTC-cap expiries are engine-driven sweeps, not client actions; they must fire even if the client is disconnected.
- **Expired and Canceled are distinguishable.** Reconciliation, client notifications, and regulatory records all care *why* an order ended, so the terminal state must carry the cause.

Model the order as this lifecycle first, then layer order type as entry guards and TIF as exit timers on top of it. The matching logic gets simpler because it only ever asks "is this transition legal?" — and the state, not a scatter of flags, is the source of truth.
