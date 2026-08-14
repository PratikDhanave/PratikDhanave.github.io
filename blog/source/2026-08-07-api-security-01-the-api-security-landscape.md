# The API Security Landscape

*Why APIs became the primary attack surface, how API risk differs from classic web-app risk, and the OWASP API Security Top 10 framework this series builds on.*

---

Fifteen years ago, an attacker probing a company looked at web pages: forms, login screens, the HTML a browser rendered. Today they look at the JSON underneath. The browser is just one more client, and behind it sit dozens — sometimes hundreds — of APIs that expose business logic and data directly to whoever can reach them. Mobile apps, single-page frontends, partner integrations, internal microservices, and increasingly autonomous agents all speak the same language: HTTP requests carrying structured data to endpoints that read and write your database.

That shift is the whole reason this series exists. An API is not a smaller, safer version of a web app — it is a *more exposed* version. It hands the caller a machine-readable contract to your data model, it usually runs without a human watching each request, and it is frequently under-monitored compared with the front door everyone remembers to guard. This first post frames the problem: why APIs are now where attackers spend their time, how API security genuinely differs from traditional web-app security, how to threat-model an endpoint, and the framework — the OWASP API Security Top 10 — that the rest of the series maps onto.

---

## Why APIs are the primary attack surface

Three properties make APIs attractive targets, and they compound.

**APIs expose business logic and data directly.** A rendered web page is a *view* — the server decides what HTML to emit, so a lot of data never leaves the building. An API endpoint is the raw contract. `GET /api/v1/accounts/4815/transactions` returns exactly what the data model holds, serialized. There is no template layer quietly filtering fields. If the endpoint returns an object with `internalRiskScore` in it, the caller sees `internalRiskScore`. The attacker reads your schema the same way your own frontend does.

**APIs are machine-to-machine.** Most API traffic has no human in the loop. A mobile client refreshes a token and pulls a feed; a partner batch job pulls ten thousand records overnight; an agent calls a tool. That means an attacker's automated probing blends in — there is no "this request looks like a bot" signal when *all* legitimate traffic is bots. It also means classic human-facing defenses (CAPTCHAs, interstitial warnings, "are you sure?" confirmations) simply don't apply.

**APIs are often under-monitored.** Organizations instrument the marketing site and the login page carefully. The `/internal/v2/` endpoint that a deprecated mobile build still calls, or the `/api/beta/` route left up after a launch, frequently has no alerting, no rate limits worth the name, and no owner. Attackers hunt exactly these forgotten surfaces — which is why *inventory* is itself one of the top ten risks (more on that below).

```text
Traditional web app                 API-first system
-------------------                 ----------------
browser -> server -> HTML view      many clients -> many endpoints -> data
  server decides what to render       endpoint serializes the model
  one guarded front door              dozens of doors, some forgotten
  human-paced traffic                 machine-paced, automated traffic
```

**The gotcha:** the danger is not that APIs are inherently insecure — it is that the *view layer that used to hide your mistakes is gone*. Over-fetching, weak authorization, and leaky objects that a server-rendered template would have masked are now shipped straight to the client, where anyone with `curl` and browser dev tools can read them.

---

## How API security differs from web-app security

If you have internalized the classic OWASP Top 10 for web applications — injection, XSS, CSRF, and friends — you know real risks, but you do not yet have API coverage. The two lists overlap, but the *center of gravity* is different.

Classic web-app security is dominated by problems at the boundary between untrusted input and a trusting interpreter: SQL injection, cross-site scripting, template injection. Those still matter for APIs (we devote a whole post to injection). But the dominant API risk is somewhere the web-app list barely addresses: **authorization at the object level.**

Consider the difference. XSS is about a browser executing attacker-controlled markup — an API returning JSON to a mobile app has no DOM to poison, so much of the XSS surface evaporates. CSRF depends on ambient browser credentials (cookies) being sent automatically — token-based APIs that require an explicit `Authorization` header are structurally less exposed. Meanwhile a new class of problem takes center stage: an authenticated, perfectly "logged-in" user asking for an object that isn't theirs.

```http
GET /api/v1/accounts/4815/statements HTTP/1.1
Host: api.example.com
Authorization: Bearer eyJhbGci...     # a VALID token for user 5000
```

