# Authentication: Proving Who Is Calling Your API

*The second post in the API Security series — a practical tour of API keys, session cookies, bearer tokens, OAuth 2.0, OIDC and JWTs, plus how to verify a token correctly and where authentication quietly breaks.*

---

Authentication is the part of an API that answers one question: *who is making this request?* Get it wrong and everything downstream is built on sand — every access-control check, every audit log, every rate limit assumes it already knows the caller. This is why broken authentication sits near the top of the OWASP API Security Top 10 (it is API2:2023). The failures are rarely exotic: an endpoint that forgets to check a token, a token whose signature is never verified, a credential that lives forever because nobody built rotation.

This post walks the options for proving identity — from the humble API key up to OAuth 2.0 and OpenID Connect — and shows how to validate a token without stepping on the classic landmines. One theme runs through all of it: **authentication proves identity; it does not grant permission.** Deciding *what* an authenticated caller may do is authorization, and that is the subject of the next post.

---

## The identities you might be proving

Before picking a mechanism, be clear about *what* you are identifying. There are two very different subjects:

- **An application** — some client software (a mobile app, a backend service, a partner integration) is calling you. You want to know which registered client it is.
- **A user** — a specific human is acting, usually through some client. You want to know which account.

API keys identify the first. Sessions, OAuth user flows and OIDC identify the second. Conflating them is a common design error: an API key in a mobile app does *not* tell you which user is holding the phone, only that the app build is legitimate.

---

## API keys: identify an app, not a person

An API key is a long, opaque, high-entropy string a client sends on every request, usually in a header:

```http
GET /v1/reports HTTP/1.1
Host: api.example.com
Authorization: Bearer ak_live_9f2c8d4a7b1e6f3c0a5d2e8b4c1f7a9d
```

Keys are simple and great for server-to-server calls where a full OAuth exchange is overkill. But they carry no notion of a user, no expiry, and no built-in scope. That puts the entire burden on you:

- **Store hashes, not keys.** Treat a key like a password. Persist only a hash (a fast keyed hash such as HMAC-SHA-256, or a slow password hash if you prefer), so a database leak does not hand out working credentials. Show the raw key to the owner exactly once, at creation.
- **Scope every key.** Bind it to a specific client, a set of allowed operations, maybe an IP allowlist. A read-only reporting key should never be able to write.
- **Rotate on a schedule.** Support two live keys per client so rotation is zero-downtime: issue the new key, let the client cut over, then revoke the old one.
- **Prefix and label.** A prefix like `ak_live_` lets secret scanners (and your own logs-scrubbing) recognise a leaked key on sight.

**The gotcha:** API keys identify an *application*, not a user, and they do not expire on their own. A key that leaks into a git commit or a client-side bundle stays valid until *you* notice and revoke it. Never ship one in front-end JavaScript or a mobile binary as if it were a user credential — scope it tightly and rotate it on a schedule rather than trusting it to age out.

---

## Session cookies: the browser's native answer

For a server-rendered web app talking to its own backend, session cookies are still the right tool. The server creates a session, stores state server-side (or in a signed cookie), and the browser resends the cookie automatically on every request:

```http
Set-Cookie: session=Ux8...; HttpOnly; Secure; SameSite=Lax; Path=/
```

The three flags matter:

- `HttpOnly` keeps JavaScript from reading the cookie, blunting token theft via XSS.
- `Secure` refuses to send it over plain HTTP.
- `SameSite` controls whether the cookie rides along on cross-site requests.

Because the browser attaches the cookie *automatically*, cookies are vulnerable to **CSRF**: a malicious page can trigger a state-changing request to your API and the browser helpfully includes the session. `SameSite=Lax` or `Strict` closes most of this, but for anything cross-origin you also want an anti-CSRF token (the synchroniser or double-submit pattern).

**The gotcha:** the same property that makes cookies convenient — automatic attachment — is exactly what makes them CSRF-prone. Bearer tokens in an `Authorization` header are *not* sent automatically by the browser, so they sidestep CSRF but must be stored and attached by your code (and kept out of `localStorage` if XSS is a concern). Pick one model per client and understand its threat; do not mix cookie auth and header auth on the same endpoint without thinking it through.

---

## Bearer tokens and OAuth 2.0

A **bearer token** is any credential where possession alone grants access — "bearer" meaning whoever holds it can use it. API keys and OAuth access tokens are both bearer tokens. The name is a warning: there is no second factor binding the token to its rightful holder, so a stolen bearer token *is* the identity until it expires. That is why transport security (TLS everywhere) and short lifetimes are non-negotiable.

