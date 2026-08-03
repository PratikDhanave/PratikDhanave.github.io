# Engineering a Pay-in-4 BNPL Flow

*Checkout-time soft credit checks, upfront merchant settlement, and the installment collection loop that carries the real risk.*

Buy-now-pay-later looks, from the shopper's seat, like a single button that splits a purchase into four equal payments. Behind that button is a short-tenor unsecured loan that the provider underwrites in a few hundred milliseconds, funds in full to the merchant the same day, and then spends the next six weeks collecting. The engineering interesting part is not the checkout widget. It is the fact that approval and loss happen at opposite ends of the timeline, and the system has to be designed around that gap.

This post walks the pay-in-4 flow the way I'd draw it on a whiteboard for a new engineer joining the team: what each stage owns, where the money and the risk sit, and which parts you will be paged about at 2 a.m.

## Where the money actually moves

The flow has four distinct actors, and it helps to keep their concerns separate from the first line of code. The shopper initiates at checkout. The provider underwrites and carries the credit risk. Settlement pushes cash to the merchant. Servicing runs the collection loop until the plan closes or defaults.

```
 shopper        provider            settlement        servicing
   |               |                    |                 |
[checkout] --> [soft check] --> [approve] --> [payout] --> [schedule]
                                   |                          |
                              [declined]                  [collect] --> [closed]
                                                              |
                                                          [default]
```

> **▸ [Open the interactive diagram](/blog/diagrams/fintech-bnpl-architecture.html)** — pan, zoom, and trace every step (light/dark, self-contained).

The key asymmetry: the merchant is paid in full, upfront, the moment the plan is approved. The provider fronts that cash and then owns every installment that follows. Everything downstream of `payout` is the provider's balance sheet at risk. That single fact drives most of the design decisions below.

## The checkout decision has to be fast and soft

At checkout the provider runs a decision that must satisfy two constraints that pull against each other: it has to be near-instant so it doesn't wreck conversion, and it has to be a *soft* credit check so it doesn't ding the shopper's credit file for a $60 purchase.

"Soft" is a hard architectural requirement, not a nicety. A soft inquiry means you query bureau data without recording a hard pull, which in turn means the decision leans heavily on signals you already hold or can pull cheaply: repayment history on prior plans, device and account age, cart value, velocity across recent orders, and thin-file bureau attributes. The model runs synchronously inside the checkout call because the shopper is staring at a spinner.

Because the underwrite is thin and fast, keep the decision idempotent and cheap to replay. A useful shape is a pure scoring function over a snapshot of features, so the same inputs always yield the same decision and you can re-score offline for audit:

```python
def decide(features) -> Decision:
    score = model.score(features)          # soft signals only
    if score < DECLINE_THRESHOLD:
        return Decision.DECLINE
    limit = assign_limit(score, features.cart_value)
    if features.cart_value > limit:
        return Decision.DECLINE
    return Decision.approve(limit=limit, plan="pay_in_4")
```

Two outcomes leave this stage: approve, which continues the main path, and decline, which is a branch you should not treat as a dead end. A decline at checkout is still a conversion opportunity — offer a smaller limit, a different plan, or a pay-in-full fallback rather than dumping the shopper back to the cart with nothing.

## Settle the merchant upfront, then reconcile

Once approved, settlement pays the merchant the full order amount minus the provider's fee. This is the moment the loan is "booked," and it should be modeled as its own step with its own ledger entry rather than folded into approval.

Treat the payout as a durable event. The provider now holds a receivable equal to the settled amount; the shopper holds a payable split into four installments. Those two sides must always reconcile. In practice that means an append-only ledger where the booking, each scheduled installment, each collection, and the fee are separate entries keyed to the same plan id. When a dispute or refund arrives weeks later, you unwind against those entries — you never mutate a balance in place.

Settlement also introduces the first real money-movement failure mode: the payout to the merchant can fail or be delayed on the banking rail even though the shopper's plan is already active. Keep approval and payout as separate states so a stuck payout doesn't leave you unsure whether the loan exists. The loan exists the instant you approve; the payout is a separate promise you retry until it clears.

## The schedule and the collection loop

With the merchant paid, servicing generates the installment schedule — for pay-in-4, typically the first payment at purchase and three more at two-week intervals — and then runs a collection loop against it.

The schedule is data, not behavior. Generate it once, store the due dates and amounts, and let the collection loop walk it:

```python
def build_schedule(principal, start, count=4, step_days=14):
    per = split_evenly(principal, count)   # handle rounding on the first
    return [
        Installment(seq=i, due=start + i * step_days, amount=per[i])
        for i in range(count)
    ]
```

Each due date triggers an auto-debit against the shopper's stored payment method. A successful debit advances the plan; when the final installment clears, the plan reaches `closed` and the receivable is fully recovered. This is the happy path, and for most plans it is uneventful.

The interesting engineering is in the retries. A failed debit is not a default — cards decline for soft reasons all the time: insufficient funds today, an expired card, a temporary issuer block. The collection loop should carry a dunning sub-state: retry on a schedule, notify the shopper through a channel they'll actually see, and offer to update the payment method or shift the due date. Only after that treatment window is exhausted does the plan move to `default`.

A worked rule of thumb: separate the *technical* retry (same card, transient failure, retry in hours) from the *treatment* retry (shopper outreach over days). Collapsing them into one counter is a common mistake that either hammers a dead card or gives up on a recoverable one.

## Failure paths carry the real cost

The two branches — decline and default — are where a BNPL book lives or dies, so they deserve first-class modeling rather than being buried in exception handlers.

Decline is cheap: no money has moved, and the cost is a lost sale. Default is expensive: the provider has already paid the merchant, so an uncollected plan is a direct loss against the balance sheet. That is why every design decision upstream — the soft-check thresholds, the assigned limits, the collection cadence — is ultimately tuned against the default rate, not the approval rate. It is easy to approve everyone; the discipline is approving the plans you can collect.

Model both as explicit terminal-ish states with owners and observable exits. A default should hand off to a recovery process (in-house dunning, then agency) with a clear ledger position, not silently disappear.

## What to instrument

Because approval and loss are separated by weeks, dashboards that only show approval rate will look great right up until the vintage sours. Instrument the timeline end to end:

- **Approval rate and mix** at checkout, sliced by limit and cart value.
- **Settlement success and lag** — how often and how fast merchants actually get paid.
- **First-payment default** — plans that miss the very first installment, the earliest and loudest fraud/underwriting signal.
- **Roll rates** — how plans move from current to late to default across each installment.
- **Recovery rate** on the dunning loop, so you know how much of a missed payment you actually get back.

Watch these as *vintages* — cohorts grouped by origination week — because a change you ship to the underwriting model today only shows up in the loss numbers a month later. The system's job is to make that lag visible instead of hiding it behind a healthy-looking approval chart.
