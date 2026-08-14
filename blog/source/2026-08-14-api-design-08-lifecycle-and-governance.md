# API Lifecycle and Governance

*How APIs are designed, shipped, and kept consistent at scale — the design review, the enforceable style guide, spec linting as policy-as-code, contract tests, an API catalog, and the org model that makes ten teams' APIs feel like one.*

---

The previous seven posts in this series were about *one* API: how to model its resources, shape its payloads, report its errors, version it safely, choose between REST and GraphQL and gRPC, and document it so a stranger can succeed. This finale is about a harder problem that only appears once you have more than one API and more than one team: **keeping them all coherent**.

A single well-designed API is a craft achievement. A hundred APIs across a dozen teams that all feel like they came from the same company — same naming, same error shape, same pagination, same versioning discipline — is an *organizational* achievement, and it doesn't happen by accident or by good taste alone. It happens because the organization treats each API as a long-lived contract and a product, and puts a lifecycle and a set of guardrails around it. That's what governance is: not a committee that slows you down, but the machinery that lets many teams move fast *and* consistently.

Everything below is drawn from public, primary sources — the OpenAPI Specification, the Spectral linter's documented rule model, the Pact contract-testing model, and the two best-known public API style guides, Google's API Improvement Proposals (AIPs) and Zalando's RESTful API Guidelines. The specifics of any one tool matter less than the shape of the practice.

---

## The API lifecycle: seven stages, one contract

An API isn't a thing you ship once. It's a contract that gets born, published, depended on, and eventually retired — often years apart. Naming the stages makes it possible to attach the right discipline to each, and every stage maps back to something earlier in this series.

