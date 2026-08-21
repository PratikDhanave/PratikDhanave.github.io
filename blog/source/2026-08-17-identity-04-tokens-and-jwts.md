# Tokens: Access, Refresh, and JWTs

*Tokens are the currency of modern identity — they carry proof of authorization and identity across every request. But "token" hides real distinctions: access versus refresh versus ID tokens do different jobs, and a JWT you can read but must validate correctly is a razor that cuts both ways. Most identity vulnerabilities live in how tokens are issued, stored, and checked.*

The flows post ended with the client holding tokens. This post asks: what *is* a token, what kinds are there, and — critically — how do you validate one without introducing a vulnerability? Tokens are where authorization and authentication become concrete artifacts that travel with requests, and mishandling them (bad validation, insecure storage) is behind a large share of identity breaches. Getting tokens right is getting identity right.

## What a token is

A **token** is a string that represents a granted permission or a verified identity — a credential the client presents to prove it's allowed to do something, so it doesn't have to re-authenticate on every request. Broadly, tokens come in two structural styles:

- **Opaque tokens** — a random, meaningless string. It carries no information itself; the resource server must ask the authorization server (introspection) or look it up to learn what it grants. The state lives on the server.
- **Structured tokens (JWTs)** — self-contained tokens that *carry* their information (claims) inside them, cryptographically signed so they can be validated without a server lookup. The state travels in the token.

Both are legitimate; they trade off differently (opaque = easy to revoke, needs a lookup; JWT = self-contained and fast, harder to revoke — more below). The style matters for how you validate and revoke, which is where security lives.

## The three tokens and their jobs

Modern identity (OAuth + OIDC) issues up to three token types, and confusing their purposes is a classic, dangerous error:

- **Access token** — the *authorization* credential. The client sends it to the **resource server** (API) to access protected resources. It's short-lived, scoped, and answers "what may this client do?" It is **not** proof of user identity and should not be used as such.
- **Refresh token** — a long-lived credential used *only* to obtain new access tokens when they expire, without re-prompting the user. The client sends it to the **authorization server** (never to the resource server) to get a fresh access token. It's powerful (it mints access tokens), so it must be stored most securely.
- **ID token** — the *authentication* credential, introduced by OpenID Connect (next post). It's a JWT that tells the *client* who the user is (their verified identity and profile claims). It's meant for the client to consume, **not** to be sent to APIs as an access token.

```text
  access token  → sent to Resource Server (API)   → "what can I access?"  (authorization)
  refresh token → sent to Authorization Server     → "give me a new access token"
  id token      → consumed by the Client           → "who is the user?"    (authentication)
```

The cardinal rule: **use each token for its job.** Sending an ID token to an API, or treating an access token as identity, or exposing a refresh token to the browser — each is a security mistake. The token type encodes its purpose; respect it.

## Anatomy of a JWT

Since JWTs (JSON Web Tokens) dominate modern identity, understanding their structure is essential. A JWT is three Base64URL-encoded parts separated by dots:

```text
   header  .  payload  .  signature
   {alg,typ}  {claims}    crypto signature over header+payload

header:    algorithm and token type
payload:   claims — e.g. sub (subject/user id), iss (issuer),
           aud (audience), exp (expiry), iat (issued-at), scopes, roles
signature: signs the header+payload with the issuer's key
```

Two crucial properties:

- **A JWT is *encoded*, not *encrypted*.** Anyone holding it can decode and read the payload — the Base64 is not secrecy. So **never put secrets in a JWT payload**; assume its claims are readable by whoever has the token.
- **The signature is what makes it trustworthy.** The issuer signs the token; a recipient verifies the signature with the issuer's public key (or shared secret) to confirm the token is authentic and unmodified. The signature — not the encoding — is the security.

## Validating a JWT correctly

