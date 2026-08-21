# HTTP Evolution: 1.1 to 2 to 3

*HTTP is the protocol your applications actually speak, and it has quietly reinvented itself twice to fight one persistent enemy: head-of-line blocking, where one slow thing stalls everything behind it. The journey from HTTP/1.1 to HTTP/2 to HTTP/3 is the story of chasing that problem down the stack — and understanding it explains why modern connections are so much faster.*

The lower layers deliver bytes securely; **HTTP** is what those bytes *mean* — the request/response protocol of the web and most APIs. But "HTTP" isn't one thing: it has three major versions in active use, each solving a performance problem the last couldn't. This post traces that evolution — HTTP/1.1's limits, HTTP/2's multiplexing, HTTP/3's move to QUIC — around the recurring villain of **head-of-line blocking**, so you understand what version your systems use and why it matters.

## HTTP, the constant

Across all versions, the *semantics* of HTTP are stable: a client sends a **request** (a method like GET/POST, a URL, headers, an optional body), and the server returns a **response** (a status code, headers, a body). Methods, status codes, and headers work the same whether you're on HTTP/1.1 or HTTP/3 — what changes between versions is the *transport mechanics*: how requests and responses are actually moved over the connection, and how efficiently. So the evolution isn't about *what* HTTP says but *how fast and concurrently* it can say it. Keep that split in mind: semantics constant, transport improving.

## HTTP/1.1 and its bottleneck

HTTP/1.1 was the web's workhorse for two decades. Its model: a request is sent on a TCP connection, and the response comes back — but crucially, on a single connection, **one request/response must complete before the next can be sent.** This creates **head-of-line (HOL) blocking at the HTTP layer**: if one response is slow, every request queued behind it on that connection waits, even if they could have been answered instantly.

```text
HTTP/1.1 on one connection:
  Request A ──▶ (slow response A) ──────────▶
                                  Request B waits... ──▶ response B
  → B is blocked by A even though B was ready
```

The workarounds of the HTTP/1.1 era reveal the pain:

- **Multiple parallel connections.** Browsers opened several TCP connections per host (typically ~6) to send requests in parallel — but each connection pays its own TCP+TLS handshake (the setup cost from earlier posts), and the number is limited, so it's a partial, expensive fix.
- **Bundling and spriting.** Web developers concatenated files (JS bundles, CSS, image sprites) to reduce the *number* of requests, working around the per-request cost. Whole build pipelines existed largely to fight HTTP/1.1's limits.

These hacks worked but were symptoms of the underlying problem: HTTP/1.1 couldn't efficiently multiplex many requests over one connection. That's what HTTP/2 set out to fix.

## HTTP/2: multiplexing over one connection

**HTTP/2** solved HTTP/1.1's blocking by introducing **multiplexing**: many requests and responses can be **in flight simultaneously over a single TCP connection**, interleaved as independent **streams**. No more waiting for one response before sending the next; no more opening six connections.

```text
HTTP/2 on ONE connection:
  Request A ──▶  ┐
  Request B ──▶  ├─ all in flight at once, responses interleaved
  Request C ──▶  ┘
  → A being slow no longer blocks B and C at the HTTP layer
```

Its improvements:

