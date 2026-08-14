# RESTful Resource Design: Nouns, Methods, and the Maturity Model

*How to model resources as nouns, choose HTTP methods by their spec-defined semantics, return the right status codes, and decide honestly how much hypermedia your API actually needs.*

---

REST is not a protocol and not a library — it is a set of constraints that Roy Fielding described in his 2000 dissertation, layered on top of HTTP. The practical payoff of following those constraints is that generic clients, caches, proxies, and monitoring tools already understand your API before they've read a line of your documentation. A cache knows a `GET` is safe to store. A proxy knows a `429` means back off. A retry library knows a `PUT` can be replayed. You get all of that for free — but only if you design resources and use methods the way the specifications define them.

This post is about the design decisions underneath that payoff: what a resource *is*, how to shape its URIs, which method carries which promise, which status code says what, and how to handle the operations that stubbornly refuse to look like CRUD. Everything here derives from HTTP Semantics (RFC 9110) and Fielding's original framing — not from any style guide's house rules.

---

## Resources are nouns, not procedures

The central move in REST is to stop thinking in verbs and start thinking in *things*. A resource is any concept your API exposes that a client can name and manipulate — a user, an invoice, a shipment, a search result, a build job. You give each resource a stable identifier (a URI), and the client acts on it using the small, fixed set of HTTP methods.

This is the inversion that trips people coming from RPC. In an RPC world you design functions: `createUser`, `getUser`, `deactivateUser`. In REST you design a `user` resource and let HTTP supply the verbs. The method *is* the verb — that's why `POST /users` and `DELETE /users/42` need no verb in the path.

Resources come in two shapes that recur everywhere:

- **Collections** — a set of items, addressed by a plural noun: `/orders`, `/customers`.
- **Items** — a single member of a collection, addressed by the collection plus an identifier: `/orders/1099`, `/customers/c_88a1`.

That single distinction drives most of your URI design. A `GET /orders` lists or filters; a `GET /orders/1099` fetches one. A `POST /orders` creates a new member of the collection; a `DELETE /orders/1099` removes one member.

---

## URI design: hierarchy without verbs

A few conventions make URIs predictable enough that a client can often guess the next one correctly.

**Use plural nouns for collections.** `/products`, not `/product` and not `/productList`. Consistency matters more than the grammar debate — pick plural and never mix.

**Model containment as path hierarchy.** When one resource clearly belongs to another, nest it:

```http
GET /customers/c_88a1/orders
```

This reads as "the orders belonging to customer `c_88a1`" and scopes the collection naturally. Nesting is a statement about ownership, so use it when the child has no meaningful existence outside the parent.

**Stop nesting when it stops helping.** Deep chains like `/customers/c_88a1/orders/1099/items/7/discounts/3` are brittle — every level is a lookup that can 404, and the URI encodes a navigation path the client rarely needs in full. Once a resource has its own stable identifier, flatten to it:

```http
GET /order-items/7
```

A good rule of thumb: nest one level to express ownership, then address deeper resources by their own top-level path. The identifier `7` is globally unique, so you don't need the ancestry to find it.

**Keep verbs out of the path.** `/getUser`, `/orders/1099/delete`, `/users/create` are the classic REST smell. The HTTP method already carries the verb; putting one in the URI duplicates it and breaks the uniform interface every tool relies on.

**The gotcha:** verbs in URLs (`/getUser`, `/createOrder`) are the single most common REST mistake, and they're not just stylistic. When the verb lives in the path, a cache can't tell a read from a write, a proxy can't safely retry, and every client has to special-case your naming. The method *is* the verb — `GET /users/42` and `DELETE /users/42` differ by method, not by path. If you find yourself reaching for a verb in the URI, you're usually missing a resource (see the controller pattern below).

**Filtering, sorting, and paging go in the query string**, because they select a *representation* of a collection rather than naming a different resource:

```http
GET /orders?status=open&sort=-created_at&page=2&per_page=50
```

---

## HTTP methods and their guarantees

The methods look interchangeable until you read what RFC 9110 actually promises about each one. Two properties do the heavy lifting:

- **Safe** — the method is read-only *by intent*. The client is not requesting any state change. `GET`, `HEAD`, and `OPTIONS` are safe. Safety is what lets caches store responses and lets crawlers follow links without side effects.
- **Idempotent** — sending the request once has the same effect on server state as sending it N times. `GET`, `HEAD`, `OPTIONS`, `PUT`, and `DELETE` are idempotent. Idempotency is what lets a client or proxy retry after a timeout without fear of doubling the effect.

Every safe method is idempotent, but not the reverse: `PUT` and `DELETE` change state yet are still idempotent. `POST` and `PATCH` are neither safe nor guaranteed idempotent.

### GET — read a representation

`GET` retrieves the current representation of a resource. It must be safe: never mutate state in a `GET` handler, no matter how convenient. A `GET` that increments a counter or triggers a job violates the contract every cache and prefetcher assumes, and those tools *will* call your endpoint speculatively.

```http
GET /orders/1099 HTTP/1.1
Host: api.example.com
Accept: application/json
```

```http
HTTP/1.1 200 OK
Content-Type: application/json

{ "id": "1099", "status": "open", "total": 4200, "currency": "INR" }
```

### PUT — full replacement, idempotent

`PUT` says "make the resource at this URI look exactly like the representation I'm sending." It replaces the whole resource. Send it twice with the same body and the resource ends in the same state both times — that's why it's idempotent.

```http
PUT /orders/1099 HTTP/1.1
Content-Type: application/json

{ "status": "shipped", "total": 4200, "currency": "INR" }
```

Because `PUT` is a full replacement, any field you *omit* is being set to absent. If your body carries only `{"status": "shipped"}`, a strict `PUT` implementation should treat `total` and `currency` as removed. That's the trap that leads most people to reach for `PATCH`.

### PATCH — partial update, not automatically idempotent

`PATCH` applies a partial modification: change these fields, leave the rest alone. It's the right tool when a client wants to touch one attribute without resending the entire resource.

```http
PATCH /orders/1099 HTTP/1.1
Content-Type: application/merge-patch+json

{ "status": "shipped" }
```

**The gotcha:** `PUT` is idempotent and replaces the *whole* resource; `PATCH` is a partial update and is **not inherently idempotent** — choose deliberately. A merge-style patch (`{"status":"shipped"}`) happens to be idempotent because reapplying it lands the same value. But a patch expressed as an operation — "append this line item," "increment quantity by 1" — is *not*: run it twice and you get two line items or a quantity of 2. If you offer `PATCH`, decide which flavor you're implementing and document it, because a client's retry logic depends on the answer. When in doubt, prefer patch semantics that are naturally idempotent (set-to-value, not apply-delta).

### POST — create and everything non-idempotent

`POST` is the general-purpose method for "process this representation according to the resource's own semantics." Its most common use is creating a new member in a collection, where the server assigns the identifier:

```http
POST /orders HTTP/1.1
Content-Type: application/json

{ "customer": "c_88a1", "total": 4200, "currency": "INR" }
```

```http
HTTP/1.1 201 Created
Location: /orders/1099
Content-Type: application/json

{ "id": "1099", "status": "open", "total": 4200, "currency": "INR" }
```

`POST` is neither safe nor idempotent — sending it twice creates two orders. That's exactly why the browser warns you before re-submitting a form. When you need create-without-duplicates over a flaky network, add an idempotency key (a client-generated token in a header) so the server can recognize and dedupe retries; the method stays `POST`, but you've layered idempotency on top.

### DELETE — remove, idempotent

`DELETE` removes the resource. It's idempotent in effect: after a successful delete, the resource is gone, and deleting it again leaves it gone.

```http
DELETE /orders/1099 HTTP/1.1
```

The subtlety is the *response* to a repeat delete. The first call returns `204 No Content`; the second, when the resource is already gone, typically returns `404`. The status codes differ, but the server *state* is identical either way — and it's server state, not the response code, that idempotency is about.

---

## Status codes that say what happened

A status code is a promise to a machine. Generic clients branch on the class (`2xx` success, `4xx` client error, `5xx` server error) before they ever look at your body, so getting the code right is not cosmetic.

