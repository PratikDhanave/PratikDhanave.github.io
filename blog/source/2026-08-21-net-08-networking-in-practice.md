# Networking in Practice for Backend Engineers

*All the theory pays off in a handful of habits that separate resilient backend code from code that falls over the first time the network misbehaves — which it will. Set timeouts on everything, reuse connections, retry idempotently, and know how to read the layers when something breaks. This closing post turns the stack into a working checklist.*

The series climbed the stack from IP to load balancers. This final post brings it down to daily code: the networking concerns a backend engineer actually handles, and how the earlier concepts turn into practices that keep services fast and resilient. The unifying truth — echoing the distributed-systems series — is that **the network is unreliable and slow relative to local operations**, so backend code must be written *expecting* it to fail and lag. These are the habits that encode that expectation.

## Always set timeouts

The single most important networking practice: **set timeouts on every network operation.** A network call with no timeout can hang *forever* — a slow or dead server, a lost packet, a black-hole route — and a hung call holds resources (a thread, a connection, memory) indefinitely. Enough hung calls exhaust your resources and take your service down. This is the cascade failure from the distributed-systems series, and the first defense is timeouts:

- **Every outbound call needs a timeout** — HTTP requests, database queries, cache lookups, any I/O to another service. No exceptions; "it's usually fast" is not a guarantee.
- **Set them deliberately, not by default.** A timeout too long lets slow calls pile up (barely better than none); too short kills healthy-but-slow requests. Base it on the operation's realistic latency plus margin.
- **Distinguish connection vs. read timeouts** — how long to wait to *establish* the connection (the TCP/TLS handshake from earlier) vs. to *receive* data. Both matter.

A missing timeout is the most common networking bug that turns one slow dependency into a full outage. If you take one practice from this series, it's: **timeouts on everything.**

## Reuse connections

The setup-cost theme from the TCP and TLS posts becomes a concrete practice: **reuse connections instead of opening a new one per request.** Recall that a new HTTPS connection pays a TCP handshake *and* a TLS handshake — round-trips of pure latency before any data. Doing that per request is wasteful; the fixes:

- **Keep-alive** — HTTP keep-alive keeps the TCP connection open after a response so the next request reuses it, skipping the handshakes. Enabled by default in modern clients, but confirm it's on.
- **Connection pooling** — maintain a pool of open connections to a service (or database) and borrow/return them per request, so the expensive setup is amortized across many requests. This is standard for database clients and HTTP clients, and mis-sized pools (too small → contention; too large → resource exhaustion) are a common performance issue worth tuning.
- **Prefer HTTP/2 or HTTP/3** — which multiplex many requests over one connection (the HTTP post), reducing the number of connections and handshakes further.

The anti-pattern to avoid: creating a fresh client/connection for every request (a surprisingly common mistake in code that instantiates an HTTP client per call). Reuse clients and pool connections — it's often a large, easy latency win.

## Retry — but carefully

Networks drop requests, so retrying is necessary — but naive retries cause harm, exactly as the distributed-systems resilience post covered:

- **Only retry idempotent operations,** or use idempotency keys. A request that timed out might have *succeeded* (the response was lost), so blindly retrying a non-idempotent operation (a payment, an order) can double it. Retry safe operations; make unsafe ones idempotent first.
- **Use exponential backoff with jitter.** Retrying immediately and in lockstep hammers a struggling service and causes thundering-herd retry storms; wait progressively longer with randomization so retries spread out and let the service recover.
- **Bound retries and combine with circuit breakers.** Don't retry forever — cap attempts, and use circuit breakers (the resilience post) to stop hammering a dependency that's clearly down, failing fast instead.

Retries plus timeouts plus circuit breakers are the resilience trio for network calls: timeout to not hang, retry (safely) to survive transient loss, circuit-break to not pile onto a failure.

## Handle failure as normal, not exceptional

The mindset from the distributed-systems series applies directly to networked backend code: **network failures are the normal case, not an edge case.** Every network call *will* sometimes fail, time out, or return slowly, so write code that handles it gracefully:

