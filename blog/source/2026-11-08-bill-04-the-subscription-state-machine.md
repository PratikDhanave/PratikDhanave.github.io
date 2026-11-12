# The Subscription State Machine — Lifecycle, Proration, and the Edges Between

*A subscription looks like a row with a plan and a date. It behaves like a state machine with a dozen states, transitions triggered by humans, payments, and the calendar, and money consequences on nearly every edge. Teams that model the lifecycle explicitly handle upgrades, trials, and cancellations as transitions with rules; teams that don't accumulate booleans — `is_trial`, `is_paused`, `cancel_at_period_end` — until no one can say what state a customer is actually in.*

Posts [2](/blog/posts/bill-02-pricing-models-in-code.html)–[3](/blog/posts/bill-03-metering-counting-at-scale.html) built prices and quantities. This post builds the object that binds them to a customer over time — and the arithmetic of changing that binding mid-period.

## The states, and the discipline of naming them

The core lifecycle is small; its value is in being *explicit*:

- **Trialing** — full or limited access, no revenue yet, a conversion deadline attached. The critical design choice: what happens at trial end *without* a payment method — convert, downgrade to free, or expire — is a product decision that must be encoded as a transition, not improvised in a cron job.
- **Active** — the steady state: entitled (post 6), accruing charges, renewing at period end. Renewal is itself a transition — one that runs through payment collection and can fail.
- **Past due** — payment failed; the grace state where dunning (post 5) retries while access policy decides how degraded the experience gets. The most consequential state nobody designs deliberately.
- **Paused** — access suspended by choice, relationship retained. Clarify what pausing does to the period clock and committed terms *before* building it.
- **Canceled** — with the vital distinction between *cancel now* and *cancel at period end* (the overwhelmingly common case: access until the paid-through date, then no renewal — which means "canceled" is often a *scheduled* transition, not an immediate one).
- **Expired/ended** — terminal; history retained for reactivation, which is a new subscription referencing old context, not a resurrection.

Every transition answers four questions: who may trigger it, what happens to money (charge, credit, nothing), what happens to entitlements, and what happens to the period clock. Writing those four answers per edge *is* the design work.

## Proration: the arithmetic of mid-period change

Change a subscription mid-period and someone owes someone money. A customer upgrading on day 10 of 30 has paid for 20 days of the old plan they won't use and owes 20 days of the new plan. Proration computes both: **credit the unused remainder of the old price, charge the remainder-period at the new price**, both proportional to time left.

The engineering content is in the policies around the arithmetic, each a decision to make once and encode:

- **Settlement timing** — invoice the net difference immediately, or accrue it to the next invoice? Immediate is cleaner for large deltas; accrued avoids micro-invoices.
- **Direction asymmetry** — upgrades commonly prorate and charge immediately (customer wants the capability now); downgrades commonly *schedule for period end* instead of prorating a refund — a policy that avoids refund mechanics and gaming, at the cost of "why am I still paying for Pro?" support tickets. Either is defensible; ambiguity is not.
- **Rounding and floors** — prorated math produces fractions of cents; pick the rounding rule, apply it consistently, and reconcile (post 8) to the cent.
- **Quantity changes** — per-seat adds mid-period are proration too (new seats at remainder-period price), and seat *removals* raise the same downgrade-timing question.
- **Usage interplay** — switching plans mid-period with metered usage (post 3) forces a sub-period aggregation split: usage before the change rates at the old version, after at the new. This is precisely why the meter keeps event-time facts and rating stays separate.

## Scheduled change: the lifecycle's time dimension

Half the lifecycle's complexity is that changes take effect *later*: cancel at period end, downgrade at renewal, a price-version migration next anniversary (post 2's versioning meeting the calendar). Model these as **scheduled transitions** — first-class records of (what changes, when, triggered by whom) — rather than flags interpreted by a nightly job. The payoff: the current state and the *future* state are both queryable ("what will this account look like on Dec 1?"), support can see and cancel pending changes, and the renewal job becomes a pure executor of declared intent instead of a nest of conditional policy. Scheduled transitions are also where testing (post 7) earns its clock-simulation machinery — nearly every bug in this post's territory is a "what fires at the boundary?" bug.

The takeaway: a subscription is a state machine — trialing, active, past-due, paused, canceled (now vs at-period-end), ended — and every edge needs four explicit answers: trigger, money effect, entitlement effect, clock effect. Mid-period change is proration — credit the unused old, charge the remaining new — governed by encoded policies for settlement timing, upgrade/downgrade asymmetry, rounding, seats, and the usage split that justifies separating rating from metering. Model deferred changes as first-class **scheduled transitions**, making future state queryable and the renewal job an executor of intent — because in billing, most states are really appointments with the calendar.

## Key takeaways

- Model the lifecycle **explicitly** — trialing / active / past-due / paused / canceled(now | at-period-end) / ended — not as accreted booleans; each edge documents trigger, money, entitlements, clock.
- **Past due** is the most consequential undesigned state: dunning runs there, and access policy during it is a product decision.
- **Proration** = credit unused old + charge remaining new; the engineering is the policies: settle now vs accrue, upgrade-now/downgrade-at-renewal asymmetry, rounding rules, seat changes, and splitting metered usage at the change boundary by event time.
- **Scheduled transitions** are first-class records, making future state queryable and renewal a pure executor — and making the calendar-boundary bugs testable with simulated clocks.

## Further reading

- [Finite-state machine — the model subscriptions actually follow](https://en.wikipedia.org/wiki/Finite-state_machine)
- [Pro rata — the principle under every mid-period adjustment](https://en.wikipedia.org/wiki/Pro_rata)
