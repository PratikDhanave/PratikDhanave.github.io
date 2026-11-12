# Testing Billing Systems — Simulated Clocks and Golden Invoices

*Billing's defining property — post 1 called it time-dominance — makes it nearly untestable by ordinary means: the interesting behavior happens at renewals, trial expiries, grace-window closures, and anniversary boundaries, none of which occur during a test run unless the test controls time itself. The teams that trust their billing systems all converged on the same answer: make the clock an injectable dependency, simulate months in milliseconds, and pin correctness with golden invoices.*

Posts [2](/blog/posts/bill-02-pricing-models-in-code.html)–[6](/blog/posts/bill-06-entitlements.html) built the machinery; this post is how you believe it. It also previews the broader testing discipline the [Testing at Scale](/blog/series/testing-at-scale/) series covers — billing is simply the domain where its clock-simulation chapter was invented out of necessity.

## The clock is a dependency — inject it

The root cause of untestable billing is code that calls the system clock directly. Every `now()` scattered through subscription logic is a hidden global that makes "what happens at renewal?" unanswerable without waiting a month. The foundational refactor: **all billing time flows through one clock interface**, injected like any dependency — production binds it to real time; tests bind it to a controllable instant.

With the clock injected, the test vocabulary becomes *temporal*: create a subscription, **advance the clock** 14 days, assert the trial-end transition fired, the conversion invoice drafted, the entitlements flipped. Advancing time must trigger everything real time would — scheduled transitions (post 4), period closures, grace-window finalizations (post 3), dunning retries (post 5) — which forces a healthy architecture property: time-driven behavior runs through explicit schedulers that the simulated clock can drive, not through cron jobs reading the wall.

What this unlocks is the test suite billing actually needs: the **full-lifecycle scenario** — trial → convert → upgrade mid-period (proration!) → payment failure → dunning recovery → renewal → cancel-at-period-end → expiry — executed in milliseconds, asserting state, entitlements, and money at each boundary. Those dozen boundary assertions cover more real risk than a thousand unit tests of the proration formula, because billing bugs live at the *joints* between subsystems, and the joints are temporal.

## Golden invoices: pin the money

For the money itself, the highest-leverage technique is the **golden invoice**: a curated set of scenarios (each pricing model from post 2, proration cases from post 4, credits, minimums, tax variants, usage splits) whose expected final invoices are stored as fixtures — line items, amounts, tax, totals, to the cent. Every change to billing code re-runs the scenarios and diffs against the goldens. The diff is the review artifact: a pricing-logic PR whose golden diff shows only the intended scenario changing is safe; one that ripples into unrelated goldens just caught a regression no unit test was pointed at. Two disciplines keep goldens honest: changes to a golden require the same scrutiny as changes to money-handling code (the fixture *is* the spec), and scenarios are added from production incidents — every billing bug becomes a golden that can never recur silently.

Re-derivability (post 5) supplies the companion invariant test: for any finalized production invoice, regenerate from versioned inputs and assert byte-equality. Run continuously on samples, this is the cheapest end-to-end audit a billing system can have.

## The rest of the pyramid

Around those two pillars: **property-based tests** for the arithmetic (prorations sum to full-period price; graduated tiers are monotonic; rounding never creates or destroys cents across an invoice — generators find the boundary quantities humans don't); **idempotency tests as first-class** — replay every webhook, retry every job, double-fire every scheduler tick and assert single effect, because post 3's and 5's safety claims deserve direct exercise; and **sandboxed integration** against the payment provider's test environment for the handful of flows (mandates, 3DS, refunds) where only the real counterparty's behavior counts. What stays rare: tests that mock the clock *and* the catalog *and* the meter into fiction — a billing test that fakes all its inputs verifies nothing but the mocks.

The takeaway: billing becomes testable the moment **time becomes an injected dependency** — simulated clocks drive schedulers through month-long lifecycles in milliseconds, turning boundary behavior (renewals, expiries, grace closures, dunning) into assertable scenarios. Pin the money with **golden invoices** diffed on every change and grown from every incident, back them with continuous **re-derivation audits** of production invoices, and complete the pyramid with property tests on the arithmetic and idempotency tests on every retry path. Trustworthy billing isn't tested harder — it's tested *temporally*.

## Key takeaways

- Inject the clock: every direct `now()` is a hidden global; time-driven behavior routed through schedulers the test clock can drive is both the refactor and the architecture win.
- The core suite is **temporal scenarios**: full lifecycles (trial → convert → prorate → fail → recover → renew → cancel) advanced in milliseconds, asserting state, entitlements, and money at each boundary — where billing bugs actually live.
- **Golden invoices** pin correctness to the cent; the golden diff is the review artifact, fixture changes get money-code scrutiny, and incidents become permanent scenarios.
- **Re-derivation audits** (regenerate finalized invoices, assert equality) are the cheapest continuous end-to-end check.
- Round out with **property tests** on proration/tier/rounding arithmetic and **idempotency tests** on every retry path; avoid tests that mock away all inputs.

## Further reading

- [Software testing — the general discipline billing bends around time](https://en.wikipedia.org/wiki/Software_testing)
- [Discrete-event simulation — advancing a system by its events, not wall time](https://en.wikipedia.org/wiki/Discrete-event_simulation)
