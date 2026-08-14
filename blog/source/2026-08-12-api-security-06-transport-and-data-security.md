# Transport and Data Security

*Part six of the API Security series: encrypt every byte in transit and at rest, hand out only the data a caller actually needs, and keep the keys that protect it out of your code and under a rotation policy.*

---

The earlier posts in this series guarded the front door — who is calling, what they are allowed to touch, and whether the payload they sent is hostile. This post is about the data itself, in the two states where it is easiest to lose: **moving across a network** and **sitting in storage**. An API can authenticate perfectly and authorize precisely and still leak everything, because a request rode over plaintext, a response carried fields nobody asked for, or a signing key was baked into a container image that ended up on a public registry.

The mental model is three rules that compound. **Encrypt in transit and at rest** so intercepted or stolen bytes are useless. **Minimize what you expose and store** so a breach reveals less. **Manage keys properly** so the encryption is not undone by a secret sitting in `git log`. Miss any one and the other two stop mattering — a field-level-encrypted column is worthless if the KMS key is in an environment variable committed to the repo, and TLS everywhere is theater if the response body dumps a customer's full card number to anyone with a valid token.

---

## TLS everywhere, including "internal" traffic

Transport Layer Security is the floor, not a feature. Every API endpoint should be HTTPS-only: reachable over TLS, and either redirecting or refusing plain HTTP. For a browser-facing surface a redirect to `https://` is acceptable for the first hop; for a machine-to-machine API, prefer refusing HTTP outright, because a redirect still means the first request — headers, tokens, body — crossed the wire in cleartext before the 301 came back.

Once you are on HTTPS, tell the client never to try HTTP again. **HTTP Strict Transport Security (HSTS)** is a response header that instructs browsers to upgrade every future request to this host to HTTPS for a fixed duration, closing the downgrade window.

```go
func hstsMiddleware(next http.Handler) http.Handler {
    return http.HandlerFunc(func(w http.ResponseWriter, r *http.Request) {
        // Only send HSTS over a connection that is already secure.
        if r.TLS != nil {
            w.Header().Set("Strict-Transport-Security",
                "max-age=31536000; includeSubDomains")
        }
        next.ServeHTTP(w, r)
    })
}
```

Configure the server for modern TLS. Set a minimum of TLS 1.2 (prefer 1.3 where your clients support it), disable the long-dead SSLv3/TLS 1.0/1.1, and let the library pick an AEAD cipher suite rather than hand-listing weak ones:

```go
srv := &http.Server{
    Addr:    ":8443",
    Handler: mux,
    TLSConfig: &tls.Config{
        MinVersion: tls.VersionTLS12, // reject TLS 1.0/1.1 and all SSL
    },
}
// Serves only over TLS; there is no plaintext listener to downgrade to.
log.Fatal(srv.ListenAndServeTLS("server.crt", "server.key"))
```

