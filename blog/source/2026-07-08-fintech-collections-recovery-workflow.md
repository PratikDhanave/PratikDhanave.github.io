# Engineering the Collections and Recovery Workflow

*Modeling post-delinquency treatment paths — reminders, restructuring, settlement offers, and the charge-off handoff — as a state machine you can reason about.*

Most lending platforms invest heavily in origination and underwriting, then treat collections as a batch job that fires a few emails. That is a mistake. Once an account goes past due, every day it spends in the wrong treatment path is measurable money lost. The recovery side deserves the same modeling discipline as the approval side: an explicit state machine, well-defined transitions, and instrumentation on the edges that actually move the portfolio.

This post walks through how I model the workflow that begins the moment an installment is missed and ends when an account either cures or is charged off and handed to an agency.

## Delinquency buckets are the coordinate system

Before any treatment logic, you need a canonical way to describe *how* late an account is. The industry convention is days-past-due (DPD) grouped into buckets, and every downstream decision keys off the bucket rather than the raw day count. A typical unsecured consumer setup looks like this:

```
current   1-29 DPD    30-59      60-89      90-179       180+ DPD
  |          |           |          |          |            |
 ok       bucket 1    bucket 2   bucket 3   bucket 4     charge-off
        (soft nudge) (dunning)  (outreach) (offer/     (accounting
                                            settle)      write-off)
```

> **▸ [Open the interactive diagram](/blog/diagrams/fintech-collections-recovery-workflow.html)** — pan, zoom, and trace every step (light/dark, self-contained).

The single most important metric that lives on this coordinate system is the *roll rate*: the fraction of balance that moves from one bucket into the next each cycle. A bucket-1-to-bucket-2 roll rate creeping from 18% to 25% is an early-warning signal worth more than almost any single-account event. Treatment effectiveness is ultimately judged by whether it bends roll rates downward, so I make the bucket transition a first-class, logged event rather than something derived after the fact from a nightly snapshot.

## The treatment ladder

Treatment escalates in cost. You spend cheap, automated contact early and reserve expensive human and legal effort for accounts that have proven unresponsive. Collapsing that ordering — calling a customer who is three days late over a forgotten autopay — burns goodwill and agent hours. The ladder has three rungs before resolution:

1. **Reminders / dunning.** Automated multi-channel nudges (push, SMS, email) with backoff. These are idempotent and rate-limited per account so a retry storm never double-messages a borrower.
2. **Outreach.** A human or dialer contact whose primary goal is a *promise-to-pay* (PTP) — a dated commitment for a specific amount. A kept PTP is the strongest leading indicator of cure.
3. **Offer.** When the borrower cannot pay the arrears in full, you present a cure lever: restructure the schedule, or settle for less than the full balance.

The distinction between the two cure levers matters at the accounting layer, not just the UX layer:

- **Restructure / repayment plan** — the borrower keeps the full obligation but on new terms (re-aged schedule, hardship forbearance, reduced APR). The receivable stays whole.
- **Settlement** — you accept a partial payment as full satisfaction and forgive the remainder. That forgiveness is a realized loss and must be booked as such.

Both paths, if honored, route the account back to *cured* and normal servicing. That return edge is easy to forget in code, and forgetting it leaves cured accounts stuck in a collections queue.

## Model it as an explicit state machine

The reason to draw this as a state machine and not a pile of cron jobs is that transitions must be *guarded, logged, and reversible in exactly the ways policy allows*. A promise-to-pay that is broken should re-escalate; a promise that is kept should suppress further dunning. Here is the shape I enforce in code:

```python
TRANSITIONS = {
    ("delinquent",  "reminded"):    guard_min_dpd(1),
    ("reminded",    "outreach"):    guard_no_response(days=7),
    ("outreach",    "ptp_open"):    guard_promise_captured,
    ("ptp_open",    "cured"):       guard_ptp_kept,
    ("ptp_open",    "outreach"):    guard_ptp_broken,      # re-escalate
    ("outreach",    "offer"):       guard_min_dpd(60),
    ("offer",       "plan_active"): guard_offer_accepted,
    ("plan_active", "cured"):       guard_arrears_cleared,
    ("offer",       "charge_off"):  guard_min_dpd(180),    # policy gate
    ("charge_off",  "agency"):      guard_placement_ready,
}

def transition(account, target):
    guard = TRANSITIONS.get((account.state, target))
    if not guard or not guard(account):
        raise IllegalTransition(account.state, target)
    emit_event(account, account.state, target)   # audit + metrics
    account.state = target
```

Two properties fall out of this structure for free. First, an audit trail: every `emit_event` is the record a regulator or a dispute investigation will ask for. Second, testability: each guard is a pure predicate over account state, so the treatment policy is unit-testable without standing up the whole platform.

## Charge-off is an accounting event, not the end

The most common conceptual error I see engineers make is treating charge-off as "give up." It is not. Charge-off is a *regulatory and accounting* transition: for unsecured consumer credit, policy (and examiner expectation) typically forces the write-off at 180 DPD regardless of collectability. The receivable leaves the performing book and the loss is recognized. What it does *not* mean is that collection stops.

After charge-off, recovery continues off the balance sheet, usually through third-party agencies on a contingency fee, or eventually via debt sale. So the state machine has two distinct terminal-ish regions that people conflate:

- **Cured** — the account resolved through treatment and returns to servicing. Good outcome.
- **Charged-off → agency** — the loss is booked, and residual recovery is pursued externally.

Keeping these separate in the model prevents a whole class of reporting bugs, like counting agency recoveries as if they reversed the original loss, or leaving a charged-off account visible in the active-servicing queue.

## Instrument the edges that move money

Because the workflow is modeled as transitions, the metrics write themselves — you measure the edges, not the nodes. The three I watch first:

- **Roll rate per bucket boundary.** The portfolio-level health signal. Everything else is a lever to bend it.
- **Promise-to-pay kept vs. broken.** The cheapest, earliest predictor of cure. A falling kept-rate tells you outreach quality or borrower stress is shifting before roll rates catch up.
- **Recovery dollars per charged-off account, by placement vintage.** This is how you judge whether agency selection and settlement authority are set correctly.

Treat these as SLOs on the recovery pipeline the same way you would treat auth rate on the payments pipeline. The workflow diagram above is the map; the roll rate is the score. When you can point at a single transition and say how much it is worth, collections stops being a batch job and becomes an engineered system — one where a policy change is a guarded edge you can test, ship, and measure.
