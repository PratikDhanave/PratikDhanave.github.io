# Collateral and LTV Management: Engineering the Loop That Watches Value Slip

*Track collateral valuation, loan-to-value, margin calls, and liquidation triggers as one auditable state machine.*

A secured loan is a bet that the thing backing it stays worth more than the debt. Whether the collateral is equities in a brokerage account, a basket of crypto, or invoices assigned to a working-capital facility, the platform's job is the same: keep re-measuring value, compare it to what is owed, and act before the cushion disappears. The interesting engineering is not the loan itself. It is the loop that runs quietly for the life of the loan and occasionally has to move fast and correctly under adversarial market conditions.

This post walks through that loop as a state machine, the computations behind each transition, and the failure modes that separate a system that survives a volatile day from one that generates a compliance incident.

## The core states

Collateral moves through a small set of well-defined states. Modelling them explicitly — rather than inferring status from a scatter of boolean columns — is what makes the system auditable later, when someone asks why a position was liquidated at a particular timestamp.

```
  PLEDGED ──► VALUED ──► HEALTHY ─────────────────► RELEASED
                          │  ▲                        (loan repaid)
              LTV breach  │  │ cured
                          ▼  │
                     MARGIN CALL
                          │
             deadline miss│
                          ▼
                     LIQUIDATION  (terminal)
```

> **▸ [Open the interactive diagram](/blog/diagrams/fintech-collateral-ltv-management.html)** — pan, zoom, and trace every step (light/dark, self-contained).

`PLEDGED` is the moment an asset is assigned to a facility but not yet priced. `VALUED` means a fresh mark exists. `HEALTHY` is the steady state: value re-measured on a cadence, loan-to-value comfortably inside limits. The two transitions that matter are the breach into `MARGIN CALL` and the escalation into `LIQUIDATION`. Everything else is bookkeeping around those two edges.

Keeping `HEALTHY` and `MARGIN CALL` as first-class states, rather than a `margin_called` flag on the loan row, means every entry and exit is an event you can replay. When a borrower disputes a liquidation, "show me the state transitions" is a far stronger answer than reconstructing intent from mutable columns.

## Valuation is the whole game

Loan-to-value is trivial arithmetic: `LTV = outstanding_debt / collateral_value`. The debt side is usually clean — principal plus accrued interest and fees, all internal numbers you control. The collateral value is where the difficulty lives, because it depends on an external price you do not control and cannot fully trust.

Three properties of the valuation feed decide whether the rest of the system behaves:

- **Source and freshness.** Every mark carries a source and a timestamp. A price older than your tolerance is not a price; it is a stale number that will lie to you. Treat missing or stale marks as an explicit `VALUED` failure, not as an implicit "last known good."
- **Haircuts.** You rarely value collateral at its raw market price. A haircut discounts for liquidity and volatility — a large position in a thin asset cannot actually be sold at screen price. The effective value is `market_price × quantity × (1 − haircut)`, and the haircut itself may scale with position size.
- **Outlier rejection.** A single feed printing a bad tick should not trigger a liquidation. Cross-check sources, reject prices that move implausibly between marks, and require confirmation before acting on a large adverse move.

```python
def compute_ltv(debt: Decimal, positions: list[Position], marks: MarkStore) -> Decimal:
    collateral = Decimal(0)
    for p in positions:
        mark = marks.latest(p.asset)
        if mark is None or mark.age > MAX_MARK_AGE:
            raise StaleMarkError(p.asset)          # fail loud, do not guess
        haircut = haircut_for(p.asset, p.quantity)
        collateral += mark.price * p.quantity * (Decimal(1) - haircut)
    if collateral == 0:
        raise ZeroCollateralError()
    return debt / collateral
```

The `raise` on a stale mark is deliberate. The unsafe design is the one that silently substitutes an old price and reports a healthy LTV while the market has already moved.

## Thresholds, hysteresis, and the margin call window

Two thresholds govern the edges: a **call level** where the position enters `MARGIN CALL`, and a **liquidation level** where the platform sells. A common shape is a call at, say, 80% LTV and forced liquidation at 90%, with the gap giving the borrower room to react.

Naive threshold checks flap. If LTV oscillates around 80% on every tick, you fire and clear margin calls repeatedly, spamming the borrower and polluting the audit trail. The fix is hysteresis: enter `MARGIN CALL` at the call level, but only return to `HEALTHY` once LTV recovers well below it — to a distinct cure level. The band between call and cure absorbs noise.

```
LTV ──►  ┌──────── liquidation (90%) ──── forced sell
         │
         ├──────── call (80%) ─────────── enter MARGIN CALL
         │  (hysteresis band)
         ├──────── cure (75%) ─────────── return to HEALTHY
         │
         └──────── healthy operating range
```

The margin call itself is a timed obligation. When the position enters `MARGIN CALL`, you record a deadline and the required action — top up collateral or repay debt to reach the cure level. The state carries that deadline so that a separate scheduler, not the price feed, can escalate on expiry. Curing before the deadline returns the position to `HEALTHY`; missing it moves to `LIQUIDATION`. Critically, a hard breach of the liquidation level can bypass the call window entirely: if value falls fast enough that even immediate action cannot cure it, waiting out the deadline only deepens the loss.

## Liquidation must be idempotent and bounded

Liquidation is the one transition that spends real money and cannot be undone, so it gets the most defensive engineering.

- **Idempotency.** The trigger can fire from a scheduled deadline check and from a price tick in the same second. Guard the transition with the position's current state and a liquidation id so two concurrent triggers cannot each launch a sell. Enter `LIQUIDATION` exactly once.
- **Sell only what you must.** Full liquidation of a position that needs a 10% top-up is both bad for the borrower and bad optics. Compute the minimum quantity that restores LTV to the cure level and sell that, leaving the remainder pledged.
- **Partial fills and slippage.** Selling into a falling market rarely fills at the mark. Reconcile actual proceeds against expected, and re-evaluate: a partial fill may leave the position still in breach, requiring another bounded sell rather than assuming the first order fixed it.
- **Terminal but reconciled.** `LIQUIDATION` is terminal for the collateral loop, but it hands off to settlement and accounting — proceeds applied to debt, any surplus returned to the borrower, any shortfall booked as a deficiency. The state machine ends; the money movement does not.

## What actually breaks in production

The subtle failures are rarely in the arithmetic. They cluster around timing and trust.

Clock and cadence gaps are the classic one: if you re-value every five minutes, a fast move can blow through both thresholds between marks, so the call window that was supposed to protect the borrower never opens. High-volatility assets need event-driven revaluation on large price moves, not just a fixed cadence.

The second is treating the price feed as ground truth. Feeds lag, halt, and print bad ticks precisely when markets are most stressed — exactly when your liquidation logic is most likely to fire. Every adverse transition should be defensible from confirmed, multi-source data, because every liquidation is a decision you may have to justify to the borrower, to an auditor, or in a dispute.

Build the loop so that the boring path — pledge, value, stay healthy, release — is the overwhelming common case, and the sharp edges into margin call and liquidation are rare, explicit, idempotent, and fully logged. That is the difference between a collateral system that quietly does its job for years and one that becomes the subject of the post-mortem after a volatile afternoon.
