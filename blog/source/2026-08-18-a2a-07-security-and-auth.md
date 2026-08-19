# A2A Security and Authentication

*When agents from different organizations delegate real work to each other, trust cannot be assumed, so A2A builds authentication into the Agent Card and demands it on every request.*

A2A is designed for agents that cross organizational boundaries — your agent calling a partner's agent, a vendor's agent calling yours. That is exactly the setting where security cannot be an afterthought. The Agent2Agent protocol (A2A) treats authentication as enterprise-grade and first-class: requirements are declared in the Agent Card and enforced on every request. This seventh post in the series covers how A2A handles authentication and authorization, the schemes it supports, and the responsibilities on each side.

## Security declared in the Agent Card

Recall that the Agent Card is the public contract for an opaque agent. Security is part of that contract. An Agent Card declares, via `securitySchemes` and `security`, exactly how a client must authenticate to use the agent. Nothing about credentials is guessed or negotiated ad hoc — a client reads the card, sees the required scheme, and authenticates accordingly before sending work.

This design keeps interoperability and security compatible. A client can look at any agent's card and know immediately whether it is allowed to call it and how, and an agent can require strong authentication without any out-of-band coordination. The card is where "how do I prove who I am to this agent" is answered.

## The supported schemes

A2A does not invent bespoke authentication; it leans on established web and enterprise standards, declared in the card's `securitySchemes`. The supported types include:

- **API Key** — a shared secret key presented with requests.
- **HTTP Authentication** — standard HTTP auth mechanisms.
- **OAuth 2.0** — token-based authorization, the workhorse for delegated access between organizations.
- **OpenID Connect** — identity on top of OAuth 2.0, for authenticating *who* the caller is.
- **Mutual TLS** — both sides present certificates, for strong, transport-level mutual authentication.

Credentials are transmitted according to the transport binding — as HTTP headers in the REST and JSON-RPC bindings, or as metadata in gRPC. Because these are standard schemes, A2A slots into existing enterprise identity infrastructure rather than requiring a parallel system: the OAuth or mTLS setup an organization already runs is what secures its agents.

## Server responsibilities

An A2A server (a remote agent) has clear obligations on every request:

- **Authenticate every request.** Unless the Agent Card explicitly permits unauthenticated access, the server validates credentials before doing anything.
- **Return the right failures.** Invalid or missing credentials yield a `401 Unauthenticated` (or the binding's equivalent); an authenticated caller lacking permission for the operation yields `403 Forbidden`.
- **Do not leak existence.** The server should not reveal whether an unauthorized resource exists — it must not distinguish "forbidden" from "not found" in a way that lets an unauthenticated caller probe for what tasks or agents are present. Unauthorized callers learn nothing about the internal state.

That last point is a subtle but important part of the model: authorization is not just about blocking actions, it is about not revealing information to callers who have not earned it. An opaque agent stays opaque to the unauthorized.

## Authentication versus authorization

The two are distinct and both matter. **Authentication** establishes *who* the caller is — proven via the declared scheme. **Authorization** decides *what* that authenticated caller may do — which skills it may invoke, which tasks it may see or cancel. A2A's `401` versus `403` distinction maps to exactly this: `401` means "I don't know who you are," `403` means "I know who you are and you may not do this." Design your agent to enforce both — verify identity, then check permission per operation — rather than treating a valid credential as blanket access.

## The extended Agent Card and tiered access

Authentication also enables tiered capabilities through the extended Agent Card. A public card can advertise `capabilities.extendedAgentCard`; a client that authenticates using the schemes from the public card can then retrieve a richer card exposing additional skills or details based on its authorization level. This lets an agent present a minimal public face to anonymous discovery and a fuller set of capabilities to trusted, authenticated partners — sensitive or premium skills stay hidden until the caller proves it is entitled to them. It is authentication doing double duty: gating access *and* shaping what an agent even advertises.

## Security across the whole interaction

Authentication is the foundation, but a secure A2A deployment thinks about the entire interaction. Use TLS for confidentiality in transit (mTLS gives you mutual authentication as well). On the push-notification path from the previous post, remember the direction reverses — the agent calls the client's webhook — so that callback needs its own authentication and the client must verify inbound notifications before acting. And because agents delegate to other agents, consider the chain: an agent acting on a task may itself call further agents, so authorization and least privilege should propagate rather than a single credential granting sweeping downstream access. A2A gives you the mechanisms — standard schemes, per-request enforcement, clear failure semantics — and it is on you to apply them across discovery, task operations, streaming, and callbacks alike.

## Key takeaways

- A2A treats security as first-class: authentication requirements are declared in the Agent Card's `securitySchemes`/`security` and enforced on every request, with no out-of-band guessing.
- Supported schemes are standard ones — API Key, HTTP Authentication, OAuth 2.0, OpenID Connect, and Mutual TLS — so A2A integrates with existing enterprise identity infrastructure.
- Servers must authenticate every request (unless the card permits anonymous access), return `401` for bad credentials and `403` for insufficient permission, and avoid revealing the existence of unauthorized resources.
- Authentication (who you are) and authorization (what you may do) are distinct; enforce both, checking permission per operation rather than treating a valid credential as blanket access.
- The extended Agent Card ties richer capabilities to authentication; and a full deployment secures the whole interaction — TLS, authenticated/verified webhooks, and least-privilege propagation across delegation chains.

## Further reading

- [A2A Protocol — official site](https://a2a-protocol.org)
- [A2A protocol specification](https://a2a-protocol.org/latest/specification/)
- [Agent2Agent (A2A) on GitHub](https://github.com/a2aproject/A2A)