Nothing here is malformed. The token is genuine, the user is authenticated, the request is well-formed. The only question that matters is: *does user 5000 own account 4815?* If the endpoint checks that the token is valid but forgets to check that the object belongs to the caller, it hands over another customer's statements. No injection, no stolen credential, no exploit payload — just a missing ownership check. This is Broken Object Level Authorization, and it is consistently the number-one API risk precisely because it is invisible to input-focused defenses. A WAF sees a clean request. A schema validator sees valid JSON. Only *authorization logic that knows who owns what* stops it.

That is the mental shift: web-app security asks "is this input safe to process?" API security adds, with much greater weight, "is this authenticated caller *allowed* to touch this specific object and this specific operation?"

---

## Threat-modeling an API endpoint

Before the specifics, a reusable lens. Threat-modeling an endpoint means answering three questions in order, and never conflating them.

**Where are the trust boundaries?** A trust boundary is any line data crosses where the level of trust changes — the internet-to-gateway edge, the gateway-to-service hop, the service-to-database call, and the service-to-third-party call when your API *consumes* someone else's. Every boundary is a place where assumptions from one side must be re-validated on the other. The classic mistake is trusting a value simply because it arrived from an internal service; "internal" is a network fact, not an authorization decision.

**Authentication vs. authorization — keep them separate.** These get blurred constantly, and the blur *is* the vulnerability.

- **Authentication (authn)** answers *who are you?* — verifying the caller is who they claim. Broken authentication means an attacker can become someone else: guessable tokens, unverified signatures, credential-stuffing an unthrottled login.
- **Authorization (authz)** answers *what are you allowed to do?* — and it has two independent dimensions. *Function-level* authz asks "may this role call this operation at all?" (can a regular user hit `DELETE /admin/users/{id}`?). *Object-level* authz asks "may this specific caller act on this specific record?" (does user 5000 own account 4815?).

A correctly authenticated user is still subject to *both* authorization checks on *every* request. The endpoint above passed authentication and failed object-level authorization — a distinction that matters because the fixes live in different code.

**What data and logic does the endpoint expose?** Map, per endpoint, exactly which fields go out, which fields can be written, and which business action is triggered. An endpoint that returns a `User` object may be leaking `passwordResetToken` or `isAdmin` because someone serialized the whole model. An endpoint that accepts a `User` object may let a caller *set* `isAdmin` because it binds the whole request body to the entity. And an endpoint that looks harmless in isolation — "add to cart," "apply promo code" — may expose a *business flow* that becomes an attack when automated a million times.

---

## The framework: the OWASP API Security Top 10

The OWASP API Security Project maintains a dedicated top-ten list because the general web-app list, as shown above, misses the risks that dominate APIs. The current edition (2023) is the backbone of this series. Here it is, faithfully summarized in plain terms — each entry links to a later post where we go deep.

| # | Risk | In one sentence |
|---|------|-----------------|
| API1 | Broken Object Level Authorization (BOLA) | An authenticated caller reaches an object they don't own because ownership isn't checked per request. |
| API2 | Broken Authentication | Identity itself can be forged, guessed, or bypassed — weak tokens, unverified signatures, unthrottled login. |
| API3 | Broken Object Property Level Authorization | The right object, but the wrong *fields* — leaking properties on read or letting callers set privileged properties on write. |
| API4 | Unrestricted Resource Consumption | No limits on requests, payload size, or cost, so callers can exhaust CPU, memory, bandwidth, or your third-party bill. |
| API5 | Broken Function Level Authorization (BFLA) | A caller invokes an operation their role should never reach — a user hitting admin routes. |
| API6 | Unrestricted Access to Sensitive Business Flows | A legitimate flow (checkout, signup, booking) is abused at scale because the *business impact* of automation was never limited. |
| API7 | Server-Side Request Forgery (SSRF) | The API fetches a caller-supplied URL and can be tricked into reaching internal services or cloud metadata. |
| API8 | Security Misconfiguration | Insecure defaults, verbose errors, missing hardening, permissive CORS, or unpatched components across the stack. |
| API9 | Improper Inventory Management | Forgotten, undocumented, or unversioned endpoints (old `/v1`, `/beta`, debug hosts) that no one is watching. |
| API10 | Unsafe Consumption of APIs | Trusting the *third-party* APIs you call as if their responses were safe, skipping validation on data you didn't produce. |

