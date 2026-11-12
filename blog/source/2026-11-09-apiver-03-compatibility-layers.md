# Compatibility Layers — Serving Twenty Versions from One Implementation

*Promising account-pinned dated versions is easy; the hard part is the server that must honor all of them. The naive answers — fork the codebase per version, or thread `if version < X` through every handler — both collapse within a year. The architecture that scales is a transform pipeline: one current implementation at the core, and a chain of small, testable version-gates that translate requests forward and responses backward. This post builds it.*

Post [2](/blog/posts/apiver-02-versioning-schemes.html) chose the scheme that makes this layer mandatory; this post is the price being paid — and why it's lower than every alternative.

## The transform-chain architecture

The organizing idea: **the core implementation speaks only the latest version**. Business logic, storage, new features — all written once, against current shapes. Each dated version (post 2) contributes a **version gate**: a pair of pure transforms — one mapping an older-version *request* forward into the next version's shape, one mapping a newer-version *response* backward into the older shape. A request from an account pinned at `2025-03-01` passes forward through every gate between its date and today before reaching the core; the response runs the same chain in reverse. The properties that make this scale:

- **Each gate is small and single-purpose.** It encodes exactly one breaking change — a renamed field, a restructured object, a split endpoint — typically a few dozen lines. The complexity of serving twenty versions becomes twenty small composable functions, not one combinatorial handler.
- **Gates are pure and testable in isolation.** Shape in, shape out, no I/O: each gate gets unit tests with fixture pairs (old-shape request → expected new-shape; new-shape response → expected old-shape), and the chain as a whole gets golden tests per supported version (bill-07's pattern again: fixed scenarios, pinned expected outputs per version, diffed on change).
- **New breaking changes have a defined cost.** Shipping one means: change the core, write the gate that reconstructs the old behavior, add its tests. The cost is visible, bounded, and borne by the author of the change — post 2's "provider carries the burden," given a unit price.
- **The chain documents history.** Read the gates in order and you have the API's actual changelog, executable.

## Where transforms get hard

Pure-shape renames are the easy case; the taxonomy of harder gates is worth knowing before committing. **Semantic changes** — a field's *meaning* shifted (amounts to minor units, timezone conventions): the gate converts values, not just names, and needs the property-testing attention of any money/time code. **Information asymmetries** — the new response lacks something the old version promised: the gate must reconstruct it (compute, refetch, or synthesize a faithful default); conversely, old requests may lack data the new core requires — defaults encode what the old era implicitly assumed. This is where gates occasionally need *context* (a lookup, a secondary read), breaking the pure-function ideal — contained by keeping such gates rare, flagged, and measured. **Behavioral changes** — different status codes, altered validation strictness, pagination semantics: gates may wrap error translation and even request *replay* logic; some behavior (timing, rate limits) can't be gated at all and must be versioned by policy exception, documented as such (post 1's behavioral contract has limits). **Fan-in/fan-out changes** — one endpoint split into two, or two merged: the gate orchestrates (calls the core twice, stitches responses), the most complex species and the strongest argument for making such restructures rarely.

## Operating the chain

The layer earns its keep operationally. **Version telemetry** (post 2's invariant) now measures each *gate*: traffic per version, latency added per gate (chains of pure transforms are cheap, but measure — a context-needing gate in a hot path is a found performance bug), and error rates by version (a spike isolated to old versions means a gate regression, not a core one — a diagnostic gift). **Version-matrix testing in CI** runs the golden suites for all supported versions on every change — the mechanical guarantee behind "we still serve 2024 correctly," and the thing that makes refactoring the core safe (gates pin observable behavior per era). **And retirement reverses the chain**: when post 5's deprecation process finally ends a version, its gate is deleted — the chain shortens, the oldest fixtures retire, and the system sheds history it no longer owes. The architecture thus gives API evolution the property zdm-07 gave migrations: changes stop being heroics and become units — authored, priced, tested, and eventually retired through machinery built once.

The takeaway: serving many versions scales only through a **transform chain** — a latest-only core wrapped in per-version gates, each a small, pure, fixture-tested pair of request-forward and response-backward transforms, composed in date order. Know the hard species in advance (semantic value conversion, information asymmetries needing context, behavioral wraps, fan-in/out orchestration) and keep them rare; operate the chain with per-gate telemetry and all-version golden CI; retire versions by deleting gates. One implementation, twenty eras, every era tested — that's the machinery that makes continuous breaking change a routine instead of a reorg.

## Key takeaways

- **Core speaks latest only**; each dated version is a **gate**: request transformed forward, response transformed backward, composed in order — twenty versions as twenty small functions, not forks or scattered ifs.
- Gates are **pure, fixture-tested pairs** with per-version golden suites in CI — which is also what makes core refactoring safe (gates pin each era's observable behavior).
- The hard-gate taxonomy: **semantic value conversion**, **information asymmetry** (reconstruct or default; context-needing gates flagged and rare), **behavioral wraps** (and the honest limits — some behavior can't be gated, only excepted), **fan-in/out orchestration** (avoid by restructuring rarely).
- Operate per-gate: version traffic, added latency, error isolation (old-version-only spikes = gate bug); **retire versions by deleting gates** — the chain shortens as debts are paid.

## Further reading

- [Adapter pattern — the translation-at-the-boundary idea the gates generalize](https://en.wikipedia.org/wiki/Adapter_pattern)
- [Middleware — the request-pipeline architecture the chain lives in](https://en.wikipedia.org/wiki/Middleware)
