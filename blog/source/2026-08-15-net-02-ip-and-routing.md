# IP and Routing

*The internet layer performs a small miracle billions of times a second: it gets a packet from any machine to any other machine on Earth, across networks owned by thousands of independent organizations, with no central controller and no guarantee it'll arrive. Understanding IP — addresses, packets, routing, and why it's deliberately unreliable — is understanding the foundation everything else is built on.*

The last post placed **IP** at the internet layer: host-to-host delivery across networks. This post opens it up — IP addresses, how packets are routed hop by hop, the crucial fact that IP is *best-effort* (unreliable by design), and the address-translation (NAT) that shapes real networks. IP is the thin waist of the internet: everything above (TCP, HTTP) relies on it, and understanding its guarantees — and non-guarantees — explains a lot of higher-layer behavior.

## IP addresses: naming every host

An **IP address** uniquely identifies a host on a network so packets can be delivered to it. Two versions coexist:

- **IPv4** — the familiar `192.0.2.1` form, a 32-bit address. There are about 4 billion possible IPv4 addresses, which sounds like a lot but ran out years ago — the shortage is *why* NAT (below) became ubiquitous.
- **IPv6** — the newer `2001:db8::1` form, a 128-bit address, providing an effectively unlimited supply to solve IPv4 exhaustion. Adoption is ongoing; both run in parallel today.

Addresses are structured, not random: an address has a **network portion** and a **host portion**, and the split is expressed with **CIDR notation** like `192.0.2.0/24` — the `/24` means the first 24 bits are the network, leaving the rest for hosts within it. This structure is what makes routing scalable: routers make decisions based on network *prefixes* (whole ranges) rather than individual addresses, so they don't need a route for every host on Earth — just for network blocks. Some ranges are special: **private address ranges** (like `10.0.0.0/8`, `192.168.0.0/16`) are reserved for internal networks and aren't routable on the public internet, which is central to how NAT works.

## Packets: the unit of delivery

IP moves data in **packets** — discrete chunks, each with an IP header carrying the **source and destination addresses** (plus other fields) followed by the payload (a TCP segment or UDP datagram from the layer above). Key properties of packet-based delivery:

- **Data is split into packets.** A large transfer becomes many packets, each routed independently.
- **Each packet is routed on its own.** Packets to the same destination can take *different paths* through the network and arrive out of order (or not at all) — IP makes no promise they travel together.
- **The header has just enough to route.** Source/destination addresses (so routers know where to send it and the recipient knows who sent it), plus a **TTL** (time-to-live) that decrements each hop and drops the packet if it hits zero — preventing packets from circling forever in a routing loop.

Because packets are independent and can take different paths, the higher layer (TCP) is what reassembles them in order and detects losses — IP itself just hands each packet toward its destination and hopes.

## Routing: how a packet crosses the world

**Routing** is how a packet gets from source to destination across many networks, and the striking thing is that it's *decentralized* — no single system knows the whole path. It works hop by hop:

```text
Your host → home router → ISP router → ... → backbone routers → ... → destination network → server
   each router looks at the destination IP, consults its routing table,
   and forwards the packet to the NEXT hop closer to the destination
```

- **Each router makes a local decision.** A router receives a packet, looks at the destination address, consults its **routing table** (which maps network prefixes to next hops), and forwards it one step closer. No router knows the full route — each just knows "for this destination network, send it *that* way."
- **Routes are learned dynamically.** Routers exchange reachability information using routing protocols; on the global internet, **BGP (Border Gateway Protocol)** is how the thousands of independent networks (autonomous systems) tell each other which address blocks they can reach. BGP is, in a real sense, what stitches the independent networks into one internet.
- **The path can change.** Because routing is dynamic and per-hop, the path between two hosts can vary over time (and per packet), rerouting around failures — resilience, at the cost of predictability.

This decentralized, hop-by-hop, dynamically-learned design is why the internet is robust (no single point of control to fail) and why network paths are variable — a packet's journey is assembled on the fly by independent routers, not dictated centrally.

## IP is best-effort (unreliable by design)

The single most important property to internalize: **IP is best-effort — it does not guarantee delivery, order, or integrity.** A packet may be:

- **Lost** — dropped by a congested router, or discarded when its TTL hits zero.
- **Delivered out of order** — because packets take independent paths.
- **Duplicated** or corrupted in transit.

And IP does *nothing* to fix these — it just tries its best to forward each packet and moves on. This sounds like a flaw but is a deliberate design choice: keeping IP simple and stateless ("dumb network, smart endpoints") is what makes it scalable and robust. The intelligence — reliability, ordering, retransmission — is pushed to the *endpoints*, specifically to **TCP** at the transport layer (the next post). This is the foundational division of labor of the internet: **IP provides best-effort host-to-host delivery, and TCP builds reliability on top of it at the edges.** Nearly everything about TCP exists precisely because IP guarantees nothing — understanding IP's unreliability is understanding *why* TCP does what it does.

## NAT: the address-sharing workaround

One more piece shapes real networks: **NAT (Network Address Translation)**. Because IPv4 addresses ran out, most devices don't have their own public address — instead, many devices on a private network (using those private ranges) share a *single* public IP, with a NAT device (your router) translating between them:

```text
Private network (many devices, private IPs)  ──NAT──▶  one public IP  ──▶  internet
  192.168.1.5 : port  ──┐
  192.168.1.6 : port  ──┼──▶  203.0.113.10 : (mapped ports)  ──▶  the internet
  192.168.1.7 : port  ──┘     (NAT tracks which internal host each connection belongs to)
```

NAT lets many devices share one public address by rewriting addresses and ports on outgoing packets and reversing it for the replies, tracking the mapping. It's why your laptop and phone at home both reach the internet through one address, and it has real consequences backend engineers meet: inbound connections to a device behind NAT don't work without special handling (port forwarding), and the client IP a server sees is often the NAT's address, not the true origin — which matters for logging and geolocation. NAT is a pragmatic workaround for IPv4 scarcity that's now deeply woven into how the internet actually operates.

## Key takeaways

- IP addresses uniquely identify hosts (IPv4's ~4 billion 32-bit addresses, exhausted, vs IPv6's vast 128-bit space); addresses have a network + host split (CIDR like /24) so routers can route by network prefix rather than per-host, making routing scalable.
- IP moves data in independently-routed packets carrying source/destination addresses and a TTL; packets can take different paths, arrive out of order, or be dropped — the higher layer reassembles them.
- Routing is decentralized and hop-by-hop: each router consults its routing table and forwards toward the destination, routes are learned dynamically (BGP stitches the independent networks into one internet), and paths can change for resilience.
- IP is best-effort by design — no guarantee of delivery, order, or integrity — pushing reliability to the endpoints (TCP); this "dumb network, smart endpoints" split is why IP scales and why TCP exists.
- NAT lets many private-addressed devices share one public IPv4 address (translating addresses/ports), a workaround for IPv4 exhaustion with real consequences: inbound connections need port forwarding, and servers see the NAT's IP rather than the true client.

## Further reading

- [The network stack (previous post)](/blog/posts/net-01-the-network-stack.html)
- [Wikipedia — IP routing](https://en.wikipedia.org/wiki/IP_routing)
- [Distributed Systems from First Principles series](/blog/series/distributed-systems-from-first-principles/)
