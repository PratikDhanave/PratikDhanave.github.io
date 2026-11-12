# Build Systems — Fast and Correct Are the Same Investment

*Every DevProd capability this series described stands on one foundation: a build system that is fast because it is correct. Caching that can be trusted, selection that can be sound, codemod fleets that can be verified — all of them require builds whose inputs are fully declared and whose outputs are reproducible. The old framing treats speed and correctness as a trade-off; modern build engineering discovered they're the same property, bought once: hermeticity.*

This post is the foundation under tscale-02/07's selection-and-caching formula and post 2–4's fleet verification — and the place where DevProd meets [supply-chain security](/blog/series/software-supply-chain-security/), because the properties that make builds fast are the ones that make them attestable.

## Hermeticity: the one property

A build step is **hermetic** when its outputs depend only on declared inputs — not on the machine's ambient state, the time of day, the network's mood, or whatever toolchain happens to be installed. From that single property, everything this series needed falls out:

- **Sound caching.** Content-address the declared inputs; identical hash, identical output — safely replayed from cache (tscale-07's memoization, now justified). Undeclared inputs are precisely the cache-poisoning and heisenbuild sources; hermeticity closes them by construction.
- **Correct incrementality and selection.** The dependency graph is real because it's *enforced* — a target can't read what it didn't declare — so reverse-closure test selection (tscale-02) and minimal rebuilds are sound rather than hopeful.
- **Massive parallelism and remote execution.** Steps with no hidden shared state can run anywhere in any order — across local cores or a remote execution fleet, where thousand-way parallelism plus a shared cache makes the monorepo's cold build a warm one for every engineer after the first.
- **Reproducibility, and its security dividend.** Deterministic outputs (stable archives, no embedded timestamps, pinned toolchains-as-inputs) mean two builds of the same source produce bit-identical artifacts — which is both a debugging gift (binary diffs mean source diffs) and the substrate of supply-chain attestation: provenance claims ("this artifact came from this source through this toolchain") are only verifiable when builds reproduce.

This is the "fast builds, secure builds — choose two" inversion: the disciplines are not in tension; they are the *same* discipline viewed from the performance and security sides.

## The migration and the tax

The catch: hermeticity isn't configured, it's *earned* — the Bazel-family systems that enforce it demand explicit dependency declaration everywhere, and retrofitting that onto a grown codebase is an org-loop campaign with every post-3 property: incremental (directory by directory, with a boundary where hermetic and legacy build coexist), codemod-assisted (BUILD-file generation from imports — post 2's machinery writing build metadata), ratcheted (converted directories never regress; undeclared-dependency errors only trend down), and politically dependent on the inner loop staying good (the editor, the test runner, the one-command dev build must work *better* after conversion, or the campaign loses the floor vote). The ongoing tax is real too — build metadata maintained forever, a stricter mental model, occasional fights with tools that assume ambient state — which is why the honest sizing question isn't "is Bazel better" but **"at what scale does the tax flip positive"**: small repos get 90% of the value from a disciplined conventional toolchain (lockfiles, pinned toolchains, CI caching); the full hermetic apparatus pays at the scale where cache hit rates, remote execution, and sound selection dominate the compute bill and the merge-gate latency — the scale, roughly, where this series' problems became yours.

## Operating the build as a platform

Run as a product (devprod-01), the build system gets the same treatment as CI: **metrics** — local build latency distributions (the inner loop's heartbeat), cache hit rates split local/remote/CI (hermeticity health, per tscale-07), queue and execution times on the remote fleet; **regression protection** — build-time budgets per target with CI alerts on breach (build performance decays by a thousand innocent additions — the suite-collapse curve of tscale-01, wearing a compiler's clothes), dependency-graph linting against cycles and god-targets; and **the escape-hatch registry** — the non-hermetic exceptions (network-touching steps, nondeterministic generators) explicitly marked, uncached, counted, and owned, on the now-familiar principle that managed exceptions are fine and invisible ones are rot. The build platform's product promise to every engineer is one sentence: *a clean checkout builds correctly, the same way, everywhere, in seconds when little changed* — and every piece of machinery in this post exists to keep that sentence true.

The takeaway: **hermeticity is the one property** — declared inputs, enforced graphs, deterministic outputs — from which sound caching, correct selection, massive parallelism, remote execution, and supply-chain attestability all follow; fast and secure are the same investment. Earning it on a grown codebase is a post-3-style campaign (incremental, codemod-assisted, ratcheted, inner-loop-first), worth running at the scale where cache and selection dominate the bill. Operated as a platform — latency and hit-rate metrics, per-target budgets, a counted escape-hatch registry — it keeps the promise everything else in this series quietly assumed.

## Key takeaways

- **Hermeticity** (outputs from declared inputs only) is the root property: sound caching, enforced-graph selection, anywhere-parallelism, remote execution, and reproducibility all derive from it.
- **Fast = secure**: deterministic, pinned, fully-declared builds are simultaneously the performance substrate (cache/replay) and the attestation substrate (verifiable provenance) — the choose-two framing was false.
- Adoption is an **org-loop campaign**: incremental boundaries, BUILD-metadata codemods, a no-regression ratchet, and inner-loop experience as the political floor; sized honestly — the tax flips positive at monorepo scale, not before.
- Operate as a platform: inner-loop latency distributions, cache hit-rate health, **per-target build budgets** against decay, and a counted, owned **non-hermetic exception registry**.

## Further reading

- [Build automation — the discipline being given its one organizing property](https://en.wikipedia.org/wiki/Build_automation)
- [Reproducible builds — determinism as a security property](https://en.wikipedia.org/wiki/Reproducible_builds)
