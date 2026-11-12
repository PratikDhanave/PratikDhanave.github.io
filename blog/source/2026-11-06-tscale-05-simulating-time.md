# Simulating Time — Testing the Behavior That Only Happens Later

*Some of the most consequential code in any system runs when nobody is deploying: renewals at midnight, trials expiring on day 14, tokens timing out, retries backing off, data retention sweeping on schedule. Testing it by waiting is absurd; testing it by mocking one clock call is fragile; testing it properly means making time itself a controllable dependency of the system under test — and that choice, it turns out, improves the architecture even before it improves the tests.*

Billing taught this series' precursor lesson ([bill-07](/blog/posts/bill-07-testing-billing-systems.html)): time-dominated systems are untestable until the clock is injected. This post generalizes it — the time-simulation patterns for any system where the calendar is a collaborator, and the architectural prerequisites they quietly enforce.

## The clock as dependency, generalized

The foundational move everywhere: **no code reads the wall clock directly**. Every `now()`, every timer, every scheduled trigger flows through an injected clock interface — production binds real time; tests bind a controllable instant. What makes this *generalize* beyond billing is recognizing how many disguises time wears: explicit timestamps, yes, but also timeouts (a deadline is a clock read), retry backoff (hook-02's schedules are time arithmetic), cache TTLs, rate-limit windows, token expiries, cron expressions, and "recent" anywhere in product logic. An honest audit of wall-clock reads is the first step and reliably shocking — dozens of hidden time dependencies per service, each one a behavior that currently can't be tested deterministically.

Advancing simulated time must *cause* what real time would cause, and that requirement is the architectural teeth: timers and schedules registered with the clock fire when the test advances past them; scheduled jobs run through an executor the clock drives, not a system cron reading the wall. Systems refactored this way end up with **explicit schedulers** — every time-driven behavior declared and discoverable rather than buried in crontabs and sleeps — which is the same legibility win the subscription state machine got from scheduled transitions (bill-04): the test infrastructure forces the inventory that operations wanted anyway.

## The patterns, by scope

- **In-process logical clocks** — the unit and service level: advance by durations, assert at boundaries ("advance 14 days → trial expired; advance 1 more second → grace begins"). Discrete-event style execution — jump directly to the next registered timer rather than ticking — makes month-long scenarios run in milliseconds, and *boundary assertions* (the instant before vs after) catch the off-by-one-period bugs that dominate this class.
- **Cross-service time** — the integration level, where it gets hard: multiple services must agree on "now" or the simulation leaks. The workable approaches, in order of preference: scope the simulated-time test to a *slice* where one clock can rule (post 4's change-slice environments, with fakes beyond the boundary holding time constants); propagate a test-time header/context through the slice for services built to honor it; or freeze external dependencies' time-sensitive behavior at the fake boundary. What doesn't work: changing the OS clock of a shared environment (global blast radius) or mixing simulated and real time in one flow (the leaks produce flakes that will haunt post 3's quarantine queue).
- **Provider-grade time simulation** — the platform level: systems that *serve* time-dependent workflows (billing platforms, workflow engines, schedulers) owe their integrators simulation as a product feature — test-mode clocks integrators can advance against sandboxed state (the capability bill-07 consumed and hook-07's platform list included). Internally, the same machinery powers scenario rehearsal: replaying a year of lifecycle against a candidate change in minutes.

Two companion disciplines round it out: **time-zone and calendar edges are test fixtures, not folklore** — DST transitions, month-length boundaries, leap days, and the user-in-Tokyo-billed-in-UTC cases live in a shared library of edge instants that time-dependent suites import (the golden-scenario pattern applied to the calendar); and **real-time smoke remains** — one thin layer of honest wall-clock tests (does the scheduler actually fire in production configuration?) guards the binding between the simulated world and the real one, in the non-blocking tier where its slowness belongs.

The takeaway: time becomes testable when it becomes a dependency — **inject the clock everywhere** (auditing time's many disguises: timeouts, backoffs, TTLs, windows, expiries), drive all scheduled behavior through clock-driven executors (which forces the explicit-scheduler architecture operations wanted anyway), and simulate by scope: discrete-event logical clocks with boundary assertions in-process, one-clock slices or propagated test-time across services, and simulation-as-product-feature at the platform level. Keep a shared fixture library of calendar edges and a thin real-time smoke layer — and the code that runs "later" finally gets tested *now*.

## Key takeaways

- **No direct wall-clock reads** — and time hides everywhere: timeouts, backoff, TTLs, rate windows, token expiry, cron, "recent". The audit is step one and always shocking.
- Advancing time must **cause** time's effects: timers and jobs registered with the injected clock, run by clock-driven executors — refactoring that leaves behind the explicit scheduler inventory ops wanted anyway.
- Patterns by scope: **discrete-event in-process clocks** (months in milliseconds, assert at boundaries), **one-clock slices / propagated test-time** across services (never OS-clock changes or mixed time), **simulation as a product feature** for platforms serving time-dependent workflows.
- **Calendar edges are shared fixtures** (DST, month lengths, leap days, cross-zone billing instants); one thin **real-time smoke layer** guards the sim-to-real binding from the non-blocking tier.

## Further reading

- [Discrete-event simulation — executing a system by its events rather than its clock](https://en.wikipedia.org/wiki/Discrete-event_simulation)
- [System time — the dependency being abstracted](https://en.wikipedia.org/wiki/System_time)
