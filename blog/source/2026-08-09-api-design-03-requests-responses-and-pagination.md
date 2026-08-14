# Requests, Responses, and Pagination

*Shaping the payloads clients actually consume — consistent bodies, content negotiation, field selection, and pagination that survives scale and mutation.*

---

Endpoints and status codes get the design attention, but the thing a client integrates against is the *shape of the bytes*: the JSON you accept and the JSON you return. A well-designed body is boring in the best way — a developer guesses the field name correctly on the first try, parses a date without a helper library, and never has to ask whether a missing key means "zero" or "unknown." This post is about earning that boringness. We'll cover how to shape request and response bodies, how content negotiation actually works per RFC 9110, how to let clients ask for exactly the fields they need, and — the part that quietly sinks APIs at scale — how to paginate collections without skipping or duplicating rows.

Everything here derives from the HTTP specifications (RFC 9110, RFC 9111) and RFC 3339 for timestamps, plus the well-documented mechanics of keyset pagination. The examples are original; the rules are the standards'.

---

## Consistent bodies: naming, casing, and shape

Pick one casing convention for JSON keys and apply it to every field in every response, forever. `snake_case` and `camelCase` are both fine; what is not fine is `userId` in one endpoint and `user_id` in the next. JSON itself is agnostic, so the convention is yours to enforce — but enforce it mechanically (a serializer setting, a linter on your schema) rather than by hoping reviewers catch drift.

```json
{
  "id": "acct_9f3a2b",
  "display_name": "Aarav Mehta",
  "email": "aarav@example.com",
  "created_at": "2026-08-14T09:12:33Z",
  "monthly_limit": { "amount": 250000, "currency": "INR" }
}
```

Names should describe the value, not its storage. `created_at` beats `ts`; `display_name` beats `name1`. Booleans read best as positive predicates — `is_active`, `email_verified` — never negated (`not_disabled` forces the reader to invert twice).

**The gotcha:** naming and casing inconsistency erodes trust faster than almost any other flaw, because it makes the whole API feel unreliable. Once a client hits `userId` on one route and `user_id` on another, they stop trusting the docs and start defensively coding for both. Decide the convention on day one and gate it in CI against your OpenAPI schema — retrofitting casing later is a breaking change you cannot take back.

---

## Envelopes versus bare bodies

There are two schools for the top-level shape of a response. A **bare body** returns the resource directly. An **envelope** wraps it in an object with a fixed `data` key (and room for `meta`, `links`, or `errors` alongside).

```json
// bare
{ "id": "acct_9f3a2b", "display_name": "Aarav Mehta" }

// enveloped
{
  "data": { "id": "acct_9f3a2b", "display_name": "Aarav Mehta" },
  "meta": { "request_id": "req_51ce" }
}
```

Bare bodies are lighter and map cleanly onto a single resource. Envelopes earn their weight on **collections**, where you need somewhere to put pagination metadata and links that isn't inside the array. The JSON:API specification standardizes the enveloped approach around top-level `data`, `errors`, and `meta` members. Whichever you choose, be consistent: a collection endpoint that returns a bare array leaves no room to add pagination later without a breaking change, so many teams envelope collections even when they leave single resources bare.

---

## Nulls versus omitted fields

`null` and *absent* are different signals, and clients will build logic on the difference whether you intend it or not. Sending `"middle_name": null` says "we know this person has no middle name." Omitting the key entirely says "we didn't fetch or don't track that." Those are not interchangeable.

Two workable conventions exist, and you must pick exactly one:

- **Always present:** every field in the schema appears in every response, using `null` for absent values. Predictable to parse; slightly larger payloads.
- **Omit when empty:** absent fields are dropped. Smaller payloads, but clients must treat "missing" as a first-class case and never assume a key exists.

```json
{
  "id": "acct_9f3a2b",
  "display_name": "Aarav Mehta",
  "middle_name": null,
  "deleted_at": null
}
```

**The gotcha:** omitting a field versus sending `null` mean different things to clients, and mixing the two within one API guarantees bugs — someone will write `if (user.phone)` and get burned when `phone` is sometimes `null`, sometimes absent, sometimes `""`. Pick one convention, document it prominently, and be especially careful on **PATCH** semantics, where the distinction is load-bearing: an omitted field means "leave unchanged" while an explicit `null` means "clear this value." Conflate them and clients can never delete a field.

---

