# Rate Limiting and Resource Consumption

*Part five of the API Security series: why limits are a security control and not just an ops knob, how the four rate-limiting algorithms trade off, which dimensions to key on, and how to protect expensive queries and sensitive business flows from bulk abuse.*

---

The last four posts dealt with a single request at a time: is this caller who they say they are, are they allowed to touch this object, and is the body they sent hostile? This post changes the unit of analysis from *one request* to *many*. A request can be perfectly authenticated, perfectly authorized, and perfectly well-formed — and still be part of an attack, because the attack is the *volume*, not the payload.

That is the insight behind two entries in the OWASP API Security Top 10 that people file under "performance" and then never harden: **API4:2023 Unrestricted Resource Consumption** and **API6:2023 Unrestricted Access to Sensitive Business Flows**. API4 is about a single request — or a flood of them — consuming more CPU, memory, database time, bandwidth, or third-party spend than you can afford. API6 is about a legitimate flow — signup, checkout, coupon redemption — being run thousands of times by a bot until it does real business harm. Neither is a broken-authentication bug. Both are limits you failed to impose.

Limits are a security control. They bound the blast radius of credential stuffing, scraping, brute force, denial of service, and — in the cloud era — a metered bill that scales with an attacker's enthusiasm. This post is about imposing them deliberately.

---

## Why a rate limit is a security boundary, not a courtesy

The usual framing is that rate limits keep well-behaved clients from accidentally overwhelming you — a fairness knob. That framing is why so many APIs ship with a limit that is trivially generous or missing entirely. Reframe it: a rate limit is the ceiling on how much damage a *single* identity can do per unit time, and almost every volumetric attack lives underneath a missing ceiling.

- **Credential stuffing** replays leaked username/password pairs against your login endpoint. Each attempt is a valid, well-formed request. Without a per-identity limit on failed logins, an attacker tries millions of pairs and harvests every account whose owner reused a password.
- **Scraping** walks your listing and detail endpoints to exfiltrate your entire catalog, price book, or user directory. Every call is authorized. The theft is the aggregate.
- **Brute force** against a password reset token, an OTP, or a coupon code is only feasible if you let the attacker guess quickly.
- **Denial of service** does not require a botnet if one endpoint is expensive enough — a single unbounded query can do it (more on that below).
- **Runaway cost** is the modern twist: if a request triggers an LLM call, a SMS send, an image transform, or a downstream metered API, then "unlimited requests" means "unlimited spend." An attacker who cannot breach you can still bankrupt the endpoint.

None of these are stopped by better authentication or stricter validation. They are stopped by a number: how many, per whom, per what window.

**The gotcha:** teams treat rate limiting as an operational nicety — "we'll add it when traffic grows" — and ship an API with no ceiling at all. But the absence of a limit is exactly what makes credential stuffing, scraping, and brute force *economical*. A limit is not there to be polite to good clients; it is there to make abuse expensive for bad ones. Ship it on day one, tuned loose, rather than never.

---

## The four algorithms and what they trade

There are four classic algorithms. They differ in memory cost, burst behavior, and how sharply they enforce the limit at window edges. Pick based on what you are protecting.

**Fixed window** counts requests in a clock-aligned bucket — say, per calendar minute — and resets the counter when the window rolls over. It is trivial to implement (one integer per key) and cheap. Its flaw is the **boundary burst**: a client can send its full quota in the last second of one window and its full quota in the first second of the next, driving 2x the intended rate across that seam.

**Sliding window** fixes the seam by considering a rolling interval rather than a fixed one. A common approximation weights the previous window's count by how far you are into the current one, smoothing the edge without storing a timestamp per request. It costs a little more state and math but eliminates the boundary-burst gap.

**Token bucket** models a bucket that refills at a steady rate up to a maximum capacity; each request removes one token, and a request with no token available is rejected or delayed. This is the one to reach for when you want a **steady average rate but tolerate short bursts** — the bucket capacity *is* your allowed burst. It maps cleanly onto real client behavior, which is bursty.

**Leaky bucket** models a queue that drains at a fixed rate: requests enter, and they leave — are processed — at a constant pace, with overflow dropped. Where token bucket permits bursts up to capacity, leaky bucket **smooths output to a strict constant rate**, which is what you want when the thing downstream cannot absorb spikes at all.

