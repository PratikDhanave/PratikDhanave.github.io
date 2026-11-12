<!-- Markdown version for AI agents and readers. Canonical: https://pratikdhanave.com/blog/posts/apiver-04-specs-and-sdks.html -->

# Specs and SDKs — Making the Contract Machine-Readable and the Clients Generated

*An API that exists as code, a spec document, hand-written SDKs in six languages, and documentation pages is an API that exists in four slowly diverging copies. The evolution-era answer is to pick one source of truth — the machine-readable spec — and generate or verify everything else from it, so a change made once propagates everywhere or fails loudly. This post is the spec-first pipeline: what it takes, what it buys, and where generated SDKs still need human hands.*

Post [3](/blog/posts/apiver-03-compatibility-layers.html) made many versions servable; this post makes them *describable* — because every version you serve is a contract someone needs in their language, and hand-maintaining N languages × M versions is how spec-reality drift (post 1) becomes a support department.

## Spec as source of truth, enforced

Declaring OpenAPI (or your IDL of choice) the source of truth is a sentence; enforcing it is a pipeline. The components that make it real:

- **The spec is complete, not aspirational.** Every endpoint, every field with nullability and constraints, every error shape, every enum with its extensibility declared (post 1's unknown-variant clause, encoded). Partial specs generate partial truths — worse than none, because they carry authority.
- **Conformance is tested both directions.** Responses from the real implementation validate against the spec in CI (contract tests over the golden scenarios of post 3 — the same fixtures, double duty); and the spec can't merge without the implementation (or gate) that honors it. Drift becomes a build failure instead of a support ticket.
- **Versioning applies to the spec too.** Each dated version (post 2) has its spec — mechanically derived by running the *spec* through the same gate definitions where feasible, or maintained as dated snapshots verified by the per-version conformance suites. The spec archive is the documented history the transform chain executes.
- **Breaking-change detection runs on diffs.** Spec-diff tooling classifies every proposed change (additive / breaking / ambiguous) in CI — post 1's operational definition, mechanized — so a "safe" PR that removes a field's nullability gets flagged by a machine before a human reviewer has to catch it. This is the API-evolution linter, sibling to zdm-07's migration linter, grown the same way: every breakage incident becomes a diff rule.

## Generated SDKs: the leverage and the limits

With a trustworthy spec, SDK generation turns N-language maintenance from authorship into review. The honest accounting: **what generation does well** — types and models (strict-reader clients, post 1, with the tolerant-reader escape hatches generated in: unknown-field retention, open enum handling), request builders, auth plumbing, pagination iterators, retry-and-idempotency scaffolding — the 80% that is mechanical and error-prone by hand. **What still needs hands** — idiomatic surface (a generated Go client that feels like Java is a generated client nobody enjoys; per-language templates carry the idiom), convenience layers (the three-call workflow every integrator performs deserves a helper no spec describes), and the handful of endpoints whose semantics resist schema description (file streams, webhooks setup — hand-written islands in generated seas, clearly fenced so regeneration doesn't flatten them). **And what generation changes about process** — SDK releases become *pipeline runs* keyed to spec versions: a dated API version ships with its SDKs the same day, SDK changelogs derive from spec diffs, and the version a client library targets is explicit in its own metadata (completing post 2's observability loop from the client side). The same spec feeds the rest of the surface — reference docs, interactive explorers, mock servers for integrator testing ([Testing at Scale](/blog/series/testing-at-scale/)'s sandbox chapter benefits directly), and the request validators at your own edge, which closes the loop: the artifact that documents the contract is the artifact that enforces it.

The takeaway: evolution at SDK scale requires **one machine-readable source of truth** — a complete spec, conformance-tested against the implementation both directions, versioned alongside the transform chain, with breaking-change detection running on every diff. From it, generate the mechanical 80% of every SDK (types, builders, pagination, retries — with tolerant-reader behaviors built in), keep humans on idiom and convenience, fence the hand-written islands, and ship SDKs as pipeline runs synchronized with dated versions. One change, one place, everywhere at once — or a loud failure telling you why not.

## Key takeaways

- Spec-as-truth is a **pipeline, not a declaration**: complete specs, bidirectional conformance tests in CI (reusing post 3's golden fixtures), dated spec snapshots per version, and **spec-diff breaking-change detection** as the evolution linter.
- Generation owns the mechanical 80%: types with **tolerant-reader escape hatches** (unknown fields, open enums), builders, pagination, retry/idempotency scaffolds — humans own idiom, convenience workflows, and fenced hand-written islands.
- SDK releases become **pipeline runs keyed to spec versions** — same-day SDKs for each dated version, changelogs from diffs, client-side version metadata closing the telemetry loop.
- The same spec feeds docs, explorers, mocks, and your own edge validators — the documenting artifact *is* the enforcing artifact.

## Further reading

- [OpenAPI Specification — the de facto contract language](https://en.wikipedia.org/wiki/OpenAPI_Specification)
- [Interface description language — the general idea of machine-readable contracts](https://en.wikipedia.org/wiki/Interface_description_language)

---

Author: Pratik Dhanave (https://pratikdhanave.com) | Published: 2026-11-10
Canonical: https://pratikdhanave.com/blog/posts/apiver-04-specs-and-sdks.html
Attribution: please link the canonical URL when citing or quoting this post.
