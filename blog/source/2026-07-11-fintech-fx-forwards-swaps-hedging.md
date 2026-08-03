# Booking and Revaluing FX Forwards and Swaps for Hedging

*Book and revalue FX forward contracts and swaps for hedging — the part of treasury that lives well beyond spot conversion.*

A spot FX trade is a one-shot event: you agree a rate, both sides deliver in two days, the position is gone. A forward is a *contract that lives*. You agree today to exchange two currencies on a date months out, at a rate fixed now, and then you carry that obligation on your book — revaluing it every single day until it settles. Most engineers meet FX as a spot conversion endpoint and are surprised to learn the hard problem is not booking the trade. It is everything that happens in the weeks after: the daily revaluation, the roll when the hedge needs to move, and the discipline of terminal states that keep your book from lying to you.

The reason forwards exist at all is hedging. A business that owes a supplier in a foreign currency in three months does not want to gamble on where spot will be. It locks the rate now with a forward and sleeps at night. Your job as the engineer is to model that contract as a lifecycle, not a row in a payments table.

```
  booked ──▶ mark-to-market ──▶ matured ──▶ settled
    │            │  ▲
    │            └──┘ (daily)
    │            │
    │            └──▶ roll / extend ──▶ (new far leg) ──▶ mark-to-market
    │
    └──▶ cancelled (terminal, before maturity)
```

> **▸ [Open the interactive diagram](/blog/diagrams/fintech-fx-forwards-swaps-hedging.html)** — pan, zoom, and trace every step (light/dark, self-contained).

## The contract is the data model

Before any pricing, get the shape of the object right, because every downstream stage reads from it. A forward is defined by more fields than a spot trade, and each one earns its place.

```
Forward = {
    trade_date:      date,       # when the rate was agreed
    value_date:      date,       # when the exchange settles (the "far" date)
    pair:            str,        # e.g. "EURUSD"
    buy_ccy:         str,
    sell_ccy:        str,
    notional:        Decimal,    # amount in the base currency
    contract_rate:   Decimal,    # the locked forward rate
    direction:       "buy" | "sell",
    status:          str,        # the lifecycle state
}
```

The two dates are the whole point. `trade_date` freezes the economics; `value_date` is when cash actually moves. The gap between them is why the contract needs revaluing — the world keeps changing while your rate stays pinned. The `contract_rate` is not a spot rate. It is spot adjusted by *forward points*, which encode the interest-rate differential between the two currencies. You never store the forward points on the contract; you store the all-in `contract_rate` and reconstruct the market's current view each day to compare against it.

## Booking: locking the rate, not moving the cash

Booking a forward is deceptively quiet. No money changes hands. You are writing down an obligation and computing the rate at which it was struck. The rate comes from covered interest parity, which every forward desk implements in some form:

```
forward_rate = spot * (1 + rate_quote * T) / (1 + rate_base * T)
```

where `T` is the fraction of a year to the value date and the two rates are the deposit rates for the quote and base currencies. In practice you do not compute this from raw deposit rates on the fly — you interpolate a published forward-points curve for the pair at the exact tenor, add it to spot, and that is your `contract_rate`. The engineering care here is tenor interpolation: a client wants a value date of, say, 74 days, and the market quotes standard tenors of one, two, and three months. You interpolate between the bracketing points, and you do it consistently, because the same interpolation must be used at revaluation or your day-one profit and loss will show a phantom gain purely from a methodology mismatch.

Once booked, the contract enters the lifecycle in the `booked` state and immediately becomes eligible for the daily cycle.

## Daily mark-to-market: the state that runs in a loop

This is the stage people underestimate. A booked forward is not static — its value drifts every day as the market moves, and treasury, risk, and accounting all need that number. Mark-to-market answers one question: if we closed this contract at today's market, what would it be worth?

The valuation is a comparison between the rate you locked and the rate the market would give you *now* for the same remaining tenor, discounted back to today:

```
remaining_forward_rate = current_spot + forward_points(remaining_tenor)

mtm = notional * (remaining_forward_rate - contract_rate) * discount_factor
```

Three subtleties make this real engineering rather than a formula. First, the tenor shrinks every day, so you re-interpolate the forward-points curve at the *new* shorter remaining tenor each run — a contract does not keep comparing against its original three-month point. Second, the discount factor pulls a future cash difference back to a present value using the settlement-currency rate; ignore it and you overstate the value of far-dated contracts. Third, the sign follows direction: a bought forward gains when the market rate rises above your locked rate, a sold forward is the mirror image.

Structurally, mark-to-market is a self-loop on the `mark-to-market` state — the contract re-enters it every valuation cycle until something ends it. That is exactly how you should model it: a state the object returns to daily, not a one-time transition. The output each cycle is a fresh MTM figure and the deltas that feed risk limits and the general ledger.

## Rolling and extending: the swap in disguise

Hedges outlive their contracts. The invoice slips a month; the exposure you hedged still exists past the value date. Rather than let the forward mature and open a brand-new one, desks *roll* it — and a roll is structurally an FX swap: two simultaneous legs in opposite directions.

```
roll = { near_leg: close the maturing forward at today's rate,
         far_leg:  open a new forward to the extended date }
```

The near leg unwinds the old contract; the far leg re-establishes the hedge to the later date. Priced together as a swap, only the *forward-point differential* between the two dates matters — the spot rate largely cancels between the legs, which is why swaps are quoted in points, not in outright rates. In the lifecycle this is a branch off `mark-to-market`: the contract does not die, it transitions through a roll that spawns a new far leg, and that new leg drops straight back into the daily mark-to-market loop. Modelling the roll as a branch rather than a close-and-rebook keeps the hedge's identity and history intact, which auditors and hedge-accounting rules very much care about.

## Terminal states keep the book honest

A lifecycle is only trustworthy if its exits are explicit. A forward leaves the daily loop through exactly one of three doors, and conflating them is how a book starts lying.

**Matured** is the natural end: the value date arrives, the contract is due, and it moves to settlement. **Settled** is terminal success — both currency legs have been exchanged, the obligation is discharged, and the position drops out of your live MTM population. Keep these two distinct: a contract that has matured but not yet settled is still an operational risk (a payment could fail) and must not be silently treated as done.

**Cancelled** is the other terminal exit, and it happens *before* maturity — a counterparty agreement to tear up the trade, or an early unwind. The critical engineering rule is that cancellation crystallises the current mark-to-market as a realised amount and then removes the contract from all forward-looking valuation. A cancelled forward that still appears in tomorrow's MTM run is a double count. Model it as a hard terminal state with no path back into the active loop, and the daily revaluation stays truthful — which, in the end, is the only thing a hedging book is for.
