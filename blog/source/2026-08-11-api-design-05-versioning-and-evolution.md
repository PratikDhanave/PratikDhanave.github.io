# Versioning and Evolution: Changing an API Without Breaking Its Consumers

*The real skill isn't cutting a v2 — it's knowing which changes are safe to ship silently, which ones break clients you'll never meet, and how to retire an old version responsibly instead of forever.*

---

An API is a promise. The moment someone integrates against it, every field name, type, default, and error becomes a contract you've signed with people you'll never talk to. And yet the software behind that promise has to keep changing — new features, new fields, fixed mistakes. **Versioning and evolution is the discipline of changing the implementation without breaking the promise.**

The common instinct is to reach for a version number the moment change looms: bump to `/v2/` and move on. But a version number is a *tool*, not a *strategy*. Most changes don't need one, and the ones that do carry a cost that outlives the release. This post works through the whole picture: what actually counts as a breaking change, the honest trade-offs between the versioning strategies, why "be liberal in what you accept" only takes you so far, and how to deprecate an old version without leaving integrators stranded.

Everything below derives from the HTTP specifications — [RFC 9110](https://www.rfc-editor.org/rfc/rfc9110) (HTTP Semantics) for content negotiation and method semantics, [RFC 8594](https://www.rfc-editor.org/rfc/rfc8594) (the `Sunset` header) and [RFC 9745](https://www.rfc-editor.org/rfc/rfc9745) (the `Deprecation` header) for retirement signalling — plus the robustness principle from [RFC 1122](https://www.rfc-editor.org/rfc/rfc1122) and its modern re-examination in [RFC 9413](https://www.rfc-editor.org/rfc/rfc9413).

---

## What actually counts as a breaking change

Before you can decide *how* to version, you have to know *when* you have to. A change is **breaking** if a client that worked yesterday could stop working today without changing a single line of its own code. The dividing line isn't "big versus small" — it's "does an existing consumer's assumption still hold."

The safe, **non-breaking** (additive) changes share one property: an old client can ignore them entirely.

- **Adding a new, optional field to a response.** A client that doesn't know about `nickname` never reads it. Harmless.
- **Adding a new endpoint or a new HTTP method to an existing resource.** Nobody was calling it yesterday.
- **Adding a new optional request parameter with a backward-compatible default.** Omitting it must behave exactly as before.
- **Adding a new value to an output enum — with caveats** (more on that below; this one bites).
- **Making a validation rule *more* permissive.** Accepting inputs you previously rejected can't break anyone who was already sending valid data.

The **breaking** changes all share the opposite property: they invalidate something a client already relies on.

- **Removing or renaming a field.** `email` becoming `email_address` breaks every client reading `email` — even though the URL is untouched.
- **Changing a field's type.** `amount` going from a JSON number `4999` to a string `"49.99"`, or a scalar becoming an array.
- **Tightening validation.** Suddenly rejecting a request you used to accept — making a field required, capping a string's length, restricting a format.
- **Changing a default.** If `page_size` defaulted to 100 and now defaults to 20, every client that relied on the old default silently gets different results.
- **Changing error semantics.** Moving a failure from `200`-with-body to a real `4xx`, renaming an error `code`, or changing which status a condition returns.
- **Removing an enum value from what you accept**, or repurposing what an existing value means.

**The gotcha:** renaming a field or tightening a validation rule is a breaking change even though the endpoint URL never changed. Teams reason about compatibility at the level of "did the route change?" and ship a field rename under the same `/v1/` path, confident it's minor. But clients bind to the *payload shape*, not the route. The URL is the smallest part of the contract; the JSON body and the validation rules are the large part. If an old client would now fail, it's breaking — regardless of what the path says.

---

## Versioning strategies and their honest trade-offs

Once you've established that a change is genuinely breaking and unavoidable, you need a place to put the new behaviour without disturbing the old. There are four broad approaches, and each buys clarity at a different price.

### URI versioning — the version lives in the path

```http
GET /v1/accounts/42 HTTP/1.1
Host: api.example.com
```

The version is right there in the URL: `/v1/`, `/v2/`. This is what most large public REST APIs converge on, and the reason is simple: it's *impossible to get wrong by accident*. The version is visible in a browser address bar, in a `curl` you paste into a bug report, in an access log, in a CDN cache key. There's no negotiation to misconfigure. A developer can see at a glance which version a call targets.

The cost is conceptual purity. A URI is supposed to identify a *resource*, and `/v1/accounts/42` and `/v2/accounts/42` are arguably the *same* account addressed two ways — which offends REST's model of resources as stable identities. In practice almost nobody cares, because the operational clarity is worth far more than the theoretical tidiness. The pragmatic convention is to version only on **major**, breaking changes: `/v1/`, `/v2/` — never `/v1.3.7/`. Minor, additive changes ship inside the existing major version without a bump.

### Media-type / header versioning — negotiate the version

```http
GET /accounts/42 HTTP/1.1
Host: api.example.com
Accept: application/vnd.example.account.v2+json
```

Here the URL is clean and stable, and the client asks for a specific representation via `Accept` — standard HTTP content negotiation, exactly as [RFC 9110](https://www.rfc-editor.org/rfc/rfc9110) intends. The server responds with a matching `Content-Type`. This is the most *architecturally correct* option: one resource, many representations, chosen by negotiation.

The cost is discoverability and human friction. You can't paste a versioned URL into a browser and see v2 — the version lives in a header nobody sees by default. It's easy to forget to set, harder to debug, and CDNs must be told to include `Accept` in the cache key or they'll serve the wrong version. Correct, but higher-friction for the humans integrating against you.

### Query-parameter versioning — the version is a parameter

```http
GET /accounts/42?version=2 HTTP/1.1
Host: api.example.com
```

A middle ground: visible like the path, but bolted onto an otherwise stable URL. It's easy to add and easy to see. The downsides are that it muddles a version (which shapes the *whole* response) with genuine query parameters (which filter or shape *data*), it's trivial to drop when copying a URL, and default-handling gets murky — what does an omitted `version` mean, and does that answer change over time? Usable, but it tends to feel like a retrofit rather than a design.

### No explicit version — additive-only continuous evolution

The fourth option is to not version the surface at all, and instead commit to *never making a breaking change*. Every change is additive; nothing is ever removed or repurposed, only deprecated in place. This is the model GraphQL encourages: a single evolving schema where new fields are added and old fields are marked `@deprecated` but keep working, so clients migrate field-by-field on their own timeline rather than all at once at a version cutover.

The appeal is that clients never face a forced "rewrite for v2" migration. The cost is discipline and accretion: you can *never* clean-break a mistake, so the schema accumulates deprecated fields indefinitely, and "don't break anyone, ever" is a demanding constraint to hold across a large team over years. It trades the pain of migrations for the pain of permanent backward compatibility.

| Strategy | Where the version lives | Wins | Costs |
|---|---|---|---|
| URI path | `/v2/accounts` | Obvious, unmissable, cache-friendly, easy to debug | "Same resource, two URLs"; encourages whole-API bumps |
| Media type / header | `Accept: …v2+json` | REST-clean, one stable URL, per-request | Invisible, easy to forget, CDN cache-key setup |
| Query parameter | `?version=2` | Visible, easy to add | Conflates version with data params; easy to drop |
| No version (additive-only) | nowhere — deprecate in place | No forced migrations for clients | Never clean-break; schema accretes forever |

**The gotcha:** "just add a version number" doesn't actually solve compatibility — it *relocates* it. The instant `/v2/` exists, you're running two APIs, and you'll run N of them forever unless you *deliberately* deprecate and remove the old ones. Every version you keep alive is code paths to maintain, tests to run, docs to keep straight, and security patches to backport. A version number without a retirement plan isn't a versioning strategy; it's a slow-growing maintenance liability. The number is the easy part — sunsetting is the hard part, and it's the part that makes versioning actually pay off.

---

## The robustness principle and its limits

There's a foundational idea running under all of this, from the earliest internet specs. The **robustness principle**, stated in [RFC 1122](https://www.rfc-editor.org/rfc/rfc1122) and often called Postel's Law, is: *"Be conservative in what you do, be liberal in what you accept from others."* Applied to APIs, this makes a client a **tolerant reader** — it ignores fields it doesn't recognise, doesn't choke on new enum values it hasn't seen, and doesn't fail because the response gained a member.

Tolerant reading is what makes additive change safe. If clients hard-fail on any unexpected field, you can't add *anything* without breaking them — every change becomes a version bump. So designing clients to tolerate additions, and designing servers to expect that clients will, is genuinely load-bearing. Build parsers that skip unknowns rather than reject them.

But the principle has a well-documented dark side, examined directly in [RFC 9413](https://www.rfc-editor.org/rfc/rfc9413) ("Maintaining Robust Protocols"). Excessive tolerance **hides drift**. When servers quietly accept malformed or slightly-wrong input, clients keep sending it, and that broken behaviour ossifies into a de-facto part of the contract. The next server that's *stricter* — even correctly stricter — breaks those clients. Being liberal in what you accept means the true contract slowly becomes "whatever we've silently tolerated so far," which is far larger and fuzzier than what you documented. RFC 9413's guidance is to be tolerant *and* to make deviations **visible** — log them, surface warnings, report the drift — rather than absorbing errors in silence. Tolerance without telemetry is how an API's real surface area quietly balloons past anything anyone intended.

**The gotcha:** repurposing an existing field's meaning is worse than removing it. If you delete `status`, a tolerant client that reads `status` fails loudly and someone gets paged. But if `status` used to mean "payment state" and you quietly start using it for "account state," the old client keeps reading the field, parses it without error, and acts on a value that now means something else entirely — silently, wrongly, with no exception to catch. A removal is a clean break the client can detect; a repurposing is a landmine. Never reuse an old field for a new meaning. Add a new field and deprecate the old one.

---

## Backward and forward compatibility

Two directions matter, and it's worth naming both.

**Backward compatibility** is the one everyone means: a *new server* still works with an *old client*. This is what additive-only change buys you — old clients keep running against the upgraded backend because nothing they depended on moved.

**Forward compatibility** is the mirror: an *old server* (or old code) gracefully handles data or requests produced by a *newer* client. This is why tolerant reading has to run in *both* directions. A client written today should skip a field the future adds; a server should ignore an optional parameter a newer client sends that it doesn't yet understand, rather than rejecting the whole request. Forward compatibility is what lets you roll out a change gradually — during a deploy, new and old instances run side by side, and messages flow both ways across the version gap.

Concretely, when you evolve the data model:

- **Default new fields.** A new required field breaks every existing writer instantly. Add it as optional with a sensible server-side default, and only consider tightening it later — after clients have adopted it.
- **Never change what an existing value means.** New enum values, yes (if readers tolerate unknowns); redefining an old one, never.
- **Widen before you narrow.** Accepting more is safe; accepting less is breaking. Sequence your changes so the permissive step ships first.

```http
POST /v1/accounts HTTP/1.1
Content-Type: application/json

{ "name": "Acme Corp", "tier": "pro" }
```

If a later release adds a `region` field, it must default server-side so this exact request — with no `region` — keeps succeeding. The old client never learns `region` exists, and that's the point.

---

## Deprecation, done responsibly

Deprecation is how a version or a field actually goes away — the step that makes versioning worth the cost. Done well, it's a communicated, measured, gradual retirement. Done badly, it's a surprise `404` on a Monday morning.

HTTP gives you two standard signals to announce it *in the responses themselves*, so even clients whose owners never read your changelog get told in-band. The [`Deprecation`](https://www.rfc-editor.org/rfc/rfc9745) header (RFC 9745) marks a resource or version as deprecated — optionally with a timestamp of when it became so — and the [`Sunset`](https://www.rfc-editor.org/rfc/rfc8594) header (RFC 8594) states the date after which it may stop working. Pair them with a `Link` to the migration guide:

```http
HTTP/1.1 200 OK
Content-Type: application/json
Deprecation: @1735689600
Sunset: Wed, 01 Jul 2026 00:00:00 GMT
Link: <https://api.example.com/docs/migrate-v1-to-v2>; rel="deprecation"

{ "id": 42, "name": "Acme Corp" }
```

The `Deprecation` value here is a timestamp (`@` plus a Unix time) marking when v1 became deprecated; `Sunset` gives the hard cutoff. A client — or a client's monitoring — can detect these headers and flag the migration long before the endpoint disappears.

But headers alone aren't a deprecation *process*. A responsible retirement has four parts:

1. **A real timeline.** Announce, then leave a generous window — long enough for integrators to plan, test, and ship on their own release cadence. For a widely-used public API that means months, not weeks.
2. **Out-of-band communication.** Changelog, email to registered API-key owners, dashboard banners, docs marked deprecated. The in-band headers are a backstop, not the whole plan.
3. **Telemetry.** Instrument usage *per version and per field* so you know who is still calling the old path — and can reach out to the specific accounts that haven't migrated before you flip the switch.
4. **A graceful end state.** After sunset, prefer a clear `410 Gone` with a problem body pointing at the new version over a bare `404` — tell the client the resource was intentionally retired, not that it never existed.

**The gotcha:** you can't deprecate what you can't measure. The single most common way a sunset goes wrong is flipping it off based on a guess — "traffic to v1 looks low, it's probably fine" — and discovering, via a flood of failures, that one high-value customer's nightly batch job still lived on it. Before you announce a sunset, you need per-version (ideally per-endpoint and per-field) usage telemetry that tells you *exactly* who is still on the old path. Instrument first, deprecate second, remove third. The measurement isn't optional overhead; it's the thing that lets you sunset without breaking someone who mattered.

---

## Putting it together

Evolution and versioning are two speeds of the same job. The everyday speed is **additive, non-breaking change inside the current version** — new optional fields, new endpoints, more permissive validation, defaulted data — safe because tolerant clients ignore what they don't need and old requests still succeed. The occasional, expensive speed is a **breaking change**, which needs a new major version (most publicly, a `/v2/` path for its unmissable clarity) *and* a plan to eventually retire the old one.

The connective tissue is honesty about what "breaking" means — payload shape and validation and defaults and error semantics, not just the URL — and the discipline to measure usage before you retire anything. Get this right and your API can change continuously for years while the clients built against it keep working, migrating deliberately rather than being broken by surprise. That's what evolution means: the promise stays intact even as everything behind it changes.

---

## Key takeaways

- **Breaking is defined by the client, not the size of the change.** If an existing consumer could fail without changing its code, it's breaking — renames, type changes, tightened validation, changed defaults, and altered error semantics all qualify even when the URL is untouched.
- **Additive changes are the safe default.** New optional fields, new endpoints, more-permissive validation — ship them inside the current version, no bump required.
- **Pick a versioning strategy for its trade-off, not by reflex.** URI paths win on clarity and debuggability (why most public REST APIs use them); media-type negotiation is REST-cleaner but invisible; additive-only evolution avoids migrations at the cost of a schema that accretes forever.
- **A version number relocates compatibility work — it doesn't remove it.** Every live version is forever-maintenance until you deliberately deprecate it.
- **Be a tolerant reader, but make drift visible.** Skip unknown fields; don't let silent tolerance turn "whatever we've accepted" into the real contract. Never repurpose an existing field's meaning — that breaks old clients worse than removing it.
- **Deprecate with `Deprecation`/`Sunset` headers, a real timeline, comms, and telemetry.** You can't sunset safely what you can't measure — instrument per-version usage before you remove anything.

---

## Further reading

- [RFC 9110 — HTTP Semantics](https://www.rfc-editor.org/rfc/rfc9110) — content negotiation (`Accept`, media types) and the definitions underpinning header-based versioning; also the authoritative source on method semantics.
- [RFC 9745 — The Deprecation HTTP Response Header Field](https://www.rfc-editor.org/rfc/rfc9745) — the standard in-band signal that a resource or version is deprecated.
- [RFC 8594 — The Sunset HTTP Header Field](https://www.rfc-editor.org/rfc/rfc8594) — announcing the date after which a resource is expected to become unresponsive.
- [RFC 1122 — Requirements for Internet Hosts](https://www.rfc-editor.org/rfc/rfc1122) — §1.2.2 states the robustness principle ("be conservative in what you do, be liberal in what you accept").
- [RFC 9413 — Maintaining Robust Protocols](https://www.rfc-editor.org/rfc/rfc9413) — the modern re-examination of the robustness principle and how excessive tolerance hides protocol drift.
- [GraphQL — Best Practices: Versioning and Deprecation](https://graphql.org/learn/best-practices/#versioning-and-nullability) — the continuous-evolution model: add fields, mark old ones `@deprecated`, avoid version cutovers.
- [Google AIP-185 — Versioning](https://google.aip.dev/185) — a public API design guideline on major versions and what constitutes a backwards-incompatible change.
