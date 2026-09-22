# eBPF for Observability

*Observability is where eBPF first went mainstream, and for good reason: it lets you see almost anything the kernel sees — syscalls, function calls, network events, disk I/O — with very low overhead and, crucially, without changing the code you're observing. That combination broke a long-standing trade-off in tracing and profiling, and it's why modern observability tools are increasingly built on eBPF.*

The mechanics posts explained how eBPF attaches to hooks and collects data in maps. This post applies that to the first of eBPF's three domains: observability. The pitch is simple and powerful — deep, low-overhead visibility into a running system with zero application changes — and it's transformed how we trace, profile, and understand production systems.

## The old observability trade-off

Before eBPF, getting deep visibility into a system meant choosing between bad options (echoing the boundary dilemma from post 2):
- **Instrument the application** — add tracing/logging code to the software you want to observe. Effective but invasive: you must modify and redeploy the code, it adds overhead, and you can only see what you thought to instrument in advance. You can't instrument code you don't control (the kernel, third-party binaries).
- **Use heavyweight external tracing** — tools that could observe without app changes often imposed significant overhead or required stopping/attaching in disruptive ways, making them unsuitable for always-on production use.
- **Settle for coarse metrics** — accept only the high-level, pre-exposed metrics and lose the deep detail.

The trade-off was **depth vs. overhead vs. invasiveness**: you could have deep visibility, low overhead, or no code changes — but not all three. This shaped observability for years: production tracing was either shallow, expensive, or required baking instrumentation into everything ahead of time.

## What eBPF changes

eBPF breaks the trade-off by giving all three at once:
- **Deep visibility** — attach to kprobes, tracepoints, and uprobes (post 3) to observe almost anything: every syscall, kernel function, network packet, disk operation, or (via uprobes) application function. You see the system at a level of detail that was previously inaccessible without invasive instrumentation.
- **Low overhead** — the eBPF program runs in the kernel, JIT-compiled to native code, aggregating data *in place* (in maps) and sending only the summarized results to user space. There's no heavyweight copying of every event out, so overhead is low enough for always-on production use. You can, for example, build a histogram of syscall latencies *in the kernel* and read the finished histogram, rather than shipping every event out to compute it.
- **No application changes** — because eBPF observes from the *kernel's* vantage, you don't touch the observed application at all. You attach to a running system and see it, without redeploying anything. This works even for code you don't control — the kernel itself, closed-source binaries, anything on the box.

Depth + low overhead + zero app changes, together, is the combination that was impossible before. That's why eBPF became the foundation for a new generation of observability tools.

## What you can observe

The breadth is striking. With eBPF you can trace and profile:
- **System calls** — every syscall a process makes: what files it opens, what network connections it makes, what it executes. A complete picture of a process's interaction with the OS.
- **Kernel functions** (kprobes) — what the kernel is doing internally: scheduling, memory management, filesystem operations, network stack behavior.
- **Application functions** (uprobes) — specific functions inside user-space programs, without recompiling them.
- **Network events** — connections, packets, latencies, at the kernel level (bridging into the networking domain, post 6).
- **Performance profiling** — sampling stack traces to build CPU flame graphs, measuring where time actually goes, with low enough overhead to run in production.
- **Latency and I/O** — measuring the latency distribution of operations (disk, network, locks) by timestamping entry and exit in the kernel.

The through-line: **if the kernel sees it, eBPF can observe it** — and the kernel sees almost everything. This is why eBPF-based tools can answer questions traditional tools couldn't: "which process is making these mysterious network calls?", "why is this syscall slow?", "where is CPU actually going?", answered on a live production system without instrumenting anything.

## The tooling landscape

You rarely write raw eBPF for observability; a rich toolset sits on top (previewed here, detailed in post 8):
- **bcc (BPF Compiler Collection)** — a toolkit and library with dozens of ready-made observability tools (trace file opens, TCP connections, latency, etc.) and a framework for writing your own.
- **bpftrace** — a high-level tracing language (awk-like) for writing ad-hoc eBPF tracing one-liners and short scripts, ideal for interactive investigation ("count syscalls by process," "histogram of read latencies").
- **Higher-level platforms** — observability products and agents (including OpenTelemetry-adjacent tooling) increasingly use eBPF under the hood to auto-instrument services without code changes — automatic, low-overhead visibility into applications and networks.

Brendan Gregg's work popularized much of this, and the practical upshot for an engineer is that eBPF observability is accessible: use bpftrace for quick investigations, bcc tools for common tasks, and eBPF-powered platforms for always-on production observability — all without instrumenting the systems you're watching.

The takeaway: eBPF broke the old depth-vs-overhead-vs-invasiveness trade-off in observability, delivering deep, low-overhead, zero-code-change visibility into anything the kernel sees. It's why observability was eBPF's breakout domain and why so much modern tracing, profiling, and monitoring is built on it — you can finally see a live system deeply without changing it. Networking and security (next posts) apply the same eBPF foundation to *acting*, not just observing.

## Key takeaways

- Observability was eBPF's breakout domain because it broke the old trade-off of **depth vs. overhead vs. invasiveness** — before, you could have deep visibility, low overhead, or no code changes, but not all three.
- eBPF delivers **all three at once**: deep visibility (attach to kprobes/tracepoints/uprobes to see almost anything), low overhead (aggregate *in the kernel* via maps, ship only summaries — not every event), and **zero application changes** (observe from the kernel's vantage, even code you don't control).
- **If the kernel sees it, eBPF can observe it**: syscalls (a process's full OS interaction), kernel internals, application functions (uprobes, no recompile), network events, CPU profiling (flame graphs), and latency/I/O distributions — on a live production system.
- This answers questions traditional tools couldn't ("which process makes these calls?", "why is this syscall slow?", "where does CPU go?") **without instrumenting anything**.
- Rich tooling makes it accessible: **bcc** (dozens of ready tools + a library), **bpftrace** (high-level tracing language for ad-hoc one-liners), and eBPF-powered observability platforms that auto-instrument services — use them rather than writing raw eBPF.

## Further reading

- [Brendan Gregg — eBPF observability](https://www.brendangregg.com/ebpf.html)
- [iovisor/bcc — BPF Compiler Collection](https://github.com/iovisor/bcc)
