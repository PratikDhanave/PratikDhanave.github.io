# gRPC in Production

*A gRPC service that works on localhost is a long way from one that runs reliably at scale. Production raises questions localhost never does: how do calls get load-balanced when connections are long-lived? How do you secure them, expose them to browsers, observe them, and evolve the contract without breaking anyone? This closing post covers what it takes to run gRPC for real.*

We've built gRPC from the object model up: the contract, codegen, call types, deadlines, errors, streaming. This final post is about operating it. These are the concerns that turn a working service into a dependable one — and several have gRPC-specific twists that catch teams off guard.

## Load balancing: the connection problem

The first surprise in production is that **gRPC breaks naive load balancing**. gRPC runs over HTTP/2, which uses *long-lived, multiplexed connections* — a client opens one connection and sends many requests over it. That's great for performance (post 1) but bad for the standard "connection-level" load balancer, which distributes *connections* across backends. If each client holds one persistent connection, all its requests pin to a single backend, and load spreads unevenly — one server melts while others idle.

There are two standard fixes:

- **Client-side load balancing.** The client is aware of multiple backend addresses and spreads *individual requests* across them (round-robin or smarter policies), using a resolver to discover the current set of backends. gRPC has built-in support for this.
- **An L7 (request-aware) proxy.** A proxy that understands HTTP/2 and gRPC — such as Envoy, or a service mesh — load-balances at the *request* level, distributing individual RPCs across backends even over shared connections. This is common in Kubernetes, where a mesh handles it transparently.

The key takeaway is to *know* this: dropping gRPC behind a plain TCP/L4 load balancer and expecting even distribution is a classic production failure. Plan for request-level balancing from the start.

## Security: TLS and auth

gRPC supports transport security and call authentication, and production should use both:

- **TLS** encrypts the connection. In production you configure the server with a certificate and the client to verify it — never the `insecure` credentials that are fine for local development. Between internal services, mutual TLS (mTLS), often provided by a service mesh, authenticates *both* ends.
- **Call authentication** rides on the metadata and interceptor mechanisms from post 5: tokens travel in metadata, and a server interceptor validates them on every call so auth isn't something individual methods can forget.

Encrypt everything and authenticate at the interceptor layer, and security is uniform rather than per-method.

## Exposing gRPC to the world

Two gaps between internal gRPC and the wider ecosystem need bridging:

- **Browsers can't speak native gRPC** (post 1). To call a gRPC service from web frontend code, you use **gRPC-Web**, which runs over HTTP/1.1-compatible framing via a proxy (often Envoy) that translates between gRPC-Web and real gRPC. It supports unary and server-streaming but not client/bidirectional streaming, reflecting browser limits.
- **REST clients and existing tooling** sometimes need a JSON/HTTP interface. **gRPC gateway** tooling generates a REST/JSON proxy *from your `.proto`* (via annotations), so you can offer both a gRPC API for internal services and a REST API for external ones from a single contract. This is a common edge pattern: gRPC everywhere internally, a generated REST gateway at the public boundary.

## Observability

The interceptors from post 5 are where production observability lives, applied to every call:

- **Metrics** — request rate, error rate (by status code), and latency (RED metrics), emitted from an interceptor so every method is measured. Status codes make error metrics especially meaningful — you can alert on a spike in `UNAVAILABLE` or `INTERNAL`.
- **Distributed tracing** — propagate a trace context through metadata so one logical request is traceable across the whole service mesh. gRPC integrates with OpenTelemetry for this.
- **Logging and health checks** — structured logs from interceptors, plus gRPC's standard **health-checking protocol** so load balancers and orchestrators (like Kubernetes) can probe whether a service is ready to receive traffic.

Because these hang off interceptors, you instrument once and get uniform coverage — the payoff of the cross-cutting design from post 5.

## Evolving the contract safely

The longest-lived production concern is *change*. Your `.proto` is a contract many services depend on, and evolving it without coordinated downtime is a core skill — built entirely on the field-numbering rules from post 2:

- **Add fields with new numbers; reserve removed ones.** Old and new clients keep interoperating because unknown fields are ignored and reused numbers are prevented. Never reuse or renumber a field.
- **Add new RPC methods freely.** Existing clients don't call them; new ones do. (The `Unimplemented` server embed from post 4 keeps servers compiling as methods are added.)
- **Version your API** in the package path (`user.v1`, `user.v2`) for genuinely breaking changes, running both versions during migration rather than breaking v1 consumers.
- **Lint and check for breaking changes** in CI. Tooling (like Buf) can detect a breaking `.proto` change *before* it merges — catching a reused field number or removed method automatically, which is exactly the kind of error that otherwise causes a silent production incident.

Treat the `.proto` with the same rigor as any public API, because that's what it is: coordinated, versioned, backward-compatible, and checked.

## The whole picture

gRPC's production story is coherent once you see how the pieces connect. The **HTTP/2 transport** that gives you performance and streaming also forces **request-level load balancing**. The **metadata and interceptor** mechanisms carry **security, observability, and deadlines** uniformly. The **`.proto` contract** that generates your typed code is also what enables **safe evolution** and **REST/gRPC-Web bridging** from one source of truth. Nothing is bolted on; every production concern traces back to a design choice earlier in the series. Run gRPC with these in place — request-aware balancing, TLS + interceptor auth, gRPC-Web/gateway at the edge, interceptor-based observability, and disciplined contract evolution — and you get what RPC promised at the very start: calling a function on another machine, safely and at scale, as if it were local.

## Key takeaways

- gRPC's long-lived HTTP/2 connections **break naive (L4) load balancing** — requests pin to one backend — so use **client-side load balancing** or an **L7/request-aware proxy or service mesh** (e.g. Envoy) to spread individual RPCs.
- Secure with **TLS everywhere** (never `insecure` in production; mTLS between internal services) and **authenticate at the interceptor layer** so no method can skip it.
- Bridge the ecosystem gaps: **gRPC-Web** (via a proxy) lets browsers call gRPC (unary + server-streaming), and a **REST/JSON gateway generated from the `.proto`** offers a public REST API from the same contract.
- Put **observability in interceptors** — RED metrics by status code, OpenTelemetry tracing propagated via metadata, structured logs, and the standard **health-checking protocol** for orchestrators — instrumenting once for uniform coverage.
- **Evolve the `.proto` safely** using the field-numbering rules (add fields/methods, reserve removals, version the package for breaking changes) and **lint for breaking changes in CI** — treat the contract as the versioned public API it is.
- Every production concern traces back to an earlier design choice — HTTP/2, metadata/interceptors, the `.proto` contract — so gRPC's operational story is coherent rather than bolted on.

## Further reading

- [gRPC — Guides (production, load balancing, auth, and more)](https://grpc.io/docs/guides/)
- [Protocol Buffers — Proto Best Practices (Dos and Don'ts)](https://protobuf.dev/programming-guides/dos-donts/)
