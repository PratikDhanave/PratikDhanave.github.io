# Gradual Typing Migrations — Retrofitting Types onto a Living Codebase

*The great typing migrations — millions of dynamic-language lines brought under TypeScript, or type checkers built for Ruby and Python — are the canonical org-loop projects: multi-year, codebase-wide, impossible to pause the business for, and transformative when they land. They're worth studying even if you never run one, because they exercise every DevProd muscle at once: incremental adoption machinery, codemod fleets, ratchets that prevent backsliding, and the political craft of keeping a thousand engineers on board for years.*

Post [2](/blog/posts/devprod-02-codemods-at-scale.html) built the tool; this post is the campaign — the worked example of changing a fundamental property of a codebase that refuses to stop moving (the same no-pause constraint that shaped [zero-downtime migrations](/blog/series/zero-downtime-data-migrations/), transposed from data to code).

## Why gradual is the only viable shape

The all-at-once version fails on arithmetic: a millions-of-lines conversion as a project means years of divergence from a codebase evolving underneath (zdm's moving-table problem at repo scale), an unreviewable landing, and zero value until the end. **Gradual typing** inverts the value curve: the system is permanently in a mixed state — typed and untyped code interoperating — where every increment of typing delivers its benefit immediately and nothing waits for completion. The design decisions that define the campaign:

- **Strictness as a per-module dial.** Gradual systems offer levels (untyped → loosely typed → strict); the migration's state is a *map* of the codebase against the dial. The campaign is the map turning strict, module by module.
- **The boundary discipline.** The mixed state lives or dies at typed-untyped borders: untyped values flowing into typed code are where the guarantees leak (the `any`-shaped hole, the dynamic escape hatch). The practical rules: boundaries are *explicit* (interface files, typed wrappers around untyped dependencies), escape hatches are *counted* (every `any`, every cast, every suppression is measurable debt — the metric below), and new boundaries are *strict by default*.
- **Sequencing by leverage.** Type the trunk first: core libraries, shared utilities, the modules everything imports — each typed foundation module improves checking for every dependent, so the campaign's early wins compound. Leaf code follows by codemod + inference; the gnarly dynamic metaprogramming corners come last or never (an honest 97% beats a stalled 100% — declare the exceptions and move on).

## The machinery: infer, ratchet, enforce

The campaign runs on three mechanisms. **Inference at scale** — post 2's type-informed codemods write the first draft: tooling that infers annotations from usage, call-graph analysis, and runtime trace collection (observed types harvested from production or test runs — an underused trick that converts dynamic behavior into draft signatures), landing ownership-sharded PR fleets of mostly-correct annotations that humans correct rather than compose. **The ratchet** — the campaign's load-bearing invariant: *typedness only increases*. CI enforces per-module floors: a module at strict never regresses; files can't add new suppressions without sign-off; the error count against the next strictness level only goes down (tscale's merge gate carrying the campaign's physics). Without the ratchet, migration and backsliding race forever; with it, every merge is campaign progress by default. **The dashboard** — percent-typed by module and team, escape-hatch counts trending, type-error-caught-bugs surfaced (the value evidence), because a multi-year campaign sustains itself on visible motion (devprod-01's measurement discipline as campaign morale).

## The political craft

The technical plan fails without the adoption campaign beside it: **make typed strictly nicer** — the editor experience (autocomplete, refactors, inline errors) is the daily bribe that recruits engineers better than any mandate; invest in IDE integration *before* pushing strictness; **centralize the toil** — the DevProd team types the hard shared modules, builds the wrappers for untyped dependencies, and runs the inference fleets; product teams mostly *receive* typedness and fix the interesting residue (post 4's upgrades-as-a-service logic, previewed); **never block the roadmap** — strictness deadlines that collide with launches lose, publicly, and cost the campaign its mandate; the ratchet's only-forward design means the campaign survives slow quarters without losing ground; and **declare victory honestly** — define done as "strict everywhere but the declared exception list, new code strict by birthright," celebrate it, and hand the ratchet to maintenance. Campaigns that can't define done become background noise that outlives their champions.

The takeaway: typing migrations work only as **gradual campaigns** — a strictness map turned module by module, boundaries explicit and escape hatches counted, trunk-first sequencing for compounding leverage — run on three mechanisms: **inference-powered codemod fleets** (usage analysis, runtime traces) for the first draft, a **CI ratchet** making typedness monotonic by construction, and a **dashboard** that keeps years-long motion visible. The human half decides it: editor experience as the daily recruiter, centralized toil, roadmap deference, and an honest definition of done. Every org-loop transformation looks like this one — which is why it's the worked example.

## Key takeaways

- Gradual is structural, not timid: **mixed-state interop** delivers value per increment; all-at-once loses the race against its own codebase (zdm's moving table, transposed).
- Campaign anatomy: **strictness map** by module, **explicit boundaries** with counted escape hatches (`any`/casts/suppressions as measured debt), **trunk-first sequencing** so foundations compound.
- Machinery: **inference + runtime-trace draft annotations** landed as sharded codemod fleets; a **CI ratchet** (typedness only increases — per-module floors, sign-off suppressions); a **campaign dashboard** including caught-bug evidence.
- Political craft: editor experience recruits better than mandates, DevProd centralizes the hard toil, the roadmap is never blocked, and **done is declared** (strict-by-birthright + exception list) — then handed to maintenance.

## Further reading

- [Gradual typing — the theory that makes the mixed state sound](https://en.wikipedia.org/wiki/Gradual_typing)
- [Type system — what the campaign is retrofitting](https://en.wikipedia.org/wiki/Type_system)
