# The Network Stack

*Every backend engineer relies on the network constantly and understands it vaguely — until a mysterious timeout, a TLS error, or a latency spike forces a reckoning. The layered model of networking is the map that makes those problems legible: each layer does one job, hides the one below it, and fails in its own characteristic way. Learn the layers and the network stops being magic.*

You make an HTTP request and data arrives. Underneath that simple act is a stack of protocols, each solving one piece of the problem of moving bytes between two machines that may be on opposite sides of the planet. This series is that stack, explained for backend engineers — IP, TCP/UDP, DNS, TLS, HTTP, load balancing — and it starts with the layered model itself, because the single most useful mental tool in networking is knowing which layer you're dealing with.

## Why networking is layered

Moving data between two computers reliably over an unreliable, global, heterogeneous network is a huge problem. The foundational engineering decision is to **decompose it into layers**, each responsible for one concern and each building on the layer below without needing to know how that layer works internally:

- Each layer solves *one* problem (addressing, reliable delivery, encryption, application semantics).
- Each layer *uses* the layer below as a service and *provides* a service to the layer above.
- Layers are **independent** — you can change how one works without touching the others (swap the physical medium from copper to fiber to wireless, and TCP above doesn't care).

This layering is why the internet works at all: it lets different technologies interoperate (any link type, any application) by agreeing on the interfaces between layers. And for you, the engineer, it's a *diagnostic map*: when something breaks, the question "which layer?" narrows an infinite problem to a specific one. A DNS failure, a TCP timeout, a TLS handshake error, and an HTTP 500 are problems at four different layers, with four different causes and fixes — and confusing them is why network debugging feels hopeless until you think in layers.

## The TCP/IP model

There are two common layer models: the theoretical 7-layer OSI model and the practical 4-layer TCP/IP model that the internet actually uses. This series uses the TCP/IP model because it maps to what you actually work with:

```text
  ┌─────────────────────────────────────────────┐
  │ Application   │ HTTP, DNS, TLS               │  what your app speaks
  ├─────────────────────────────────────────────┤
  │ Transport     │ TCP, UDP                     │  process-to-process delivery
  ├─────────────────────────────────────────────┤
  │ Internet      │ IP                           │  host-to-host addressing/routing
  ├─────────────────────────────────────────────┤
  │ Link          │ Ethernet, Wi-Fi              │  the physical hop
  └─────────────────────────────────────────────┘
```

- **Link layer** — moves data across a *single physical hop* (your machine to the router). Ethernet, Wi-Fi. Below most backend concerns, but it's the ground truth.
- **Internet layer (IP)** — moves packets *host to host* across networks, using IP addresses and routing (the next post). It gets a packet from any machine to any other machine, globally — but without guarantees.
- **Transport layer (TCP/UDP)** — moves data *process to process* on those hosts, and (for TCP) adds reliability on top of IP's best-effort delivery. This is where "reliable connection" vs. "fast datagram" is decided (the TCP/UDP post).
- **Application layer** — the protocols your application actually speaks: HTTP for web, DNS for name lookup, and TLS for encryption sits here too. This is where most backend work lives, but it *rests on everything below*.

The key relationships: **IP addresses hosts, TCP/UDP addresses processes on those hosts (via ports), and the application layer gives meaning to the bytes.** Most backend engineers live at the application layer (HTTP) but hit problems that originate lower (a TCP timeout, a DNS failure, a TLS mismatch) — which is exactly why understanding the whole stack pays off.

## Encapsulation: how the layers combine

The layers cooperate through **encapsulation** — each layer wraps the data from the layer above with its own header, like nested envelopes:

```text
Sending (wrapping):                    Receiving (unwrapping):
  App:   [ HTTP request ]                Link strips its header →
  TCP:   [TCP hdr][ HTTP request ]       IP strips its header →
  IP:    [IP hdr][TCP hdr][ HTTP ]       TCP strips its header →
  Link:  [Link hdr][IP][TCP][ HTTP ]     App receives the HTTP request
         → bytes on the wire
```

- When you **send**, data descends the stack: HTTP hands its request to TCP, which prepends a TCP header (with port numbers) and hands it to IP, which prepends an IP header (with addresses) and hands it to the link layer, which frames it for the physical medium. Each layer adds the information *its peer* on the other end needs.
- When you **receive**, it ascends: each layer reads and strips *its own* header, using that information to decide what to do, then passes the payload up. The IP layer uses the IP header to confirm delivery, TCP uses its header to reassemble and order, and HTTP finally sees a clean request.

The elegance: each layer only reads *its own* header and treats everything above as opaque payload. This is what makes the layers independent — TCP doesn't parse HTTP, IP doesn't parse TCP. Encapsulation is the mechanism that turns the conceptual layering into an actual working protocol stack.

## Why this matters for backend engineers

You might ask why an application developer needs the lower layers. Because the abstractions leak, and when they do, only layer-thinking saves you:

- **Latency has layer-specific sources** — DNS resolution, TCP handshake, TLS handshake, and the actual HTTP request each add time (later posts quantify this). "The request is slow" is really "which layer's step is slow?"
- **Failures have layer-specific causes** — connection refused (transport), name not resolved (DNS), certificate invalid (TLS), 500 error (application). The fix depends entirely on the layer.
- **Performance tuning targets specific layers** — connection pooling and keep-alive (transport), DNS caching, TLS session reuse, HTTP/2 multiplexing — each optimizes a different layer's cost (the practice post).

The map is the payoff: when you hold the stack in your head, a networking problem becomes "isolate the layer, then diagnose within it," which is tractable, instead of "the network is broken," which is despair. The rest of the series walks up the stack — IP and routing, TCP/UDP, DNS, TLS, HTTP, load balancing — giving you the working knowledge of each layer that backend engineering quietly demands.

## Key takeaways

- Networking is layered because moving data reliably across a global, heterogeneous, unreliable network is decomposed into independent layers, each solving one concern and using the layer below as a service — which is what lets diverse technologies interoperate.
- The practical model is TCP/IP's four layers: Link (one physical hop), Internet/IP (host-to-host addressing and routing), Transport/TCP-UDP (process-to-process delivery, TCP adds reliability), and Application (HTTP, DNS, TLS — what your app speaks).
- IP addresses hosts, TCP/UDP addresses processes via ports, and the application layer gives the bytes meaning — most backend work is at the application layer but hits problems originating lower.
- Layers combine via encapsulation: sending wraps data in each layer's header (descending the stack), receiving strips each header (ascending); every layer reads only its own header and treats the rest as opaque payload, which is what keeps them independent.
- Layer-thinking is the diagnostic payoff: latency, failures, and tuning are all layer-specific (DNS vs TCP vs TLS vs HTTP), so "which layer?" turns an intractable "the network is broken" into a specific, solvable problem.

## Further reading

- [MDN — how the web works / HTTP overview](https://developer.mozilla.org/en-US/docs/Web/HTTP/Overview)
- [Wikipedia — the OSI model](https://en.wikipedia.org/wiki/OSI_model)
- [System Design Fundamentals series](/blog/series/system-design-fundamentals/)
