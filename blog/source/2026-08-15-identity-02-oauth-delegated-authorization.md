# OAuth 2.0: Delegated Authorization

*OAuth solved a specific, once-terrible problem: how does an app access your data on another service without you handing over your password? Its answer — a scoped, revocable token granted through a trusted intermediary — is elegant, but only if you remember what OAuth actually is. It's authorization, not login, and everything about it makes sense once you hold that firmly.*

The last post placed OAuth 2.0 as the **authorization** answer to "what are you allowed to do?" This post explains the framework itself: the problem it solves, its four roles, and how a delegated grant works at a high level. OAuth is the foundation the rest of the series builds on — OIDC sits on top of it, and tokens flow through it — so understanding its structure and *purpose* is essential.

## The problem OAuth solves

Before OAuth, if a third-party app wanted to access your data on another service — say, a printing app wanting your cloud photos — the only way was to give the app your *password* to that service. This was catastrophic:

- The app now had your full credentials and could do *anything* your account could, not just access photos.
- You couldn't revoke the app's access without changing your password (which broke everything else).
- Your password was stored by every app you'd ever connected — a breach at any of them exposed it.

OAuth 2.0 was designed to end this "password anti-pattern." Its core idea: **delegated authorization** — let you grant an app *limited, revocable* permission to access specific resources on your behalf, *without* ever sharing your password. The app gets a **token** representing that scoped permission, not your credentials. This is the whole point of OAuth, and it's why it's an *authorization* framework: it's about granting *access to resources*, not about proving *who you are*.

## The four roles

OAuth defines four roles, and naming them precisely dissolves most confusion, because every step of every flow is an interaction between them:

- **Resource Owner** — *you*, the user who owns the data and can grant access to it.
- **Client** — the *application* that wants to access the data on your behalf (the printing app). "Client" means the third-party app, not a browser or a person.
- **Authorization Server** — the server that *authenticates the resource owner* and *issues tokens* after they grant permission. This is the identity/OAuth provider (e.g. Google's OAuth server).
- **Resource Server** — the API that *holds the protected resources* and accepts tokens to serve them (the cloud photos API).

```text
  Resource Owner (you)
        │ grants permission
        ▼
  Client (the app)  ──asks──▶  Authorization Server  ──issues token──▶ Client
        │                          (authenticates you, gets consent)
        │ uses token
        ▼
  Resource Server (the API) ──serves the scoped resource──▶ Client
```

The elegance: the **client never sees your password**. You authenticate directly to the *authorization server*, approve a specific scope of access, and the client receives only a *token*. The client uses that token against the resource server. Your credentials stay between you and the authorization server.

## Scopes: limited permission

The "limited" in "limited permission" is expressed through **scopes** — named permissions the client requests and you approve. A client asks for specific scopes (`photos.read`, not `account.full`), and you see and consent to exactly what you're granting:

- **Scopes make access granular** — the printing app gets `photos.read`, not the ability to delete your photos or read your email. Least privilege, built in.
- **You consent to specific scopes** — the "this app wants to access X, Y, Z — allow?" screen is scope consent. You grant only what you approve.
- **The token carries the scope** — the resource server enforces that the token is only used for what was granted.

Scopes are how OAuth delivers *limited* delegation instead of all-or-nothing access — the direct fix for the old "give the app your password (and thus everything)" problem. Request the minimum scopes you need; over-requesting scares users and violates least privilege.

## Revocable, not permanent

The other half of the fix is **revocability**. Because the client holds a *token* rather than your password, that token can be revoked — by you (removing the app's access in your account settings) or by the authorization server — *without* affecting your password or other apps. This is impossible with the password anti-pattern (revoking meant changing your password and breaking everything). Tokens can also *expire* (a later post on tokens), so access is naturally time-bounded. Delegated access that's scoped *and* revocable *and* expiring is the security model OAuth exists to provide.

## What OAuth is NOT

Because it's so widely used, it's worth stating plainly what OAuth 2.0 is *not*, reinforcing the last post:

- **It is not authentication / login.** OAuth grants an app *access to resources*; it does not, by itself, tell the client *who the user is* in a secure, standard way. An access token means "this app may access these resources" — not "this is verified user Alice." Using a raw OAuth access token as proof of identity is the classic mistake OIDC (next posts) was created to fix.
- **It is not a single rigid protocol.** OAuth 2.0 is a *framework* with several **flows** (grant types) for different client situations — the subject of the next post. There isn't one "OAuth flow"; there are several, and choosing the right one is a real decision.
- **It doesn't define the token format.** OAuth says "the client gets a token" but historically didn't mandate what's *in* it — tokens can be opaque strings or structured JWTs (the tokens post). This flexibility is why token handling deserves its own discussion.

Holding "OAuth = delegated *authorization*, via scoped revocable tokens, through an authorization server, without sharing the password" firmly is what keeps everything downstream straight. The next post opens up *how* the client actually obtains a token — the OAuth flows — where the security-critical details live.

## Key takeaways

- OAuth 2.0 exists to end the "give the app your password" anti-pattern: it grants an application limited, revocable permission to access specific resources on your behalf without ever sharing your credentials — this is delegated authorization.
- Four roles structure it: resource owner (you), client (the app), authorization server (authenticates you and issues tokens), resource server (the API holding the data) — and crucially the client never sees your password; you authenticate to the authorization server.
- Scopes express limited permission: the client requests specific named permissions, you consent to exactly those, and the token carries them — least privilege instead of all-or-nothing, so request the minimum scopes needed.
- Access is revocable and expiring: because the client holds a token, not your password, access can be revoked (by you or the server) and time-bounded without touching your password or other apps.
- OAuth is NOT login (an access token proves authorization, not identity — the mistake OIDC fixes), NOT a single rigid protocol (a framework with multiple flows), and historically NOT tied to a token format (opaque or JWT).

## Further reading

- [OAuth 2.0 Authorization Framework (RFC 6749)](https://datatracker.ietf.org/doc/html/rfc6749)
- [Authentication vs authorization (previous post)](/blog/posts/identity-01-authn-vs-authz.html)
- [oauth.net — OAuth 2.0](https://oauth.net/2/)
