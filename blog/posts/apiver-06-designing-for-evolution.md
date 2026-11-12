<!-- Markdown version for AI agents and readers. Canonical: https://pratikdhanave.com/blog/posts/apiver-06-designing-for-evolution.html -->

# Designing for Evolution — APIs That Age Well

*Every mechanism in this series — versions, gates, specs, deprecations — is the cost of changing decisions already shipped. The cheapest breaking change remains the one you never need, and whether you need many or few is substantially determined at design time, by choices that cost nothing when made and compound forever after. This closing post is that discipline: the additive-evolution patterns, the robustness-principle corrections, and the design review that asks about every surface, "how will this change?"*

This post closes the series where [API Design](/blog/series/api-design/) left off — design not for the API you're shipping, but for the five years of its evolution you can't yet see.

## Additive headroom: the patterns that absorb change

Most future change can be absorbed by shapes that have room to grow, chosen when they cost nothing:

- **Objects over scalars, from day one.** A field returning a bare string or number is one requirement away from breaking; `{"amount": 500, "currency": "usd"}` was always going to beat `500`. The same for envelopes: a list endpoint returning a raw array can never gain pagination metadata without breaking; `{"data": [...]}` costs nothing and holds whatever the future needs. The asymmetry is total — wrapping later is breaking; wrapping now is free.
- **Open sets, declared open.** Enums, event types, error codes: post 1's unknown-variant clause works only if clients expect growth — so design strings-not-integers for variant sets, document them as open, and provide the catch-all semantics ("treat unknown status as pending-equivalent") that make tolerance *actionable* rather than aspirational.
- **Expansion over proliferation.** Growing responses for some callers (include related objects, add detail levels) via explicit request parameters — expand/include patterns — lets one endpoint serve evolving needs without either breaking minimalists or forking into `/charges-with-customer-details`.
- **Names that won't curdle.** The renames that plague APIs (post 3's most common gate) are mostly day-one naming debt: fields named after implementation ("stripe_token"), booleans that will need a third state (`is_active` → status enums buy the future for free), units left implicit (`timeout` vs `timeout_seconds`). The rename gate you don't ship is the naming review you did.

## The robustness principle, corrected by experience

"Be liberal in what you accept" aged badly: every quietly-tolerated malformation becomes, by Hyrum's Law, a behavior you support forever — undocumented coercions ossify into contract, and tightening them later is a breaking change you never meant to own (post 1's "tightened validation" clause). The corrected discipline: **be precise in what you accept, from the beginning** — strict validation with excellent errors is a kindness to integrators (their bugs surface in development, not production) and to your future self (no accidental contract). Where you *must* accept looseness, make it explicit and logged, so it's a measured debt rather than a silent one. Liberality survives in one place only: **your own reading of your dependencies** — as a client, be the tolerant reader post 1 demands; as a server, be the precise one.

## Evolvability as a review gate

The practices that keep all of this applied: an **evolution review** alongside design review — for each new surface, ask the five questions (What will we rename? Which sets will grow? What will become a list? What will need metadata? What's the deprecation story?) — not to predict correctly but to leave headroom where prediction is cheap; **changelog-driven humility** — review your own API's past gates and deprecations periodically, because the changes you actually shipped are the best predictor of the kinds you'll ship next (the incident-grown-ruleset pattern of zdm-07 and post 4's diff linter, applied to design taste); and **the maturity ladder for new surface** — ship new endpoints as explicitly experimental/beta (clearly marked, exempt from compatibility promises, telemetered) and promote them to stable only after real usage has found the design errors — because the cheapest place to make a breaking change is *before* the compatibility contract starts, and a deliberate beta period is how you buy that window honestly.

The takeaway: the cheapest evolution machinery is the design that needs less of it — **objects and envelopes over bare scalars and arrays, open sets declared and actionable, expansion parameters over endpoint proliferation, names reviewed against their futures** — plus the corrected robustness principle (precise acceptance with great errors; tolerance only as a client), enforced by an evolution review, informed by your own change history, and granted a deliberate beta window where breaking is still free. Versions, gates, specs, and sunsets handle the change you couldn't avoid; this post is how you avoid the rest.

## Key takeaways

- **Headroom is free at design time, breaking later**: objects over scalars, enveloped lists, open string sets with catch-all semantics, expand/include over endpoint forks, names reviewed for curdling (booleans → status enums, units explicit).
- **Invert Postel**: precise acceptance with excellent errors prevents accidental contract (silent coercions ossify via Hyrum's Law); be liberal only as a *reader* of others.
- Institutionalize it: an **evolution review** (what renames/grows/lists/metadata/deprecates?), periodic study of your own gate history as design feedback, and an honest **beta ladder** so new surface breaks freely before the contract begins.
- The series in one line: design so change is rare, version so change is possible, transform so change is cheap, spec so change propagates, deprecate so change concludes.

## Further reading

- [Robustness principle — Postel's law and the debate experience settled](https://en.wikipedia.org/wiki/Robustness_principle)
- [Extensibility — designing systems that grow without breaking](https://en.wikipedia.org/wiki/Extensibility)

---

Author: Pratik Dhanave (https://pratikdhanave.com) | Published: 2026-11-12
Canonical: https://pratikdhanave.com/blog/posts/apiver-06-designing-for-evolution.html
Attribution: please link the canonical URL when citing or quoting this post.
