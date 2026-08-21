# Authentication vs Authorization

*Half of all identity confusion — and a surprising share of security bugs — comes from blurring two words that sound alike and mean opposite things. Authentication asks "who are you?"; authorization asks "what are you allowed to do?" Every protocol in this series exists to answer one or the other, and mixing them up is how you build systems that are both insecure and broken.*

Identity is one of those topics engineers use daily and understand shakily. OAuth, OIDC, SAML, tokens, sessions, SSO — the vocabulary is a thicket, and much of the confusion traces to one root distinction this first post nails down: **authentication versus authorization**. Get this clear and the entire series — and the protocols themselves — become far more legible, because each one is fundamentally an answer to one of these two questions.

## The two questions

Every access-control system answers two distinct questions, in order:

- **Authentication (AuthN) — "Who are you?"** Verifying identity: proving the entity making a request is who it claims to be. Logging in with a password, a passkey, or via "Sign in with Google" is authentication.
- **Authorization (AuthZ) — "What are you allowed to do?"** Determining permissions: given a known identity, deciding whether it may perform a specific action or access a specific resource. Checking that a logged-in user is an admin before showing the admin panel is authorization.

The order matters: you authenticate *first* (establish who), then authorize (decide what they can do). You can't sensibly decide what someone may do until you know who they are. They're sequential, related, and — critically — *not the same thing*.

## Why the distinction is more than pedantry

Blurring these isn't a vocabulary nitpick; it causes real, common security failures:

- **Using an authorization mechanism for authentication.** This is the classic OAuth mistake, and the reason OpenID Connect exists (a later post). OAuth 2.0 is an *authorization* protocol — it grants an app permission to access resources — but developers routinely misused it as a *login* mechanism, which is subtly insecure because an access token proves an app was *authorized*, not *who the user is*. OIDC was created precisely to add a proper authentication layer on top of OAuth.
- **Authenticating without authorizing.** A system that confirms *who* you are but doesn't properly check *what* you're allowed to do leads to "broken access control" — a logged-in user accessing another user's data because the app authenticated them but never authorized the specific request. This is consistently among the most common and severe web vulnerabilities.
- **Confusing the tokens.** Identity systems issue different tokens for different purposes (access tokens for authorization, ID tokens for authentication — later posts), and using one where the other belongs is a frequent, dangerous error.

So the distinction is load-bearing: the protocols, the tokens, and the vulnerabilities all sort into "authentication" or "authorization," and reasoning about identity correctly *starts* with knowing which one you're dealing with.

## Mapping the protocols to the questions

Here's the payoff that makes the rest of the series click. Each major protocol is primarily an answer to one of the two questions:

```text
                  "Who are you?"          "What can you do?"
                  (Authentication)        (Authorization)

  OAuth 2.0             —                  ✔ delegated authorization
  OpenID Connect   ✔ authentication       (built on OAuth's authorization)
  SAML             ✔ authentication       (also carries authorization attributes)
```

- **OAuth 2.0** is an **authorization** framework — it lets an app get *permission* to access resources on a user's behalf, without handling their password. It is *not* a login protocol, though it's endlessly misused as one.
- **OpenID Connect (OIDC)** is an **authentication** layer built *on top of* OAuth 2.0 — a standard way to verify *who the user is* (an ID token), fixing OAuth's authentication gap. This is modern "Sign in with…" done right.
- **SAML** is an older **authentication** (and attribute) standard for enterprise single sign-on — the same federated-login goal as OIDC with different, XML-based machinery.

The pattern: OAuth answers *what can you do*; OIDC and SAML answer *who are you* (with OIDC building on OAuth). The series is essentially OAuth for authorization, then OIDC and SAML for authentication, then the tokens and sessions that carry both, then how to secure it all.

## Why identity got complicated: delegation and federation

If authentication is just "check a password," why the elaborate protocols? Because two needs made identity genuinely hard, and the protocols exist to meet them safely:

- **Delegation** — letting an application act on your behalf against *another* service without giving it your password. You want a photo-printing app to access your cloud photos, but you must *not* hand it your cloud password. Delegated authorization (OAuth) solves exactly this: grant a scoped, revocable permission instead of sharing credentials. Before OAuth, apps asked for your password to other services — a security disaster OAuth was invented to end.
- **Federation** — letting one system trust another to vouch for identity, so you don't need a separate password for every service. "Sign in with Google," and enterprise SSO where one login grants access to dozens of apps, are federation: a trusted **identity provider (IdP)** authenticates you, and other services (**relying parties** / **service providers**) trust its word. This is what OIDC and SAML enable.

Both introduce a third party into what used to be a simple two-party (user ↔ app) exchange, and coordinating that trust *securely* — proving who vouched for whom, with tokens that can't be forged or replayed — is why the protocols have the structure they do. The complexity isn't gratuitous; it's the cost of delegating access and federating identity without sharing passwords.

## The mental model to carry forward

As the series covers each protocol, keep asking the orienting question: **is this answering "who are you" or "what can you do"?**

- OAuth flows, scopes, and access tokens → *authorization* (what can you do).
- OIDC ID tokens and SAML assertions → *authentication* (who are you).
- Sessions and SSO → maintaining an *authenticated* identity across requests and apps.
- The security post → protecting both, and never confusing an authorization artifact for an authentication one.

That single distinction organizes the whole domain. With it clear — plus the delegation and federation needs that drove the protocols — you're ready for the first and most misunderstood of them: OAuth 2.0, the authorization framework.

## Key takeaways

- Authentication (AuthN) answers "who are you?" (verifying identity); authorization (AuthZ) answers "what are you allowed to do?" (permissions) — you authenticate first, then authorize, and they are not the same thing.
- Confusing them causes real bugs: misusing OAuth (authorization) as login (authentication) is subtly insecure (and why OIDC exists); authenticating without properly authorizing each request causes broken access control, a top web vulnerability.
- The protocols sort by question: OAuth 2.0 is authorization (delegated permission), while OpenID Connect and SAML are authentication (federated login) — with OIDC built on top of OAuth.
- Identity is complicated because of delegation (an app acting on your behalf without your password) and federation (trusting an identity provider so you don't need a password per service) — both add a trusted third party that must be coordinated securely.
- Carry one orienting question through the series: is this mechanism answering "who are you" or "what can you do?" — it organizes OAuth, OIDC, SAML, tokens, sessions, and their vulnerabilities.

## Further reading

- [OAuth 2.0 — oauth.net](https://oauth.net/2/)
- [OpenID Connect — openid.net](https://openid.net/developers/how-connect-works/)
- [API Security series](/blog/series/api-security/)