Two things about this list are worth internalizing. First, **authorization owns three of the ten slots** (API1, API3, API5) — object-level, property-level, and function-level. That is not a coincidence; it is the empirical center of gravity of API risk. Second, several entries have *no analog* on the classic web-app list — sensitive business flow abuse (API6), inventory management (API9), and unsafe consumption of upstream APIs (API10) are API-native problems that come directly from the machine-to-machine, distributed nature of the surface.

**The gotcha:** the Top 10 is a *prioritization* list, not a checklist you complete once. A single endpoint can carry several of these at once — a forgotten `/v1` route (API9) with verbose errors (API8) that leaks another user's object (API1). Defense in depth means treating them as overlapping layers, not boxes to tick.

---

## How this series is organized

The remaining posts map onto the framework above, grouped so that related risks are tackled together. Roughly eight installments follow:

- **Authentication** — proving *who* the caller is: token formats, signature verification, session and key management, and the throttling that turns a weak login from catastrophic into merely annoying (API2).
- **Authorization: BOLA and BFLA** — the heart of API security: enforcing object-level and function-level access on every request, and why "check ownership in the service, never trust the client" is the load-bearing rule (API1, API5).
- **Input validation and injection** — schema validation, allow-lists, and the classic injection families that still apply to JSON and query parameters (overlaps API8, plus object-property abuse from API3).
- **Rate limiting and resource consumption** — quotas, payload caps, pagination limits, and pricing-aware throttling that protects both your infrastructure and your business flows (API4, API6).
- **Transport and data security** — TLS done properly, secrets handling, and not serializing fields the caller was never meant to see (API3).
- **Gateways and runtime protection** — where an API gateway, WAF, and runtime monitoring genuinely help, where they give false comfort, and SSRF defenses at the egress boundary (API7, API8).
- **The secure API lifecycle** — inventory, versioning, deprecation, and safely consuming upstream APIs, so security is a property of how you *ship and retire* endpoints, not a one-time review (API9, API10).

This series is a companion to the site's **AI Security Engineering** series — agents calling tools are API clients, and every risk here applies when the caller is an LLM instead of a mobile app — and to the **API Design** series, which covers the contract-shaping decisions (versioning, resource modeling, error semantics) that this series then hardens. Good design and good security are the same conversation viewed from two angles.

---

## Key takeaways

- **APIs are the primary attack surface** because they expose business logic and data directly, run machine-to-machine without a human in the loop, and are often the least-monitored part of the stack.
- **The view layer that used to hide mistakes is gone.** Over-fetching and weak authorization ship straight to the client, where `curl` and dev tools read them.
- **Authorization dominates API risk.** The single most common flaw is an authenticated caller reaching an object they don't own — invisible to WAFs and schema validators, catchable only by ownership logic.
- **Keep authn and authz separate, and check authz on every request** — both function-level (may this role call this?) and object-level (may this caller touch this record?).
- **The OWASP API Security Top 10 is the map for this series** — a prioritization of overlapping risks, three of which are pure authorization, several of which have no web-app analog. Treat them as defense-in-depth layers, not a one-time checklist.

---

## Further reading

- [OWASP API Security Top 10 (2023)](https://owasp.org/API-Security/editions/2023/en/0x11-t10/) — the current edition, with per-risk detail.
- [OWASP API Security Project](https://owasp.org/www-project-api-security/) — the project home, methodology, and community resources.
- [OWASP Top 10 (web application)](https://owasp.org/www-project-top-ten/) — the classic list, for the contrast drawn above.
- [NIST SP 800-204: Security Strategies for Microservices-based Application Systems](https://csrc.nist.gov/pubs/sp/800/204/final) — authentication, authorization, and gateway guidance for distributed API systems.
- [NIST SP 800-95: Guide to Secure Web Services](https://csrc.nist.gov/pubs/sp/800/95/final) — foundational guidance on trust boundaries and service-to-service security.
