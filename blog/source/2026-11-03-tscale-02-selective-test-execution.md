# Selective Test Execution — Running Only the Tests a Change Can Break

*The single highest-leverage move against suite collapse is refusing the premise: a change touching one module does not need the whole suite — it needs the tests that could plausibly fail because of it. Selecting that subset correctly, from dependency structure rather than hope, is how 50-million-line codebases keep CI in minutes. The engineering is in the word "correctly": an over-selective system merges breakage; an under-selective one buys nothing.*

Post [1](/blog/posts/tscale-01-why-test-suites-collapse.html) priced the all-tests-always model; this post is its replacement — the technique at the heart of every monorepo-scale CI system.

## Selection by dependency graph

The sound foundation is reachability: a change can only break tests that **transitively depend** on what changed. The implementation ladder, in increasing precision and cost:

- **Build-graph selection.** Where a build system with explicit dependency declarations exists (the Bazel-family world), the graph is already there: compute the reverse transitive closure of changed targets; run the tests inside it. Sound by construction (modulo the escapes below), fast to compute, and the strongest single argument for graph-based build systems at scale.
- **Language-level dependency extraction.** Without declared graphs, derive them: import analysis, module resolution, package manifests. Coarser (file- or module-granular) and language-specific, but serviceable — most changes in a large codebase touch leaves, and even coarse reachability prunes the vast majority of the suite.
- **Coverage-based selection.** Record, per test, which files (or finer, lines) it actually executed; select tests whose recorded footprint intersects the diff. More precise than static graphs for sprawling integration tests — and more fragile: coverage maps go stale between recordings, so they need continuous refresh and a staleness policy. In practice the strong systems *combine* static reachability (sound skeleton) with coverage data (precision trim).

The granularity dial matters as much as the method: target-level selection (run the test *target*) is robust; file-level is tighter; individual-test-level selection squeezes most but amplifies every mapping error. Most large systems settle on target granularity with sharding (post 7) absorbing the rest.

## The escapes: where the graph lies

Selection's correctness depends on the dependency graph being the whole truth, and every real codebase has edges the graph can't see: **runtime wiring** — reflection, dependency injection by string, dynamic imports, plugin registries; **out-of-band contracts** — two services sharing a database schema, a queue topic, an API shape (the graph sees no edge; production will); **global resources** — config files, feature flags, environment definitions, where a one-line change genuinely affects everything; and **the build system itself** — changes to toolchains, compilers, or CI config. The disciplines that keep selection safe anyway: **over-select on fear** — files and directories known to have invisible edges carry explicit "affects everything" (or "affects these") annotations, trading efficiency for soundness exactly where the graph is blind; **the safety net run** — selection gates merges, but the *full* suite still runs post-merge (or on a rolling batch cadence); a full-run failure that selection missed is a **selection bug**, triaged like one: find the invisible edge, add it to the graph or the annotations; and **measure escape rate** — missed-breakage per thousand merges is the system's integrity metric, and its trend tells you whether the graph is keeping up with the codebase's dynamism.

## Selection as product

At scale, selection graduates from script to service: it computes subsets in seconds even for huge graphs (precomputed reverse closures, incremental updates), explains itself ("your change selected 1,842 of 194,000 tests; here's the path from your diff to this test" — trust requires traceability, because the first unexplained miss converts engineers back to run-everything superstition), and feeds the portfolio economics of post 1 (selection data *is* per-test relevance data: a test never selected by a year of changes is prima facie portfolio-review material). Combined with post 7's caching — don't rerun tests whose inputs are bit-identical — the two techniques compose into the real monorepo formula: **select what could break, skip what provably didn't change, shard the remainder** — minutes-level CI at any codebase size, bought with graph hygiene rather than hardware.

The takeaway: selective execution runs the **reverse transitive closure** of a change — via build graphs (soundest), extracted dependencies, or coverage maps (precise but staleness-prone), usually at target granularity — while honestly engineering the escapes: annotated invisible edges, a post-merge full-suite safety net whose misses are triaged as selection bugs, and a measured escape rate. Operated as an explainable service and composed with input-hash caching, it's the difference between CI that scales with change size and CI that scales with codebase size — the central economic victory of post 1's reframe.

## Key takeaways

- Foundation: **a change can only break what transitively depends on it** — build-graph reverse closures (soundest), import/module extraction, or coverage intersections (fresh-or-wrong), typically at target granularity.
- The graph always lies somewhere: **runtime wiring, shared-schema/queue/API contracts, global config, the toolchain** — cover with "affects-everything" annotations, over-selecting where blind.
- **Full suite still runs post-merge**: its misses are *selection bugs* with root-cause triage (find the invisible edge); **escape rate per 1k merges** is the integrity metric.
- Run selection as an **explainable service** (seconds, with diff→test paths shown — trust requires traceability), and mine its data for portfolio review (never-selected tests).
- The monorepo formula: **select + cache + shard** — CI scaling with change size, not codebase size.

## Further reading

- [Regression testing — the practice selection makes affordable](https://en.wikipedia.org/wiki/Regression_testing)
- [Dependency graph — the structure selection computes over](https://en.wikipedia.org/wiki/Dependency_graph)