| Algorithm | State per key | Bursts? | Best for |
|---|---|---|---|
| Fixed window | one counter | yes, at the seam | cheap, coarse limits |
| Sliding window | counter(s) + window | no | fair enforcement without seam abuse |
| Token bucket | tokens + last-refill time | up to capacity | steady rate, bursty clients |
| Leaky bucket | queue depth + drain time | no (smoothed) | protecting a fixed-rate downstream |

**The gotcha:** fixed-window is the default people reach for because it is one integer, but its boundary burst means your "100 per minute" limit permits 200 requests across two adjacent seconds. If the endpoint you are protecting is expensive or the limit is a security threshold (login attempts), that 2x matters — use a sliding window or token bucket, where the guarantee holds across the boundary.

---

## Key on identity, not just IP

An algorithm is only half the design. The other half is the **key** — what you count against. Get this wrong and a correct algorithm protects nothing.

- **Per-IP** is the reflexive choice and the weakest one alone. IPs are cheap and shared. An attacker rotates through a residential proxy pool or a cloud provider's address space and each "identity" gets a fresh quota. Meanwhile a thousand legitimate users behind one corporate NAT or mobile carrier gateway share a single IP and trip your limit collectively. Per-IP punishes the innocent and waves through the motivated.
- **Per-authenticated-identity** — per user, per API key, per OAuth client — is the strong key. It ties the ceiling to something the attacker cannot mint for free. To get 100 API keys, they need 100 accounts, and account creation is itself a flow you rate-limit (that is API6, below). This is the key that actually bounds abuse.
- **Per-endpoint** granularity lets you set a strict limit on `/login` and `/password-reset` while leaving `/products` generous. A single global number for the whole API is either too loose for the dangerous endpoints or too tight for the cheap ones.
- **Global** (a ceiling across all callers) is your backstop against a distributed flood no per-identity limit catches — a last-resort valve to protect the service as a whole, layered on top of the finer keys, not instead of them.

The right design is layered: a global cap for total capacity, per-endpoint limits sized to each endpoint's cost, and — the load-bearing one — per-authenticated-identity limits, with per-IP as a coarse pre-auth filter on the endpoints that have to accept unauthenticated traffic (login, signup) precisely because there is no identity to key on yet.

**The gotcha:** per-IP limits alone are trivially bypassed. Rotating proxies give an attacker a fresh quota per address, while shared NAT makes many honest users look like one abuser. Key on the authenticated identity (user ID, API key, client ID) as the primary dimension, and use IP only as a secondary, coarse filter for the pre-authentication endpoints where no identity exists yet.

---

## The standardized response: 429, Retry-After, and RateLimit headers

When a caller exceeds a limit, how you say "no" matters. The correct status is **429 Too Many Requests**. Pair it with a `Retry-After` header telling the client how long to wait — either seconds or an HTTP date. Well-behaved clients read it and back off; without it, they retry immediately and turn your limit into a tight retry loop that makes the pressure worse.

Beyond the rejection, expose the client's budget *before* they hit the wall using the IETF `RateLimit` header fields. The current draft standardizes `RateLimit-Limit`, `RateLimit-Remaining`, and `RateLimit-Reset` (seconds until the window refills) so clients can pace themselves rather than discovering the limit by tripping it.

```http
HTTP/1.1 429 Too Many Requests
Content-Type: application/json
Retry-After: 30
RateLimit-Limit: 100
RateLimit-Remaining: 0
RateLimit-Reset: 30

{ "error": "rate_limit_exceeded", "message": "Too many requests. Retry after 30 seconds." }
```

**The gotcha:** returning a bare 429 with no `Retry-After` teaches clients nothing, so they retry instantly and hammer you harder — the limit amplifies load instead of shedding it. Always include `Retry-After` (and the `RateLimit-*` budget headers) so a cooperative client backs off gracefully and only the genuinely abusive ones keep knocking.

---

## A token-bucket limiter in Go, keyed per API key

Go's standard extended library ships a production-grade token-bucket limiter in `golang.org/x/time/rate`. A `rate.Limiter` is one bucket; to key per identity we keep a map of limiters, one per API key, created on first sight. `limiter.Allow()` removes a token if one is available and returns false otherwise.

