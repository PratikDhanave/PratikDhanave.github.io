# OpenID Connect: Authentication on OAuth

*Everyone kept using OAuth to log users in, and everyone kept doing it slightly wrong, because OAuth was never designed to answer "who is this user?" OpenID Connect is the fix: a thin, standardized authentication layer on top of OAuth that adds one crucial thing — an ID token that securely tells you who the user is. It's what "Sign in with Google" actually runs on.*

The tokens post named the ID token as the *authentication* credential. This post covers the protocol that introduced it — **OpenID Connect (OIDC)** — and why it exists. OIDC is the modern standard for federated login, and understanding it as "OAuth plus a proper answer to *who are you*" is the key. Everything you know about OAuth flows and tokens carries over; OIDC just adds the authentication piece OAuth was missing.

## Why OAuth alone isn't login

Recall the recurring theme: OAuth 2.0 is *authorization* — it gets an app *permission to access resources*. Developers constantly wanted to use "Sign in with [provider]" for *login*, and reached for OAuth to do it. The problem, from the first post: an OAuth **access token proves an app was authorized, not who the user is.** Trying to authenticate with OAuth alone leads to subtle but real insecurities:

- An access token is meant for an API, not as proof of identity — using it to establish "who is logged in" conflates authorization with authentication.
- Different providers implemented "get the user's info" differently, so every "Sign in with X" integration was bespoke and error-prone.
- There was no *standard, verifiable* statement of "this specific user was authenticated by this provider at this time" that a client could trust.

OIDC was created to solve exactly this: to provide a **standard authentication layer** on top of OAuth so that federated login is done consistently and securely. It doesn't replace OAuth; it *extends* it.

## What OIDC adds: the ID token

The core addition of OIDC is the **ID token** — a JWT (from the tokens post) that is a *verifiable statement of authentication*. Where an access token says "the bearer may access these resources," an ID token says "*this specific user* was authenticated by *this issuer* at *this time*." It's issued to the **client** and meant for the client to consume, answering "who is the user?"

Its standard **claims** make it a reliable identity statement:

```text
ID token (a JWT) claims:
  iss  — issuer (which provider authenticated the user)
  sub  — subject: a STABLE unique identifier for the user
  aud  — audience: which client this token is for
  exp  — expiry;  iat — issued-at
  auth_time, nonce — when authenticated; replay protection
  (+ profile claims: name, email, etc. via scopes)
```

The most important claim is **`sub`** — a stable, unique identifier for the user *from that provider*. This is what you key your user records on. A critical subtlety: use `sub` (together with `iss`), **not email**, as the user's identity — emails can change or be reused, while `sub` is stable and unique per provider. Building your "who is this user" logic on email instead of `sub` is a common identity bug.

Because the ID token is a signed JWT, the client **validates it** exactly as the tokens post described — signature, expiry, issuer, *and audience* (confirming the token was minted for *this* client) — plus checking the `nonce` to prevent replay. A properly validated ID token is a trustworthy answer to "who is this user," which is precisely what OAuth alone couldn't give.

## How OIDC works: OAuth plus a scope

The elegance of OIDC is how *little* it adds mechanically. It runs the same OAuth authorization code flow (with PKCE) from the flows post, with two additions:

```text
1. Client starts the OAuth authorization code + PKCE flow,
   requesting the special scope "openid"  (this signals OIDC)
2. User authenticates and consents at the provider (the OpenID Provider)
3. Client exchanges the code and receives:
     - an ACCESS token (OAuth, for APIs)  AND
     - an ID TOKEN (OIDC, proving who the user is)
4. Client VALIDATES the ID token → knows who the user is → logs them in
```

- Requesting the **`openid` scope** is the switch that turns an OAuth flow into an OIDC flow — it tells the provider "also authenticate the user and return an ID token."
- Additional scopes like `profile` and `email` request specific identity claims (name, email) to be included or available.
- The **UserInfo endpoint** is an OIDC-standard API where the client can fetch additional profile claims using the access token, if not all are in the ID token.

So OIDC reuses OAuth's entire machinery and adds: the `openid` scope, the ID token, standardized claims, and the UserInfo endpoint. That's why it's described as a *thin layer* — it's OAuth for the flow, plus a standard, secure identity statement on top. In OIDC terminology, the authorization server is called the **OpenID Provider (OP)** and the client is the **Relying Party (RP)**.

## Why OIDC won for modern login

OIDC became the standard for consumer and modern federated login for good reasons:

- **It standardizes what was ad hoc.** One protocol for "Sign in with X" across providers, instead of a bespoke OAuth-based integration per provider. The ID token and claims are standardized, so integrations are consistent.
- **It's secure by design for authentication.** It provides the verifiable identity statement OAuth lacked, done through the secure authorization code + PKCE flow, with validation rules that prevent the common mistakes.
- **It builds on OAuth.** You get authentication (ID token) *and* authorization (access token) from one flow — log the user in *and* get permission to call APIs on their behalf, together.
- **It's simpler and more developer-friendly than SAML** (next post) — JSON/JWT and REST-style flows instead of XML, better suited to modern web, mobile, and SPA clients.

The practical guidance: for new applications needing federated login or "Sign in with…", **OIDC is the default choice.** It's the right, standard, secure way to do the authentication that people were incorrectly bolting onto raw OAuth. The next post covers the older standard that still dominates one domain — enterprise SSO — SAML, and when you'll meet it instead.

## Key takeaways

- OAuth alone can't do login: an access token proves authorization (an app may access resources), not identity (who the user is) — so authenticating with raw OAuth is subtly insecure and was done inconsistently across providers.
- OpenID Connect fixes this by adding the ID token — a signed JWT that is a verifiable statement that a specific user was authenticated by a specific issuer at a specific time, issued to and consumed by the client.
- Key the user on the `sub` claim (stable, unique per provider) together with `iss` — not email, which can change or be reused; validate the ID token (signature, expiry, issuer, audience, nonce) like any JWT.
- OIDC is a thin layer on OAuth: run the authorization code + PKCE flow with the `openid` scope, receive both an access token (APIs) and an ID token (identity), plus a standard UserInfo endpoint for more claims — provider is the OpenID Provider, client the Relying Party.
- OIDC is the modern default for federated login: it standardizes "Sign in with…" securely, gives authentication and authorization in one flow, and is simpler and more developer-friendly (JSON/JWT/REST) than SAML.

## Further reading

- [OpenID Connect Core specification](https://openid.net/specs/openid-connect-core-1_0.html)
- [Tokens: access, refresh, and JWTs (previous post)](/blog/posts/identity-04-tokens-and-jwts.html)
- [openid.net — how OpenID Connect works](https://openid.net/developers/how-connect-works/)
