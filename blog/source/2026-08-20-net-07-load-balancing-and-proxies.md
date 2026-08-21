# Load Balancing and Proxies

*Almost nothing on the modern internet talks directly to the server that answers it. In between sit proxies and load balancers — the traffic directors that spread load across many servers, terminate TLS, cache responses, and shield your backends. Understanding this layer is understanding how a single domain name serves millions of users from hundreds of machines.*

The previous posts got a secure HTTP request from client to server. But "the server" is usually a fiction — behind one address are many servers, with **load balancers** and **proxies** directing traffic among them. This infrastructure layer is where scalability, resilience, and much operational control live. This post covers reverse vs forward proxies, load balancing and its algorithms, the crucial L4-vs-L7 distinction, and CDNs — the pieces that turn "a server" into "a system that scales."

## Proxies: intermediaries with a purpose

A **proxy** is an intermediary that sits between client and server, forwarding requests and responses. The direction it faces defines its type, and confusing the two is common:

- **Forward proxy** — sits in front of *clients*, forwarding their requests out to the internet. It acts on behalf of the *client* (corporate proxies, content filters, some VPNs). The server sees the proxy, not the client.
- **Reverse proxy** — sits in front of *servers*, receiving requests from the internet and forwarding them to backend servers. It acts on behalf of the *server*. The client sees the proxy, not the individual backend.

The **reverse proxy** is the one central to backend architecture, because it's the single entry point in front of your servers and the natural home for a whole set of jobs:

- **Load balancing** — distributing requests across many backends (below).
- **TLS termination** — handling HTTPS/certificates centrally (the TLS post) so backends don't each manage TLS.
- **Caching** — serving cached responses without hitting backends.
- **Compression, rate limiting, request routing, and security filtering** — cross-cutting concerns handled once, at the edge, instead of in every backend.

A reverse proxy is thus the control point in front of your system — one place to terminate TLS, spread load, cache, and enforce policy. Common reverse proxies (nginx, Envoy, HAProxy, cloud load balancers) are foundational infrastructure.

## Load balancing: one address, many servers

**Load balancing** is the reverse proxy's headline job: distribute incoming requests across a pool of backend servers so no single one is overwhelmed. It's what makes horizontal scaling possible — add more servers behind the balancer to handle more load — and it delivers two things at once:

- **Scalability** — spread traffic across many machines, so capacity grows by adding servers (the horizontal-scaling story from System Design).
- **Availability** — if a backend fails, the balancer stops sending it traffic (via health checks) and routes to healthy ones, so one server's death doesn't take down the service. This is the resilience the distributed-systems series called for, realized in infrastructure.

The balancer decides *which* backend gets each request using a **load-balancing algorithm**:

- **Round robin** — each request to the next server in turn. Simple, even distribution when servers and requests are uniform.
- **Least connections** — send to the server with the fewest active connections. Better when requests vary in duration, avoiding piling onto a busy server.
- **IP hash / consistent hashing** — route based on a hash of the client (or key), so a given client consistently hits the same backend — useful for session affinity (below) and, via consistent hashing (the partitioning post), for minimizing disruption when servers are added/removed.
- **Weighted** variants — send more traffic to more capable servers.

**Health checks** underpin all of it: the balancer continuously checks backends and routes only to healthy ones, which is how failures are handled automatically. Choosing an algorithm depends on your traffic; round robin and least-connections cover most cases.

## L4 vs L7: the crucial distinction

The most important concept in this post is *at which layer* a load balancer operates, because it determines what it can do — and it ties directly back to the network stack from post one:

- **Layer 4 (transport) load balancing** — operates at the TCP/UDP level. It routes based on **IP address and port**, forwarding packets/connections *without looking at their content*. It doesn't know or care whether the traffic is HTTP; it just balances connections. This makes it **fast and simple** (minimal processing) but **limited** — it can't make decisions based on the request's content (URL, headers, cookies) because it doesn't inspect them.
- **Layer 7 (application) load balancing** — operates at the HTTP level. It *understands the request* — URL path, headers, cookies, method — and can route based on them: send `/api/*` to one pool and `/images/*` to another, route by hostname, do cookie-based session affinity, rewrite requests, and cache. This is **more powerful** (content-aware routing, the reverse-proxy features above) but does **more work** per request.

