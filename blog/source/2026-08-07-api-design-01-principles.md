# API Design Principles

*The opening post of a series on designing APIs people actually enjoy using — why an API is a contract and a product, the qualities that separate a good one from a bad one, and why the contract should exist before a single line of implementation.*

---

Every API is a promise. When you publish an endpoint, a schema, or an RPC method, you are telling every developer who integrates with it: *call this way, and I will behave this way — today, tomorrow, and after the next deploy.* Break that promise and you don't just ship a bug; you break someone else's production system that you can't see and can't test. That is what makes API design a different discipline from writing internal code. Internal code has one reader who can refactor freely. An API has strangers who built on top of your last decision.

This series is about designing APIs that keep their promises well. This first post stays at the level of principles — the ideas that hold whether you ship REST over HTTP, GraphQL, gRPC, or a stream of webhook events. The later posts get concrete. But if you internalize only the principles here, most of the concrete decisions become obvious.

---

## An API is a contract

Start with the word that matters most: **contract**. An API is a formal agreement about what a caller may send and what they will receive back. RFC 9110, the current specification for HTTP semantics, is precise about this framing — a method like `GET` or `DELETE` carries a defined meaning, and a status code like `404` or `409` has an agreed interpretation, so that a client and a server written by strangers can interoperate without ever coordinating. That is the whole point of a standard: shared meaning replaces private coordination.

Your API inherits this obligation. The contract is not "whatever the code currently does." It is the subset of behavior you have committed to keep stable. Everything you expose becomes something you owe. A field you returned "just because it was in the struct" is now a field someone parses. A quirk in your error message that a client learned to string-match is now, functionally, part of your interface.

The practical consequence: **be deliberate about what you promise, because you cannot cheaply un-promise it.** The narrowest contract that solves the caller's problem is the one that leaves you the most room to change your mind later.

---

## An API is a product, and its users are developers

The second reframe: an API is a product. Its customers are developers, and their experience of your product is entirely mediated by the interface. For a normal app, UX is the buttons and screens. For an API, the developer experience — DX — *is* the UX. There are no screens; there is only the shape of the request, the clarity of the response, the quality of the error when something goes wrong, and the documentation that explains it.

This has a blunt implication. A developer evaluating your API forms an opinion in the first ten minutes. Can they authenticate without reading three pages? Does the first `curl` return something sensible? When they send a malformed request, does the error tell them what to fix, or does it say `500 Internal Server Error`? Every one of those moments is a product moment. You are not "returning JSON"; you are onboarding a user who has other options.

**The gotcha:** teams measure API quality by uptime and latency because those are easy to graph, then wonder why adoption is slow. The metrics that predict adoption — time-to-first-successful-call, how often integrators file "how do I…" tickets, how many retries a typical client needs — rarely appear on a dashboard. If DX is the UX, you have to instrument the developer's journey, not just the server's health.

---

## The qualities that separate good from bad

Cut across every well-designed API and the same handful of qualities recur. None is exotic; the discipline is applying them consistently.

**Consistency, or least surprise.** The single highest-leverage quality. If listing resources returns `{ "data": [...], "next": "..." }` in one place, it must not return a bare array somewhere else. If timestamps are RFC 3339 strings in one endpoint, they are RFC 3339 everywhere. Consistency is what lets a developer learn your API once and then *guess correctly* about the parts they haven't read yet. Every inconsistency forces them back to the docs and quietly teaches them not to trust their intuition about your system.

**Simplicity.** The best API exposes the caller's mental model, not yours. It has few concepts, each doing one thing, composed predictably. Simplicity is not the same as small — a large API can be simple if it is regular. It is the absence of special cases the caller has to memorize.

**Predictability.** The same input produces the same shape of output. Optional fields are absent, not sometimes-`null`-sometimes-missing. Errors come back in one envelope, not three depending on which layer failed. A predictable API is one a client can be written against defensively without a page of `if` branches for your inconsistencies.

**Good defaults.** The common case should require the least work, and the safe choice should be the default choice. If pagination defaults to a sane page size, most callers never think about it. If a destructive operation requires an explicit flag, nobody deletes production by omission. Defaults are where you encode your judgment so the caller doesn't have to have any.

**Hard to misuse.** This is the quality most teams skip. It is not enough that a careful developer *can* use your API correctly; a hurried one should find it hard to use *incorrectly*. Require the dangerous parameter to be explicit. Make illegal states unrepresentable in the request schema. Return a clear `400` the instant a request is malformed rather than accepting it and doing something surprising three steps later. The measure of a good interface is what happens when someone uses it wrong.

