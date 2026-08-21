# TCP and UDP

*IP gets packets to a host but promises nothing about whether they arrive, in order, or intact. The transport layer is where that gap is filled — or deliberately left open. TCP builds a reliable, ordered connection on top of unreliable IP; UDP declines to, trading guarantees for speed. Choosing between them, and understanding TCP's costs, is core backend knowledge.*

The last post established that IP is best-effort: no delivery, order, or integrity guarantees, with reliability pushed to the endpoints. The **transport layer** is those endpoints, and it offers two very different protocols: **TCP**, which turns IP's chaos into a reliable ordered stream, and **UDP**, which adds almost nothing and stays fast. This post covers how TCP achieves reliability (and what it costs), when UDP's minimalism wins, and the ports that let both address individual processes.

## Ports: addressing the process

First, the piece both share. IP addresses get a packet to the right *host*, but a host runs many processes (a web server, a database, an SSH daemon). **Ports** — 16-bit numbers — address the specific *process/service* on that host. The combination of IP address + port identifies a specific endpoint of a connection:

```text
  IP address  → which host        (203.0.113.10)
  Port        → which process     (:443 for HTTPS, :22 for SSH, :5432 for Postgres)
  together    → a specific socket  (203.0.113.10:443)
```

**Well-known ports** conventionally identify services (80 HTTP, 443 HTTPS, 53 DNS, 22 SSH, 5432 Postgres). A TCP or UDP header carries source and destination ports, which is how the transport layer delivers data to the right process and how replies find their way back. Ports are why one server can run many services and one machine can hold many simultaneous connections — each is a distinct (address, port) pair.

## TCP: reliability on top of unreliable IP

**TCP (Transmission Control Protocol)** provides a **reliable, ordered, connection-oriented byte stream** over best-effort IP. Everything it does exists to compensate for IP's non-guarantees:

- **Reliable delivery** — TCP numbers the bytes (sequence numbers) and the receiver **acknowledges** what it got; unacknowledged data is **retransmitted**. Lost packets (which IP allows) are detected and resent, so the application sees no loss.
- **Ordered delivery** — because IP packets can arrive out of order, TCP uses the sequence numbers to **reassemble** the stream in the correct order before handing it to the application. The app reads bytes in the exact order they were sent.
- **Connection-oriented** — TCP establishes a connection before data flows (the handshake, below) and tears it down after, maintaining state on both ends. It's a *stream* abstraction: you write bytes, the other side reads the same bytes in order, as if through a pipe.
- **Flow control and congestion control** — TCP paces sending to avoid overwhelming the receiver (flow control) or the network (congestion control), backing off when it detects loss. This is what keeps the internet from collapsing under load, and it's why TCP throughput adapts to conditions.

The result is the abstraction most applications want: a reliable, ordered pipe. HTTP, database connections, SSH — all run on TCP because they need every byte, in order. TCP hides IP's unreliability so completely that application developers rarely think about packets at all.

## The TCP handshake (and its cost)

TCP establishes a connection with a **three-way handshake** before any data is sent:

```text
Client → Server:  SYN            "I want to connect (here's my sequence number)"
Server → Client:  SYN-ACK        "OK, and here's mine"
Client → Server:  ACK            "Got it — connected"
   → NOW data can flow
```

This exchange synchronizes both sides' sequence numbers and confirms both can send and receive. It's essential for reliability — but it costs a **full round-trip** (one there-and-back) *before any data moves*. That round-trip time (RTT) is pure latency added to every new TCP connection, and it's the source of a major backend performance concern:

- **Connection setup is expensive**, especially over long distances (high RTT). A new connection to a distant server pays the handshake latency before the first byte.
- **This is why connection reuse matters so much.** Reusing an existing TCP connection (keep-alive, connection pooling — the practice post) avoids paying the handshake repeatedly. Opening a fresh TCP connection per request is a classic, costly mistake.
- **And it compounds with TLS** — an HTTPS connection adds a TLS handshake *on top of* the TCP handshake (the TLS post), multiplying the setup cost, which is why connection reuse and newer protocols (HTTP/2, HTTP/3) that avoid repeated setup are so valuable.