**OAuth 2.0** (RFC 6749) is the framework for issuing those tokens without handing your credentials to every app. Its value is *delegation*: a user lets a client act on their behalf at a resource server, without the client ever seeing the user's password. Four roles are worth memorising:

- **Resource owner** — the user who owns the data.
- **Client** — the app requesting access.
- **Authorization server** — issues tokens after authenticating the resource owner.
- **Resource server** — your API, which accepts and validates the tokens.

### Which grant type, and when

The grant type is *how* a client obtains a token. Only two are recommended today:

| Grant | Use it for | Notes |
|---|---|---|
| Authorization Code + PKCE | User-facing apps (web, mobile, SPA) | The default for anything with a user. PKCE is now required for all clients. |
| Client Credentials | Machine-to-machine, no user present | The client authenticates as itself and gets a token for its own access. |

The current OAuth Security Best Current Practice (RFC 9700) is explicit about what to **avoid**:

- **Implicit grant** (`response_type=token`) — returned tokens directly in the URL fragment. Deprecated; use authorization code + PKCE instead.
- **Resource Owner Password Credentials (ROPC)** — the client collects the user's actual username and password. This defeats the entire point of OAuth and must not be used.

**PKCE** (Proof Key for Code Exchange) protects the authorization-code flow from interception. The client generates a random `code_verifier`, sends its hash (`code_challenge`) on the initial request, and later presents the raw verifier when redeeming the code. An attacker who steals the authorization code off the redirect cannot exchange it without the verifier.

```http
GET /authorize?response_type=code
  &client_id=s6BhdRkqt3
  &redirect_uri=https://app.example.com/callback
  &scope=read:reports
  &state=xyz
  &code_challenge=E9Melhoa2OwvFrEMTJguCHaoeK1t8URWbuGJSstw-cM
  &code_challenge_method=S256 HTTP/1.1
Host: auth.example.com
```

**The gotcha:** OAuth 2.0 is an *authorization* framework — it gets a client a token to call an API. It was never designed to tell the client *who the user is*. Bolting identity onto raw OAuth (for example, treating an access token as proof of login) is how "log in with X" implementations leak. When you need identity, use OpenID Connect, which was built for exactly that.

---

## OpenID Connect: the identity layer

**OpenID Connect (OIDC)** is a thin standard layer on top of OAuth 2.0 that adds authentication. Alongside the access token, the authorization server returns an **ID token** — a JWT with standard claims about the authentication event: who the user is (`sub`), who issued it (`iss`), who it is for (`aud`), when it was issued (`iat`) and when it expires (`exp`).

The distinction is worth holding onto:

- The **access token** is for calling APIs. Your resource server validates it. The client should treat it as opaque.
- The **ID token** is for the client. It tells the client "this user just authenticated." It is *not* meant to be sent to your API as an access credential.

OIDC also standardises discovery (`/.well-known/openid-configuration`) and a JWKS endpoint that publishes the signing keys — which is exactly what you need to verify tokens, coming up next.

---

## JWTs: structure and stateless validation

A **JSON Web Token** (RFC 7519) is a compact, signed (and optionally encrypted) container of claims. Both OAuth access tokens and OIDC ID tokens are frequently JWTs. The format is three Base64URL segments joined by dots:

```
eyJhbGciOiJSUzI1NiIsImtpZCI6ImsxIn0   ← header
.
eyJpc3MiOiJodHRwczovL2F1dGguZXhhbXBsZS5jb20iLCJhdWQiOiJhcGk...   ← payload
.
Z3J1bXB5LWNhdC1zaWduYXR1cmU...   ← signature
```

- **Header** — the signing algorithm (`alg`) and often a key id (`kid`).
- **Payload** — the claims: `iss`, `aud`, `sub`, `exp`, `iat`, plus whatever you add.
- **Signature** — a MAC or digital signature over `header.payload`, computed with the issuer's key.

The appeal is **stateless validation**: your API can verify a JWT with just the issuer's public key, no database round-trip, no session store. That is also the trap — statelessness means you must check *everything* yourself, and a token you cannot un-issue.

A correct validation checks all of the following, and rejects on any failure:

1. The signature, using the algorithm **you** expect and the key **you** trust.
2. `exp` — not expired (with a small clock-skew leeway at most).
3. `nbf` / `iat` — not used before it is valid.
4. `aud` — the token is intended for *your* API.
5. `iss` — the token came from the issuer you trust.

