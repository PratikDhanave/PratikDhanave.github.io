# eBPF for Networking

*Networking is where eBPF delivers its most dramatic performance wins. By running packet-processing logic in the kernel — at the earliest possible moment a packet arrives, before the kernel even builds its usual data structures — eBPF can filter, route, and load-balance at speeds user-space networking can't touch. It's why the networking layer of modern cloud-native infrastructure is increasingly eBPF underneath.*

The observability post used eBPF to *watch*; this post uses it to *act* — on network packets, in the fast path. Networking is eBPF's highest-performance domain, and understanding XDP, the kernel networking hooks, and what they enable explains why projects like Cilium built the future of container networking on eBPF. This is the return to eBPF's roots (it began as a packet filter) at a vastly larger scale.

## Why in-kernel packet processing wins

Packets arrive constantly and must be processed fast — a busy server handles millions per second. Where you process them matters enormously:
- **User-space networking** means each packet (or its data) crosses the kernel/user boundary — copied out, context-switched to, processed, and often copied back. At millions of packets per second, that boundary-crossing overhead dominates and caps throughput. It's the boundary cost from post 2, paid per packet.
- **In-kernel processing** (eBPF) handles the packet *in the kernel*, in the fast path, without crossing to user space. No copy, no context switch — just fast, native, verified code acting on the packet where it already is.

The performance difference is large: processing packets in the kernel with eBPF avoids the per-packet boundary tax entirely, enabling throughput and latency that user-space approaches struggle to match. For anything high-volume — load balancing, DDoS filtering, firewalling at scale — that difference is decisive. eBPF put fast, programmable packet processing in reach without writing a kernel module or custom driver.

## XDP: the earliest, fastest hook

The star of eBPF networking is **XDP (eXpress Data Path)** — an eBPF hook at the *earliest* point a packet enters the system, right in the network driver, *before* the kernel has done its usual packet processing or allocated its standard networking data structures.

Attaching an eBPF program at XDP means you can act on a raw packet the instant it arrives, and return a verdict:
- **Drop it** — discard the packet immediately (the basis for extremely efficient DDoS mitigation and firewalling: malicious packets are dropped at the earliest point, before they consume any further kernel resources).
- **Pass it** — let it continue up the normal network stack.
- **Redirect it** — send it out another interface or to another CPU (the basis for high-speed load balancing and routing).
- **Transmit it back** — bounce it out the same interface (useful for certain fast responses).

Because XDP runs before the expensive parts of packet handling, it's the fastest place to process packets in Linux — dropping or redirecting at XDP costs a tiny fraction of doing so higher in the stack. This is what enables line-rate DDoS filtering and software load balancers that rival dedicated hardware. There's also the **tc (traffic control)** hook, slightly later in the stack, which gives more context (the kernel has done more processing) in exchange for a bit more cost — used when XDP is too early for what you need.

## What eBPF networking enables

The combination of speed and programmability enables a lot:
- **Load balancing** — distribute connections across backends in the kernel at high speed, replacing or augmenting hardware and user-space load balancers.
- **DDoS mitigation and firewalling** — drop malicious or unwanted traffic at XDP, before it costs anything, at line rate.
- **Packet filtering and manipulation** — inspect, modify, and route packets with custom logic, programmatically.
- **Network observability** — the observability domain (post 5) applied to networking: see connections, latencies, and traffic patterns in the kernel.
- **Container and service networking** — the big one: implementing the networking, load balancing, and network policy for containerized/Kubernetes environments efficiently in the kernel.

That last point is why eBPF networking matters most in practice today. **Cilium**, the widely-adopted cloud-native networking and security project, is built on eBPF: it provides Kubernetes pod networking, service load balancing, and network policy enforcement using eBPF programs in the kernel, replacing older, slower mechanisms (like long chains of iptables rules) with fast, programmable eBPF. As Kubernetes became ubiquitous, eBPF-based networking (via Cilium and others) became the modern default, because it scales and performs where the older approaches struggled.

## Programmable networking without kernel hacking

The deeper significance mirrors the whole series' theme. Fast, custom packet processing used to require writing kernel modules or custom drivers — dangerous, expert-only work (post 2). eBPF makes it *safe and accessible*: you write a verified eBPF program, attach it at XDP or tc, and get kernel-speed, custom networking logic without the risk. This democratized high-performance networking — the same technology that powers a hyperscaler's load balancer is available to any team, expressed as safe eBPF programs rather than perilous kernel code.

The takeaway: eBPF's networking power comes from processing packets *in the kernel, in the fast path* (especially at XDP, the earliest hook), avoiding the per-packet boundary cost that caps user-space networking — enabling line-rate load balancing, DDoS filtering, and, above all, the efficient container/Kubernetes networking that Cilium built on eBPF. It's programmable, high-performance networking without the danger of kernel modules — eBPF's roots as a packet filter, grown into the foundation of cloud-native networking. Security, the third domain, is next.

## Key takeaways

- **In-kernel packet processing wins on performance** because it avoids the per-packet kernel/user boundary cost (copy + context switch) that caps user-space networking at millions of packets/second — decisive for high-volume load balancing, DDoS filtering, and firewalling.
- **XDP (eXpress Data Path)** is the star: an eBPF hook at the *earliest* point a packet enters (in the driver, before the kernel's usual processing), where a program returns a verdict — **drop** (line-rate DDoS mitigation), **pass**, **redirect** (high-speed load balancing), or transmit — at a tiny fraction of the cost higher in the stack. (**tc** is a slightly-later hook with more context for a bit more cost.)
- eBPF networking enables **load balancing, DDoS mitigation/firewalling, packet filtering/manipulation, network observability, and — the big one — container/Kubernetes networking**.
- **Cilium** made this mainstream: it implements Kubernetes pod networking, service load balancing, and network policy in eBPF, replacing slower mechanisms (long iptables chains) — which is why eBPF-based networking became the cloud-native default as Kubernetes spread.
- Like the rest of eBPF, it's **programmable high-performance networking without kernel hacking** — write a verified eBPF program instead of a dangerous kernel module/driver — democratizing hyperscaler-grade networking.

## Further reading

- [Cilium — eBPF-based networking, observability, security](https://cilium.io/)
- [ebpf.io — What is eBPF? (networking)](https://ebpf.io/what-is-ebpf/)
