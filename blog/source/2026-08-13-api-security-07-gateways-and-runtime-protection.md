# API Gateways and Runtime Protection

*Part seven of the API Security series: the perimeter and runtime layer that enforces security consistently — the gateway as a policy enforcement point, the limits of a WAF, keeping an honest inventory of every endpoint you expose, hardening defaults, and watching the traffic for abuse you can only see at runtime.*

---

Everything earlier in this series lives inside a service: how you prove who is calling, how you check what they may touch, how you validate the bytes crossing the boundary. All of it assumes the request already reached your handler. This post is about the layer *in front* of the handler — the gateway that every request passes through — and the layer *around* it — the monitoring that tells you an attack is happening while it happens.

The temptation is to treat this perimeter as the security story: put a gateway and a web application firewall in front of the fleet and call it hardened. It is not the whole story, and the two most common failures in this layer — OWASP API8 (Security Misconfiguration) and API9 (Improper Inventory Management) — are failures of the perimeter itself, not of any single service. The gateway centralizes the *coarse* controls so you write them once instead of forty times. Fine-grained authorization stays in the service. Inventory and monitoring close the gaps between them.

---

## The gateway as a policy enforcement point

An API gateway sits between clients and your services and terminates every request before it reaches a backend. Because *all* traffic funnels through it, it is the natural place to enforce the controls that should be identical for every service:

- **TLS termination** — one place that owns certificates, cipher suites, and protocol versions, so you are not auditing TLS config on every service.
- **Authentication and token validation** — verify the bearer token's signature, issuer, audience, and expiry once, reject anonymous traffic at the door, and pass a verified identity downstream.
- **Rate limiting and quotas** — the throttling controls this series covered earlier, applied uniformly so no single client can exhaust a backend.
- **Request validation** — reject malformed requests, oversized bodies, and unexpected content types before they cost a backend anything.
- **Routing** — map public paths to internal services, which also lets you hide your topology behind a stable public contract.

The argument for centralizing is not elegance, it is *consistency*. If each of forty services parses JWTs on its own, you have forty subtly different implementations, and the weakest one is your real security posture. Move signature verification, clock-skew handling, and issuer checks to the gateway and every service inherits the same correct behavior. When you rotate a signing key or tighten an accepted audience, you change it in one place.

A gateway policy is usually declarative. A sketch — the exact syntax varies by product, but the shape is universal:

```yaml
routes:
  - path: /v2/orders
    upstream: orders-service.internal:8443
    tls:
      min_version: "1.2"
    auth:
      type: jwt
      issuer: https://auth.example.com/
      audience: api.example.com
      jwks_uri: https://auth.example.com/.well-known/jwks.json
      require_claims: [sub, scope]
    rate_limit:
      requests_per_minute: 600
      key: token.sub          # per-caller, not per-IP
    request:
      max_body_bytes: 262144
      allowed_content_types: [application/json]
    cors:
      allow_origins: [https://app.example.com]   # explicit, never "*"
      allow_methods: [GET, POST]
      allow_credentials: true
```

Notice what this policy does *not* say: it never decides whether *this* caller may see *that* order. It confirms the token is real, the caller is within quota, the body is sane, and the origin is allowed — then forwards a verified identity to the orders service. What the caller is allowed to do with a specific object is a decision the gateway cannot make.

**The gotcha:** a gateway that validates the token and forwards it to a service that then skips object-level checks still has a Broken Object Level Authorization (BOLA) hole — and BOLA is the number-one API risk. The gateway knows the token belongs to user 481; it has no idea that order `9c2f` belongs to user 902. Ownership lives in your data, and only the service holding that data can check it. Terminating auth at the gateway feels like "authorization is handled," and that feeling is exactly how BOLA ships to production. Coarse controls at the edge; per-object authorization in the service, on every request, always.

---

## WAF: useful, and easy to over-trust

A web application firewall inspects requests against a ruleset and blocks ones that match known-bad patterns — SQL injection payloads, cross-site scripting fragments, path-traversal sequences, known scanner signatures. Sitting in front of the gateway (or built into it), a WAF buys you real value: it filters the constant background noise of generic automated attacks and gives you a fast lever to virtually patch a newly disclosed vulnerability class while you deploy a real fix.

But a WAF reasons about *bytes*, not about *your business*. It can recognize that `' OR 1=1--` looks like injection. It cannot recognize that user 481 requesting `/v2/orders/9c2f` is reading someone else's order, because that request is perfectly well-formed — correct method, valid token, syntactically clean path. Nothing in the bytes is anomalous. The abuse is entirely in the *meaning*, and the meaning depends on data the WAF never sees.

