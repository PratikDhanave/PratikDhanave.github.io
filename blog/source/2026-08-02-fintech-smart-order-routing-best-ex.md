# Smart Order Routing and Best Execution

*How a buy-side smart order router turns one parent order into dozens of child orders, scores venues in real time, and then proves it did the right thing.*

A portfolio manager decides to buy 500,000 shares. That single instruction — the *parent order* — almost never hits the market as one print. If you sent it whole to a single exchange, you would sweep the visible book, move the price against yourself, and hand a gift to every faster participant watching the tape. Instead, a **smart order router (SOR)** breaks the parent into small **child orders**, decides *where* and *when* each one goes, listens to what comes back, and adjusts. Wrapped around all of it is a legal and commercial obligation: **best execution**. This post walks through the machinery an engineer actually has to build.

## Best execution is not "best price"

The first misconception to kill is that best execution means getting the best displayed price. Price is one input. A realistic best-execution policy weighs price alongside **cost** (exchange fees, rebates, clearing), **speed**, **likelihood of execution and settlement**, **order size**, and the **nature of the order**. A venue quoting the best price but filling only 5% of what you send is worse than a slightly inferior quote that fills reliably without leaking your intent.

Best execution is therefore a *process* obligation, not a per-fill guarantee. You are not promising the optimal outcome on every child order — impossible to know in advance. You are promising a consistent, documented, reviewable method for pursuing the best result, and evidence that you followed it. That distinction shapes the whole system: every routing decision has to be *explainable after the fact*.

## The routing decision: scoring venues

At the center is a scoring loop. For each child order, the router ranks candidate venues — lit exchanges, dark pools, and single-dealer or alternative trading systems — on a blend of signals:

- **Price / spread** at the top of book, plus queue position if you can estimate it.
- **Displayed and expected liquidity** — how much you can realistically take without walking the book.
- **Fee or rebate** under the venue's maker-taker schedule; a rebate can flip the ranking on a marginal order.
- **Latency** to reach the venue and get an ack — a slow path means the quote you aimed at is gone.
- **Fill probability**, usually a model trained on your own recent fills per venue, symbol, and order type.

A simple, honest scorer is a weighted sum whose weights come from the execution policy and the order's urgency:

```
score(venue) = w_p·price + w_l·liquidity − w_f·fee − w_λ·latency + w_φ·fill_prob
```

Urgency tilts the weights. A "get me done now" order leans on fill probability and speed; a passive, cost-sensitive order leans on price and rebates. The scorer runs continuously because the book changes millisecond to millisecond — a venue that was rank one when you sliced can be rank four by the time the child is ready to send.

## Slicing and schedules

Before routing, the parent has to be *sliced* into a stream of children over time. The schedule is chosen to balance market impact against timing risk:

- **TWAP** (time-weighted) spreads evenly across an interval — simple, predictable, easy to game.
- **VWAP** (volume-weighted) front- or back-loads to match the day's expected volume curve, so you trade more when the market is naturally deep.
- **POV** (percentage of volume) pegs your participation to real-time traded volume — you take, say, 10% of whatever prints, speeding up when the market is active and pausing when it is thin.

The slicer emits children; the scorer routes each one. Keeping these two concerns separate is the single most useful architectural decision here: the schedule answers *how fast*, the router answers *where*.

## Handling partial fills and re-routing

Real venues rarely fill a child completely. You send 5,000 shares as an immediate-or-cancel (IOC) order, get 1,800 back, and the rest is cancelled. Or the venue rejects the order outright — a stale quote, a risk check, a timeout. The router must treat the **residual** as a first-class object: the unfilled quantity flows back into the loop, gets re-scored against the *current* book (not the stale one you routed against), and re-routed. Nothing is allowed to silently vanish; every child is accounted for as filled, cancelled, or re-routed.

```
                            SMART ORDER ROUTER
        ┌───────────────────────────────────────────────────┐
        │  score venues  →  slice (VWAP/POV)  →  route child  │
        └───────────────────────────────────────────────────┘
   Parent order              │      │      │
   (buy 500k)  ───────────►  │      │      │
                             ▼      ▼      ▼
                        ┌────────┐┌────────┐┌────────┐
                        │Venue A ││Venue B ││Venue C │
                        │ (lit)  ││ (dark) ││ (ATS)  │
                        └───┬────┘└───┬────┘└───┬────┘
              partial fill /│ reject  │ fills   │
              re-route  ◄───┴─────────┼─────────┘
                                      ▼
                             ┌─────────────────┐
                             │ AGGREGATE FILLS  │  avg price + filled qty
                             └────────┬─────────┘
                                      ▼
                             ┌─────────────────┐
                             │       TCA        │  arrival / VWAP / IS
                             └─────────────────┘
```

> **▸ [Open the interactive diagram](/blog/diagrams/fintech-smart-order-routing-best-ex.html)** — the same routing workflow with lit and dark venues, the re-route branch for partial fills and rejects, and the path to TCA.

## Proving it: transaction cost analysis

Aggregate the fills and you have an average execution price and a filled quantity. That is where **transaction cost analysis (TCA)** begins. TCA measures your execution against benchmarks so the "was this best execution?" question has a number attached:

- **Arrival price** — the mid at the moment the order arrived at the desk. The gap between arrival and your average fill is the headline cost of trading.
- **VWAP** — how you did versus the volume-weighted average over your trading window; the standard "did I beat the market's average price" yardstick.
- **Implementation shortfall (IS)** — the total difference between the *decision price* (when the PM decided) and the realized outcome, including the opportunity cost of anything you failed to fill. IS is the most complete measure because it charges you for both the shares you traded badly and the shares you never got.

Good TCA is stored per child order with the routing rationale attached — venue scores, the book snapshot, the order type. That record is what turns a routing decision into best-execution *evidence*.

## Pitfalls

- **Information leakage.** Predictable slicing (fixed size, fixed cadence) is a signal. Others detect it and trade ahead. Randomize sizes and timing.
- **Adverse selection.** If you only get filled when the price is about to move against you, your "good" venue is quietly toxic. Measure post-fill price drift ("markout"), not just fill rate.
- **Latency races.** By the time your order lands, the quote you scored may be gone, and you take a worse price or a reject. Score with latency-adjusted, not last-seen, quotes.
- **Venue toxicity.** Some dark pools leak or host predatory flow. Rank venues on *realized* outcomes and be willing to switch a venue off entirely.
- **Over-fitting the scorer.** A fill-probability model tuned to last month's regime fails in this month's. Retrain, monitor drift, and keep a simple fallback.

## What to remember

A smart order router is a control loop, not a lookup table: slice, score, send, listen, re-route, repeat — under real latency and adversarial counterparties. Best execution is the discipline wrapped around that loop. Keep scheduling and routing as separate concerns, treat every residual as a live object, and record the rationale behind each child order. Then let TCA close the feedback loop against arrival price, VWAP, and implementation shortfall — so best execution is something you can *prove*, not just assert.