### The classic JWT pitfalls

The JWT Best Current Practices (RFC 8725) exist because these mistakes are common and severe:

- **`alg: none`.** The spec allows an "unsecured" JWT with no signature. A library that honours the token's own `alg` header will happily accept a forged, unsigned token. Never allow `none`.
- **Algorithm confusion (RS256 ↔ HS256).** If your API verifies with a *public* RSA key but a naive library lets an attacker switch `alg` to `HS256`, the library may use that public key as an HMAC *secret* — which is public — and the attacker forges valid tokens. Pin the expected algorithm; do not let the token pick.
- **Not verifying the signature at all.** Decoding a JWT is not verifying it. Plenty of code base64-decodes the payload, reads `sub`, and trusts it. Always call the *verify* path, never a bare decode.
- **Skipping `exp` / `aud` / `iss`.** A token minted for another service, or one that expired last week, must be rejected. A token valid for `aud: other-service` should not open *your* API.
- **Long-lived tokens with no revocation.** A JWT is valid until it expires; there is no server-side "log out" for a stateless token.
- **Secrets in the payload.** The payload is signed, not encrypted — anyone can base64-decode and read it. Never put passwords, keys or PII you would not print in a log.

**The gotcha:** never accept the token's own `alg` header blindly. `alg: none` and the RS256→HS256 confusion are real, exploited bypasses, not theory. Pin the algorithm *and* the key on the verifier side, so a token that says "verify me with none" or "verify me with HMAC" is rejected before its claims are ever read.

---

## Verifying a JWT correctly

Here is the shape of a correct verification in Go, using a JWKS-published RSA key. The load-bearing detail is `WithValidMethods` — it pins the accepted algorithm so a forged `alg` never reaches the key.

```go
import "github.com/golang-jwt/jwt/v5"

func verify(tokenString string, keyfunc jwt.Keyfunc) (*jwt.Token, error) {
    return jwt.Parse(
        tokenString,
        keyfunc, // returns the RSA public key for the token's kid
        jwt.WithValidMethods([]string{"RS256"}), // PIN the algorithm — no "none", no HS256
        jwt.WithExpirationRequired(),            // exp must be present and unexpired
        jwt.WithAudience("https://api.example.com"), // aud must match us
        jwt.WithIssuer("https://auth.example.com"),  // iss must be trusted
        jwt.WithLeeway(30*time.Second),          // small clock-skew tolerance only
    )
}
```

And in Python with PyJWT, the same pins — `algorithms` is a fixed allowlist, and `audience` / `issuer` are checked:

```python
import jwt  # PyJWT
from jwt import PyJWKClient

def verify(token: str) -> dict:
    jwk_client = PyJWKClient("https://auth.example.com/.well-known/jwks.json")
    signing_key = jwk_client.get_signing_key_from_jwt(token)
    return jwt.decode(
        token,
        signing_key.key,
        algorithms=["RS256"],            # allowlist — never read alg from the token
        audience="https://api.example.com",
        issuer="https://auth.example.com",
        options={"require": ["exp", "iat", "aud", "iss"]},
    )
```

Note what both do: the algorithm is an explicit allowlist, expiry is required, and audience and issuer are matched. Drop any of those and you have re-created one of the pitfalls above.

---

## An API-key middleware with constant-time comparison

For plain API-key auth, the subtle bug is comparing the presented key against the stored one with `==`. A naive string comparison returns as soon as two bytes differ, and that timing difference can leak the key byte by byte to a patient attacker. Compare in **constant time**.

```go
import (
    "crypto/hmac"
    "crypto/sha256"
    "net/http"
)

// storedHash is HMAC-SHA-256(serverKey, apiKey), computed once at key creation.
func apiKeyMiddleware(storedHash []byte, serverKey []byte, next http.Handler) http.Handler {
    return http.HandlerFunc(func(w http.ResponseWriter, r *http.Request) {
        presented := r.Header.Get("X-API-Key")
        if presented == "" {
            http.Error(w, "missing API key", http.StatusUnauthorized)
            return
        }
        mac := hmac.New(sha256.New, serverKey)
        mac.Write([]byte(presented))
        // hmac.Equal is constant-time; a plain == would leak timing.
        if !hmac.Equal(mac.Sum(nil), storedHash) {
            http.Error(w, "invalid API key", http.StatusUnauthorized)
            return
        }
        next.ServeHTTP(w, r)
    })
}
```