Certificates are not set-and-forget. Automate issuance and renewal (ACME/Let's Encrypt for public endpoints, an internal CA for private ones), monitor expiry, and rehearse rotation before a cert actually lapses at 2 a.m. An expired certificate is an outage; a leaked private key is a breach, so treat the key material like any other secret (below).

**The gotcha:** "it's internal, so plain HTTP is fine" is the assumption zero-trust exists to kill. The perimeter is not a wall — a compromised pod, a mis-scoped service account, a coworker's laptop on the same VPC, or a cloud metadata pivot all put an attacker *inside*, where they read your east-west traffic as plaintext and harvest the very tokens your auth layer worked so hard to issue. Encrypt service-to-service traffic too; the network is never trusted just because it is private.

---

## mTLS for service-to-service and high-assurance clients

Ordinary TLS authenticates the *server* to the client. **Mutual TLS (mTLS)** adds the other direction: the client presents a certificate too, and the server refuses the handshake unless that cert chains to a CA it trusts. Now both ends are cryptographically identified before a single byte of the request is processed.

```go
clientCAs := x509.NewCertPool()
pem, _ := os.ReadFile("client-ca.crt")
clientCAs.AppendCertsFromPEM(pem)

srv := &http.Server{
    Addr:    ":8443",
    Handler: mux,
    TLSConfig: &tls.Config{
        MinVersion: tls.VersionTLS12,
        ClientCAs:  clientCAs,
        ClientAuth: tls.RequireAndVerifyClientCert, // reject anyone without a valid cert
    },
}
```

mTLS is worth the operational cost when the caller is a *known, enrolled identity*: another one of your services (a service mesh handles cert issuance and rotation for you), a partner integration, or a small set of high-assurance clients like a settlement system moving money. It is a poor fit for a large, open population of end-user clients — you cannot realistically provision and rotate a client certificate for every mobile app install, and for that audience a bearer token or OAuth flow is the right tool. Use mTLS as a network-identity layer *underneath* application auth, not as a replacement for it.

---

## Sensitive data exposure: give back only what's needed

OWASP flags sensitive-data problems on both ends of the request. On the way out, the classic API failure is *returning more than the caller needs* — the excessive-data-exposure pattern this series covered when discussing authorization. A handler serializes the whole database row (including `password_hash`, `full_pan`, internal flags) and leans on the client to display only some fields. Anyone reading the raw response gets the rest.

The fix is to serialize an explicit response type, never the storage model:

```go
// Storage model — never serialized to a client directly.
type Account struct {
    ID           string
    Email        string
    PasswordHash string
    FullPAN      string // 16-digit card number
    InternalRisk int
}

// Response DTO — the only shape a caller ever sees.
type AccountResponse struct {
    ID       string `json:"id"`
    Email    string `json:"email"`
    CardLast4 string `json:"card_last4"`
}

func toResponse(a Account) AccountResponse {
    return AccountResponse{
        ID:        a.ID,
        Email:     a.Email,
        CardLast4: a.FullPAN[len(a.FullPAN)-4:], // expose 4 digits, never 16
    }
}
```

A separate response DTO is not busywork — it is the boundary that makes over-exposure a compile-time decision instead of an accident. Adding a sensitive column to `Account` later cannot leak it, because nothing copies it into `AccountResponse` unless a human writes that line.

For the most sensitive fields, storing them at all is the risk. Two techniques reduce it:

- **Field-level (application-layer) encryption** — encrypt specific columns (SSNs, health data) with a key from your KMS before they hit the database, so a stolen DB dump or a snooping DBA sees ciphertext. This is *in addition to* encryption at rest, and it narrows who can decrypt to the services holding the key.
- **Tokenization** — replace a secret like a card **PAN** (Primary Account Number) with a random surrogate token, and keep the real value in a hardened vault. Your services and logs carry the token; only the vault can detokenize. In the fintech world this is how you keep the bulk of your systems *out of PCI DSS scope* — most of the estate never touches a real card number, so there is nothing to steal there.

Everything you *do* store should sit on **encryption at rest**: full-disk/volume encryption plus database transparent data encryption, with the keys held in a **KMS** (Key Management Service) rather than on the same disk. KMS-managed keys give you central access control, an audit trail of every decrypt, and a rotation schedule — rotate the data-encryption key on a cadence and immediately on any suspected compromise.

---

## Secrets management: out of code, out of the image

API keys, database credentials, and JWT/webhook signing keys are the crown jewels — whoever holds them *is* your service. They belong in a dedicated **secret manager** (HashiCorp Vault, AWS Secrets Manager, GCP Secret Manager, Azure Key Vault), fetched at runtime, never written into source, config files, or container images.

```go
// Read secrets from the environment, which is populated at runtime
// by the secret manager / orchestrator — NOT from a committed file.
dbPassword := os.Getenv("DB_PASSWORD")
signingKey := os.Getenv("JWT_SIGNING_KEY")
if dbPassword == "" || signingKey == "" {
    log.Fatal("required secret not provided by the secret manager")
}
```

Apply the same discipline the AI Security series applied to model and provider keys: **least privilege** (each service reads only the secrets it needs), **rotation** (short-lived, automatically rolled credentials beat long-lived static ones), and **auditing** (the manager logs who fetched what and when). Dynamic secrets — where the manager mints a fresh, expiring database credential per service on request — mean a leaked value is useless within minutes.

```bash
# A pre-commit / CI guardrail: fail the build if a likely secret is committed.
# gitleaks scans the diff for high-entropy strings and known key formats.
gitleaks protect --staged --redact --verbose || {
  echo "Potential secret in staged changes — commit blocked." >&2
  exit 1
}
```

**The gotcha:** secrets committed to the repo, or baked into a container image as build args or a copied `.env`, are the single most common way credentials leak. Git history is forever — a key deleted in the next commit still lives in the history and in every clone and fork, so it must be treated as compromised and rotated, not just removed. An image pushed to a registry carries every layer, including the one that `COPY`'d your `.env`. Keep secrets in a manager, inject them at runtime, and scan diffs in CI so a mistake never reaches `main`.

---

## PII handling and logging hygiene

Logs are the leak nobody plans for. A well-meant "log the full request and response so we can debug" line quietly writes card numbers, bearer tokens, passwords, and personal data to a log store that has looser access controls than your database and often ships to a third-party aggregator. Logs are data too — they need the same minimization and, where they must contain sensitive fields, the same protection.

The rule is **redact before you write**, not after. Structure your logs, and pass values through a redactor that masks known-sensitive keys:

```go
var sensitiveKeys = map[string]bool{
    "password": true, "authorization": true, "token": true,
    "pan": true, "card_number": true, "ssn": true, "cvv": true,
}

// redact returns a copy safe to log: sensitive values are masked,
// so the original PII/secret never reaches the log sink.
func redact(fields map[string]any) map[string]any {
    out := make(map[string]any, len(fields))
    for k, v := range fields {
        if sensitiveKeys[strings.ToLower(k)] {
            out[k] = "[REDACTED]"
            continue
        }
        out[k] = v
    }
    return out
}

func logRequest(logger *slog.Logger, fields map[string]any) {
    logger.Info("request", "fields", redact(fields)) // masked before it hits the sink
}
```

Prefer logging identifiers over values — a `user_id` instead of an email, a token's ID or last four characters instead of the token. Never log full request/response bodies for endpoints that carry sensitive data. And set retention: PII you no longer need is liability you are still storing, so expire logs on a schedule.

**The gotcha:** logging full request and response bodies is the leak that survives your best transport and storage encryption. TLS protected the bytes on the wire and at-rest encryption protected the database, but the moment you `logger.Info("body", rawJSON)` you copy the PAN and the bearer token in cleartext into a system that indexes it, replicates it, and forwards it to an analytics vendor. Redact at the point of writing — a filter applied after the fact always misses the field added last week.

---

## Security-relevant HTTP headers, and the CORS trap

A few response headers harden an API surface. HSTS (above) is the important one for transport. `Content-Type: application/json` with `X-Content-Type-Options: nosniff` stops a browser from re-interpreting a JSON response as HTML. `Cache-Control: no-store` on responses carrying sensitive data keeps them out of shared caches.

**CORS deserves its own paragraph because it is routinely misunderstood.** Cross-Origin Resource Sharing is *not* a security defense — it is a browser mechanism that *relaxes* the same-origin policy to let specific web origins call your API from the browser. It protects the *user's browser session*, not your API; a non-browser client (curl, a server, a script) ignores CORS entirely. So CORS never replaces authentication or authorization. But a *misconfigured* CORS policy is a genuine vulnerability, because it can invite hostile web pages to make credentialed calls on a logged-in user's behalf.

Do it with an explicit allow-list, and never combine a wildcard origin with credentials:

```go
var allowedOrigins = map[string]bool{
    "https://app.example.com":     true,
    "https://console.example.com": true,
}

func cors(next http.Handler) http.Handler {
    return http.HandlerFunc(func(w http.ResponseWriter, r *http.Request) {
        origin := r.Header.Get("Origin")
        if allowedOrigins[origin] { // exact match against a known set
            w.Header().Set("Access-Control-Allow-Origin", origin)
            w.Header().Set("Vary", "Origin") // caches must key on Origin
            w.Header().Set("Access-Control-Allow-Credentials", "true")
            w.Header().Set("Access-Control-Allow-Methods", "GET, POST, OPTIONS")
            w.Header().Set("Access-Control-Allow-Headers", "Authorization, Content-Type")
        }
        if r.Method == http.MethodOptions {
            w.WriteHeader(http.StatusNoContent)
            return
        }
        next.ServeHTTP(w, r)
    })
}
```

**The gotcha:** the two CORS configurations that hand your API to any website are `Access-Control-Allow-Origin: *` together with `Access-Control-Allow-Credentials: true`, and *reflecting* whatever `Origin` the request sent back into the allow header. The first is actually rejected by browsers when credentials are involved — but developers "fix" the resulting error by reflecting the origin, which is worse: it means *every* origin is allowed, including the attacker's phishing page, and now it can make authenticated requests using the victim's cookies. Match against a fixed allow-list of exact origins, add `Vary: Origin` so a permissive cached response is not served to the wrong site, and never echo an untrusted origin back.

---

## Where each control fits

| Concern | Control | Protects against |
|---|---|---|
| Data in transit | TLS 1.2+/1.3, HTTPS-only, HSTS | Eavesdropping, downgrade, MITM |
| Internal traffic | mTLS / mesh encryption | Attacker already inside the perimeter |
| Over-exposure in responses | Response DTO, not the storage model | Leaking fields nobody requested |
| Most sensitive fields | Field-level encryption, tokenization | DB dump theft, PCI scope creep |
| Data at rest | Disk/DB encryption, KMS-managed keys | Stolen volumes, backups, insider access |
| Credentials & keys | Secret manager, least privilege, rotation | Committed/baked-in secret leaks |
| PII in logs | Redact before write, log IDs not values | The debug-logging leak |
| Browser cross-origin calls | Exact-match CORS allow-list | Hostile sites making credentialed calls |

---

## Key takeaways

- **Encrypt in transit, everywhere.** HTTPS-only with modern TLS and HSTS, and mTLS or mesh encryption for service-to-service traffic — zero-trust means "internal" is not a reason to send plaintext.
- **Give back only what's needed.** Serialize an explicit response DTO, never the storage row, so over-exposure is a line of code a human has to write, not an accident.
- **Shrink the blast radius of stored data.** Encrypt at rest with KMS-managed, rotated keys; add field-level encryption for the most sensitive columns; tokenize secrets like PANs so most of your systems never hold the real value.
- **Keep secrets out of code and images.** A secret manager, least privilege, rotation, and a CI secret-scan beat any `.env` in the repo — and a leaked key is compromised the moment it lands in git history.
- **Redact before you log.** Full request/response logging is the leak that outlives your encryption; mask sensitive keys at write time and log identifiers, not values.
- **CORS is not a defense — but misconfiguring it is a vulnerability.** Allow-list exact origins, never pair a wildcard with credentials, and never reflect the request's origin back.

---

## Further reading

- [OWASP Cheat Sheet — Transport Layer Security](https://cheatsheetseries.owasp.org/cheatsheets/Transport_Layer_Protection_Cheat_Sheet.html)
- [OWASP Cheat Sheet — Cryptographic Storage](https://cheatsheetseries.owasp.org/cheatsheets/Cryptographic_Storage_Cheat_Sheet.html)
- [OWASP Cheat Sheet — Secrets Management](https://cheatsheetseries.owasp.org/cheatsheets/Secrets_Management_Cheat_Sheet.html)
- [OWASP Cheat Sheet — Cross-Origin Resource Sharing (CORS)](https://cheatsheetseries.owasp.org/cheatsheets/HTML5_Security_Cheat_Sheet.html#cross-origin-resource-sharing)
- [Mozilla — Server Side TLS configuration guidelines](https://wiki.mozilla.org/Security/Server_Side_TLS)
- [OWASP Cheat Sheet — Logging](https://cheatsheetseries.owasp.org/cheatsheets/Logging_Cheat_Sheet.html)
