# SAML: Enterprise Single Sign-On

*SAML is older, XML-heavy, and unfashionable — and it still runs enterprise identity, because the corporate world standardized on it a decade before OIDC existed and enterprise software moves slowly. If you build anything sold to businesses, you will meet SAML, and understanding it as "the same federated-login idea as OIDC, different machinery" is what makes it approachable.*

The last post positioned OIDC as the modern default for federated login. This post covers **SAML** (Security Assertion Markup Language), the older standard that still dominates *enterprise* single sign-on. It solves the same core problem as OIDC — let a trusted identity provider authenticate users for many applications — with different, XML-based technology. Knowing SAML matters because B2B and enterprise customers overwhelmingly expect it, regardless of what's newer.

## The same problem, an earlier answer

SAML and OIDC address the identical need: **federated authentication / single sign-on** — a user authenticates once with a trusted **identity provider**, and multiple applications trust that authentication instead of each maintaining its own login. The value is the same one from the first post: one login, many apps, no separate password per service, centrally managed.

SAML just got there first. It's an OASIS standard that matured in the mid-2000s, well before OAuth/OIDC, and enterprises built their identity infrastructure — corporate directories, SSO portals, employee access to dozens of SaaS apps — around it. That entrenchment is why SAML persists: not because it's better than OIDC (it generally isn't for new consumer apps), but because the enterprise world standardized on it and the switching cost is enormous. SAML is legacy in the sense of "older," not "abandoned" — it's actively load-bearing across corporate IT.

## The roles and the assertion

SAML has two main roles (parallel to OIDC's provider and relying party):

- **Identity Provider (IdP)** — the system that authenticates the user and vouches for their identity (the corporate identity system / SSO provider). Analogous to OIDC's OpenID Provider.
- **Service Provider (SP)** — the application the user wants to access, which trusts the IdP (your app, if enterprises log into it via SSO). Analogous to OIDC's Relying Party.

The central artifact is the **SAML assertion** — an XML document, digitally signed by the IdP, stating that a user was authenticated and carrying information about them:

```text
SAML Assertion (XML, signed by the IdP):
  - Authentication statement: this user authenticated, when, how
  - Subject: who the user is (a NameID)
  - Attributes: user info — email, name, GROUPS/ROLES, department, etc.
  - Conditions: validity window, intended audience (the SP)
  - Signature: the IdP's cryptographic signature over the assertion
```

The assertion is SAML's equivalent of OIDC's ID token — a signed, verifiable statement of authentication — just in XML rather than a JWT. And like a JWT, its trust comes from the **signature**: the SP verifies the assertion was signed by the trusted IdP and hasn't been tampered with, and checks the conditions (validity window, that *this* SP is the intended audience). The same validation discipline as tokens applies: verify signature, audience, and timing, or you accept forged identity.

## How SAML SSO works

The common flow (SP-initiated SSO) mirrors OIDC's shape with XML and browser redirects/POSTs instead of JSON:

```text
1. User visits the SP (your app) and is unauthenticated
2. SP generates a SAML AuthnRequest and redirects the user's browser to the IdP
3. User authenticates at the IdP (corporate login — often already logged in → true SSO)
4. IdP creates a signed SAML Assertion and sends it back via the browser
   (typically an HTTP POST to the SP's Assertion Consumer Service)
5. SP validates the assertion's signature, conditions, and audience
   → establishes a session → user is logged in
```

The structure is recognizable: redirect to the IdP, authenticate there, come back with a signed statement of identity, validate it, log the user in. The differences from OIDC are mechanical — **XML assertions instead of JSON/JWT, SOAP/XML tooling and browser POST bindings instead of REST**, and XML signature handling (which is notoriously fiddly and a source of implementation bugs). Conceptually, though, it's the same federated-login dance.

## SAML vs OIDC: when you'll use each

They do the same job, so the choice is driven by context, not raw capability:

- **SAML dominates enterprise/B2B SSO.** If you sell software to businesses, their IT departments will expect to connect *their* IdP (often a corporate identity platform) to your app via SAML — it's frequently a hard requirement for enterprise deals. Enterprise identity infrastructure is built on it.
- **OIDC dominates modern, consumer, and new applications.** For "Sign in with Google/social," mobile, SPAs, and greenfield apps, OIDC's JSON/JWT/REST simplicity wins (the last post).
- **Many systems support both.** A B2B SaaS app commonly offers OIDC *and* SAML, using SAML for enterprise customers' SSO and OIDC for others — because you don't get to dictate which your enterprise customers use.

The honest framing: **OIDC is technically newer and simpler and the right default for new development, but SAML is not going away** because enterprise adoption is deep and durable. Treat SAML as a requirement you support for enterprise reach, not a technology to avoid. The practical guidance: build new consumer-facing auth on OIDC, and add SAML when (not if) enterprise customers require it — and when you do, lean on a well-tested SAML library, because hand-rolling XML signature validation is a classic source of serious vulnerabilities.

## The security caution

SAML's XML foundation carries specific risks worth flagging:

- **XML signature validation is subtle and historically buggy.** Vulnerabilities like XML signature wrapping (manipulating the XML so a valid signature covers different content than what's processed) have hit real SAML implementations. This is not a reason to fear SAML, but a strong reason to **use a mature, maintained library** and never implement assertion validation yourself.
- **Validate everything, as with tokens.** Signature, the validity window, and that your SP is the intended audience — an assertion for a different SP, or an expired one, must be rejected.

SAML is the enterprise half of federated identity: same goal as OIDC, older XML machinery, still essential for B2B. With OAuth (authorization), OIDC (modern authentication), and SAML (enterprise authentication) covered, the next posts address what happens *after* login — sessions and SSO — and how to secure the whole system.

## Key takeaways

- SAML solves the same problem as OIDC — federated authentication / single sign-on via a trusted identity provider — but with older, XML-based machinery, and it still dominates enterprise/B2B SSO because corporate identity infrastructure was built on it.
- Its roles parallel OIDC's: Identity Provider (IdP, authenticates and vouches — like the OpenID Provider) and Service Provider (SP, the trusting app — like the Relying Party).
- The SAML assertion is a signed XML statement of authentication carrying the subject and attributes (including groups/roles) — SAML's equivalent of the OIDC ID token, trusted via the IdP's signature, validated for signature/conditions/audience.
- The SSO flow mirrors OIDC (redirect to IdP → authenticate → return a signed statement → validate → session), differing mechanically: XML assertions and browser POST bindings instead of JSON/JWT/REST, with fiddly XML signature handling.
- Use OIDC for new/consumer apps (simpler, modern) and SAML for enterprise SSO (frequently a hard B2B requirement); many apps support both — and always use a mature library, since XML signature validation (e.g. signature-wrapping attacks) is a classic vulnerability source.

## Further reading

- [OpenID Connect (previous post) — the modern counterpart](/blog/posts/identity-05-openid-connect.html)
- [SAML 2.0 (OASIS standard overview)](https://en.wikipedia.org/wiki/SAML_2.0)
- [API Security series](/blog/series/api-security/)