## Dates as RFC 3339, money as minor units, IDs as opaque strings

Three data types cause more integration pain than all others combined. Handle them by convention, once.

**Timestamps.** Serialize every date and time as an RFC 3339 string in UTC with an explicit offset — `2026-08-14T09:12:33Z`. RFC 3339 is the internet profile of ISO 8601, and its `date-time` form is unambiguous, sortable as a plain string, and parseable by every standard library. Do not invent `MM/DD/YYYY`, do not emit epoch integers without saying so, and do not omit the timezone — a naive `2026-08-14T09:12:33` forces every client to guess the zone.

**Money.** Never represent money as a floating-point number. IEEE 754 binary floats cannot represent most decimal fractions exactly, so `0.1 + 0.2` is not `0.3`, and cents evaporate under arithmetic. Represent an amount as an **integer count of the currency's minor unit** paired with an ISO 4217 currency code.

```json
"price": { "amount": 199900, "currency": "INR" }
```

Here `199900` means ₹1,999.00 — the minor unit for INR is the paisa (1/100). The currency code is mandatory because the minor-unit exponent varies: JPY has no minor unit (¥500 is `{"amount": 500, "currency": "JPY"}`), while most currencies use two decimal places. Never assume "divide by 100."

**Identifiers.** Expose IDs as opaque strings, even when they are integers underneath. A prefixed string like `acct_9f3a2b` tells you the resource type at a glance, survives a migration from auto-increment integers to UUIDs without a schema change, and stops clients from doing arithmetic on IDs or guessing the next one. Treat the ID as a token the client stores and echoes back, nothing more.

**The gotcha:** floats for money silently lose cents. A `19.99` that round-trips through JSON, a spreadsheet, and back can become `19.989999999999998`, and summing thousands of those drifts by real money you'll answer for in an audit. Integer minor units plus a currency code make every amount exact and every rounding decision explicit — the number in the payload is the exact number of paise, cents, or yen, with no fractional part to lose.

---

## Content negotiation: Accept and Content-Type

RFC 9110 defines how a client and server agree on representation. The client advertises what it can consume with the `Accept` request header; the server states what it actually sent with the `Content-Type` response header. On requests that carry a body (POST, PUT, PATCH), the client also sets `Content-Type` to describe what it is sending.

```http
POST /v1/accounts HTTP/1.1
Content-Type: application/json
Accept: application/json

{ "display_name": "Aarav Mehta", "email": "aarav@example.com" }
```

```http
HTTP/1.1 201 Created
Content-Type: application/json; charset=utf-8

{ "id": "acct_9f3a2b", "display_name": "Aarav Mehta" }
```

For a JSON API, default to `application/json` and treat it as the fallback when `Accept` is absent or `*/*`. If a client asks for a media type you cannot produce, RFC 9110 says you may respond `406 Not Acceptable` — but for a JSON-only API it is usually kinder to serve JSON than to reject the request. If a client sends a body in a media type you do not support, return `415 Unsupported Media Type`.

**Compression** is negotiated the same way, on a separate axis. The client sends `Accept-Encoding: gzip, br`; the server compresses the body and echoes `Content-Encoding: gzip`. Because JSON is highly compressible text, gzip or Brotli routinely cuts response size by 70–90% for large collections, at the cost of CPU. Whenever a response varies by a request header, include `Vary` (e.g. `Vary: Accept-Encoding`) so caches store the right variant.

**The gotcha:** `Accept` and `Content-Type` describe different directions and are not interchangeable — `Accept` is the client saying what it *wants back*, `Content-Type` is either party describing the body *it is sending now*. Setting `Content-Type` on a GET with no body does nothing useful, and reading `Accept` to decide how to parse an incoming body is a category error. Keep the two roles straight: one is a wish, the other is a fact.

---

## Field selection and expansion

Two failure modes haunt fixed response shapes. **Over-fetching** ships a fat object when the client wanted three fields for a list view. **Under-fetching** forces an N+1 stampede of follow-up requests to hydrate related resources. Give clients two knobs and both problems shrink.

**Sparse fieldsets** let a client name the fields it wants, so a mobile list view pays for only what it renders:

```http
GET /v1/accounts?fields=id,display_name HTTP/1.1
Accept: application/json
```

```json
{ "data": [
  { "id": "acct_9f3a2b", "display_name": "Aarav Mehta" },
  { "id": "acct_71dd0e", "display_name": "Neha Rao" }
] }
```

