# Errors and Idempotency: The Two Things That Make an API Safe to Build On

*Why a consistent, machine-readable error model (RFC 9457 problem+json) and idempotency keys are the difference between an API clients can trust and one that quietly double-charges them.*

---

Most API design guides spend their energy on the happy path — resource naming, pagination, versioning. But the two features that decide whether a client can *actually* build on your API live on the unhappy path: **what happens when a request fails**, and **what happens when the client can't tell whether it failed**. Get these wrong and you get support tickets that start with "your API charged my customer twice" and "I have no idea why this returned a 500." Get them right and integrators trust you enough to automate against you.

This post covers two disciplines that go together. First, a **consistent error model** — one shape for every error, machine-readable, safe to expose. Second, **idempotency** — the property that lets a client retry a request after a timeout without fear of executing it twice. They pair up because the same reality drives both: networks are unreliable, clients retry, and your API has to behave predictably when they do.

Everything below derives from the HTTP specifications — [RFC 9110](https://www.rfc-editor.org/rfc/rfc9110) (HTTP Semantics) for status codes and method properties, and [RFC 9457](https://www.rfc-editor.org/rfc/rfc9457) (Problem Details for HTTP APIs) for the error format — plus the widely documented `Idempotency-Key` convention.

---

## Errors: one shape for every failure

The first rule of error design is that every error should look the same. When each endpoint invents its own error JSON — one returns `{"error": "..."}`, another `{"message": "..."}`, a third `{"errors": [...]}` — every client has to write bespoke parsing per endpoint. A consistent envelope means a client writes error handling *once*.

The IETF standardised exactly such an envelope in RFC 9457, "Problem Details for HTTP APIs" (which obsoletes the earlier RFC 7807). It defines a media type — `application/problem+json` — and a small set of standard members:

- **`type`** — a URI that identifies the *kind* of problem. It's the primary, stable identifier. It doesn't have to resolve, but if it does it should point at human-readable documentation.
- **`title`** — a short, human-readable summary of the problem type. It shouldn't change from occurrence to occurrence.
- **`status`** — the HTTP status code, repeated in the body so it survives proxies and logging.
- **`detail`** — a human-readable explanation *specific to this occurrence*.
- **`instance`** — a URI identifying this specific occurrence (often a request ID or a link to a log).

Crucially, the format is extensible: you can add your own members alongside the standard ones. That extension space is where a real API earns its keep.

Here is a problem+json response for a validation failure:

```http
HTTP/1.1 422 Unprocessable Content
Content-Type: application/problem+json
Content-Language: en

{
  "type": "https://api.example.com/problems/validation-error",
  "title": "Your request parameters didn't validate.",
  "status": 422,
  "detail": "The 'amount' field must be a positive integer of minor units.",
  "instance": "/requests/9f2c1b7e",
  "code": "validation_error",
  "errors": [
    { "field": "amount", "code": "must_be_positive", "message": "amount must be greater than 0" },
    { "field": "currency", "code": "unsupported", "message": "currency 'XZY' is not supported" }
  ]
}
```

Note the `Content-Type: application/problem+json` — not plain `application/json`. That tells a generic client "this body is an error described by RFC 9457" without inspecting the payload.

**The gotcha:** returning `200 OK` with an error field in the body — `{"success": false, "error": "..."}` — is invisible to everything that isn't your own hand-written client. Load balancers, retry libraries, uptime monitors, and API gateways all read the status line, not your JSON. A `200` says "this worked," so your monitoring shows green while customers fail, and a client's automatic retry-on-5xx never fires because there was no 5xx. Use the *actual* failure status and the problem+json body together.

---

## A stable error code, distinct from the HTTP status

The single most useful thing you can add to the standard problem members is a **stable string error code** — the `code` field in the example above. It exists because HTTP status codes are too coarse for clients to branch on.

Consider a `422`. It might mean the amount was negative, the currency is unsupported, the account is frozen, or the idempotency key was reused with a different body. A client that wants to say "unsupported currency — offer the user a different one" but "frozen account — send them to support" cannot distinguish those from the `422` alone. Parsing the human-readable `detail` string is a trap: it's written for people, it gets reworded, and it may be localised.

So give each distinct failure a short, stable, machine-oriented code — `unsupported_currency`, `account_frozen`, `idempotency_key_reused` — that never changes once shipped. Clients switch on the code; humans read the title and detail.

```go
// A code is part of your API contract. Treat it like a public constant:
// never rename or repurpose it, only add new ones.
const (
    CodeValidation        = "validation_error"
    CodeUnsupportedCcy    = "unsupported_currency"
    CodeAccountFrozen     = "account_frozen"
    CodeIdempotencyReused = "idempotency_key_reused"
    CodeRateLimited       = "rate_limited"
)
```

The status code answers "what category of failure, at the HTTP level" (so infrastructure can act on it); the `code` answers "what exactly went wrong, at the application level" (so client code can act on it). You need both.

For validation specifically, return **all** the field errors at once, not just the first one — as the `errors` array does above. A form that surfaces one error, gets resubmitted, then reveals a second is a miserable experience. Each entry should name the offending `field`, carry its own machine `code`, and give an actionable `message`.

---

## Choosing the status: 400 vs 422 vs 409

RFC 9110 defines the status codes; the design decision is matching each failure to the right one. Three cause the most confusion.

| Situation | Status | Meaning |
|---|---|---|
| The request is malformed — bad JSON, missing required field, wrong type | `400 Bad Request` | The server can't parse or understand the request at all |
| The request is well-formed but semantically invalid — negative amount, unknown currency | `422 Unprocessable Content` | Syntax is fine; the *content* fails business rules |
| The request conflicts with the current state of the resource | `409 Conflict` | Valid request, but it can't be applied given what exists now |

The `400` vs `422` line is: could the server even *understand* the request? Unparseable JSON or a missing required field is a `400` — the server never got far enough to evaluate your business rules. A perfectly-parsed body whose values break a rule (amount must be positive, currency must be supported) is a `422`. RFC 9110 defines `422 Unprocessable Content` precisely for "the content was understood but couldn't be processed."

`409 Conflict` is for state collisions: creating a resource with a slug that already exists, editing a record someone else changed underneath you (a lost-update / version mismatch), or — as we'll see — reusing an idempotency key with a *different* request body. The request itself is fine; it just can't be reconciled with reality.

**The gotcha:** don't reach for `400` as a catch-all for every client mistake. When everything from a syntax error to a business-rule violation to a state conflict returns `400`, clients lose the ability to react differently — retry-able versus not, fix-the-body versus refresh-and-retry. The status code is a signal; collapsing it to one value throws that signal away. Reserve `400` for "I couldn't understand you," and use `422`/`409` for the failures that come after understanding.

---

## Never leak internals in an error

An error body is attacker-readable output. A stack trace, a raw database driver message, or an unhandled exception string handed to the client is both a bad experience and a security problem:

```json
{
  "error": "pq: duplicate key value violates unique constraint \"users_email_key\"",
  "trace": "at db.Exec (/app/internal/store/users.go:88) ..."
}
```

That single message leaks your database engine (Postgres), your schema (a `users` table with a unique `email`), your internal file paths, and your ORM layout. Multiply it across every error and an attacker maps your stack for free. It can also leak secrets — connection strings, internal hostnames, and tokens routinely appear in raw error text.

The discipline: **log the full detail server-side, return a sanitised problem+json to the client.** Attach a correlation ID (the `instance` member) so a support engineer can find the full trace from the ID the client reports, without any internal detail crossing the wire.

```go
func writeProblem(w http.ResponseWriter, status int, code, title, detail string) {
    w.Header().Set("Content-Type", "application/problem+json")
    w.WriteHeader(status)
    _ = json.NewEncoder(w).Encode(map[string]any{
        "type":   "https://api.example.com/problems/" + code,
        "title":  title,
        "status": status,
        "code":   code,
        "detail": detail, // curated text — never a raw error or trace
    })
}

// For a 5xx, the detail is deliberately generic; the real cause is logged.
func handleInternal(w http.ResponseWriter, r *http.Request, err error) {
    reqID := requestID(r)
    log.Printf("reqID=%s internal error: %v", reqID, err) // full detail stays here
    w.Header().Set("Content-Type", "application/problem+json")
    w.WriteHeader(http.StatusInternalServerError)
    _ = json.NewEncoder(w).Encode(map[string]any{
        "type":     "https://api.example.com/problems/internal-error",
        "title":    "An unexpected error occurred.",
        "status":   500,
        "code":     "internal_error",
        "instance": "/requests/" + reqID,
    })
}
```

The client gets an ID it can quote; you keep the trace where it belongs.

---

## Idempotency: why retries make it non-negotiable

Now the second discipline, and it flows directly from the first. Errors tell a client *that* something failed. But there's a worse case: the client can't tell whether it failed at all.

Picture a client that sends `POST /charges` to charge a card. The server processes it, charges the card, and starts sending the `200`. Midway, the connection drops — a timeout, a dropped packet, a load balancer recycling. The client sees only a timeout. It has no idea whether the charge happened. The server did the work; the confirmation never arrived.

What does a well-behaved client do on a timeout? It **retries**. That's correct behaviour — timeouts are usually transient. But if the first request *did* charge the card, the retry charges it again. The customer is billed twice, and neither side did anything obviously wrong.

This isn't an edge case; at scale it's a certainty. Retries are inevitable — every serious HTTP client, SDK, and service mesh retries on timeouts and 5xxs. So any operation with a side effect *will* eventually be delivered more than once. The only question is whether your API is built to absorb the duplicate.

**The gotcha:** a non-idempotent `POST` that does something irreversible — charge a card, place an order, transfer money — *will* eventually double-execute in production, because retries are not optional and duplicates are not rare. You cannot fix this by telling clients "don't retry" — they will, and they should. The fix has to live on the server: make the operation safe to call twice.

---

## Which methods are idempotent already

HTTP has a formal notion of this. RFC 9110 defines a method as **idempotent** if sending the same request multiple times has the same effect on server state as sending it once. By the specification:

- **`GET`** — idempotent (and safe: no state change at all). Reading twice is reading once.
- **`PUT`** — idempotent. "Set this resource to exactly this state." Doing it twice leaves the same state.
- **`DELETE`** — idempotent. Deleting an already-deleted resource leaves it deleted. (The *status* may differ — `204` then `404` — but the state doesn't.)
- **`POST`** — **not** idempotent. "Create a new thing" or "run this action" done twice means two things, two actions. This is the one that double-charges.

So a well-designed API gets idempotency for free wherever the operation fits `PUT`/`DELETE`/`GET`. Where you genuinely need `POST` — creating a charge, submitting an order, anything that isn't "set to this exact state" — you have to add idempotency yourself. The mechanism is the `Idempotency-Key` header.

---

## The Idempotency-Key pattern

The convention, documented publicly by payment APIs like Stripe and PayPal and now the subject of an IETF draft, is simple: **the client generates a unique key** (a UUID or similar) **for each distinct operation and sends it in an `Idempotency-Key` header.** The *server* remembers, for a window of time, the result it produced for that key. On a retry with the same key, the server doesn't re-execute — it replays the stored result.

The client's first attempt and its retry look identical on the wire:

```http
POST /v1/charges HTTP/1.1
Host: api.example.com
Content-Type: application/json
Idempotency-Key: 5f8a2c1d-9b3e-4a7f-8c21-0d6e4b9a1f22

{ "amount": 4999, "currency": "usd", "source": "card_1a2b" }
```

The first time, the server processes the charge, stores `(key → response)`, and returns:

```http
HTTP/1.1 201 Created
Content-Type: application/json
Idempotency-Replayed: false

{ "id": "ch_3nP8x", "amount": 4999, "currency": "usd", "status": "succeeded" }
```

When the retry arrives with the same `Idempotency-Key`, the server finds the stored result and replays it byte-for-byte — no second charge:

```http
HTTP/1.1 201 Created
Content-Type: application/json
Idempotency-Replayed: true

{ "id": "ch_3nP8x", "amount": 4999, "currency": "usd", "status": "succeeded" }
```

The client sees the same `201` and the same charge id it would have seen the first time, had the connection held. As far as it's concerned, the request happened exactly once. (The `Idempotency-Replayed` header is a convenience some APIs add so a client can tell a replay from a fresh execution; it's not required for the pattern to work.)

A few design points that make this robust:

- **Scope the key** to a customer or API key, not globally, so two clients that happen to pick the same UUID don't collide.
- **Bind the key to the request body.** Store a hash of the request alongside the key. If the same key arrives with a *different* body, that's a client bug — reject it with `409 Conflict` and a clear `code`, rather than silently replaying the old result or executing the new one.
- **Set a retention window** — typically 24 hours. Keys live long enough to cover realistic retry storms, then expire. A key reused after expiry is treated as new.

---

## Implementing the key store

The server side is a small piece of middleware plus a store. The store needs three states per key, not two: not only "done, here's the result," but also **"in flight"** — because concurrent retries are common. A client that times out at 100ms may fire its retry while the original request is *still running* on the server. If your store only records completed results, both requests sail through and you're back to double-execution.

The fix is to atomically claim the key *before* doing the work, and have concurrent arrivals for an in-flight key wait or bounce:

```go
type record struct {
    status   int
    body     []byte
    reqHash  string
    done     bool
}

type store struct {
    mu   sync.Mutex
    keys map[string]*record
}

// claim atomically reserves a key. It returns (existing, true) if a record
// already exists (in-flight or done), or reserves and returns (new, false).
func (s *store) claim(key, reqHash string) (*record, bool) {
    s.mu.Lock()
    defer s.mu.Unlock()
    if r, ok := s.keys[key]; ok {
        return r, true // caller inspects r.done and r.reqHash
    }
    r := &record{reqHash: reqHash}
    s.keys[key] = r
    return r, false
}

func Middleware(s *store, next http.Handler) http.Handler {
    return http.HandlerFunc(func(w http.ResponseWriter, r *http.Request) {
        key := r.Header.Get("Idempotency-Key")
        if key == "" || r.Method != http.MethodPost {
            next.ServeHTTP(w, r) // key only applies to non-idempotent POSTs
            return
        }
        body, _ := io.ReadAll(r.Body)
        r.Body = io.NopCloser(bytes.NewReader(body))
        hash := sha256Hex(body)

        rec, existed := s.claim(key, hash)
        if existed {
            switch {
            case rec.reqHash != hash:
                // same key, different body — a client bug
                writeProblem(w, http.StatusConflict, "idempotency_key_reused",
                    "Idempotency key reused with a different request.", "")
            case !rec.done:
                // original request still running — tell the client to retry later
                w.Header().Set("Retry-After", "1")
                writeProblem(w, http.StatusConflict, "idempotency_in_progress",
                    "A request with this idempotency key is still being processed.", "")
            default:
                // completed — replay the stored response
                w.Header().Set("Idempotency-Replayed", "true")
                w.WriteHeader(rec.status)
                _, _ = w.Write(rec.body)
            }
            return
        }

        // We own the key. Run the handler, capturing its response.
        rw := &captureWriter{ResponseWriter: w, status: 200}
        next.ServeHTTP(rw, r)

        s.mu.Lock()
        rec.status, rec.body, rec.done = rw.status, rw.buf.Bytes(), true
        s.mu.Unlock()
    })
}
```

This sketch uses an in-process map and a mutex for clarity. In production the store is shared (Redis, or a database row with a unique constraint on the key), and the "claim" is an atomic `INSERT ... ON CONFLICT DO NOTHING` or a `SET NX` — the same idea, made durable and cross-instance. The essential move is unchanged: **reserve the key atomically before doing the work, so an in-flight request is visible to its own retry.**

**The gotcha:** concurrent retries of the same key will *race* if the store only tracks completed results. A key store that records "done" but not "in progress" lets two simultaneous requests both find "no result yet," both execute, and both charge. The store must claim the key atomically at the *start* of processing and make later arrivals for that key wait, replay, or receive a `409 in_progress` — never let a second execution begin.

---

## How this ties back to reliability

Zoom out and these two disciplines are one story about building on unreliable networks. A distributed system has no way to guarantee a response arrives; the client can always be left uncertain. The standard remedy for that uncertainty is **retries** — but retries are only safe if the operation is **idempotent**. So the reliability recipe that shows up everywhere, from payment systems to message queues to your own service mesh, is the same pair: *retry with backoff, made safe by idempotency keys.*

The error model is the other half. Retries need to know *when* to fire (a `503` or a timeout, yes; a `422 validation_error`, never — retrying a malformed request just fails faster). A precise status code plus a stable error code is what lets a retry layer make that call automatically. Vague `200`-with-error bodies and catch-all `400`s blind the retry logic exactly when it matters.

Design the two together and you get an API that a client can wrap in a generic, aggressive retry policy and trust completely — which is the whole point. That trust is what "safe to build on" actually means.

---

## Key takeaways

- **One error shape everywhere.** Adopt RFC 9457 `application/problem+json` with `type`, `title`, `status`, `detail`, `instance`, and extend it with your own members.
- **Add a stable, machine-readable `code`** distinct from the HTTP status — clients switch on the code, humans read the title and detail. Never make clients parse prose.
- **Match the status to the failure:** `400` for "couldn't understand you," `422` for "understood but breaks a rule," `409` for "conflicts with current state." Don't collapse everything to `400`.
- **Never return stack traces or raw internal errors** — log them server-side with a correlation id, return a sanitised body. Error output is attacker-readable.
- **Retries are inevitable, so non-idempotent `POST`s eventually double-execute.** `GET`/`PUT`/`DELETE` are idempotent by spec; protect `POST` with an `Idempotency-Key`.
- **Store keys with an in-flight state, claimed atomically before the work.** Otherwise concurrent retries race past a "completed-only" store and both execute.

---

## Further reading

- [RFC 9457 — Problem Details for HTTP APIs](https://www.rfc-editor.org/rfc/rfc9457) — the standard error format; obsoletes RFC 7807.
- [RFC 9110 — HTTP Semantics](https://www.rfc-editor.org/rfc/rfc9110) — the authoritative source for status code meanings and the definition of idempotent and safe methods (§9.2.2, §15).
- [RFC 9110 §15.5 — Client Error 4xx](https://www.rfc-editor.org/rfc/rfc9110#section-15.5) — precise semantics for `400`, `409`, and (via RFC 9110's registry) `422`.
- [The Idempotency-Key HTTP Header Field (IETF draft)](https://datatracker.ietf.org/doc/draft-ietf-httpapi-idempotency-key-header/) — the in-progress standardisation of the header convention.
- [Stripe API — Idempotent requests](https://docs.stripe.com/api/idempotent_requests) — a widely-referenced public description of the key pattern in production.
- [PayPal — Idempotency](https://developer.paypal.com/api/rest/reference/idempotency/) — a second public reference for the same convention.