| Code | Meaning | When to use |
|---|---|---|
| `200 OK` | Success with a body | `GET`, or `PUT`/`PATCH`/`POST` that returns the updated representation |
| `201 Created` | New resource created | Successful create; include a `Location` header pointing at it |
| `202 Accepted` | Accepted, not yet done | Async work queued; the result isn't ready yet |
| `204 No Content` | Success, no body | `DELETE`, or an update where you return nothing |
| `400 Bad Request` | Malformed request | Unparseable JSON, missing required field at the syntax level |
| `401 Unauthorized` | Not authenticated | Missing or invalid credentials — "who are you?" |
| `403 Forbidden` | Authenticated but not allowed | Valid identity, insufficient permission — "I know you, but no" |
| `404 Not Found` | No such resource | The URI names nothing |
| `409 Conflict` | State conflict | Duplicate unique key, edit against a stale version, illegal state transition |
| `422 Unprocessable Content` | Semantically invalid | Well-formed request whose contents fail business rules |
| `429 Too Many Requests` | Rate limited | Client exceeded a quota; pair with a `Retry-After` header |
| `500 Internal Server Error` | Server bug | An unexpected, unhandled failure on your side |
| `503 Service Unavailable` | Temporarily down | Overload or maintenance; also pair with `Retry-After` |

A few distinctions carry real weight:

**`400` vs `422`.** Reserve `400` for requests the server can't even parse — broken JSON, wrong content type. Use `422` when the request is syntactically fine but violates a business rule: a negative order total, an end date before a start date, an unknown currency code. The split lets clients tell "I sent garbage" from "I sent something well-formed that you rejected."

**`401` vs `403`.** `401` means "I don't know who you are" — authentication failed or is missing. `403` means "I know exactly who you are, and you still can't do this." A `401` invites the client to retry with credentials; a `403` tells it not to bother.

**`409` for conflicts and optimistic concurrency.** When two clients race to update the same resource, `409` is how you reject the loser. Combined with an `ETag` and `If-Match`, it powers optimistic locking: the client sends the version it read, and the server returns `409` (or `412 Precondition Failed`) if that version is stale.

**The gotcha:** returning `200 OK` with an error buried in the body — `{"success": false, "error": "..."}` — breaks every generic client and monitor you'll ever put in front of your API. Load balancers, uptime checks, retry libraries, and API gateways all branch on the *status class*. A `200` tells them everything is fine, so a failure that ships as `200` is invisible: no alert fires, no retry triggers, no circuit breaker opens. Map failures to the honest `4xx`/`5xx` code and let the body carry the human-readable detail.

**The gotcha:** `404` versus `403` can leak information. If `/accounts/999` returns `403` when the account exists but you can't see it, and `404` when it doesn't exist, an attacker can enumerate valid IDs just by watching which code comes back. For resources where mere existence is sensitive, deliberately return `404` for both "not found" and "found but forbidden," so the response reveals nothing about which case is true. This is a real tradeoff — a plain `403` is friendlier to legitimate clients — so decide per resource based on how sensitive existence is.

---

## Actions that aren't CRUD

Sooner or later you hit an operation that isn't create/read/update/delete: *send* an invoice, *cancel* a subscription, *retry* a failed job, *convert* a currency. The instinct is to invent a verb path — `POST /invoices/42/send` — and reintroduce exactly the smell we banned.

REST's answer is to model the action itself as a resource, usually a sub-resource that represents the *thing produced by the action* rather than the action as a procedure. Instead of "send the invoice," create a *delivery*:

```http
POST /invoices/42/deliveries HTTP/1.1
Content-Type: application/json

{ "channel": "email", "to": "billing@buyer.example" }
```

```http
HTTP/1.1 202 Accepted
Location: /invoices/42/deliveries/d_7
```

Now the action has an identity. You can `GET /invoices/42/deliveries/d_7` to check whether the email actually went out, list all past delivery attempts, and retry by `POST`ing a new one. The state transition became a resource with its own history — far more useful than a fire-and-forget verb.

When an operation genuinely resists this modeling — a stateless transform like currency conversion — it's acceptable to expose a **controller resource**: a resource whose whole job is to run a computation. Keep it a noun where you can (`POST /conversions`) and treat it as the pragmatic exception, not the default. The test is simple: if you can name the *result* of the action as a thing, model that thing; only fall back to a controller when there's no durable result to name.

---

## The Richardson Maturity Model, honestly

Leonard Richardson's maturity model, popularized by Martin Fowler, describes four levels of how "RESTful" an HTTP API is:

