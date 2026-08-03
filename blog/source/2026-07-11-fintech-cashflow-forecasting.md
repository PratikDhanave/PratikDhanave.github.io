# Building a Cash-Flow Forecasting Pipeline for Treasury

*Project liquidity positions from known and predicted flows to drive funding decisions.*

A treasury team's core question is deceptively simple: on any future date, in any currency, will we have enough cash — and if not, how much do we need to move, and from where? Answering it well is the difference between letting idle balances earn nothing and getting caught short on a settlement date. The engine that answers it is a cash-flow forecast: a projection of the ending balance in every currency, out to some horizon, built by summing everything you expect to pay and receive.

The mistake I see most often is treating this as a reporting problem — a nightly query that dumps the current ledger balance into a spreadsheet. That tells you where you are, not where you are going. A forecast is a pipeline: it ingests flows of two very different kinds, aggregates them onto a currency-by-date grid, rolls them into projected positions, and then closes the loop by comparing yesterday's projection against what actually happened.

```
  known flows ──┐
                ├─▶ aggregate ─▶ forecast ─▶ variance ─▶ funding
  predicted ────┘   (ccy/date)   (balance)   (vs actual)  decision
```

> **▸ [Open the interactive diagram](/blog/diagrams/fintech-cashflow-forecasting.html)** — pan, zoom, and trace every step (light/dark, self-contained).

## Two kinds of flows, two data models

The first design decision is to stop treating all future cash movements as one list. They split cleanly into two classes with different confidence, different provenance, and different update rules.

**Known flows** are contractual or already-instructed. A loan repayment scheduled for the 15th, a coupon due next month, a supplier invoice with agreed terms, a settlement leg for a trade you have already booked. These carry a firm amount, a firm currency, and a value date. Their defining property is that they change only through an explicit event — the trade is amended, the invoice is cancelled. You never *estimate* a known flow; you record it and then age it as its date approaches.

**Predicted flows** are statistical. Card acquiring inflows, payroll outflows, the daily float from a payments book, FX conversions your customers will probably request. You do not have an instruction for these; you have history and a model. A predicted flow carries an expected amount, a currency, a date, and — crucially — a confidence band. Treating a prediction as if it were certain is how forecasts quietly lie.

Because the two classes behave differently, they deserve different storage. Known flows belong in an append-only ledger of dated obligations keyed by their source instruction, so an amendment supersedes rather than mutates. Predicted flows belong in a regenerable table stamped with the model version and the run timestamp, so you can throw the whole prediction set away and rebuild it when the model changes without touching a single known flow.

```
Flow = {
    value_date:  date,
    currency:    str,
    amount:      Decimal,     # signed: +inflow, -outflow
    kind:        "known" | "predicted",
    confidence:  Decimal,     # 1.0 for known, <1.0 for predicted
    source_id:   str,         # instruction id or model run id
}
```

## Aggregation is a grid, not a sum

The temptation is to reduce everything to one number: net cash tomorrow. That number is useless the moment you hold more than one currency, because currencies do not net. A surplus of ten million in one currency does not cover a shortfall in another without an FX trade that has its own settlement date and cost.

So the aggregation stage projects onto a two-dimensional grid: currency on one axis, value date on the other. Every cell holds the net expected movement for that currency on that day. This is a `GROUP BY (currency, value_date)` over the union of known and predicted flows, and the grid granularity should match your funding decisions — daily out to a few weeks, then weekly or monthly further out where precision is lower anyway.

Keep the two flow classes distinguishable inside each cell. A cell that is a firm outflow of a known amount is a different risk than a cell of the same size built entirely from low-confidence predictions. Carry both the net and a confidence-weighted band per cell, so downstream you can ask not just "what is the expected position" but "what is the position if predictions come in at the pessimistic end of their band."

## The forecast is a running balance, not a list of deltas

A grid of daily *net movements* is not yet a forecast. The number a treasurer acts on is the projected *ending balance* per currency per day — because an overdraft on Tuesday is a problem even if Wednesday's inflow would have covered it. You cannot net across time any more than you can net across currency.

So the forecast stage takes today's actual opening balance per currency and accumulates the daily nets forward:

```
balance[ccy][d] = balance[ccy][d-1] + net_movement[ccy][d]
```

The output is a curve per currency: the projected end-of-day balance across the horizon. This is where a forecast earns its keep. You scan each curve for the days it dips below zero, or below a required buffer, and those breach points — with their dates and depths — are the actionable signal. A single netted number could never surface them.

## Variance is the feedback loop that keeps you honest

A forecast you never check against reality decays silently. The variance stage is what separates a genuine forecasting system from a projection nobody trusts by the third week.

Each day, take yesterday's forecast for today and diff it against the actual settled flows from the ledger. Attribute the variance by cell: which currency, which date, and — this is the payoff of keeping the classes separate — was the miss in a known flow or a predicted one?

```
variance = actual_flow - forecast_flow

known miss     -> data problem   (late instruction, missed booking)
predicted miss -> model problem  (bias, seasonality, regime change)
```

The two point at different fixes. A large, recurring miss on *known* flows means an upstream system is not feeding instructions in time — a plumbing bug, not a modelling one. A systematic miss on *predicted* flows means the model has drift: a weekday effect it never learned, a seasonal pattern, a shifted customer base. Feeding these residuals back is how the prediction model improves; without the attribution you cannot tell whether to fix a data pipe or retrain.

## Funding decisions are the whole point

Everything upstream exists to produce one thing: a decision to move money. Where the balance curve breaches its buffer, the system proposes a funding action — draw on a credit line, sweep a surplus from another entity, or execute an FX trade to cover a currency you are short.

Two properties make these proposals safe to act on. First, they must respect *value dates*, not trade dates: a spot FX trade to cover a Thursday shortfall has to settle by Thursday, which given standard settlement means acting earlier. Second, the proposal should carry its own confidence. A breach driven by firm known outflows warrants a firm funding action now; a breach that only appears at the pessimistic edge of predicted flows warrants watching, not committing, until the flows firm up.

The forecast should never silently auto-execute. Its job is to surface the shortfall, size it, date it, and attribute its certainty — then hand a treasurer a ranked list of proposals. The pipeline turns a wall of individual flows into that short, dated, confidence-tagged list, and that is the entire value it delivers.