**Expansion** goes the other way, inlining a related resource that would otherwise be a second request:

```http
GET /v1/orders/ord_4c21?expand=customer HTTP/1.1
```

```json
{ "data": {
  "id": "ord_4c21",
  "total": { "amount": 199900, "currency": "INR" },
  "customer": { "id": "acct_9f3a2b", "display_name": "Aarav Mehta" }
} }
```

Without `expand`, `customer` would be a bare id (`"customer": "acct_9f3a2b"`) and the client fetches it separately if needed. Keep the default lean — return ids by default and expand only on request — so the common path stays cheap and the expensive joins are opt-in. Cap expansion depth (one level is a sane default) so a client can't ask you to serialize the entire object graph in one call.

---

## Filtering and sorting

Collections need to be narrowed and ordered from the query string. Keep filter keys aligned with response field names so a developer who saw `status` in a body knows to filter on `status`.

```http
GET /v1/orders?status=paid&created_after=2026-08-01T00:00:00Z&sort=-created_at&limit=25 HTTP/1.1
```

A common, readable sort convention is a comma-separated field list where a leading `-` means descending: `sort=-created_at,display_name` sorts by newest first, then by name. Document which fields are filterable and sortable — an unbounded "filter on anything" surface is a query-planner nightmare and a denial-of-service vector. And make sorting **total**: sorting by a non-unique column like `created_at` alone leaves rows with equal timestamps in an undefined order, which quietly breaks pagination. Append a unique tiebreaker (the id) to every sort so the ordering is deterministic.

---

## Pagination done right: offset versus cursor

Every collection endpoint needs pagination, and the choice you make here is the one clients feel most. There are two families.

**Offset/limit** pagination asks for a slice by position: "skip 40, give me 20." It is trivial to implement and lets a client jump to an arbitrary page.

```http
GET /v1/orders?limit=20&offset=40 HTTP/1.1
```

It has two serious problems at scale. First, it is **slow deep into a collection**: `OFFSET 100000` still makes the database scan and discard 100,000 rows before returning any, so latency grows with page depth — an O(n) cost in the offset. Second, and worse, it is **unstable on mutating data**. Offsets are computed against a snapshot that no longer holds once rows are inserted or deleted between page requests. Insert a row before the current page and every subsequent page shifts by one: the client re-sees a row it already read (a duplicate) or skips one entirely.

**Cursor (keyset) pagination** fixes both. Instead of a position, the client passes an opaque cursor that encodes *where the last page ended*, and the server continues from there using a `WHERE` clause on an indexed, ordered, unique key:

```http
GET /v1/orders?limit=20 HTTP/1.1
```

```json
{
  "data": [
    { "id": "ord_88f0", "created_at": "2026-08-14T09:10:00Z" },
    { "id": "ord_87a1", "created_at": "2026-08-14T09:08:41Z" }
  ],
  "meta": { "has_more": true, "next_cursor": "b3JkXzg3YTF8MjAyNi0wOC0xNFQwOTowODo0MVo" }
}
```

The client sends the cursor back to get the next page, and nothing else changes:

```http
GET /v1/orders?limit=20&cursor=b3JkXzg3YTF8MjAyNi0wOC0xNFQwOTowODo0MVo HTTP/1.1
```

Under the hood the cursor decodes to the sort key of the last returned row — here `(created_at, id) = ("2026-08-14T09:08:41Z", "ord_87a1")` — and the query becomes a range scan: `WHERE (created_at, id) < ('2026-08-14T09:08:41Z', 'ord_87a1') ORDER BY created_at DESC, id DESC LIMIT 20`. Because that condition rides an index and never counts skipped rows, page 5,000 costs the same as page 1. And because it anchors to a *value* rather than a *position*, inserts and deletes elsewhere in the collection don't shift the client's place — no skips, no duplicates.

The cursor must be **opaque**: base64-encode it and treat it as a token clients store and return verbatim, never parse or construct. That freedom lets you change what the cursor encodes — add a tiebreaker, switch the sort key — without a breaking change, and it stops clients from forging positions you never intended to support.

**The gotcha:** offset pagination is O(n) deep and silently skips or duplicates rows the moment the underlying data changes mid-scroll. On a live feed where rows arrive constantly, a user paging through offsets will re-read items and miss others without any error ever surfacing — the API looks fine and the data is wrong. Use cursor/keyset pagination for any collection that is large or actively mutating; reserve offset pagination for small, stable, admin-style lists where jumping to "page 7" genuinely matters and the data barely changes.