**The gotcha:** a WAF catches generic injection and XSS, not business-logic abuse or BOLA — do not treat "the WAF is on" as "the API is secure." The attacks that actually breach APIs are usually authorization failures dressed as normal traffic, and those pass straight through a pattern matcher. A WAF is one layer that reduces noise and blocks the crude stuff. It is never a substitute for authorization in the service or for validation at the data sink.

---

## Improper inventory management (API9): the endpoints you forgot

You cannot protect what you do not know exists. OWASP calls this API9, Improper Inventory Management, and it is the risk that turns a well-secured API program into a breach anyway — because the breached endpoint was one nobody was watching. It shows up in three shapes:

- **Shadow APIs** — endpoints that exist in production but not in your documentation, catalog, or gateway config. A team shipped a service directly, a "temporary" internal endpoint became load-bearing, or a debug route was never removed. It serves real traffic and no security control was ever applied to it because, officially, it does not exist.
- **Zombie APIs** — deprecated versions still live. You shipped `/v2`, told everyone to migrate, and left `/v1` running "just in case." The old version rarely gets the patches, the tightened validation, or the new authorization checks the current version received. Attackers enumerate `/v1`, `/v0`, `/api/old` precisely because those paths are where the weak, unmaintained code lives.
- **Non-prod endpoints exposed** — staging, QA, or debug environments reachable from the internet, often with weaker auth, seeded test data, verbose errors, or default credentials, and pointed at data that is more real than anyone admits.

The through-line is that each of these is a fully functional attack surface that receives *none* of your security attention because it is off the map. The fix is not clever, it is disciplined:

1. **Maintain an inventory.** Every host, every environment, every API version, its owner, its status (active / deprecated / retired), and the date support ends. This ties directly to the API design work covered later in the series — a machine-readable spec (OpenAPI) per version is the backbone of the catalog, because a documented contract is an inventoried endpoint.
2. **Discover continuously.** The inventory drifts the moment you write it. Diff your live routing table against your catalog, scan your own address space, and parse gateway access logs for paths that serve traffic but appear in no spec. Anything live and uncataloged is a finding.
3. **Retire, do not abandon.** Deprecation needs an end date and an actual shutdown. A version you stopped maintaining but left running is not deprecated; it is a liability with uptime.

**The gotcha:** shadow and zombie endpoints — a forgotten `/v1`, a debug route left enabled, a staging host with a public IP — get breached constantly precisely because nobody is watching them. No alert fires, because they are not in the monitoring. No patch lands, because they are not in the pipeline. The only defenses are an honest inventory and the discipline to actually turn old things off.

---

## Security misconfiguration (API8): the low-effort breach

OWASP API8, Security Misconfiguration, is the category attackers love because it costs them almost nothing. There is no clever exploit chain — the door was left open. The recurring offenders:

- **Default credentials.** An admin console, a database, a message broker, or a management dashboard still on its shipped username and password. Automated scanners try these first, on every host, all day.
- **Verbose errors and stack traces.** An unhandled exception that returns the framework version, a file path, a SQL fragment, or a full stack trace hands the attacker a map of your internals for free. Return a generic error and an opaque correlation ID to the client; keep the detail in your logs.
- **Permissive CORS.** `Access-Control-Allow-Origin: *` — especially paired with credentialed requests — invites any origin to call your API from a victim's browser. Cross-origin resource sharing was covered earlier in this series; the gateway is where you enforce an explicit allow-list of origins rather than a wildcard.
- **Missing security headers.** No `Strict-Transport-Security`, no `X-Content-Type-Options: nosniff`, no restrictive `Content-Security-Policy` on responses that render. Cheap to add at the gateway, and their absence is exactly what automated audits flag.
- **Debug endpoints and dangerous defaults.** Profilers, heap dumps, `/actuator`-style management routes, directory listing, or verbose logging switched on in production because it was never switched off after the last incident.

The unifying theme: these are not vulnerabilities you introduced, they are hardening you skipped. The countermeasure is a secure baseline applied uniformly — a hardened default gateway and service configuration, disabled debug surfaces, generic client-facing errors, rotated credentials, and an automated check that a new deployment inherits the baseline instead of a framework's ship-with-everything-on defaults.