```text
L4: routes on IP:port, blind to content        → fast, simple, connection-level
L7: routes on URL/headers/cookies, HTTP-aware   → powerful, content-based, request-level
```

The practical guidance: **L7 for HTTP applications** (you almost always want content-aware routing, TLS termination, and the reverse-proxy features), **L4 when you need raw speed** or are balancing non-HTTP traffic where you don't need to inspect content. Most web-application load balancing is L7; L4 shines for high-throughput, protocol-agnostic, or lowest-latency cases. Knowing which layer your balancer works at tells you what routing decisions it can (and can't) make.

## Session affinity: a caveat

One recurring wrinkle: **session affinity (sticky sessions)** — configuring the balancer to send a given user consistently to the same backend (via cookie or IP hash). This is sometimes needed when a backend holds per-user *state* in memory (a session). But it's usually a **design smell**: it undermines even load distribution and resilience (if that server dies, the user's state is lost), and it complicates scaling. The better pattern, from the distributed-systems and sessions discussions, is to make backends **stateless** — store session state externally (a shared cache/database) so *any* backend can serve *any* request, and the balancer can distribute freely. Reach for sticky sessions only when you must; prefer stateless backends that don't need them.

## CDNs: load balancing across the globe

Extending these ideas geographically gives the **CDN (Content Delivery Network)** — a globally distributed network of proxy/cache servers that serve users from a location *near them*:

- **Latency** — serving content from a nearby edge server (rather than a distant origin) cuts the network round-trip time (the physics of distance from post one), making responses much faster for a global audience.
- **Caching at the edge** — CDNs cache static (and increasingly dynamic) content at edge locations, serving it without hitting your origin — reducing origin load and speeding delivery.
- **Scale and resilience** — CDNs absorb huge traffic (including DDoS) and shield your origin, acting as a massive distributed reverse proxy in front of everything.

A CDN is essentially reverse-proxy + caching + load balancing applied *globally*, routing each user to a nearby edge — the geographic realization of this whole layer. For any service with a global audience or significant static content, a CDN is standard infrastructure.

## The infrastructure that makes "a server" scale

Load balancers, proxies, and CDNs are the layer that turns a single domain into a scalable, resilient system: a reverse proxy fronts your servers (terminating TLS, caching, filtering), a load balancer spreads traffic across many backends and routes around failures (L7 for content-aware HTTP, L4 for raw speed), stateless backends let it distribute freely, and a CDN extends it all globally for latency and scale. This is where the network knowledge from the whole series meets real architecture. The final post brings it down to earth: the networking concerns backend engineers handle in day-to-day code.

## Key takeaways

- A proxy is an intermediary: a forward proxy fronts clients (acting for the client), a reverse proxy fronts servers (acting for the server) — the reverse proxy is the central entry point for load balancing, TLS termination, caching, and security filtering.
- Load balancing distributes requests across many backends for scalability (add servers to grow capacity) and availability (health checks route around failed servers), using algorithms like round robin, least connections, IP/consistent hash, and weighted.
- The key distinction is L4 vs L7: L4 balances on IP:port without inspecting content (fast, simple, connection-level), L7 understands HTTP (URL/headers/cookies) for content-based routing and reverse-proxy features (powerful, request-level) — use L7 for web apps, L4 for raw speed or non-HTTP.
- Session affinity (sticky sessions) pins a user to one backend for in-memory state but undermines load balancing and resilience — prefer stateless backends with externalized session state so any backend serves any request.
- CDNs apply reverse-proxy + caching + load balancing globally, serving users from nearby edge servers to cut latency, cache at the edge to offload origin, and absorb traffic/DDoS — standard for global or static-heavy services.

## Further reading

- [HTTP evolution (previous post)](/blog/posts/net-06-http-evolution.html)
- [Wikipedia — load balancing](https://en.wikipedia.org/wiki/Load_balancing_(computing))
- [System Design Fundamentals series](/blog/series/system-design-fundamentals/)