| Concern | Offset/limit | Cursor (keyset) |
|---|---|---|
| Deep-page latency | Degrades (O(n) in offset) | Flat (indexed range scan) |
| Stability under inserts/deletes | Skips and duplicates rows | Stable — anchored to a value |
| Jump to arbitrary page | Yes | No (sequential only) |
| Total count available | Easy | Expensive or omitted |
| Best for | Small, stable datasets | Large or live datasets |

Cursor pagination gives up one thing: random access to an arbitrary page, and a cheap total count. If the UI genuinely needs "page 47 of 900," offset may be the honest choice for that small, stable dataset. For everything that grows or changes, keyset wins.

---

## Partial responses and useful headers

Two header families make large and rate-limited APIs pleasant to consume.

**Range requests** (RFC 9110) let a client fetch part of a large representation — resumable downloads, streaming a slice of a big file. The client sends `Range: bytes=0-1023`; the server replies `206 Partial Content` with a `Content-Range` header describing the slice. Advertise support with `Accept-Ranges: bytes`. This is orthogonal to collection pagination — it operates on bytes of one representation, not on members of a list.

**Rate-limit headers** tell clients how much budget they have left so they can self-throttle instead of hammering into `429 Too Many Requests`. A widely used convention exposes the ceiling, the remainder, and when the window resets:

```http
HTTP/1.1 200 OK
Content-Type: application/json
RateLimit-Limit: 1000
RateLimit-Remaining: 993
RateLimit-Reset: 42
```

When you do return `429`, include a `Retry-After` header (RFC 9110) telling the client how many seconds to wait — a well-behaved client will honor it rather than retry blindly and make congestion worse. Together with `ETag`/`Last-Modified` for caching and `Vary` for negotiated variants, these headers move coordination out of the body and into the protocol, where infrastructure can act on it.

---

## Key takeaways

- **Consistency is the feature.** One casing convention, one null-vs-omit rule, RFC 3339 dates, integer-minor-unit money, opaque string IDs — decided once and enforced mechanically.
- **Content negotiation has two axes.** `Accept`/`Content-Type` choose the media type; `Accept-Encoding`/`Content-Encoding` choose compression. Default to JSON, add `Vary` when a response depends on a request header.
- **Let clients ask for the right shape.** Sparse fieldsets kill over-fetching; bounded expansion kills under-fetching. Keep the default lean and make joins opt-in.
- **Cursor pagination for anything that grows or moves.** Offset is O(n) deep and skips or duplicates rows on mutating data; keyset anchors to a value on an indexed, total ordering and stays fast and stable. Return opaque cursors and page metadata.
- **Push coordination into headers.** Rate-limit and `Retry-After` headers, `ETag`/`Vary` for caching, and range requests for partial payloads keep the body clean and let infrastructure help.

The payload is the contract. Endpoints and verbs frame it, but the JSON a client parses — and the cursor it pages with — is what a developer lives inside every day. Make it predictable, make it exact, and make it survive scale.

---

## Further reading

- [RFC 9110 — HTTP Semantics](https://www.rfc-editor.org/rfc/rfc9110.html) (content negotiation, `Accept`/`Content-Type`, status codes, range requests, `Retry-After`)
- [RFC 9111 — HTTP Caching](https://www.rfc-editor.org/rfc/rfc9111.html) (`Vary`, `ETag`, cache behavior for negotiated responses)
- [RFC 3339 — Date and Time on the Internet: Timestamps](https://www.rfc-editor.org/rfc/rfc3339.html)
- [RFC 4627 / RFC 8259 — The JSON Data Interchange Format](https://www.rfc-editor.org/rfc/rfc8259.html)
- [ISO 4217 — Currency codes](https://www.iso.org/iso-4217-currency-codes.html) (minor-unit exponents per currency)
- [Use the Index, Luke — "Paging Through Results" (keyset pagination)](https://use-the-index-luke.com/no-offset)
- [JSON:API specification](https://jsonapi.org/format/) (top-level `data`/`errors`/`meta`, sparse fieldsets, pagination links)
- [IETF draft — RateLimit header fields for HTTP](https://datatracker.ietf.org/doc/draft-ietf-httpapi-ratelimit-headers/)
