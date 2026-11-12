<!-- Markdown version for AI agents and readers. Canonical: https://pratikdhanave.com/blog/posts/apiver-02-versioning-schemes.html -->

# Versioning Schemes — URL, Header, Date-Pinned, and the Scheme Behind the Scheme

*Where does the version live — in the path, a header, a date? The debate consumes design reviews and misses the real decision underneath: what a version even is (the whole API? a resource? a behavior?), who chooses it (the request? the account?), and how many will you honestly support? This post surveys the schemes with their true trade-offs, including the account-pinned date scheme that the most evolution-serious API companies converged on — and why.*

Post [1](/blog/posts/apiver-01-why-apis-rot.html) defined the contract; this post is about creating *room* to change it — the mechanism that lets v-next fix what v-now got wrong without breaking anyone who hasn't asked for the fix.

## The surface schemes

- **URL-path versioning** (`/v2/charges`) — the version is in the address. Virtues: maximally visible, trivially routable, cache-friendly, debuggable from a log line. Costs: it versions the *entire API* in one coarse number, so any breaking change anywhere demands a new global version — which is why v2s become multi-year migration projects and why path-versioned APIs often stay on v1 forever, accreting warts (post 1's change aversion, mechanized). Clients also hardcode paths, making even the version string itself load-bearing.
- **Header versioning** (`Accept: application/vnd.api.v2+json` or a custom header) — the version travels out-of-band. Virtues: URLs stay stable and resource-oriented; granularity can be finer. Costs: invisible in casual debugging, frequently omitted (demanding a default-version policy — the *real* design decision this scheme usually hides), and cache keys need care.
- **Per-resource or capability versioning** — different resources evolve independently. Honest about how change actually arrives (one endpoint at a time) but pushes a combinatorial testing and documentation burden onto clients; rare as a public scheme, common as an internal reality.

The observation that reframes the debate: these schemes mostly differ in *where the number goes*, while the costs live in *how many numbers exist* and *how long each lives* — which the surface choice barely affects.

## The scheme behind the scheme: account-pinned dates

The pattern the most change-intensive API providers converged on restructures the question. Instead of a few big versions, **every breaking change creates a new dated version** (`2026-08-14`); instead of each request choosing, **each account is pinned** to the version current when it integrated; requests may override per-call (for testing the future), and accounts upgrade deliberately, one dated step visible in a changelog at a time. What this buys: **breaking changes decouple from each other** — shipping a fix today doesn't wait for a v2 omnibus, and clients adopt changes incrementally instead of facing a migration cliff; **integrations freeze in the era they were built** — code written in 2024 keeps 2024 semantics until its owners choose otherwise, which is post 1's contract honored by default; and **the provider carries the burden** — which is the honest accounting, because the provider wrote the breaking change and is the only party who can make it cheap. The cost is real and concentrated: dozens of live dated versions mean the implementation must serve all of them — mechanically impossible without post 3's compatibility-transform architecture, which is why this scheme and that architecture are effectively one decision. Account pinning also changes *defaults*: the dangerous "no version specified → latest" policy (every new deploy breaks someone) becomes "no version → your account's pin," which is both safer and stickier.

## Choosing, honestly

The decision tree is shorter than the debate: an **internal or few-consumer API** — skip ceremony, coordinate deploys, use additive evolution (post 6) and version nothing until forced. A **public API changing rarely** — URL versioning is fine *if* you accept that each version is a near-permanent commitment (budget for a decade, not a deprecation quarter — post 5 covers why sunsets slip). A **public API that intends to evolve continuously** — the dated-pin model is the one that scales with change rate, priced at building the transform layer. And in every scheme, two invariants hold: **the version policy is documented as part of the API** (what counts as breaking, what may appear without notice — post 1's tolerant-reader demand in writing), and **version metadata is observable** (every response echoes the version that served it; your telemetry can say who is on what — the raw material post 5's deprecation machinery requires).

The takeaway: the visible schemes — path, header, per-resource — mostly relocate the version number, while the real decisions are granularity, default policy, and lifetime. The convergent answer for continuously-evolving APIs is **dated versions pinned per account**: every breaking change ships independently as a date, integrations keep the semantics of their era, upgrades are deliberate single steps, and the provider pays the (real) cost in a compatibility-transform layer — the subject of post 3. Whatever the scheme: write the policy into the API's contract and make the serving version observable everywhere.

## Key takeaways

- **Path versioning** is visible and coarse — whole-API versions breed omnibus v2 migrations and forever-v1 paralysis; **header versioning** is granular and invisible, hiding the default-version decision; **per-resource** is honest and combinatorially expensive.
- The real axes are **granularity, default policy, and lifetime** — not where the number sits.
- **Account-pinned dated versions** decouple breaking changes, freeze integrations in their era, and shift the burden to the party who caused it — priced at needing the transform architecture (post 3) and paid back in continuous evolvability.
- Universal invariants: the **versioning policy is documented contract** (including the additive/tolerant-reader rules), and **every response declares its serving version** — telemetry on version usage is the precondition for ever retiring one.

## Further reading

- [Software versioning — the general discipline of naming change](https://en.wikipedia.org/wiki/Software_versioning)
- [Hypertext Transfer Protocol — the header and content-negotiation machinery schemes build on](https://en.wikipedia.org/wiki/Hypertext_Transfer_Protocol)

---

Author: Pratik Dhanave (https://pratikdhanave.com) | Published: 2026-11-08
Canonical: https://pratikdhanave.com/blog/posts/apiver-02-versioning-schemes.html
Attribution: please link the canonical URL when citing or quoting this post.