Connection teardown has its own exchange (and leaves connections briefly in a waiting state), but the handshake's setup RTT is the cost that most shapes backend performance.

## UDP: speed by omission

**UDP (User Datagram Protocol)** is TCP's opposite: it adds almost *nothing* to IP. It provides ports (to reach a process) and a checksum (basic integrity) and that's essentially it — **no connection, no handshake, no acknowledgments, no retransmission, no ordering, no congestion control.** UDP sends independent **datagrams** and does not care whether they arrive:

- **No connection setup** — no handshake, so no setup round-trip; you just send. Lower latency to first byte.
- **No reliability or ordering** — datagrams can be lost, duplicated, or reordered, and UDP won't fix it. If the application needs reliability, it must build it itself.
- **Lower overhead** — a tiny header and no per-connection state, so it's lightweight and fast.

UDP is "fire and forget." That sounds worse than TCP, but for the right use cases the *absence* of TCP's machinery is exactly what you want.

## Choosing TCP or UDP

The choice is driven by whether you need reliability/ordering or speed/low-latency more:

- **Use TCP when you need every byte, in order** — the default for most applications: web (HTTP), APIs, databases, file transfer, anything where missing or reordered data is unacceptable. Reliability is worth the handshake and overhead.
- **Use UDP when speed and low latency matter more than perfect delivery**, and either loss is tolerable or the app handles reliability itself:
  - **Real-time media** (voice/video calls, live streaming) — a lost packet is better dropped than resent late; a slightly glitchy frame beats a stalled stream waiting for a retransmit.
  - **Gaming** — low latency is everything; stale position data is useless, so there's no point retransmitting it.
  - **DNS** — a small request/response where TCP's handshake overhead would dominate (the DNS post).
  - **Modern protocols that rebuild reliability their own way** — notably **QUIC** (the basis of HTTP/3, a later post) runs over UDP and implements its own reliability and ordering *without* TCP's constraints, getting reliability while avoiding TCP's head-of-line blocking and setup costs. This is a major modern trend: use UDP as a lightweight base and build exactly the guarantees you want on top.

The mental model: **TCP is the reliable, ordered, but heavier default; UDP is the fast, minimal, but bare option** for when you'd rather build (or skip) reliability yourself. Most backend work is TCP; know UDP for real-time, DNS, and the QUIC-based future. The next post covers a protocol that famously uses UDP — DNS, the internet's name resolution.

## Key takeaways

- Ports (16-bit numbers) address the specific process on a host, so IP+port identifies a connection endpoint; well-known ports name services (443 HTTPS, 53 DNS, 5432 Postgres), letting one host run many services and connections.
- TCP provides a reliable, ordered, connection-oriented byte stream over unreliable IP: sequence numbers + acknowledgments + retransmission (reliability), reassembly (ordering), plus flow and congestion control — hiding IP's unreliability so apps see a clean pipe.
- TCP's three-way handshake (SYN, SYN-ACK, ACK) costs a full round-trip before any data flows, so connection setup is expensive (worse at high RTT and compounded by TLS) — which is why connection reuse (keep-alive, pooling) matters enormously.
- UDP adds almost nothing to IP (ports + checksum, no handshake/acks/ordering/congestion control) — "fire and forget" datagrams that are fast and low-overhead but unreliable, leaving any needed reliability to the application.
- Use TCP when you need every byte in order (web, APIs, databases — the default); use UDP for real-time media, gaming, DNS, and modern protocols like QUIC/HTTP/3 that build custom reliability over UDP to avoid TCP's costs.

## Further reading

- [IP and routing (previous post)](/blog/posts/net-02-ip-and-routing.html)
- [MDN — TCP](https://developer.mozilla.org/en-US/docs/Glossary/TCP)
- [LLM Inference and Serving — where connection reuse and latency matter](/blog/series/llm-inference-and-serving/)
