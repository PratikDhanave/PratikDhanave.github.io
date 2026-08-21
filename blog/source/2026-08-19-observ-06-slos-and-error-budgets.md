# SLIs, SLOs, and Error Budgets

*"Is the system reliable?" is a useless question until you define reliability as a number. SLOs turn reliability from a vague aspiration into a measurable target, and the error budget — the small amount of unreliability you're allowed — turns it into a tool that settles the eternal fight between shipping features and keeping things stable. This is where telemetry becomes a way to run engineering, not just watch it.*

The pillars and OpenTelemetry give you telemetry. This post turns that telemetry into *reliability management* using the Google SRE framework: **SLIs** (what you measure), **SLOs** (the target you commit to), and **error budgets** (the tool that operationalizes it). This is the shift from "we have dashboards" to "we manage reliability deliberately" — and the error budget idea is one of the most useful concepts in all of operations.

## Why reliability needs a number

"The system should be reliable" is meaningless as stated — reliable enough for what? 100% reliability is impossible (things fail) and, crucially, *not even desirable*: chasing the last fraction of a percent costs exponentially more and delivers diminishing value users can't perceive. The SRE insight is that reliability must be a **defined, measured target** — a specific number you commit to — so you can tell whether you're meeting it and make deliberate trade-offs. That's what SLIs, SLOs, and error budgets provide, building directly on the metrics from the earlier post.

## The three concepts

They stack, each built on the last:

- **SLI — Service Level Indicator** — a *measurement* of some aspect of service quality, as a number, usually a ratio of good events to total. "The proportion of requests that succeed," "the proportion of requests served under 300ms." An SLI is a metric (from the metrics post) chosen specifically because it reflects *user experience*. Good SLIs measure what users actually care about: availability, latency, correctness — not internal minutiae like CPU.
- **SLO — Service Level Objective** — a *target* for an SLI over a time window. "99.9% of requests succeed over 30 days," "99% of requests are served under 300ms over 30 days." The SLO is the reliability goal you *commit to internally* — the line between "reliable enough" and "not." It's a deliberate choice, not a max-it-out reflex.
- **SLA — Service Level Agreement** (related) — a *contractual* promise to customers with consequences (refunds) if missed. SLAs are business contracts and are typically set *looser* than your internal SLO, so you have margin — you aim to beat your SLA by meeting a stricter SLO internally. (SLAs are the external cousin; SLOs are the internal engineering tool.)

```text
SLI  = what you measure   → "% of requests under 300ms" (a number)
SLO  = the target         → "99% under 300ms over 30 days" (your commitment)
SLA  = the contract       → "99% or we credit you" (external, looser)
```

The most important choice is picking **user-centric SLIs**: measure the things whose failure the user *feels* (requests succeeding, responses being fast enough), because reliability is ultimately about user experience, not internal metrics. An SLO on a metric users don't care about is reliability theater.

## The error budget: the powerful part

Here's the concept that makes SLOs genuinely useful. If your SLO is 99.9% success, then you are *explicitly allowing* 0.1% failure — and that 0.1% is your **error budget**: the amount of unreliability you're permitted to spend over the window before you've violated the SLO.

```text
SLO 99.9% over 30 days  →  error budget = 0.1% of requests may fail
   (≈ 43 minutes of full downtime per 30 days, or the equivalent in errors)

Budget remaining → you can take risks (ship fast, experiment)
Budget exhausted → stop shipping risky changes, focus on reliability
```

This reframes reliability from "never fail" to "**stay within budget**," and that reframing is transformative because the error budget becomes a **shared, objective decision tool** for the classic conflict between two forces:

- **Product/developers** want to ship features fast, which risks reliability.
- **Operations/SRE** want stability, which resists change.

The error budget settles this *with data instead of politics*:

- **Budget remaining** → you can afford to move fast, deploy frequently, and take risks — reliability is comfortably within target, so spend the budget on velocity.
- **Budget exhausted** → you've used up your allowed unreliability, so the priority automatically shifts to reliability work (fixing what's breaking, hardening, slowing risky releases) until you're back within budget.

Instead of an endless "ship vs. stabilize" argument decided by whoever's loudest, the error budget gives an objective, agreed rule: *the budget tells you which mode you're in.* This is why error budgets are considered one of SRE's best ideas — they turn reliability into a resource you manage, aligning product and operations around a shared number rather than pitting them against each other.

## Choosing SLOs well

Setting SLOs is a skill, and common mistakes undermine the whole system:

- **Base the target on user needs, not aspiration.** The right SLO is "reliable enough that users are happy and the business is fine," not "as many nines as possible." Every extra nine costs exponentially more; pick the level that actually matters, then stop. Over-tight SLOs waste effort and generate noise; too-loose ones let real pain through.
- **Measure SLIs from the user's perspective** — ideally as close to the user as possible (did *their* request succeed and arrive quickly?), because that's what reliability means.
- **Pick a sensible window** (e.g. 30 days rolling) — long enough to be meaningful, short enough to be actionable.
- **Fewer, meaningful SLOs beat many.** A couple of SLOs on the things that matter (availability, latency) are more useful than dozens no one acts on.
- **Actually enforce the error budget policy.** The error budget only works if the team *honors* it — if "budget exhausted" genuinely triggers a shift to reliability work. An error budget nobody acts on is just a number.

## From telemetry to engineering management

SLIs/SLOs/error budgets are where observability stops being *watching* and becomes *managing*: your telemetry (metrics especially) feeds SLIs, the SLO defines the target, and the error budget drives concrete decisions about where engineering effort goes. This is also the foundation for *good alerting* (next post) — you alert when the error budget is at risk (burning too fast), not on every blip, which is how you escape alert fatigue. Reliability, defined as a number and managed as a budget, is the difference between an ops practice that's deliberate and one that lurches from fire to fire.

## Key takeaways

- Reliability must be a defined, measured number because 100% is impossible and undesirable (the last nines cost exponentially for value users can't perceive) — SLIs/SLOs/error budgets provide that definition.
- SLI = a user-centric measurement (ratio of good events, e.g. % of requests under 300ms); SLO = the target you commit to over a window (99% under 300ms/30 days); SLA = the looser external contract — pick SLIs for what users actually feel.
- The error budget is the allowed unreliability implied by the SLO (99.9% → 0.1% may fail); it reframes reliability from "never fail" to "stay within budget," making it a resource you manage.
- The error budget objectively settles ship-fast-vs-stability: budget remaining → move fast and take risks; budget exhausted → shift to reliability work — replacing politics with a shared number (one of SRE's best ideas).
- Set SLOs from user needs not aspiration (stop at the nines that matter), measure SLIs close to the user, keep them few and meaningful, and actually enforce the error-budget policy — then alert on budget burn, not every blip.

## Further reading

- [OpenTelemetry (previous post)](/blog/posts/observ-05-opentelemetry.html)
- [Google SRE Book — Service Level Objectives](https://sre.google/sre-book/service-level-objectives/)
- [Metrics — the measurements SLIs are built on](/blog/posts/observ-02-metrics.html)