- **Multiplexing** — many concurrent streams on one connection, eliminating HTTP-layer HOL blocking and the need for many connections. One connection, one handshake, many parallel requests.
- **Header compression** — HTTP headers are repetitive and verbose; HTTP/2 compresses them (HPACK), cutting overhead, especially for many small requests.
- **Binary framing** — HTTP/2 is a binary protocol (vs HTTP/1.1's text), more efficient to parse.

HTTP/2 made the HTTP/1.1 workarounds largely unnecessary — bundling and multiple connections became counterproductive — and sped up the web substantially. But it had a subtle remaining flaw, one it couldn't fix because of the layer it ran on.

## The TCP head-of-line blocking problem

HTTP/2 removed HOL blocking at the *HTTP* layer — but a deeper one remained at the *TCP* layer. Recall that TCP guarantees *ordered* delivery (the TCP post): it delivers bytes to the application strictly in order, holding back later bytes until earlier lost ones are retransmitted. HTTP/2 runs all its multiplexed streams over *one* TCP connection, so:

```text
HTTP/2 streams A, B, C multiplexed over ONE TCP connection.
A packet for stream A is LOST →
  TCP holds ALL subsequent bytes (including B's and C's) until A's packet is retransmitted
  → streams B and C stall waiting for A's lost packet — TCP-level HOL blocking
```

Because TCP can't tell that the bytes belong to *independent* streams, a single lost packet stalls *all* the multiplexed streams until retransmission — the blocking HTTP/2 fixed at its own layer reappears at the transport layer beneath it. This is worse on lossy networks (mobile, congested links). HTTP/2 fundamentally *can't* fix this, because the problem lives in TCP, below HTTP. Solving it required changing the transport itself.

## HTTP/3: HTTP over QUIC

**HTTP/3** eliminates TCP head-of-line blocking by abandoning TCP entirely and running over **QUIC** — a modern transport built on **UDP** (the TCP/UDP post foreshadowed this). QUIC reimplements the reliability and ordering TCP provided, but with *independent streams*, so a lost packet only stalls *its own* stream:

```text
HTTP/3 over QUIC (on UDP):
  Streams A, B, C are independent within QUIC.
  A packet for stream A is lost →
  only stream A waits; B and C proceed unaffected → no cross-stream HOL blocking
```

Why build on UDP? Because TCP's ordered-delivery-across-everything is exactly the constraint causing the problem, and TCP is deeply baked into operating systems and network hardware (hard to change). By building on UDP (which imposes no ordering) and implementing its own per-stream reliability, QUIC gets TCP's guarantees *where wanted* without its cross-stream blocking. QUIC's other wins:

- **True per-stream independence** — no transport-level HOL blocking; one stream's loss doesn't stall others.
- **Faster connection setup** — QUIC integrates the cryptographic handshake with the transport handshake, so establishing a secure connection takes fewer round-trips than TCP+TLS separately (attacking the setup-cost theme from the TCP and TLS posts).
- **Connection migration** — a QUIC connection can survive a network change (Wi-Fi to cellular) without fully re-establishing, useful for mobile.

HTTP/3 is the current state of the art, increasingly deployed, and it completes the arc: HTTP/1.1's per-request blocking → HTTP/2's multiplexing (HTTP-layer fix) → HTTP/3's QUIC (transport-layer fix). Each step chased head-of-line blocking one layer deeper.

## What this means for backend engineers

You don't usually implement these protocols, but the evolution shapes real decisions:

- **Use HTTP/2 or HTTP/3** where available — they're substantially faster than 1.1, largely for free (supported by modern servers, load balancers, and CDNs). Enabling them is often a config change with real gains.
- **Drop the HTTP/1.1 workarounds** — excessive bundling, domain sharding, and many parallel connections are counterproductive under HTTP/2/3; they optimized for a bottleneck that no longer exists.
- **Understand where each is spoken** — often HTTP/2 or HTTP/3 runs between the client and your CDN/load balancer, which may talk HTTP/1.1 or HTTP/2 to your backends; know the versions across your path.
- **The setup-cost and connection-reuse themes persist** — HTTP/2/3 reduce them (one connection, faster handshakes), which is one more reason to prefer them.

HTTP is the language your applications speak, and its three versions are a masterclass in chasing one performance problem down the stack. With HTTP understood, the last building blocks are the infrastructure that sits in front of your servers — load balancers and proxies — the next post.

## Key takeaways

- HTTP's semantics (methods, status codes, headers, request/response) are constant across versions; what evolves is the transport mechanics — how concurrently and efficiently requests move — driven by chasing head-of-line blocking.
- HTTP/1.1 sends one request/response at a time per connection, causing HTTP-layer HOL blocking; the era's workarounds (multiple connections, bundling/spriting) were symptoms of that limit.
- HTTP/2 introduced multiplexing — many interleaved streams over one connection — plus header compression and binary framing, eliminating HTTP-layer HOL blocking and making the old workarounds counterproductive.
- HTTP/2 still suffered TCP-layer HOL blocking: because all streams share one ordered TCP connection, a single lost packet stalls every multiplexed stream — a problem HTTP/2 can't fix because it lives in TCP below it.
- HTTP/3 runs over QUIC (built on UDP) with independent per-stream reliability, so a lost packet stalls only its own stream — plus faster combined transport+crypto handshakes and connection migration; use HTTP/2/3 where available and drop the HTTP/1.1 workarounds.

## Further reading

- [TLS and HTTPS (previous post)](/blog/posts/net-05-tls-and-https.html)
- [MDN — evolution of HTTP](https://developer.mozilla.org/en-US/docs/Web/HTTP/Guides/Evolution_of_HTTP)
- [TCP and UDP — why QUIC builds on UDP](/blog/posts/net-03-tcp-and-udp.html)
