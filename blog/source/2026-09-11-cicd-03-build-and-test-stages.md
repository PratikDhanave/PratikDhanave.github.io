# The Build and Test Stages

*The build and test stages are the engine of a pipeline — the part that decides, on every change, whether it's safe to proceed. Get them fast and trustworthy and the whole pipeline flows; get them slow or flaky and the pipeline becomes something developers route around. This post is about designing tests and builds that give a fast, reliable verdict.*

CI depends on a build that's fast and reliable (previous post). This post is how you actually achieve that: structuring tests so they're quick and trustworthy, building artifacts once, and using caching and parallelism to keep the whole thing fast. This is where the pipeline earns or loses developers' trust.

## The test pyramid: shape your tests for speed and signal

Not all tests are equal in cost or value, and the classic guide to balancing them is the **test pyramid**:

- **Unit tests** (the wide base) — test a single function or class in isolation. Fast (milliseconds), numerous, pinpoint failures precisely. The bulk of your tests should be here.
- **Integration tests** (the middle) — test components working together (a service and its database, two modules). Slower, fewer, catch wiring bugs units miss.
- **End-to-end tests** (the narrow top) — drive the whole system as a user would. Slowest, most brittle, fewest — but they verify the system actually works end to end.

The pyramid shape (many unit, some integration, few E2E) is deliberate. The inverted "ice-cream cone" — mostly slow E2E tests — is the classic anti-pattern: it produces a test suite that's slow (killing CI speed), flaky (E2E tests break for environmental reasons), and vague (an E2E failure could be anything). Push testing *down* the pyramid: prefer a fast, precise unit test over a slow, brittle E2E test wherever you can, and use E2E tests only for the critical user journeys that genuinely need full-system verification.

## Tests must be fast, deterministic, and isolated

Beyond the pyramid, three properties make a test suite trustworthy in CI:

- **Fast.** The pipeline's speed is dominated by test time. Fast tests keep CI's feedback loop tight (post 2). Achieve it with the pyramid, parallelism, and by keeping slow tests out of the first stage.
- **Deterministic.** A test must give the same result every run for the same code — pass or fail, never random. **Flaky tests** (the determinism killers) usually come from timing/race conditions, shared state between tests, real network calls, or dependence on wall-clock time or ordering. Every flaky test erodes trust in the whole suite (post 2), so hunt them down and fix or quarantine them — a flaky test is a bug in the test.
- **Isolated.** Tests shouldn't depend on each other or on external state. Each test sets up what it needs and cleans up after, so tests can run in any order and in parallel without interfering. Shared mutable state between tests is the most common source of both flakiness and order-dependence.

These properties are what let you *trust a green build* — the entire premise of CI. A suite that's slow, flaky, or interdependent produces a signal nobody believes.

## Staged testing: fail fast, cheap first

A well-designed pipeline runs tests in **stages ordered by cost**, so cheap fast checks run first and expensive slow ones only if those pass:

1. **Lint / format / type-check** — seconds. Catch trivial issues instantly.
2. **Unit tests** — seconds to a couple minutes. The bulk of verification.
3. **Integration tests** — minutes. Only if units pass.
4. **End-to-end tests** — minutes to longer. Only if everything below passes.

This **fail-fast** ordering means a change with a syntax error or a broken unit test is rejected in seconds, not after a 20-minute E2E run. It gives developers the fastest possible feedback on the most common failures, and reserves the expensive stages for changes that have already cleared the cheap gates. Order your pipeline so the quickest way to find a problem runs first.

## Build once, promote the same artifact

A foundational principle that prevents a whole class of bugs: **build your deployable artifact once, and promote that exact artifact through every environment.**

The anti-pattern is rebuilding the application separately for staging and for production. If you rebuild, the staging artifact and the production artifact are *not guaranteed identical* — different dependency versions, different build-time state, different environment — so testing staging tells you less about production than you think. You can pass every test on a staging build and ship a subtly different production build.

Instead: the pipeline builds the artifact (a container image, a binary, a package) *once*, early, and that identical artifact flows through test → staging → production. Configuration that differs between environments is injected at deploy time (environment variables, config files, secrets), *not* baked into separate builds. This guarantees that what you tested is exactly what you ship — the artifact is immutable as it's promoted. It's a small discipline with a large payoff in confidence.

## Caching and parallelism: keeping it fast

Two techniques keep a growing pipeline fast:

- **Caching.** Don't redo work that hasn't changed. Cache dependencies (downloaded packages), build outputs, and layers so each run only rebuilds what actually changed. Dependency download and compilation are often the biggest time sinks, and both cache well. A good cache can turn a 10-minute build into a 2-minute one.
- **Parallelism.** Run independent work concurrently — split the test suite across multiple runners, run lint and unit tests simultaneously, test multiple platforms in parallel. Since test time dominates and tests are (if isolated) independent, parallelism is often the biggest single speedup available.

Both depend on the earlier disciplines: caching relies on deterministic builds (so a cache hit is safe), and parallelism relies on isolated tests (so they don't interfere when run concurrently). The properties compound — good test hygiene isn't just about correctness, it's what makes the pipeline fast enough to stay continuous.

## Key takeaways

- Shape tests as a **pyramid** — many fast unit tests, some integration, few E2E — and avoid the inverted "ice-cream cone" of mostly slow, flaky E2E tests; push testing *down* to the fastest level that catches the bug.
- Tests must be **fast, deterministic, and isolated** — flaky (non-deterministic) tests and inter-test state dependence destroy trust in the green build, which is CI's whole premise; a flaky test is a bug in the test.
- Order the pipeline **cheap-and-fast first** (lint → unit → integration → E2E) so it **fails fast** — a syntax error is caught in seconds, not after a 20-minute E2E run.
- **Build the artifact once and promote that exact artifact** through every environment (inject config at deploy time) — rebuilding per environment means you didn't test what you ship.
- Keep a growing pipeline fast with **caching** (dependencies, build outputs — relies on deterministic builds) and **parallelism** (split test suites, run stages concurrently — relies on isolated tests); good test hygiene is what makes speed possible.

## Further reading

- [Martin Fowler — The Practical Test Pyramid](https://martinfowler.com/articles/practical-test-pyramid.html)
- [Martin Fowler — Continuous Integration](https://martinfowler.com/articles/continuousIntegration.html)