**Evolvability.** You will change this API. A good design plans for that from day one — additive changes (new optional fields, new endpoints) don't break existing clients, and there is a defined path for the changes that would. We devote a whole later post to versioning; the principle to hold now is that *the ability to change safely is a design property you build in, not a feature you add later.*

---

## Design the contract before you write the code

There are two ways to arrive at an API. In **code-first**, you write the handlers, wire up a framework, and whatever shape falls out becomes the API — documentation, if it exists, is generated after the fact from the code. In **API-first** (also called contract-first or design-first), you write the contract *first*, as an explicit artifact, review it with the people who will consume it, and only then implement against it.

API-first wins for anything with more than one consumer, and here is the mechanical reason. When the contract is a real artifact — an OpenAPI document for a REST API, a `.proto` file for gRPC, an SDL schema for GraphQL — it becomes something you can review, diff, lint, and generate from *before* implementation cost is sunk. The OpenAPI Specification exists precisely so this contract can be machine-readable: you can generate server stubs, client SDKs, and mock servers from the same document, and validate that the running service matches what you published.

A typical API-first loop looks like this:

```yaml
# openapi.yaml — the contract, written and reviewed before any handler exists
paths:
  /orders/{orderId}:
    get:
      summary: Retrieve a single order
      parameters:
        - name: orderId
          in: path
          required: true
          schema: { type: string, format: uuid }
      responses:
        "200":
          description: The order
          content:
            application/json:
              schema: { $ref: "#/components/schemas/Order" }
        "404":
          description: No order with that id
          content:
            application/json:
              schema: { $ref: "#/components/schemas/Error" }
```

From that document you generate the server interface and let the compiler hold you to it:

```go
// Generated from openapi.yaml — you implement the interface, the contract defines it.
type OrdersServer interface {
    // GET /orders/{orderId}
    GetOrder(ctx context.Context, orderID string) (*Order, error)
}
```

The payoff is that the expensive conversations happen while they are still cheap. Renaming a field is a one-line edit in a YAML review comment; it is a migration and a deprecation cycle once clients depend on it. Design-before-code moves your mistakes to the phase where mistakes are free.

**The gotcha:** API-first fails when the contract and the implementation drift apart — the document says one thing, the service does another, and now the contract is a lie that's worse than no contract. The fix is to close the loop in CI: generate the server types from the spec so the code can't compile with a mismatched signature, and run contract tests that assert the live service conforms to the published document. A contract you don't enforce is just documentation that rots.

---

## Interface is not implementation

The deepest principle, and the one that quietly determines how long your API survives: **the interface must be decoupled from the implementation behind it.** Roy Fielding's dissertation, which named and defined REST, frames this as the reason the web scaled — components interact through a uniform interface and stay independent of each other's internals, so any side can evolve without renegotiating with the others. That independence is the value.

The most common way to violate it is to let your storage layer leak through the API. Your database has a `users` table with a `pwd_hash` column, a `fk_org_id`, a `deleted_flag`, and a `legacy_role_int`. It is enormously tempting to serialize that row straight to JSON — it's one line of code. Do it and you have just published your schema as your contract. Now you cannot rename a column, split a table, move to a different datastore, or drop a legacy field without breaking every client, because your internal representation *is* their interface.

Compare a leaked response with a designed one:

```json
// Leaked: the database row, serialized. Every internal name is now a public promise.
{
  "id": 4021,
  "pwd_hash": "$2b$12$...",
  "fk_org_id": 77,
  "deleted_flag": 0,
  "legacy_role_int": 3
}
```

```json
// Designed: the resource the caller actually needs, in the caller's vocabulary.
{
  "id": "usr_a1b2c3",
  "organization": "org_x9y8z7",
  "role": "admin",
  "status": "active"
}
```

The designed version exposes a *concept the caller cares about* — a user with a role and a status — and says nothing about how it is stored. The password hash never crosses the boundary. The opaque string ids let you change your primary keys later. `role` is a stable enum, not an integer whose meaning lives in code the caller can't see. Behind that response you can migrate databases, denormalize, or re-key entirely, and no client notices. That freedom is the entire return on the small cost of writing a mapping layer.

The rule of thumb: **design the resource around the consumer's problem, not around your tables.** The API is a facade over your implementation, and its job is to give you room to change everything behind it.

---

## The paradigms you'll weigh across this series

"API" is not one technology. Over the series we'll evaluate four families, each with a different sweet spot. A one-paragraph orientation now:

**REST over HTTP** models your domain as *resources* addressed by URLs, manipulated with a small fixed set of HTTP methods, leaning on the built-in semantics of methods, status codes, and caching that RFC 9110 defines. It is the default for public web APIs because it rides infrastructure everyone already has, and it is where this series spends most of its time.

**GraphQL** exposes a single endpoint and a typed schema, and lets the *client* specify exactly which fields it wants in one query. It shines when clients are diverse and over-fetching or chatty round-trips hurt — a mobile screen assembling data from many resources — at the cost of moving complexity (caching, query cost, authorization) onto the server.

**gRPC / RPC** models the API as *typed procedure calls* rather than resources, using a schema like Protocol Buffers and, in gRPC's case, HTTP/2 with binary framing and streaming. It excels for low-latency, high-throughput service-to-service traffic inside a system you control, where both ends can share generated stubs.

**Events and webhooks** invert the direction: instead of the client asking, the server *notifies* — an HTTP callback or a message on a stream when something happens. This is how you avoid polling and decouple producers from consumers, and it brings its own contract concerns: delivery guarantees, ordering, retries, and idempotent receivers.

| Paradigm | Model | Best when |
|---|---|---|
| REST / HTTP | Resources + uniform methods | Public web APIs, broad reach, cacheable reads |
| GraphQL | Typed schema, client-selected fields | Diverse clients, avoid over/under-fetching |
| gRPC / RPC | Typed procedure calls | Internal, low-latency, high-throughput services |
| Events / webhooks | Server-initiated notifications | Decoupling, avoiding polling, async workflows |

These are not mutually exclusive. Mature systems mix them — REST at the public edge, gRPC between internal services, webhooks for async notifications. The skill is matching the paradigm to the interaction, and the principles in this post apply to all four.

---

## The road ahead

Here is the map for the rest of the series. Each post takes one area from principle to practice:

1. **Principles** — this post: contract, product, and the qualities that matter.
2. **RESTful resource design** — modeling your domain as resources, naming, and using HTTP methods to their defined meaning.
3. **Requests, responses, and pagination** — payload shape, filtering, sorting, and paging large collections without falling over.
4. **Errors and idempotency** — a consistent error contract, meaningful status codes, and safe retries with idempotency keys.
5. **Versioning and evolution** — changing an API without breaking the clients who depend on it.
6. **GraphQL vs gRPC** — choosing a paradigm, with the trade-offs made concrete.
7. **Documentation and DX** — the reference, the quickstart, and the SDKs that decide whether anyone adopts you.
8. **API lifecycle and governance** — design review, deprecation, and keeping consistency across many teams.

The throughline is the tone this post has set: **contract-first and consumer-empathetic.** Design the promise deliberately, write it down before you write the code, protect the boundary between what you expose and how you build it, and remember at every step that a person you will never meet is reading your response and hoping it makes sense.

---

## Key takeaways

- **An API is a contract.** Everything you expose is something you owe; promise the narrowest thing that solves the caller's problem, because un-promising is expensive.
- **An API is a product for developers.** DX is the UX — the request shape, the error message, and the docs *are* the interface. Measure the developer's journey, not just server health.
- **Consistency is the highest-leverage quality.** It lets a developer learn your API once and guess the rest correctly. Pair it with simplicity, predictability, good defaults, and being hard to misuse.
- **Design the contract before the code.** An explicit OpenAPI/proto/SDL artifact can be reviewed and generated from before implementation cost is sunk — then enforce it in CI so it never drifts.
- **Interface is not implementation.** Never leak your database schema through your API. A designed facade in the caller's vocabulary buys you the freedom to change everything behind it.

---

## Further reading

- [RFC 9110 — HTTP Semantics](https://www.rfc-editor.org/rfc/rfc9110.html) — the authoritative definition of HTTP methods, status codes, and the meaning your REST contract inherits.
- [Architectural Styles and the Design of Network-based Software Architectures](https://ics.uci.edu/~fielding/pubs/dissertation/top.htm) — Roy Fielding's dissertation, which defines REST and the uniform-interface / independence-of-implementation principle.
- [OpenAPI Specification](https://spec.openapis.org/oas/latest.html) — the machine-readable contract format that makes API-first practical: review, mock, and code-generate from one document.
- [Google API Improvement Laws (AIPs)](https://google.aip.dev/) — a mature, publicly published API style guide; a useful reference for consistency and resource-design conventions.
- [Microsoft REST API Guidelines](https://github.com/microsoft/api-guidelines) — another reputable public style guide, valuable for its concrete rules on naming, errors, and versioning.