- **Expect and handle errors on every call** — connection refused, timeout, DNS failure, TLS error, 5xx responses. Code that assumes calls succeed breaks in production.
- **Degrade gracefully** — when a non-critical dependency fails, serve a fallback (cached value, default) rather than failing the whole request (the graceful-degradation practice). Distinguish essential from enhancing calls.
- **Don't let one dependency's failure cascade** — timeouts, circuit breakers, and bulkheads (isolating resources per dependency) keep a failing dependency from taking down everything (the cascade lesson).

Robust backend code treats the network as hostile terrain: it assumes calls can fail and lag, and it contains the damage when they do.

## Know how to debug across the layers

When something breaks, the layered model from post one becomes your diagnostic tool — isolate the layer, then use the right tool:

- **DNS?** — does the name resolve, to the right address? (The "it's always DNS" check.) Tools: `dig`, `nslookup`.
- **Connectivity / transport?** — can you even reach the host and port? Is it a connection refused (nothing listening) vs. timeout (blocked/unreachable)? Tools: `ping`, `telnet`/`nc` to a port, `traceroute` for the path.
- **TLS?** — certificate valid, not expired, right domain, protocol version supported? Tools: `openssl s_client`, `curl -v`.
- **HTTP/application?** — right status code, headers, body? Tools: `curl -v`, browser dev tools, application logs.
- **Latency — which layer?** — use timing breakdowns (e.g. `curl`'s timing output, tracing from the observability series) to see whether time went to DNS, connect, TLS, or the server. This is where the observability series and this one meet: distributed tracing localizes *where* across services, and per-request timing localizes *which layer*.

The discipline is the same as the whole series: **ask "which layer?"** A methodical layer-by-layer check turns "the network is broken" into a specific, fixable diagnosis, fast.

## The series in one checklist

Networking for backend engineers, distilled: understand the **stack** (which layer?), know that **IP** is best-effort and **TCP** builds reliability at a handshake cost, that **DNS** resolves names (and fails often), that **TLS** secures connections at another handshake cost, that **HTTP/2-3** multiplex to fight head-of-line blocking, and that **load balancers/proxies/CDNs** scale and shield your servers. Then, in code: **timeouts on everything, reuse connections, retry idempotently with backoff, handle failure as normal, and debug by layer.** The network is unreliable and slow by nature; the engineer who writes code expecting that — and who can read the layers when it misbehaves — builds services that stay up. That expectation, encoded in these habits, is what the whole series was for.

## Key takeaways

- Set timeouts on every network operation — a call with no timeout can hang forever, holding resources until they exhaust and cascade into an outage; set them deliberately (connection vs. read) based on realistic latency. This is the top networking practice.
- Reuse connections to amortize the TCP+TLS handshake cost: use keep-alive and connection pooling (tune pool size), reuse HTTP/DB clients rather than creating one per request, and prefer HTTP/2-3 multiplexing — often a large, easy latency win.
- Retry carefully: only retry idempotent operations (or use idempotency keys, since a timed-out request may have succeeded), use exponential backoff with jitter to avoid retry storms, and bound retries with circuit breakers.
- Treat network failure as the normal case, not an edge case: handle errors on every call, degrade gracefully with fallbacks for non-critical dependencies, and contain failures with timeouts/circuit breakers/bulkheads so one dependency can't cascade.
- Debug by layer: check DNS (dig), connectivity/transport (ping, nc, traceroute), TLS (openssl, curl -v), and HTTP (curl -v, logs), and use timing breakdowns/tracing to localize which layer owns a latency problem — "which layer?" turns "the network is broken" into a fixable diagnosis.

## Further reading

- [Load balancing and proxies (previous post)](/blog/posts/net-07-load-balancing-and-proxies.html)
- [The network stack — start of the series](/blog/posts/net-01-the-network-stack.html)
- [Distributed Systems: failure and resilience](/blog/posts/distsys-08-failure-and-resilience.html)
