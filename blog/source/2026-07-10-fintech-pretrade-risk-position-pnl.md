# Pre-Trade Risk, Positions, and Real-Time P&L

*Enforce pre-trade risk limits and keep real-time positions and mark-to-market P&L without stalling the order path.*

---

Every order that leaves a trading system has to pass through a gate that answers one question in the low-millisecond range: *is this order allowed right now?* Behind that gate sits the machinery that tracks what you own and what it is worth. Get the gate wrong and you either leak risk or reject good flow; get the bookkeeping wrong and every downstream limit is computed against a lie. This post walks the order path from submission to P&L and the engineering choices that keep it both safe and fast.

Here is the whole path on one line:

```
                        ┌── reject (fail closed)
                        │
  Order ──▶ Pre-Trade Risk ──▶ Matching ──▶ Position Keeper ──▶ Mark-to-Market ──▶ P&L
            limits/buying         venue        net qty +          mark price       realized +
            power/checks                       avg cost                            unrealized
```

> **▸ [Open the interactive diagram](/blog/diagrams/fintech-pretrade-risk-position-pnl.html)** — pan, zoom, and trace every step (light/dark, self-contained).

## The gate is on the critical path

Pre-trade risk is synchronous. The order cannot go to a venue until the check returns, so its latency is added directly to the time-to-market of every order. That single fact shapes the whole design. You order the checks cheapest-first and bail on the first failure, you keep the state the checks read entirely in memory, and you treat the risk engine as a hot loop rather than a service you call over the network.

A practical latency budget for the check itself is single-digit microseconds to low tens of microseconds when it is in-process, and low milliseconds if it must cross a socket. The rule of thumb: anything the gate needs must already be resident. If a check would require a database round trip, it does not belong in the synchronous path — precompute it and refresh it asynchronously.

The gate is also **fail-closed**. If the engine cannot evaluate a rule — stale market data, a missing limit, an unreadable position — it rejects. A trading system that fails open under uncertainty is a trading system that blows through its limits exactly when conditions are worst.

## What pre-trade risk actually checks

"Risk check" is a bundle of independent validations. Ordering them cheap-to-expensive lets the common rejections short-circuit before the costly ones run:

- **Static / sanity checks.** Is the instrument tradeable, is the account enabled, is the price within a fat-finger band around the reference price, is the quantity a valid lot size? These are field lookups and comparisons — nanoseconds.
- **Restricted and hard limits.** Is the symbol on a restricted list? Does the order breach a per-order max notional or a per-symbol position cap? Simple map lookups against preloaded config.
- **Aggregate exposure limits.** Would this order push gross or net exposure past the account or desk limit? This reads the live position plus open-order exposure.
- **Buying power.** Does the account have enough purchasing power, given cash, margin, and everything already working in the market?

The last two are the ones that require live state, and they are where correctness gets hard. The first two are effectively pure functions over static config.

```
for order:
    reject_if not static_ok(order)          # cheapest
    reject_if restricted(order.symbol)
    reject_if breaches_position_cap(order)   # reads live position
    reject_if breaches_buying_power(order)   # reads reservations
    accept(order)                            # reserve, then release to venue
```

## Buying power is a reservation, not a balance

The single most common bug in a pre-trade system is checking buying power against *settled state* instead of *committed state*. If you only debit buying power when a fill arrives, then two orders submitted a microsecond apart both see the full balance and both pass — and now you are over-committed.

The fix is to treat buying power like a semaphore. At the moment an order is **accepted**, you reserve its worst-case cost against the account. The order's lifecycle then drives the reservation:

- **Accept** → reserve buying power for the full order.
- **Partial fill** → convert the filled portion into a real position; keep reserving the unfilled remainder.
- **Full fill / cancel / reject** → release any remaining reservation.

So the amount a new order is checked against is `available = cash_and_margin − open_reservations − position_cost`. Because open orders are already netted in, a burst of orders cannot each spend the same dollar twice. The reservation ledger is the source of truth for "money in flight," and it must be updated in the same critical section that accepts the order — not eventually.

## The position keeper: fills in, average cost out

Downstream of the venue, fills stream back and the **position keeper** turns them into a position. The keeper is naturally event-sourced: the sequence of fills is the log, and the current position is a fold over that log. For each fill you update net quantity and running average cost, and you compute realized P&L when a fill reduces or flips the position.

The average-cost update is the part people get subtly wrong. When a fill adds to a position in the same direction, you blend cost. When it reduces the position, you realize P&L against the existing average and leave the average untouched. When it flips the sign, you realize the whole old position and start a fresh average at the fill price for the residual.

```
on fill (qty q at price p):
    if same_direction(position, q):
        avg_cost = (avg_cost*|position| + p*|q|) / (|position| + |q|)
        position += q
    else:
        closing = min(|q|, |position|)
        realized += closing * (p − avg_cost) * sign(position)
        position += q
        if sign flipped: avg_cost = p        # residual opens at fill price
```

Because the keeper is a fold over an ordered log, recovery is just replay: persist fills durably, and on restart rebuild the position from the last snapshot plus the tail of fills after it. Snapshot-plus-delta keeps startup fast without losing the exact average cost.

## Marking and P&L: realized versus unrealized

Realized P&L comes only from fills and never changes once booked. **Unrealized** P&L is the open position marked against a current price, and it moves on every market tick: `unrealized = position × (mark − avg_cost)`. Total P&L is the sum of the two.

The engineering decision here is *which price is the mark*. Last-trade is noisy and can be stale on illiquid names; mid-price from the top of book is usually the honest default; a dedicated marking source may be required for compliance or end-of-day valuation. Whatever you choose, be explicit — a limit computed against a stale or manipulable mark is a limit that can be gamed. And feed unrealized P&L straight back into the gate: a loss that eats into buying power should tighten what the next order is allowed to do, closing the loop between risk and reality.

## Making it consistent and fast

The gate, the reservation ledger, and the position keeper all read and write the same per-account state, which invites races. The clean answer is a **single writer per account**: route every order, fill, and cancel for one account through one sequenced processor so all mutations are serialized without locks. Different accounts shard onto different processors, so throughput scales horizontally while each account stays strictly consistent.

That single-writer discipline is also what makes the numbers trustworthy. There is exactly one place where buying power is reserved, one place where positions fold in fills, and one place where marks update P&L. When those three live behind one sequenced writer, the gate always evaluates against a coherent snapshot — and "is this order allowed right now?" gets an answer you can actually stand behind.
