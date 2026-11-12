# Flakiness — The Operational Disease That Kills Test Signal

*A flaky test — same code, different verdicts — is worse than no test: it costs full price, delivers noise, and teaches the team that red means retry. Post 1 did the arithmetic (ten thousand 99.9%-reliable tests ≈ permanent red); this post is the operating system for the disease: detect flakes statistically, quarantine them mechanically, fix them by root-cause class, and prevent the re-infection that follows any one-time cleanup.*

Flake management is where test engineering most resembles SRE: the suite has an error budget, reliability is a measured property, and heroic one-off cleanups decay without a standing system — the same operational logic as [observability engineering](/blog/series/observability-engineering/), pointed inward at CI.

## Detect: flakiness is a statistic, not an opinion

The definition is operational: a test is flaky if it produces different outcomes on identical inputs (same commit, same environment). Detection follows: **rerun-on-failure with recording** — a failed test retried against the same commit that then passes is a *measured flake event*, logged with full context (not silently retried-and-forgotten, which is where most teams throw the data away); **cross-build correlation** — the same test failing on unrelated changes across the fleet is flake evidence even without reruns (the selection system of post 2 helps: a failure in a test with *no dependency path* to the diff is near-certain flake); and **targeted re-execution** — suspicious tests run N times against a fixed commit to estimate a failure rate with confidence, turning "I think it's flaky" into "2.3% ± 0.4%". The output is a **flake score per test**, continuously maintained — the suite's reliability ledger, and the input every downstream decision reads.

## Quarantine: protect the signal first, fix second

The controversial, correct move: a test crossing the flake threshold is **automatically quarantined** — removed from the merge-blocking path (it still runs, non-blocking, for data) and filed against its owning team with the evidence attached. The reasoning is signal economics: one flaky test in the gate taxes *every engineer's every merge* with noise and retries; quarantine contains the damage to the one behavior that test covered — a visible, bounded hole instead of ambient signal decay. The system stays honest through its constraints: quarantine is **loud** (owners notified, dashboards show quarantined-count and age — a rising count is a team-health metric, not background), **bounded** (SLA to fix or delete; a test quarantined 90 days is a test the team has decided they don't need — post 1's deletion discipline, forced), and **never silent** (the failure mode to design against is quarantine-as-landfill; the SLA and aging reports exist precisely to prevent it).

## Fix and prevent: the root-cause taxonomy

Flakes cluster into a short, well-known taxonomy, and fixing by class beats fixing by instance:

- **Async and timing** — the dominant class: sleeps standing in for synchronization, races between setup and assertion, timeouts tuned to yesterday's CI load. Cure: explicit synchronization (wait-for-condition, not wait-for-duration) and the simulated clocks of post 5 — a test that owns time can't lose a race against it.
- **Isolation failures** — shared state between tests: leftover database rows, static singletons, port collisions, order dependence (passes alone, fails after test X). Cure: hermetic per-test state (post 4's environments scaled down), randomized execution order *as a flake-detection tool* (order-dependence surfaces immediately), and unique-per-test resources.
- **External dependencies** — real networks, real services, real time: the test inherits every dependency's reliability. Cure: fakes at the boundary for the merge path, with genuinely-integration tests moved to the non-blocking tier where their honest flake rate doesn't tax merges.
- **Resource sensitivity** — passes locally, fails under CI parallelism: memory pressure, CPU starvation masquerading as timeout. Cure: resource-aware scheduling (post 7) and timeout policies set from measured distributions, not folklore.

Prevention closes the loop: flake-prone patterns become lint rules (bare sleeps, shared fixtures without isolation, wall-clock reads — the incident-grown-ruleset pattern once more), new tests run a burn-in (N executions before entering the blocking tier — reliability proven, not presumed), and the flake score feeds the portfolio: a test that keeps returning to quarantine is telling you its design — or its value — is wrong.

The takeaway: flakiness is managed as an operational disease — **detected statistically** (recorded rerun events, cross-build correlation, targeted re-execution into a per-test flake score), **quarantined mechanically** (out of the gate, loudly, with fix-or-delete SLAs — protecting suite signal over individual coverage), and **fixed by taxonomy** (synchronization over sleeps, hermetic isolation with randomized order, fakes at boundaries, resource-aware timeouts), with lint rules and burn-in preventing re-infection. The goal is the one post 1 set: red means broken — and every part of this system exists to keep that sentence true.

## Key takeaways

- Flakiness is **measured, not debated**: same-commit rerun flips recorded as events, no-dependency-path failures as evidence, N-run re-execution for confidence — maintained as a per-test **flake score**.
- **Quarantine protects the many from the one**: automatic removal from the gate at threshold, still running for data — loud, owned, and SLA-bounded (fix or delete; 90 quarantined days = a deletion decision already made).
- Fix by class: **wait-for-condition not duration** + simulated clocks; **hermetic state** + randomized order (order-dependence surfaces instantly); **fakes in the gate**, honest integration tests in the non-blocking tier; timeouts from measured distributions.
- Prevent re-infection: flake-pattern lint rules, **burn-in** for new tests before they can block merges, repeat-offender tests escalated to portfolio review.

## Further reading

- [Race condition — the root of the dominant flake class](https://en.wikipedia.org/wiki/Race_condition)
- [Test automation — the machinery whose reliability this post engineers](https://en.wikipedia.org/wiki/Test_automation)
