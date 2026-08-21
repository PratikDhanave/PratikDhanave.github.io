# Sessions, Single Sign-On, and Logout

*Logging a user in is the easy part; keeping them logged in — and, harder than anyone expects, logging them out — is where identity gets subtle. Sessions bridge stateless requests into a continuous identity, single sign-on shares that identity across apps, and single logout is a genuinely hard problem that most systems get partly wrong.*

The protocols so far establish *who* a user is at login. But HTTP is stateless — each request stands alone — so something must remember that a user authenticated, across many requests and often many applications. That's **sessions**, **single sign-on (SSO)**, and the surprisingly thorny matter of **logout**. This post covers how authenticated identity persists after login, and why ending it cleanly is harder than starting it.

## Sessions: persisting identity across stateless requests

After a user authenticates, you don't want to re-authenticate them on every request. A **session** is the server-side (or token-based) memory that "this user is authenticated," referenced on each subsequent request. Two dominant models:

- **Server-side sessions (stateful).** The server stores session state (who the user is, when they logged in) and gives the browser a **session cookie** holding an opaque session ID. Each request sends the cookie; the server looks up the session. State lives on the server, so revocation is easy (delete the session), but it requires shared session storage to scale across servers (the state problem from distributed systems).
- **Token-based sessions (stateless).** The client holds a token (often a JWT) that *is* the proof of authentication, sent on each request; the server validates it without storing session state. Scales easily (no shared store), but inherits JWTs' revocation problem (from the tokens post) — you can't easily invalidate a valid, unexpired token.

The trade-off mirrors the tokens post: **stateful is easy to revoke but needs shared storage; stateless scales but is hard to revoke.** Many real systems combine them — a short-lived stateless access token for API calls plus a longer-lived, revocable server-side session or refresh token — to get scalability *and* revocability. The choice shapes both scaling and how cleanly you can log users out (below).

## Cookies: the session's vehicle, and its risks

Browser sessions ride on **cookies**, and cookie security is session security. The critical attributes:

- **`HttpOnly`** — the cookie is inaccessible to JavaScript, protecting the session ID/token from theft via **XSS**. Session cookies should almost always be HttpOnly.
- **`Secure`** — the cookie is only sent over HTTPS, preventing interception.
- **`SameSite`** — controls whether the cookie is sent on cross-site requests, a key defense against **CSRF** (an attacker's site triggering authenticated requests to yours). `SameSite=Lax` or `Strict` mitigates CSRF.

The recurring browser tension from the tokens post reappears: cookies (HttpOnly) resist XSS token theft but need **CSRF** protection; tokens in JavaScript-accessible storage avoid CSRF but are exposed to XSS. There's no free lunch — you pick a model and defend its weakness (HttpOnly cookies + CSRF tokens/SameSite is a common, solid choice). Session cookies must be HttpOnly, Secure, and SameSite-configured, with session IDs that are long, random, and regenerated on login (to prevent session fixation).

## Single sign-on: one login, many apps

**Single sign-on (SSO)** is the payoff of federated identity (OIDC/SAML): a user authenticates *once* with the identity provider and can then access *multiple* applications without logging in again. The mechanism builds on the sessions above:

```text
1. User logs into App A → authenticated at the IdP → IdP sets its OWN session
2. User visits App B → App B redirects to the IdP
3. IdP sees its existing session (user already authenticated) → issues a
   token/assertion to App B WITHOUT prompting for credentials again
4. User is logged into App B seamlessly
```

The key is that the **IdP maintains its own session.** Once you've authenticated to the IdP (via App A), it remembers you, so when App B redirects you there, the IdP recognizes the existing session and vouches for you immediately — no second login. This is why enterprise users log in once in the morning and access dozens of apps all day. Each app still gets its *own* proof (an ID token or SAML assertion) and establishes its *own* local session — SSO shares the *IdP's* authentication, not the apps' sessions.

## Logout: the genuinely hard problem

Here's the twist most systems underestimate: **logging out is much harder than logging in**, precisely because of sessions and SSO. Logging in creates *one* authenticated state; logging out must tear down *several*, and they don't all live in one place:

- **Local logout is easy** — end the session at *one* app (clear its session/cookie). But with SSO, the user is still logged into the *IdP* and every *other* app. Clicking "log out" of App A while remaining logged into the IdP means visiting App B logs you right back in — surprising and often a security problem (e.g. on a shared computer).
- **Single Logout (SLO) is hard** — logging out of *everything*: the IdP session *and* all the apps that share it. This requires the IdP to notify every application that the user's session should end, coordinating logout across independent systems — a distributed-systems problem (from that series) of propagating a state change to many parties, some of which may be unreachable. SAML defines a Single Logout profile and OIDC has logout mechanisms, but they're complex, inconsistently implemented, and frequently unreliable in practice.
- **Token-based sessions complicate it further** — if sessions are stateless JWTs, "logging out" doesn't invalidate an already-issued access token (it's valid until expiry, from the tokens post). True logout may require short token lifetimes plus a revocation list, or ending the refresh-token/server-side session so no *new* access tokens are minted.

