<!-- Markdown version for AI agents and readers. Canonical: https://pratikdhanave.com/blog/posts/apiver-01-why-apis-rot.html -->

# Why APIs Rot — The Compatibility Contract You Signed Without Reading

*The day an API gets its first external integration, its shape stops being yours. Every field name, every status code, every undocumented quirk becomes load-bearing for code you can't see, written by teams you can't reach, deployed on schedules you don't control. API evolution is the discipline of changing a thing that thousands of strangers depend on — and it begins with understanding exactly what you promised, because most breakage comes from changes the provider genuinely believed were safe.*

The [API Design](/blog/series/api-design/) series covers designing the interface; this short series covers *changing* it — the discipline Stripe-class API companies treat as existential and most teams discover during their first integration-breaking incident.

## What "breaking" actually means

The naive definition — "changing a documented behavior" — is both too narrow and too wide. The operational definition: **a change is breaking if any plausible existing client stops working**. That framing forces the uncomfortable inventory:

- **Obviously breaking**: removing or renaming fields, changing types, tightening request validation (what was accepted yesterday is rejected today), changing status codes or error shapes, altering authentication.
- **Subtly breaking**: reordering enum-like values a client switch-statements over; changing a field from always-present to sometimes-null; changing default sort order; *expanding* a response with new fields (safe — unless a client deserializes strictly); changing rate limits or latency characteristics (behavioral contracts are still contracts); fixing a bug clients built workarounds around — the workaround now double-corrects.
- **Hyrum's Law territory**: with enough users, every observable behavior becomes depended-upon — ID formats ("it's always 24 chars"), error message strings (parsed by someone, guaranteed), timestamp precision, the stability of pagination cursors across deploys. The provider's documentation describes the contract they *meant* to offer; the clients' code defines the one that *exists*.

The asymmetry that makes this hard: providers see their API as a surface they maintain; integrators see it as ground they built on. Both are right, and evolution discipline is the negotiation between them.

## The two consumption styles that split every decision

Every versioning decision downstream (posts 2–6) turns on a fact about clients that providers chronically forget: clients consume APIs in two styles with opposite failure modes. **Tolerant readers** — parse what they need, ignore the rest — are safe against additive change and silently wrong when semantics shift under unchanged shapes. **Strict readers** — validate schemas, reject unknowns, generate types from specs — break loudly on additions but catch semantic drift early. A provider's compatibility policy must declare which style it supports: the near-universal convention — **additive changes are non-breaking** (new fields, new endpoints, new enum values may appear at any time) — is really a demand that clients be tolerant readers, and it must be *stated*, because strict-reader clients that schema-validate will break on your "safe" addition and file the incident against you. The sleeper in that convention is **new enum values**: a client exhaustively switching over `status` meets a value it never imagined, and the tolerant-reader rule extends to "handle unknown variants" — the single most violated clause in the implied contract.

## Rot, named

With the contract understood, "rot" decomposes into forces this series answers one by one. **Design debt surfaces**: early naming mistakes, wrong resource boundaries, overloaded endpoints — fixable only through change, and change is what breaks people (post 2: versioning schemes that create room to fix things). **Version sprawl**: every version kept alive multiplies maintenance; post 3's compatibility layers are how one implementation serves many versions without forking the codebase. **Spec-reality drift**: the OpenAPI document says one thing, the server does another, the SDKs a third (post 4: making the spec the source of truth that generates the rest). **Zombie versions**: clients that never upgrade, pinning you to the past indefinitely (post 5: deprecation as a designed process with telemetry and sunsets). And the meta-force — **change aversion**: teams so burned by breakage they stop evolving at all, freezing their worst decisions in place (post 6: designing new surface so that future change is cheap, which is the only durable cure).

The takeaway: an API's real contract is operational — a change is breaking if any plausible client stops working — and it extends past documentation into everything observable (Hyrum's Law), split across tolerant and strict reader styles whose expectations conflict. The convention that additive is safe is a *demand on clients* (tolerate unknowns, including enum values) that must be declared, not assumed. Rot is the sum of nameable forces — design debt, version sprawl, spec drift, zombie clients, change aversion — and the rest of this series is the machinery that answers each.

## Key takeaways

- Operational definition: breaking = **any plausible existing client stops working** — which includes tightened validation, sometimes-null shifts, default-order changes, and fixed bugs that clients worked around.
- **Hyrum's Law** is the ceiling: with enough users, every observable behavior (ID shapes, error strings, cursor stability) is somebody's dependency — the real contract is defined by client code, not docs.
- Declare the reader model: "additive is non-breaking" means **clients must be tolerant readers** — including handling unknown enum values, the most-violated clause.
- Rot decomposes into answerable forces: design debt (→ versioning room), sprawl (→ compat layers), spec drift (→ spec-as-source), zombies (→ designed deprecation), and change aversion (→ evolvable design).

## Further reading

- [API — the interface whose change this series disciplines](https://en.wikipedia.org/wiki/API)
- [Backward compatibility — the promise that makes change hard](https://en.wikipedia.org/wiki/Backward_compatibility)

---

Author: Pratik Dhanave (https://pratikdhanave.com) | Published: 2026-11-07
Canonical: https://pratikdhanave.com/blog/posts/apiver-01-why-apis-rot.html
Attribution: please link the canonical URL when citing or quoting this post.
