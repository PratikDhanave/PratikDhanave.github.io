<!-- Markdown version for AI agents and readers. Canonical: https://pratikdhanave.com/blog/posts/bill-06-entitlements.html -->

# Entitlements — Decoupling What Customers Can Do from What They Pay

*Scattered through most SaaS codebases is the same bug factory: `if plan == "pro"` checks guarding features. They work until the first pricing change, when "pro" splits into three plans, grandfathered customers keep old capabilities, sales grants an exception, and a trial needs temporary access — and suddenly product code is re-implementing billing logic badly. Entitlements are the missing layer: a dedicated system answering "may this customer do X?" so that product code never asks about plans at all.*

Post [4](/blog/posts/bill-04-the-subscription-state-machine.html) built the subscription; this post builds the layer between it and the product — small in code, outsized in how much future pain it prevents.

## The core move: capabilities, not plans

The design has three parts, and the discipline is keeping them separate:

- **Features** — named capabilities the product checks: `api.access`, `exports.scheduled`, `seats.limit`, `tokens.monthly_quota`. Features come in kinds: **boolean** (may/may not), **limit** (numeric ceiling — seats, requests/minute), and **quota** (consumable allowance per period — the kind that meets metering below).
- **Grants** — statements that an account holds a feature, with a value, a source, and a validity window. Sources matter: a grant may come from a *plan* (the common case), a *trial*, a *sales exception*, a *promotion*, or an *add-on* purchase. Modeling the source is what makes exceptions auditable instead of mysterious.
- **Resolution** — the answer to "what does this account hold right now?": merge all active grants (plan + add-ons + exceptions), resolve conflicts by a declared rule (typically most-generous-wins per feature), and expose the result behind one check: `entitled(account, feature)`.

Plans then become *bundles of grants* — a mapping owned by the pricing catalog (post 2), versioned like everything else there. When pricing changes, the bundle mapping changes; product code, which only ever asked about features, doesn't notice. That indirection is the entire point: pricing can now be re-packaged freely — the business's favorite activity — without a product deploy.

## The runtime: fast, cached, and fail-deliberate

Entitlement checks sit on hot paths — sometimes per-request — so the resolution above can't be a five-table join at runtime. The standard shape: resolve *on change* (subscription transitions, grant edits trigger re-resolution), cache the flattened result (account → feature-values) close to the product, and propagate changes via events with seconds-not-hours staleness budgets. Two policies need deciding, not defaulting: **failure mode** — when the entitlement service is unreachable, failing *closed* protects revenue and failing *open* protects experience, and the right answer differs per feature (fail open on a UI nicety, closed on expensive API access); and **grace semantics** — post 4's past-due state typically degrades entitlements gradually (warn, then limit, then suspend) rather than cliff-edge, and that ladder is grant logic, not scattered ifs.

Quota features add the loop with metering (post 3): the meter counts consumption; entitlements hold the allowance; enforcement compares the two — with the streaming meter's near-real-time totals, since quota enforcement is exactly the product surface approximate-but-fast was built for. The invoice still bills from batch truth; the quota gate just needs to be roughly right *now*.

## What good entitlements buy later

The payoffs stack up quietly. **Experimentation**: packaging tests (feature X in plan A vs B) become grant-bundle changes with cohorts, no code. **Sales flexibility**: exceptions are explicit grants with sources, owners, and expiry — visible, auditable, revocable — instead of folklore. **Trials and previews**: time-boxed grants, same machinery. **Migrations**: moving customers between price versions (post 2) or plan structures is a grant-mapping exercise with a diffable before/after per account. **Support**: "why can't this customer export?" is answered by reading their resolved grants, not by archaeology across plan checks. And one boundary note: entitlements answer *commercial* permission (did they pay for it?), not *security* permission (are they allowed by role?) — keep it beside, not inside, your authorization system; conflating them couples billing changes to security reviews.

The takeaway: entitlements replace `if plan == "pro"` with a layer of **features (boolean / limit / quota), grants (valued, sourced, time-boxed), and resolution** behind a single fast check — with plans demoted to versioned bundles of grants owned by the catalog. Resolve on change, cache flat, pick failure modes and past-due degradation ladders per feature, and let quotas enforce against the streaming meter while invoices bill from batch truth. The reward is the decoupling itself: pricing re-packages freely, exceptions become auditable, and product code never learns what a plan is.

## Key takeaways

- The pattern: **features** (boolean, limit, quota) checked by product code; **grants** with value, *source* (plan, trial, exception, add-on), and validity; **resolution** merging grants by declared conflict rules into one `entitled()` check.
- **Plans are bundles of grants**, versioned in the catalog — re-packaging pricing stops requiring product deploys.
- Runtime shape: resolve on change, cache the flattened result, propagate by events; decide **fail-open vs fail-closed per feature** and encode past-due degradation as a grant ladder.
- **Quotas** = entitlement allowance + streaming-meter consumption at the gate (fast, approximate), batch truth on the invoice — the two-meter pattern paying off again.
- Entitlements are **commercial** permission, adjacent to but distinct from security authorization — keep the systems separate.

## Further reading

- [Access control — the enforcement family entitlements belong to](https://en.wikipedia.org/wiki/Access_control)
- [Feature toggle — the runtime-flag machinery entitlements resemble and exceed](https://en.wikipedia.org/wiki/Feature_toggle)

---

Author: Pratik Dhanave (https://pratikdhanave.com) | Published: 2026-11-10
Canonical: https://pratikdhanave.com/blog/posts/bill-06-entitlements.html
Attribution: please link the canonical URL when citing or quoting this post.