- **Design** — the API is specified before it's built, usually as an OpenAPI (or Protobuf/GraphQL SDL) document. This is where posts 1–6 live: principles, resource modeling, payloads and pagination, the error model, the versioning strategy, the protocol choice.
- **Review** — a human looks at the design for the things machines can't judge: is this the right resource model? Does this abstraction leak? Is this a breaking change dressed up as an addition?
- **Build** — the service is implemented against the agreed spec. Spec-first means the contract exists before the handler does.
- **Test** — unit and integration tests, plus the two governance-specific ones we'll cover: spec linting and contract testing.
- **Publish** — the spec, the reference docs (post 7), and the endpoint go live. The API enters someone else's dependency graph.
- **Operate** — the API runs in production and you watch it: latency, error rates, per-endpoint and per-version usage.
- **Deprecate / retire** — a version is marked deprecated, consumers are migrated, and eventually the old version is switched off (post 5's versioning discipline made this possible).

The throughline is that a decision made cheaply at *design* becomes expensive at *operate* and brutal at *retire*. Governance front-loads the cheap decisions.

**The gotcha:** teams that skip the design and review stages and jump straight to build end up "designing" their API in production, where every fix is a breaking change to a live contract. The whole point of a spec-first lifecycle is that the cheapest place to change an API is a document nobody has integrated against yet.

---

## Design review and the style guide

The first governance tool is a **style guide**: a shared, written set of conventions so that ten teams' APIs feel like one. It codifies exactly the decisions this series has been making — but makes them *once*, for everyone:

- **Naming** — plural nouns for collections, `kebab-case` or `snake_case` (pick one) for path segments, consistent field casing in payloads.
- **Errors** — every API returns the same error envelope (post 4's `application/problem+json` / RFC 9457), so a client writes error handling once for the whole platform.
- **Pagination** — one pagination style (post 3's cursor-based pattern), not "offset here, cursor there, page tokens over there."
- **Versioning** — one versioning scheme and one deprecation policy (post 5), so consumers learn the migration rules once.

Google's AIPs and Zalando's guidelines are public examples of exactly this: numbered, rationale-bearing rules that anyone can cite in a review ("this violates AIP-132's standard-methods pattern").

The style guide is what a **design review** checks against. But reviews should reserve human attention for *judgment*, not *conformance*. A reviewer's scarce time is best spent on "is this the right resource model?" — not on "you used `camelCase` here and `snake_case` there," which a machine can catch instantly.

**The gotcha:** a style guide nobody enforces is just a wiki page. It will be read once during onboarding and never again, and drift starts on day one. The fix isn't more diligent reviewers — it's moving every mechanically checkable rule out of human review and into automation, which is the next section.

---

## Linting the spec: consistency as policy-as-code

If your APIs are described by OpenAPI documents, then a huge fraction of your style guide is *checkable by a program reading that document*. This is what an OpenAPI linter like **Spectral** does: you express your conventions as a **ruleset**, and the linter flags every violation. Consistency becomes automated, not nagged.

A Spectral rule targets a location in the document with a JSONPath expression (`given`), then applies a function (`then`) — built-ins include `truthy`, `pattern`, `casing`, `length`, and `enumeration`. A small ruleset that encodes a few of this series' conventions:

```yaml
# .spectral.yaml — a house style, enforced
extends: ["spectral:oas"]   # start from the built-in OpenAPI ruleset

rules:
  operation-must-have-summary:
    description: Every operation needs a human-readable summary (post 7, docs/DX).
    given: $.paths[*][get,post,put,patch,delete]
    severity: error
    then:
      field: summary
      function: truthy

  path-segments-kebab-case:
    description: Path segments use kebab-case, not camelCase (naming convention).
    given: $.paths[*]~   # '~' selects the property key (the path string)
    severity: error
    then:
      function: pattern
      functionOptions:
        match: "^(/[a-z0-9-{}]+)+$"

  error-responses-use-problem-json:
    description: 4xx/5xx responses must use application/problem+json (post 4).
    given: $.paths[*][*].responses[?(@property.match(/^[45]/))].content
    severity: error
    then:
      field: application/problem+json
      function: truthy
```

You then run `spectral lint openapi.yaml` in CI. Because `severity: error` returns a non-zero exit code, a violating spec **fails the pipeline** and blocks the pull request. The rules that used to be a reviewer's tedious comments are now a red check next to the diff.

**The gotcha:** a lint rule that only *warns* is a lint rule teams learn to ignore — the warning scrolls past in the CI log and the drift continues. If a convention is genuinely part of your house style, make its rule `severity: error` so it blocks the merge. Reserve `warn` for genuinely advisory rules, and be honest that "advisory" means "optional."

---

## Contract testing: proving you didn't break anyone

Linting checks that a spec is *well-formed and on-style*. It says nothing about whether a change to the implementation broke a real consumer. That's what **contract testing** is for, and it closes a gap that ordinary integration tests leave wide open.

The classic failure mode: a provider team renames a field from `full_name` to `name`, runs their own tests (all green — they updated them), deploys, and silently breaks three consumer teams who were reading `full_name`. Nobody caught it because the provider's tests didn't know what consumers actually depend on.

Consumer-driven contract testing (the model popularized by **Pact**) inverts this. Each *consumer* declares, in the form of a test, exactly the requests it makes and the response shape it relies on. Those expectations are collected into a **contract**, and the *provider* runs the contract as part of its own CI — replaying every consumer's expected interactions against the real provider and failing the build if any expectation is no longer met.

A sketch of the consumer side of such a contract (the interaction a consumer records):

```yaml
# consumer contract: "billing-ui" depends on "accounts-api"
consumer: billing-ui
provider: accounts-api
interactions:
  - description: fetch an account by id
    request:
      method: GET
      path: /accounts/42
    response:
      status: 200
      headers:
        content-type: application/json
      body:
        id: 42
        full_name: "Ada Lovelace"   # billing-ui reads THIS field
        status: active
```

When the provider later removes or renames `full_name`, replaying this contract fails on the provider's CI — *before* the change ships — with a message naming the consumer and the broken field. The provider now has a concrete list of who to coordinate with. Schema-based contract tests (validating live responses against the published OpenAPI schema) are a lighter-weight cousin: they don't capture per-consumer expectations, but they catch "the implementation drifted from the spec."

**The gotcha:** without contract tests, "we didn't change anything breaking" is a *hope*, not a guarantee. A provider genuinely cannot know from inside its own repo which fields consumers read, which optional fields they treat as required, or which enum values they switch on. Contract tests make those hidden dependencies explicit and enforceable at merge time, when they're still cheap to fix.

---

## The API catalog and ownership

Lifecycle and testing keep *individual* APIs healthy. An **API catalog** (or registry) keeps the *fleet* discoverable. It's a single place that lists every API, with — at minimum — its OpenAPI spec, its owning team, its lifecycle stage (design / active / deprecated / retired), and a link to its docs and its on-call.

The catalog answers questions that get expensive fast without it: *Does an API for this already exist? Who owns the `payments` API? Which version is current? What's deprecated and when does it switch off?* At small scale you can hold these answers in your head. At ten teams you cannot, and the absence of a catalog has a predictable cost.

**The gotcha:** no catalog means shadow and duplicate APIs — two teams building the same "user profile" endpoint because neither knew the other's existed — and orphaned services with no clear owner when something breaks at 2 a.m. Ownership isn't a metadata nicety; it's the difference between an incident that has a responder and one that gets bounced between teams. Every entry in the catalog should name a team, not a person.

---

## Observing APIs in production

Once an API is live, governance shifts from "is this designed well?" to "is this behaving well, and who's using it?" The core signals are the familiar reliability ones — latency (with percentiles, not just averages), error rates, and traffic — but for governance they matter *broken down per endpoint and per version*.

Per-endpoint metrics tell you which parts of the surface area are hot and which are dead. Per-version metrics are what make post 5's deprecation strategy *executable* rather than aspirational: you cannot responsibly retire `v1` until you can see that traffic to `v1` has actually drained to zero (or to a known, contactable set of stragglers). Usage-by-consumer closes the loop with the catalog — when you deprecate an endpoint, the metrics tell you exactly who to email.

This is the same reliability discipline covered in the System Design track's reliability post, applied at the granularity of the API contract. An SLO on an endpoint's error rate is a governance artifact: it's the promise attached to that part of the contract, and the error budget is the room you have to change things underneath it.

| Signal | Broken down by | Governance question it answers |
|---|---|---|
| Latency (p50/p95/p99) | endpoint, version | Is this contract meeting its SLO? |
| Error rate | endpoint, status class | Which part of the surface is unhealthy? |
| Request volume | endpoint, version, consumer | Can we deprecate this version yet, and who's still on it? |
| 4xx by type | error `type` (post 4) | Are clients misusing the API — a docs/DX gap? |

---

## The org model: API-as-a-product

The final piece is organizational. Treating an **API as a product** means it has an owning team, a roadmap, documented consumers, a support channel, and a deprecation policy — the same things a customer-facing product has. The consumers are developers, but they are customers, and post 7's developer experience is that product's UX.

Two structures dominate, and most organizations blend them:

- **Platform team** — a central team owns the shared infrastructure: the style guide, the linting ruleset, the catalog, the gateway, the contract-testing harness. They provide the paved road.
- **Federated ownership** — individual product teams own their own APIs' design and implementation, driving on that paved road. Design authority lives with the teams; the platform team owns the *rules*, not the *APIs*.

The healthy version is a platform team that ships automation and a federation of teams that own their contracts. The unhealthy version is a central review board that hand-inspects every API and becomes a bottleneck.

**The gotcha:** governance that only gatekeeps — slow manual reviews, no automation, a queue to get anything approved — gets *routed around*. Teams under deadline pressure ship the API somewhere the review board can't see it, and now you have the shadow-API problem *plus* resentment. Governance earns compliance by being fast: automate every mechanical rule so the machine gives instant feedback, and reserve scarce human review for genuine design judgment. It should feel like a paved road, not a toll booth.

---

## The series arc

This is the last post, so here is the whole throughline in one breath:

1. **Principles** — an API is an interface others build on; design it for its consumers, not your database.
2. **RESTful resource design** — model the domain as resources and use HTTP's methods and status codes as intended.
3. **Requests, responses, and pagination** — shape payloads deliberately and paginate before collections grow unbounded.
4. **Errors and idempotency** — one machine-readable error shape and safe retries make an API trustworthy on the unhappy path.
5. **Versioning and evolution** — change without breaking consumers, and deprecate on a policy, not a whim.
6. **GraphQL and gRPC** — REST isn't the only contract; choose the protocol that fits the consumer and the traffic.
7. **Documentation and developer experience** — the contract only exists to the extent someone can understand and succeed with it.
8. **Lifecycle and governance** — do all of the above consistently, across many teams, forever.

The single idea underneath every post is this: **an API is a long-lived contract and a product.** A contract because once someone integrates, you owe them stability. A product because it has customers whose success is your responsibility. Govern it like one — with a lifecycle, an enforceable style guide, automated checks, contract tests, a catalog, observability, and clear ownership — and ten teams can move fast while shipping one coherent platform. Skip the governance and you get a hundred APIs that each made locally reasonable choices and collectively feel like a hundred different companies.

---

## Key takeaways

- **Name the lifecycle stages** (design → review → build → test → publish → operate → deprecate/retire) so you can attach the right discipline to each. A decision is cheap at design and brutal at retire.
- **A style guide nobody enforces is a wiki page.** Codify naming, errors, pagination, and versioning once, then move every mechanically checkable rule into a linter.
- **Lint the spec in CI as policy-as-code.** A Spectral ruleset with `severity: error` blocks the PR — consistency becomes automated, not nagged, and human review is freed for design judgment.
- **Contract tests turn "we didn't break anything" from a hope into a guarantee.** Consumer-driven contracts make hidden dependencies explicit and fail the provider's build before a breaking change ships.
- **A catalog with ownership prevents shadow and duplicate APIs** and gives every service a responder when it breaks.
- **Observe per-endpoint and per-version** so deprecation is executable and SLOs are enforceable.
- **Treat the API as a product** with a platform team paving the road and federated teams owning their contracts — automate the rules, and reserve humans for judgment.

---

## Further reading

- [OpenAPI Specification](https://spec.openapis.org/oas/latest.html) — the machine-readable contract format that everything above lints, tests, and catalogs.
- [Spectral documentation (Stoplight)](https://docs.stoplight.io/docs/spectral/674b27b261c3c-overview) — the OpenAPI/JSON linter, its ruleset model, and the built-in functions used above.
- [Pact: contract testing](https://docs.pact.io/) — the consumer-driven contract-testing model and how provider verification works.
- [Google API Improvement Proposals (AIPs)](https://google.aip.dev/) — a large, public, numbered API style guide with rationale for each rule.
- [Zalando RESTful API Guidelines](https://opensource.zalando.com/restful-api-guidelines/) — another public, enforceable house style, with a companion Zally linter.