The Python equivalent uses `hmac.compare_digest`, which is likewise designed to run in constant time:

```python
import hmac, hashlib

def check_api_key(presented: str, stored_hash: bytes, server_key: bytes) -> bool:
    computed = hmac.new(server_key, presented.encode(), hashlib.sha256).digest()
    return hmac.compare_digest(computed, stored_hash)  # constant-time
```

**The gotcha:** compare secrets, keys and MACs in constant time, always. A regular `==` or `bytes.equal` short-circuits on the first differing byte, and that timing signal is enough to reconstruct a secret over many requests. Use `hmac.Equal` / `hmac.compare_digest` (or your language's equivalent) for anything an attacker gets to guess repeatedly.

---

## Access tokens, refresh tokens and rotation

Short-lived access tokens limit the blast radius of theft, but forcing the user to log in every few minutes is hostile. The standard answer is a pair:

- **Access token** — short life (minutes), sent on every API call. If stolen, it expires quickly.
- **Refresh token** — longer life, kept private by the client, sent *only* to the authorization server to mint a fresh access token.

The security-critical practice is **refresh token rotation**: each time a refresh token is redeemed, the authorization server issues a *new* refresh token and invalidates the old one. If a stolen refresh token is later replayed, the server sees a already-used token and can revoke the whole token family — turning theft into a detectable event rather than silent, indefinite access. RFC 9700 recommends rotation (or sender-constraining) for exactly this reason.

**The gotcha:** a JWT cannot be un-issued. A long expiry with no revocation list means a stolen access token stays valid until it lapses — there is no "log out" that reaches a token already in an attacker's hands. Keep access-token lifetimes short, put revocation behind the refresh flow (rotate refresh tokens, maintain a server-side denylist for the rare emergency), and resist the temptation to issue a 24-hour access token because refresh "is annoying."

---

## MFA and step-up, briefly

Everything above proves you hold *a* credential. **Multi-factor authentication** raises the bar at the moment of login by requiring a second factor — something you have (a device, a passkey) or are (a biometric) — so a stolen password alone is not enough. From an API's perspective, MFA usually happens at the authorization server and shows up as a claim in the resulting token (for example, an `amr` or `acr` claim describing how the user authenticated).

**Step-up authentication** is the useful extension: most endpoints accept an ordinary token, but a few high-risk ones (change bank details, delete an account) demand a fresh, stronger authentication first. Your API enforces this by inspecting the authentication-context claims and rejecting the request — typically with a challenge — when the token was not minted with a strong-enough factor recently enough. It is a clean way to keep everyday use frictionless while gating the dangerous operations.

---

## Key takeaways

- **Authentication is not authorization.** Proving *who* is calling is this post; deciding *what* they may do is the next one. Never let a valid token imply permission.
- **Match the mechanism to the subject.** API keys identify apps; sessions, OAuth user flows and OIDC identify users. Do not use one where you need the other.
- **Pin the algorithm and the key when verifying JWTs.** Reject `alg: none`, refuse algorithm swaps, and always verify signature, `exp`, `aud` and `iss` — decoding is not verifying.
- **Use authorization code + PKCE for users and client credentials for machines.** Avoid the deprecated implicit and ROPC grants entirely.
- **Plan for revocation and rotation.** Short access tokens, rotating refresh tokens, scoped-and-rotated API keys, and constant-time secret comparison turn credential theft from silent disaster into a bounded, detectable event.

Authentication is the foundation, not the whole building. Once you know *who* is calling — reliably, with tokens you actually verify — you can start deciding what they are allowed to touch. That is authorization, and where the next post picks up.

---

## Further reading

- [The OAuth 2.0 Authorization Framework (RFC 6749)](https://datatracker.ietf.org/doc/html/rfc6749)
- [OAuth 2.0 Security Best Current Practice (RFC 9700)](https://datatracker.ietf.org/doc/html/rfc9700)
- [Proof Key for Code Exchange — PKCE (RFC 7636)](https://datatracker.ietf.org/doc/html/rfc7636)
- [OpenID Connect Core 1.0](https://openid.net/specs/openid-connect-core-1_0.html)
- [JSON Web Token — JWT (RFC 7519)](https://datatracker.ietf.org/doc/html/rfc7519)
- [JSON Web Token Best Current Practices (RFC 8725)](https://datatracker.ietf.org/doc/html/rfc8725)
- [OWASP API Security Top 10 — API2:2023 Broken Authentication](https://owasp.org/API-Security/editions/2023/en/0xa2-broken-authentication/)
