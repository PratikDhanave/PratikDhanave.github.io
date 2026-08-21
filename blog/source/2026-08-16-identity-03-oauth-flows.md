# The OAuth Flows

*OAuth isn't one procedure — it's a family of flows for different kinds of clients, and picking the wrong one is a security bug, not a style choice. The good news is that modern guidance has collapsed the confusion: for almost every case today, the answer is the authorization code flow with PKCE, and knowing why the alternatives were deprecated is knowing OAuth security.*

The last post covered *what* OAuth is; this one covers *how* a client actually obtains a token — the **grant types** (flows). Historically there were several, and choosing among them confused everyone. Modern OAuth security guidance (embodied in OAuth 2.1) has simplified this dramatically by deprecating the dangerous ones, so this post explains the flows that matter, the one you should almost always use, and why the others fell away.

## Why there are multiple flows

Different clients have different security capabilities, and a token-issuing procedure safe for one is unsafe for another. The key distinction:

- **Confidential clients** can keep a secret. A server-side web app has a backend that can store a client secret where users and browsers can't see it.
- **Public clients** cannot keep a secret. A single-page app (SPA) running in a browser, or a mobile app on a device, has all its code on the user's machine — any embedded secret can be extracted, so it can't be trusted with one.

Flows exist to handle these differently, plus the case of no user at all (service-to-service). The security question every flow answers is: *how does the client prove it's entitled to the token, and how do we keep the token (and the code that yields it) from being stolen in transit?*

## The authorization code flow

The **authorization code flow** is the primary, secure flow for user-authorization, and understanding it is understanding OAuth. Its defining feature is a two-step exchange that keeps the token off the browser's address bar:

```text
1. Client redirects the user to the Authorization Server (with client_id, scopes, redirect_uri)
2. User authenticates and consents at the Authorization Server
3. Auth Server redirects back to the client with a short-lived AUTHORIZATION CODE
4. Client exchanges the code (on the BACK CHANNEL) for tokens
   → sends the code + (for confidential clients) its secret to the token endpoint
5. Auth Server returns the ACCESS TOKEN (and refresh/ID tokens)
```

The cleverness is the **authorization code** as an intermediary. Rather than handing the token straight to the browser (where it'd be exposed in the URL, history, and logs), the auth server returns a short-lived, single-use *code* via the browser, which the client then exchanges for the actual token over a direct **back-channel** server call. The valuable token never travels through the browser's front channel. For confidential clients, the code exchange also requires the client secret, proving the client's identity.

## PKCE: securing the flow for everyone

The authorization code flow has a weakness for *public* clients (SPAs, mobile): they can't use a client secret to prove themselves at the exchange step, so an attacker who intercepts the authorization code (e.g. via a malicious app registering the same redirect) could exchange it for a token. **PKCE (Proof Key for Code Exchange)** closes this:

```text
1. Client generates a random secret ("code verifier") and sends its hash
   ("code challenge") when starting the flow
2. ... authorization proceeds, client gets the code ...
3. At the code exchange, the client sends the original code verifier
4. Auth Server checks it hashes to the challenge from step 1 → only the
   client that started the flow can complete it
```

PKCE ties the code exchange to the specific client that initiated the flow, using a dynamically generated secret instead of a static one — so a stolen authorization code is useless to anyone else. Originally designed for mobile/SPA public clients, PKCE is now **recommended for all clients**, including confidential ones, as defense in depth. The modern default is therefore: **authorization code flow with PKCE**, for essentially every user-facing client. If you remember one thing about OAuth flows, remember that.

## The client credentials flow

Not all OAuth is on behalf of a user. The **client credentials flow** handles **machine-to-machine** access — a backend service accessing an API as *itself*, with no user involved:

```text
Client (a confidential service) → sends its client_id + client_secret → Token endpoint
Token endpoint → returns an access token (no user, no consent screen)
```

There's no resource owner, no browser redirect, no consent — just a service authenticating with its credentials to get a token for its own access. Use this for backend jobs, service integrations, and daemons. It's only for *confidential* clients (it relies on a secret), and it grants the *service's* own permissions, not any user's.

## The flows that got deprecated (and why)

Modern OAuth security guidance (OAuth 2.1 consolidates it) **removed** two once-common flows, and knowing why teaches the security principles:

- **Implicit flow (deprecated).** It returned the access token *directly* in the browser redirect (the front channel), skipping the code exchange — exposing the token in the URL, browser history, and logs, where it could be stolen. It existed because SPAs historically couldn't do the code exchange securely; PKCE made the authorization code flow work for SPAs, so the implicit flow's risk is no longer justified. **Use authorization code + PKCE instead.**
- **Resource owner password credentials (ROPC) flow (deprecated).** The client collected the user's *username and password directly* and sent them to the auth server. This resurrects the exact anti-pattern OAuth was built to kill — the client handling the user's password — defeating the purpose. **Never use it**; redirect the user to the auth server instead.

The through-line: both deprecated flows compromised the core protections (don't expose tokens in the browser; never let the client touch the password), and modern OAuth removed them once the authorization code flow with PKCE could safely cover their use cases.

## Choosing a flow

The decision is now refreshingly simple:

- **User-facing app (web, SPA, mobile) → authorization code flow with PKCE.** The universal default for anything acting on a user's behalf, confidential or public.
- **Service-to-service, no user → client credentials flow.** For backends and daemons accessing an API as themselves.
- **Device with limited input (TVs, CLI) → device authorization flow.** (A specialized flow where the user authorizes on a separate device — worth knowing exists.)
- **Never → implicit or ROPC.** Deprecated for real security reasons.

That's essentially it: authorization code + PKCE for users, client credentials for machines. The historical complexity is gone; the modern guidance is clear. With a token obtained, the next question is what a token actually *is* and how to validate it — the subject of the next post.

## Key takeaways

- OAuth has multiple flows because clients differ: confidential clients (server-side) can keep a secret, public clients (SPAs, mobile) cannot — and a flow safe for one is unsafe for the other.
- The authorization code flow returns a short-lived code via the browser, then exchanges it for the token over a direct back channel, keeping the valuable token out of the browser's URL/history/logs.
- PKCE secures the code exchange by tying it to the client that started the flow (via a dynamically generated verifier/challenge), making a stolen code useless — now recommended for ALL clients; authorization code + PKCE is the modern default for every user-facing app.
- The client credentials flow handles machine-to-machine access (a service acting as itself with its secret, no user or consent) — for backends, daemons, and integrations.
- The implicit flow (token in the browser redirect) and ROPC flow (client collects the password) are deprecated for real security reasons — use authorization code + PKCE for users and client credentials for machines instead.

## Further reading

- [Proof Key for Code Exchange (PKCE, RFC 7636)](https://datatracker.ietf.org/doc/html/rfc7636)
- [OAuth 2.0: delegated authorization (previous post)](/blog/posts/identity-02-oauth-delegated-authorization.html)
- [oauth.net — OAuth 2.1](https://oauth.net/2.1/)