The practical reality: **complete logout across an SSO ecosystem is genuinely difficult**, and many systems only do local logout, leaving the IdP session alive. Designing logout deliberately — deciding whether "log out" means this app, or everywhere, and implementing accordingly — is a real responsibility, especially for shared-device scenarios. Don't assume "log out" cleanly ends everything; it usually doesn't unless you engineer it to.

## Designing sessions and logout well

- **Choose a session model deliberately** — stateful (revocable, needs shared store) vs. stateless (scalable, hard to revoke), or a hybrid (short access token + revocable session/refresh token) for both benefits.
- **Lock down cookies** — HttpOnly, Secure, SameSite; long random session IDs regenerated on login; and defend the weakness of your model (CSRF for cookies, XSS for JS-accessible tokens).
- **Understand SSO shares the IdP session** — each app gets its own proof and local session; the IdP's session is what makes re-login seamless.
- **Design logout explicitly** — decide local vs. single logout, use short-lived tokens plus revocation for stateless sessions, and be especially careful on shared devices where lingering IdP sessions are a real risk.

Sessions and SSO are how login *persists*, and logout is where its difficulty concentrates. The final post pulls the whole series into the security practices that protect identity end to end.

## Key takeaways

- HTTP is stateless, so sessions persist authenticated identity across requests: server-side (stateful — easy to revoke, needs shared storage) or token-based (stateless — scales, hard to revoke), often combined as a short access token plus a revocable session/refresh token.
- Browser sessions ride on cookies, so cookie security is session security: HttpOnly (resists XSS token theft), Secure (HTTPS only), and SameSite (mitigates CSRF) — pick a model and defend its weakness (HttpOnly cookies + CSRF defense is a common solid choice).
- SSO works because the IdP maintains its own session: after one login, other apps redirecting to the IdP get a token/assertion without re-prompting — sharing the IdP's authentication, while each app keeps its own local session.
- Logout is much harder than login: local logout ends one app but leaves the IdP and other apps logged in; Single Logout (propagating logout to the IdP and all apps) is a hard distributed-systems problem, complex and often unreliable, and stateless tokens stay valid until expiry.
- Design sessions and logout deliberately: choose the session model on purpose, lock down cookies (HttpOnly/Secure/SameSite, random regenerated IDs), and decide explicitly whether "log out" means this app or everywhere — critical on shared devices.

## Further reading

- [SAML: enterprise SSO (previous post)](/blog/posts/identity-06-saml-enterprise-sso.html)
- [Distributed Systems: failure and resilience — propagating state across systems](/blog/posts/distsys-08-failure-and-resilience.html)
- [API Security series](/blog/series/api-security/)
