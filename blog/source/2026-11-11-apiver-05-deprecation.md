# Deprecation — Retiring API Versions Without Burning Your Integrators

*Shipping a version is a product launch; retiring one is a diplomatic mission. The clients still on it are, by definition, the ones who didn't upgrade when asked — working code owned by teams with no budget for your roadmap — and behind every deprecation that went badly is an integrator who found out from an outage. Deprecation done well is a designed process: telemetry that knows who's affected, communication that reaches them, migration paths that respect their economics, and sunsets that mean what they say.*

Post [2](/blog/posts/apiver-02-versioning-schemes.html) required version observability and post [3](/blog/posts/apiver-03-compatibility-layers.html) priced keeping versions alive; this post is the other half of that ledger — how a version's life deliberately ends.

## The lifecycle, declared in advance

Deprecation goes smoothly in proportion to how little of it is improvised. The stages, each with explicit semantics published *before anyone integrates*:

- **Active** — current, recommended, fully supported.
- **Deprecated** — still fully functional (this is the clause teams violate first: deprecated must not mean degraded), but marked: no new features land here, new integrations are discouraged or blocked, and a sunset date exists. Machine-readable marking matters as much as documentation — deprecation headers on every response (with the sunset date and a migration link), SDK deprecation annotations that surface in integrators' own build tooling (post 4's pipeline carrying the message into their IDE), and changelog entries.
- **Sunset announced → warning period** — the date is fixed and communicated on a cadence (announcement, then reminders at e.g. 90/30/7 days), targeted by telemetry (below), with escalating visibility: email, dashboard banners, and — the step that actually gets attention — scheduled **brownouts**: brief, pre-announced windows where the deprecated version returns errors, converting "we'll get to it" into a staged, reversible fire drill instead of a real one.
- **Sunset** — the version stops serving, returning a clear error with a migration pointer (not a mysterious 404). Post 3's gate gets deleted; the chain shortens.

The policy question underneath: **how long must versions live?** Public-API answers run years, not quarters (post 2's warning), and the honest commitment is a *minimum support window* declared at version release — integrators can plan against "every version lives ≥24 months from deprecation" in a way they can't against vibes.

## Telemetry-driven, economically honest

Generic deprecation emails to an integrator mailing list retire nothing. The process that works is **account-level**: post 2's observability means you know exactly which accounts call the deprecated version, which endpoints, at what volume — so communication is targeted ("your integration made 1.2M calls to v2024-03 last week; here are the three endpoints you use and what changes"), progress is measurable (accounts-remaining curves per deprecated version — the deprecation burndown that tells you whether the date is achievable), and the long tail is visible early (the handful of high-volume holdouts who'll need white-glove help are identifiable in month one, not week minus-one). Economic honesty shapes the migration path itself: **the provider absorbs what it can** — migration guides written against actual observed usage (not the full change surface), automated migration tooling where mechanical (post 4's spec diffs can generate the first draft of "what changes for you"), compatibility shims for the highest-friction changes, and sandbox environments where integrators test the new version against their traffic shapes ([Testing at Scale](/blog/series/testing-at-scale/)'s machinery, offered outward). The asymmetry argument from post 2 applies to endings too: you are one team retiring a version; they are a thousand teams being made to work. Every hour of provider-side tooling is a thousand hours of integrator effort somewhere.

And the hardest honesty: **sometimes the sunset must slip, and policy should say when**. A fixed framework — slip only for named systemic blockers, announced once, never silently — preserves the credibility that makes future sunsets believable. A provider whose dates always slide trains its ecosystem to ignore them, which is how ten-year zombie versions are made.

The takeaway: deprecation is a designed lifecycle — **deprecated-but-fully-functional, machine-readably marked** (headers, SDK annotations), sunset dates with declared minimum support windows, warning cadences escalating through **pre-announced brownouts**, and endings that error clearly and delete gates. Run it on account-level telemetry (targeted comms, burndown curves, early sight of the long tail) and economic honesty (guides from observed usage, migration tooling, shims, sandboxes — provider hours against ecosystem thousands). Keep sunset credibility with an explicit slip policy — because the alternative to deprecation done well isn't deprecation avoided; it's zombie versions forever.

## Key takeaways

- Lifecycle with published semantics: **deprecated ≠ degraded**; machine-readable marking (response headers with sunset dates, SDK annotations reaching integrators' builds); declared **minimum support windows** at release.
- **Brownouts work**: brief, pre-announced error windows convert procrastination into staged rehearsal — the single most effective step between email and outage.
- Run on telemetry: account-level usage → targeted comms, **burndown curves** per version, early identification of high-volume holdouts needing white-glove paths.
- Absorb the asymmetry: migration guides scoped to *observed* usage, diff-generated change summaries, shims for high-friction changes, sandboxes for testing — provider effort multiplies across the ecosystem.
- Protect date credibility with an explicit, rarely-used **slip policy** — sliding sunsets train integrators to ignore you, and that's how zombies are born.

## Further reading

- [Deprecation — the practice of marked, scheduled retirement](https://en.wikipedia.org/wiki/Deprecation)
- [Product lifecycle — the commercial frame a version's life follows](https://en.wikipedia.org/wiki/Product_lifecycle)