- **Level 0 — one URI, one method.** Everything tunnels through a single endpoint (classic SOAP-over-HTTP or a lone `/api` that takes an action name in the body). HTTP is just a pipe.
- **Level 1 — resources.** You split the API into many URIs, one per resource, but still use one method (usually `POST`) for everything.
- **Level 2 — HTTP verbs and status codes.** You use `GET`/`POST`/`PUT`/`PATCH`/`DELETE` with their real semantics and return meaningful status codes. This is where almost every well-designed API you've used actually lives.
- **Level 3 — hypermedia controls (HATEOAS).** Responses embed links telling the client what it can do next, so the client navigates the API by following links rather than hard-coding URIs.

Level 3 is the part of REST most APIs skip — and Fielding considered it non-negotiable for something to be truly "RESTful." A level-3 response looks like this:

```http
HTTP/1.1 200 OK
Content-Type: application/json

{
  "id": "1099",
  "status": "open",
  "total": 4200,
  "_links": {
    "self":   { "href": "/orders/1099" },
    "cancel": { "href": "/orders/1099/cancellation", "method": "POST" },
    "pay":    { "href": "/orders/1099/payments", "method": "POST" }
  }
}
```

The promise is decoupling: the client discovers that "cancel" is available (and its URI) from the response, so the server can move endpoints or gate actions by state without breaking clients. When `status` becomes `shipped`, the server simply stops emitting the `cancel` link.

**The realistic take:** most production APIs stop at level 2, and for most of them that's the right call. HATEOAS pays off when clients are generic and long-lived enough to navigate dynamically — but the dominant client today is a purpose-built frontend or SDK written against fixed, documented endpoints, and it ignores the links entirely. The discipline of embedding and maintaining hypermedia has a real cost, and if no client follows the links, you're paying it for nothing. Level 2 done well — proper nouns, correct methods, honest status codes — captures the large majority of REST's practical benefits. Reach for level 3 when you actually have clients that will consume the links (public platforms, workflow-driven state machines, evolving APIs with many independent consumers); otherwise, ship a clean level 2 and don't apologize for it.

---

## Key takeaways

- **Resources are nouns.** Model things, not procedures; let the HTTP method supply the verb. A verb in the path usually means you're missing a resource.
- **Shape URIs by collection/item and ownership.** Plural nouns, one level of nesting for containment, flatten to a resource's own path once it has a stable id, filters in the query string.
- **Learn safe vs idempotent precisely.** Safe = read-only intent (`GET`/`HEAD`/`OPTIONS`); idempotent = repeatable without extra effect (adds `PUT`/`DELETE`). `POST` and `PATCH` are neither by default.
- **`PUT` replaces the whole resource and is idempotent; `PATCH` is partial and only idempotent if you design it that way.** Pick per endpoint and document the choice.
- **Status codes are promises to machines.** Use the honest `4xx`/`5xx` — never a `200` with an error body — and mind the `400`/`422`, `401`/`403`, and `404`/`403`-leak distinctions.
- **Model non-CRUD actions as resources** (a *delivery*, a *cancellation*), falling back to a named controller only when there's no result to name.
- **Level 2 is a fine destination.** Add HATEOAS when real clients will follow the links, not as a checkbox.

---

## Further reading

- [RFC 9110 — HTTP Semantics](https://www.rfc-editor.org/rfc/rfc9110.html) — the authoritative definition of methods, safe/idempotent properties, and status codes.
- [RFC 9110 §9.2 — Common Method Properties (Safe and Idempotent Methods)](https://www.rfc-editor.org/rfc/rfc9110.html#name-common-method-properties)
- [Roy Fielding — Architectural Styles and the Design of Network-based Software Architectures (Ch. 5, REST)](https://ics.uci.edu/~fielding/pubs/dissertation/rest_arch_style.htm) — the original REST constraints.
- [Roy Fielding — REST APIs must be hypertext-driven](https://roy.gbiv.com/untangled/2008/rest-apis-must-be-hypertext-driven) — his own case for level 3.
- [Martin Fowler — Richardson Maturity Model](https://martinfowler.com/articles/richardsonMaturityModel.html) — the widely cited walkthrough of levels 0–3.
- [RFC 5789 — PATCH Method for HTTP](https://www.rfc-editor.org/rfc/rfc5789.html) — where `PATCH` and its non-idempotent nature are specified.
