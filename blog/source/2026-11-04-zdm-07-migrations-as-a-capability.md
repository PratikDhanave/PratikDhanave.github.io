# Migrations as a Capability — Linters, Harnesses, and the Fleet View

*One team running one careful migration is craft; an organization running hundreds a month across a fleet of databases is either a capability or a casino. The closing move of this series is the same one the enterprise-AI series made about adoption: stop treating each migration as a bespoke heroic project, and build the machinery that makes the safe way the easy way — linters that catch the outage before review, harnesses that embody posts 2–5 so nobody re-implements them, and automation that watches the fleet so humans watch the exceptions.*

This post closes the series by scaling it: from the migration you run to the hundreds you'll approve, with the platform-engineering lens of [Platform Engineering](/blog/series/platform-engineering/) applied to schema change.

## Linters: the taxonomy, enforced mechanically

Post 1's failure taxonomy and post 2's fine print are knowable in advance — which means they're lintable. A **migration linter** sits in CI and reads every proposed migration against the rules: no full-table rewrites disguised as column adds (engine-version-aware, because "safe" varies by version); no plain index builds where concurrent variants exist; constraints must arrive declare-then-validate; every migration sets the lock timeout; no data-proportional statements outside the backfill harness; renames and drops only through the expand/contract sequence (the linter literally refuses a bare `RENAME`). The design points that make linters stick: **block with an explanation and the safe alternative** (the error message is the teaching moment — "use ADD COLUMN + backfill + contract; here's the template"), **allow escape hatches with sign-off** (an `allow-unsafe` annotation requiring a named approver keeps the linter honest about its own incompleteness), and **grow the ruleset from incidents** — like golden invoices (bill-07), every migration incident becomes a rule that prevents its recurrence, which is how the linter becomes the organization's accumulated scar tissue, mechanized.

## Harnesses: the patterns as product

Posts 3–5 described machinery — batched throttled backfills, shadow-read comparators, ramped flags — that no one should build twice. The **migration harness** packages them: declare a backfill as *table, transform, batch target, throttle signals* and the harness supplies keyset walking, adaptive sizing, checkpointing, idempotent application, the progress dashboard, and the automatic backoff loop; declare a verification as *source, target, canonicalizer* and get sampled shadow reads, noise filtering, diff queues, and the agreement-rate metric; declare a cutover as *flag, cohorts, ramp schedule, canary metrics* and get the staged exposure with automatic halt-on-regression. The capability payoff is the same compounding the platform series promised: the *second* migration through the harness costs a fraction of the first, the safety properties stop depending on which team is migrating — and the harness becomes where fixes land once for everyone (a smarter throttle signal ships to every future backfill).

## The fleet view: migrations as operations

At fleet scale — many services, many databases, migrations weekly — the remaining work is operational architecture. A **migration control plane** tracks every migration's state (proposed, linted, expanding, backfilling at N%, verifying at X-nines agreement, ramping, awaiting contract) across the fleet, which converts tribal status into queryable fact and makes the stalled-migration problem (zdm-06's warning) *visible* as aging dashboards instead of forgotten branches. **Progressive automation** follows the autonomy ladder logic (entai-04, agmem-07 — the same ladder every time): routine migrations (lint-clean adds, index builds) run fully automated through the harness; standard expand/contract sequences automate the mechanics with human approval at read-cutover and contract; novel or cross-store migrations get the full human ceremony — and the boundary moves down the ladder as the harness earns trust, measured by its own incident rate. The closing symmetry with post 1: the taxonomy said migrations break things in five repeatable ways; the capability answer is that repeatable failures deserve repeatable prevention — linted, harnessed, observed — until the heroics are reserved for the migrations that genuinely are novel, which is the only place heroics ever belonged.

The takeaway: scaling migration safety means productizing it — **linters** that mechanize the failure taxonomy (teaching errors, signed escape hatches, incident-grown rules), **harnesses** that package backfill/verification/cutover as declarative machinery so safety stops depending on the team, and a **control plane** with progressive, ladder-climbing automation that keeps humans on the novel cases and dashboards on the stalls. Craft runs one migration; capability runs hundreds — and the organization that builds the capability gets the craft back for the problems that deserve it.

## Key takeaways

- **Lint the taxonomy**: engine-aware rules against rewrites-in-disguise, plain index builds, un-staged constraints, missing lock timeouts, bare renames — blocking with the safe alternative, escaping only with named sign-off, growing from incidents.
- **Harness the patterns**: declarative backfills (walk/size/checkpoint/throttle supplied), verification (shadow reads + diff queues + agreement metric), cutover (ramps + canary halts) — built once, compounding every migration after.
- **Operate the fleet**: a control plane making every migration's state queryable (stalls become visible aging, not forgotten branches).
- **Automate up the ladder**: routine fully automated → standard with human gates at cutover/contract → novel with full ceremony — the boundary descending as the harness's own incident rate earns it.
- The series' close: repeatable failures deserve repeatable prevention; save the heroics for the genuinely novel.

## Further reading

- [Finite-state machine — the model a migration control plane tracks](https://en.wikipedia.org/wiki/Finite-state_machine)
- [Lint (software) — mechanized enforcement of known-dangerous patterns](https://en.wikipedia.org/wiki/Lint_(software))