```go
import (
	"net/http"
	"strconv"
	"sync"
	"time"

	"golang.org/x/time/rate"
)

// One token bucket per API key. r = steady refill rate, b = burst capacity.
type keyedLimiter struct {
	mu    sync.Mutex
	buckets map[string]*rate.Limiter
	r     rate.Limit
	b     int
}

func newKeyedLimiter(perSecond float64, burst int) *keyedLimiter {
	return &keyedLimiter{
		buckets: make(map[string]*rate.Limiter),
		r:       rate.Limit(perSecond),
		b:       burst,
	}
}

func (k *keyedLimiter) get(apiKey string) *rate.Limiter {
	k.mu.Lock()
	defer k.mu.Unlock()
	lim, ok := k.buckets[apiKey]
	if !ok {
		lim = rate.NewLimiter(k.r, k.b) // e.g. 5 req/s sustained, burst of 20
		k.buckets[apiKey] = lim
	}
	return lim
}

func (k *keyedLimiter) Middleware(next http.Handler) http.Handler {
	return http.HandlerFunc(func(w http.ResponseWriter, req *http.Request) {
		apiKey := req.Header.Get("X-API-Key")
		if apiKey == "" {
			http.Error(w, "missing API key", http.StatusUnauthorized)
			return
		}
		lim := k.get(apiKey)
		if !lim.Allow() {
			// Reserve to learn how long until a token is free, then reject.
			delay := lim.Reserve().Delay()
			w.Header().Set("Retry-After", strconv.Itoa(int(delay.Round(time.Second).Seconds())))
			w.Header().Set("RateLimit-Limit", strconv.Itoa(k.b))
			w.Header().Set("RateLimit-Remaining", "0")
			http.Error(w, "rate limit exceeded", http.StatusTooManyRequests)
			return
		}
		next.ServeHTTP(w, req)
	})
}
```

Two practical notes. The in-memory map works for a single process; behind a load balancer you need a **shared store** (Redis with an atomic token-bucket script, or a dedicated gateway) so the limit is enforced across all instances rather than per-instance — otherwise N replicas grant N times the intended rate. And the map grows unbounded as new keys appear; in production, evict idle limiters on a timer or cap the map size.

---

## Protect the expensive operations, not just the frequent ones

API4 is not only about request *count*. A single request can be catastrophically expensive if the endpoint lets the client dictate how much work it does. These are denial-of-service vectors you ship yourself, and no per-minute limit saves you if one call can pin the database.