This is the security heart of the post, because *incorrect JWT validation is a common, severe vulnerability*. A JWT is only trustworthy if you validate it properly — accepting one you haven't fully checked is accepting forged identity. Correct validation means checking *all* of:

- **Signature** — verify it with the issuer's key, and **enforce the expected algorithm.** The infamous vulnerability: accepting a token whose header says `alg: none` (no signature) or letting an attacker downgrade the algorithm. Never trust the token's own `alg` header blindly; require the algorithm you expect.
- **Expiry (`exp`)** — reject expired tokens. A token past its expiry must not be accepted, no matter how valid its signature.
- **Issuer (`iss`)** — confirm it was issued by the authorization server you trust, not some other issuer.
- **Audience (`aud`)** — confirm the token was intended for *your* service. A token minted for a different service must not be accepted by yours, even if signed by the same issuer — skipping the audience check lets a token meant for API A be replayed against API B.

Skipping any of these is a hole. The safe path is to **use a well-maintained, vetted library** for JWT validation rather than hand-rolling it — the edge cases (algorithm confusion, key handling, clock skew) are exactly where hand-written validation fails. Validate signature + expiry + issuer + audience, always, with a trusted library.

## The revocation trade-off, and token storage

JWTs' self-contained nature creates their main weakness: **they're hard to revoke.** Because a valid signature and unexpired `exp` are sufficient, a JWT is accepted until it expires *even if you want to revoke it early* (the user logged out, the token leaked) — there's no server-side state to invalidate. The standard mitigations:

- **Keep access tokens short-lived** — so a leaked/should-be-revoked token is only dangerous briefly. Use refresh tokens to get new ones seamlessly.
- **Maintain a revocation/denylist** for the cases that need immediate invalidation (accepting the lookup cost that partly undoes JWTs' statelessness), or use opaque tokens with introspection where instant revocation matters.

And **token storage** is its own security-critical decision, especially in browsers:

- **Refresh tokens are the crown jewels** — long-lived and able to mint access tokens — so protect them most (secure, HttpOnly cookies or secure native storage), never expose them to JavaScript where XSS could steal them.
- **In browsers, storing tokens in `localStorage` risks XSS theft**; HttpOnly cookies protect against XSS but require CSRF defenses — a real trade-off with no perfect answer, handled carefully per app (the security post returns to this).

Tokens are where identity becomes tangible and where much can go wrong: use each token for its purpose, never put secrets in a JWT, validate signature/expiry/issuer/audience with a trusted library, keep access tokens short-lived, and guard refresh tokens above all. The next post covers the token that answers "who are you" — the ID token — and the protocol that adds it: OpenID Connect.

## Key takeaways

- A token represents granted permission or verified identity; it's either opaque (random, needs a server lookup, easy to revoke) or a structured JWT (self-contained, signed, fast to validate, hard to revoke).
- Three tokens have distinct jobs: access token → API (authorization, short-lived), refresh token → auth server only (mints new access tokens, guard most), ID token → client (authentication, who the user is) — use each only for its purpose.
- A JWT is header.payload.signature, Base64-*encoded* not encrypted (anyone can read the payload, so never put secrets in it); the signature, verified with the issuer's key, is what makes it trustworthy.
- Validate JWTs completely — signature (enforcing the expected algorithm, never trusting `alg: none` or the token's own header), expiry, issuer, and audience — using a vetted library, because incorrect validation is a common severe vulnerability.
- JWTs are hard to revoke (valid until expiry), so keep access tokens short-lived with refresh tokens, use denylists/opaque tokens where instant revocation matters, and store tokens carefully (guard refresh tokens; browser localStorage risks XSS, HttpOnly cookies need CSRF defenses).

## Further reading

- [JSON Web Token (JWT, RFC 7519)](https://datatracker.ietf.org/doc/html/rfc7519)
- [The OAuth flows (previous post)](/blog/posts/identity-03-oauth-flows.html)
- [API Security series](/blog/series/api-security/)