**The gotcha:** misconfiguration — verbose errors, default credentials, wildcard CORS — is the lowest-effort, highest-frequency way in, because it requires no exploit, just a scan. Harden the defaults once, enforce the baseline in your deploy pipeline, and re-run an audit so a single service's stale config does not reopen a door you closed everywhere else.

---

## Runtime detection: watching the traffic you cannot pre-validate

The controls above are preventive — they stop known-bad requests. But the attacks that matter most against APIs (authorization abuse, enumeration, credential stuffing) are made of individually valid requests. You cannot block them at the door; you can only *detect the pattern over time*. That requires logging and monitoring built for security, not just for debugging.

Log, per request, the fields that let you reconstruct who did what:

```text
timestamp            2026-08-13T14:22:07Z
request_id           01J...              # correlation id, returned to client
route                POST /v2/orders/{id}
caller_sub           user_481            # authenticated identity, not just IP
source_ip            203.0.113.10
status               403
auth_result          denied_object_level # authn ok, authz failed
object_id            9c2f                # the resource acted on (or its hash)
latency_ms           12
```

Note what is *not* in that line: no tokens, no passwords, no request bodies, no PII beyond a stable pseudonymous identifier. You want enough to investigate, never enough to leak.

With that stream, you can build API-specific detection that a generic WAF cannot:

- **Per-endpoint authentication and authorization failures.** A rising rate of `401`s on `/login` is credential stuffing. A rising rate of `403 denied_object_level` from one caller is someone probing objects they do not own — a live BOLA attempt, visible only because you logged the authorization *decision*, not just the status code.
- **Anomalous access patterns.** One caller reading thousands of distinct object IDs, sequential IDs walked in order, a token used from two continents in a minute, or traffic to a route that normally sees none. Each is a signature of enumeration or a stolen credential.
- **BOLA-probing signatures.** A single caller whose ratio of *denied* to *allowed* object accesses spikes is enumerating identifiers to find one they can reach. That ratio is a high-signal alert and it exists only if the service logs the object-level decision.

Then *alert* on these — a spike in per-caller authorization denials, a surge of `401`s on an auth route, access to a newly appeared path — and route the alert somewhere a human sees it in minutes, not in next quarter's log review. Detection you never look at is not detection.

**The gotcha:** monitoring only pays off if it captures the *authorization decision*, not just the HTTP status. Two requests can both return `200`, one legitimate and one a successful BOLA — the difference is whether an ownership check ran and passed. Log the decision (`allowed` / `denied_object_level` / `denied_scope`) at the point you make it, and enumeration attacks that look like ordinary traffic finally become visible.

---

## Key takeaways

- **The gateway centralizes coarse controls.** TLS, token validation, rate limiting, request validation, CORS, and routing belong in one enforcement point so every service inherits the same correct behavior.
- **The gateway is not your authorization layer.** It can verify identity; it cannot know ownership. BOLA and other object-level checks stay in the service, on every request, against your data.
- **A WAF filters generic attacks, not business logic.** It blocks injection and scanner noise. It cannot see authorization abuse dressed as valid traffic — never treat "WAF on" as "done."
- **You cannot protect what you have not inventoried.** Shadow, zombie, and exposed non-prod endpoints get breached because nobody is watching them. Catalog every version and environment, discover continuously, and actually retire the old ones.
- **Misconfiguration is the cheapest breach.** Default credentials, verbose errors, wildcard CORS, and missing headers require no exploit. Harden defaults once and enforce the baseline in your pipeline.
- **Detection lives in the logs.** Record the authorization decision, not just the status code, then alert on per-caller denial spikes and anomalous access. The attacks that matter are patterns you can only see at runtime.

---

## Further reading

- [OWASP API Security Top 10 — API8:2023 Security Misconfiguration](https://owasp.org/API-Security/editions/2023/en/0xa8-security-misconfiguration/)
- [OWASP API Security Top 10 — API9:2023 Improper Inventory Management](https://owasp.org/API-Security/editions/2023/en/0xa9-improper-inventory-management/)
- [OWASP Cheat Sheet — REST Security](https://cheatsheetseries.owasp.org/cheatsheets/REST_Security_Cheat_Sheet.html)
- [Kong Gateway — Security reference](https://docs.konghq.com/gateway/latest/)
- [Envoy Proxy — Security documentation](https://www.envoyproxy.io/docs/envoy/latest/intro/arch_overview/security/security)
- [AWS API Gateway — Security in Amazon API Gateway](https://docs.aws.amazon.com/apigateway/latest/developerguide/security.html)