- **Pagination must be bounded.** An endpoint that honors `?limit=1000000` will happily try to serialize a million rows into one response — memory, CPU, and bandwidth in a single request. Set a **maximum page size** the client cannot exceed (clamp, don't trust) and require pagination on any collection that can grow. This is the same discipline covered when designing paginated APIs; here it is a security control, not just ergonomics.
- **Query cost / complexity must be capped.** Anywhere the client shapes the query — filter combinations, sort fields, and especially GraphQL, where a nested query can fan out into an exponential number of resolver calls — you need a cost budget. Depth limiting, complexity scoring, and node caps are the GraphQL-specific tools (covered in the GraphQL post); the principle is universal: never let one request purchase unbounded work.
- **Request bodies must be size-capped.** An unbounded upload or JSON body is a memory-exhaustion vector. Cap it at the edge.
- **Operations must time out.** A slow query or a hung downstream call holds a connection and a goroutine/thread; enough of them and the pool is exhausted. Set server read/write timeouts and per-operation deadlines.

The body-size guard in Go is one line at the top of the handler, using `http.MaxBytesReader`, which caps the read *and* signals the client with a clean error rather than reading gigabytes into memory first:

```go
func createOrder(w http.ResponseWriter, r *http.Request) {
	// Cap the body at 1 MiB. Reads past the limit fail instead of buffering.
	r.Body = http.MaxBytesReader(w, r.Body, 1<<20)

	dec := json.NewDecoder(r.Body)
	dec.DisallowUnknownFields()
	var in CreateOrder
	if err := dec.Decode(&in); err != nil {
		// MaxBytesReader surfaces an oversize body as an error here.
		http.Error(w, "request body too large or malformed", http.StatusRequestEntityTooLarge)
		return
	}
	// ... clamp pagination the same way, distrusting client-supplied sizes:
	// pageSize := min(in.PageSize, maxPageSize)
	_ = in
}
```

**The gotcha:** an endpoint with no maximum page size or query-cost limit is a denial-of-service vulnerability you built and shipped. `?limit=10000000` or a deeply nested GraphQL query lets a single authenticated, authorized, well-formed request exhaust the database or the app's memory. Clamp page size server-side, cap query complexity, size-limit bodies, and set timeouts — resource limits are input validation for *cost*.

---

## API6: rate-limit the flow, not just the endpoint

Now the subtler class. Some flows are made of individually legitimate requests that become harmful only in bulk. Each call passes every check you have. The harm is the aggregate against your *business*, and OWASP names it API6:2023 Unrestricted Access to Sensitive Business Flows.

Consider the flows: automated **signup** to farm free-trial accounts or seed spam; **checkout / add-to-cart** run by scalper bots that clear limited inventory the moment it drops; **coupon or gift-card redemption** brute-forced for value; **password reset** or **invite** endpoints abused to spam real users' inboxes; **comment or review** posting weaponized for astroturfing. A single signup is not an attack. Ten thousand signups a minute from a bot farm is — even though every one of them is a valid request your API was designed to serve.

The mitigations layer, because no single one is sufficient:

- **Rate-limit the flow itself**, keyed on the best available identity and on secondary signals (IP, device) for the pre-auth flows. The limit here protects a *business outcome* (accounts created, coupons redeemed), so size it to the business, not to raw traffic.
- **Interpose a challenge** — a CAPTCHA or proof-of-work on the anonymous flows (signup, reset), and **step-up authentication** (re-auth, MFA) on the sensitive authenticated ones (checkout, changing payout details). A challenge raises the per-attempt cost enough to break the economics of bulk automation.
- **Device fingerprinting** links requests that rotate IPs but share a browser/device signature, so the ceiling follows the actor rather than the address.
- **Anomaly detection** watches for the shape of automation — inhuman timing, a spike in a normally-rare flow, a burst of failures — and escalates to a challenge or a temporary block.

**The gotcha:** a flow can be an API6 vulnerability even when every single request in it is authenticated, authorized, and valid — because the abuse is running a *legitimate* flow at illegitimate scale. Signup, checkout, and coupon redemption are the classic examples: nothing about one call is wrong. Rate-limit the **flow** against identity and device, and gate it with a CAPTCHA or step-up so bulk automation stops being profitable.

---

## Where each limit lives

| Threat (OWASP) | Limit | Keyed / scoped on |
|---|---|---|
| Credential stuffing, brute force (API4) | Failed-attempt limit on `/login`, `/reset` | Identity + IP, per-endpoint |
| Scraping, general flooding (API4) | Request-rate limit (token/sliding window) | Authenticated identity, then IP |
| One expensive request (API4) | Max page size, query-cost cap, body-size limit, timeouts | Per-request, clamped server-side |
| Runaway third-party cost (API4) | Quota on metered operations | Per API key / tenant |
| Distributed flood (API4) | Global ceiling | Whole service |
| Bulk abuse of a valid flow (API6) | Flow rate limit + CAPTCHA / step-up | Flow, per identity + device |

---

## Key takeaways

- **Limits are a security control.** They bound the blast radius of credential stuffing, scraping, brute force, DoS, and runaway cost — abuse made of individually valid requests. Ship a limit on day one, not "when traffic grows."
- **Pick the algorithm for the job.** Fixed window is cheap but bursts at the seam; sliding window enforces fairly; token bucket allows controlled bursts; leaky bucket smooths to a constant rate. Don't default to fixed window for security thresholds.
- **Key on identity, not IP.** Rotating proxies defeat per-IP limits and shared NAT punishes honest users. Make the authenticated identity the primary key and use IP only as a coarse pre-auth filter.
- **Say no correctly.** Return 429 with `Retry-After` and the `RateLimit-*` budget headers so cooperative clients back off instead of hammering you into a tighter loop.
- **Cost is input, too.** Clamp page size, cap query complexity, size-limit bodies, and set timeouts — an unbounded query or upload is a DoS you shipped yourself.
- **Rate-limit the flow.** Signup, checkout, and coupon redemption are API6 risks even when every request is legitimate. Limit the flow against identity and device, and gate it with a challenge or step-up to break the economics of bulk automation.

---

## Further reading

- [OWASP API Security Top 10 — API4:2023 Unrestricted Resource Consumption](https://owasp.org/API-Security/editions/2023/en/0xa4-unrestricted-resource-consumption/)
- [OWASP API Security Top 10 — API6:2023 Unrestricted Access to Sensitive Business Flows](https://owasp.org/API-Security/editions/2023/en/0xa6-unrestricted-access-to-sensitive-business-flows/)
- [IETF — RateLimit header fields for HTTP (Internet-Draft)](https://datatracker.ietf.org/doc/draft-ietf-httpapi-ratelimit-headers/)
- [Go package documentation — golang.org/x/time/rate](https://pkg.go.dev/golang.org/x/time/rate)
