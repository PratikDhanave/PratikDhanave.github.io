<!-- Markdown version for AI agents and readers. Canonical: https://pratikdhanave.com/blog/posts/devprod-06-paved-roads.html -->

# Paved Roads — Turning Tools into a Platform People Choose

*A pile of excellent tools is not a developer platform, any more than a pile of excellent services is a product. The organizations that get compounding returns from DevProd all converge on the same packaging: the paved road — a supported, integrated, measurably-better default path through the entire development lifecycle, adopted because it wins rather than because it's mandated. This closing post is the assembly: how the series' pieces become a platform, how adoption actually happens, and how to avoid the paved road's own failure modes.*

The [Platform Engineering](/blog/series/platform-engineering/) series made this argument for runtime infrastructure; this post makes it for development-time — and closes the series where post 1 began: tooling as a product with users.

## What a paved road actually is

The paved road is a **coherent default**, not a mandate: for each lifecycle stage — scaffold, build, test, review, land, release — there is one supported path, integrated end-to-end, and teams may leave it, accepting that off-road means self-support. Its components, assembled from this series and its siblings: scaffolding that generates services already *on* the road (build files per post 5, CI per tscale, seed specs per tscale-06, observability and deploy per the platform series — the golden path's first mile is a generator, because defaults adopted at birth never need migrating); the inner-loop toolchain (one-command build/test/run, editor integration — post 3's lesson that the IDE experience is the daily referendum on the platform); the outer-loop machinery (selection, caching, merge queues — tscale-02/07); and the org-loop services (codemod fleets, upgrades-as-a-service, typing ratchets — posts 2–4) that quietly maintain everything on the road. The economic logic is standardization's: every team on the road multiplies the leverage of every road improvement, and every off-road team pays full price for their divergence *and* dilutes the platform's returns.

## Adoption: won, not decreed

The paved road's defining constraint — adoption by choice — is also its quality mechanism, and it has craft: **be better on day one for the common case** (the road must beat the status quo for a median team's median week, measured, or the platform is a mandate wearing a smile); **migrate by service, not by edict** (the DevProd team moves teams onto the road the way post 4 moves versions — doing the toil centrally, sharding the residue — because "adopt our platform" as a ticket on *your* backlog is how platforms die); **support is the product's price** (an on-road team with a problem gets platform-team help; this is both the deal that justifies standardization and the feedback channel that keeps the road honest — support load *is* the platform's bug tracker); and **measure adoption as the north star** (percent of services on-road per lifecycle stage, trend over time, exits analyzed like churn — devprod-01's measurement discipline, aimed at the platform itself; a team leaving the road is a product review, not a compliance incident).

## The failure modes, named

Paved roads fail in characteristic ways worth engineering against: **the road that rots** — the platform team ships the road then moves on; defaults age; by year three the road is the slow path and adoption inverts (the cure is the same product stance throughout: roads have roadmaps, deprecations, upgrades — posts 4–5's machinery pointed at the platform's own stack); **the road that forbids** — standardization hardening into prohibition, where off-road exploration is punished rather than priced, and the platform calcifies exactly where the org needed to learn (the cure: explicit off-road provisions — you may leave, you self-support, and the platform team *studies* successful exits as R&D, because today's off-road hack is sometimes next year's road); and **the road nobody asked for** — platform teams building for an imagined median while real teams route around them (the cure is the embedded feedback the support channel provides, plus the humility metric: if the road's own builders don't use it daily, nobody else will). Underneath all three, the closing principle of the series: **developer platforms compound or decay — there is no steady state**. Each investment either feeds the loop (better road → more adoption → more leverage per improvement → better road) or the loop runs backward. The organizations that treat engineer-time as the scarcest resource — and staff its multiplication as a product, with the measurement, campaigns, and machinery this series described — are the ones for whom the codebase stays an asset instead of becoming the mortgage.

The takeaway: the paved road packages the series into a platform — **scaffolded-on by default, integrated across the lifecycle, maintained by the org-loop services** — and wins by product craft: measurably better for the median week, migration done as a service, support as both price and feedback, adoption as the north star with exits analyzed like churn. Engineer against the three failure modes (rot, prohibition, irrelevance) with roadmaps, priced off-road freedom, and dogfooding — because developer platforms compound or decay, and the whole discipline of DevProd is choosing, deliberately and measurably, to compound.

## Key takeaways

- A paved road is a **coherent, supported default** — scaffold/build/test/land/release integrated — not a mandate; off-road is allowed and priced (self-support).
- **Birth beats migration**: scaffolding that generates services already on-road is the cheapest adoption there is; the IDE and inner loop are the daily referendum.
- Adoption is product craft: measurably better for the **median team's median week**, migrations performed *as a service*, support as the feedback channel, **on-road percentage as north star** with exits studied like churn.
- The failure modes: **rot** (roads need roadmaps and their own upgrade service), **prohibition** (price divergence, don't punish it — successful exits are R&D), **irrelevance** (dogfooding as the humility check).
- The series' close: **compound or decay** — engineer-time multiplication is a product, and it's staffed or it's fiction.

## Further reading

- [DevOps — the adjacent movement whose lessons paved roads industrialize](https://en.wikipedia.org/wiki/DevOps)
- [Standardization — the economics underneath the road](https://en.wikipedia.org/wiki/Standardization)

---

Author: Pratik Dhanave (https://pratikdhanave.com) | Published: 2026-11-04
Canonical: https://pratikdhanave.com/blog/posts/devprod-06-paved-roads.html
Attribution: please link the canonical URL when citing or quoting this post.
