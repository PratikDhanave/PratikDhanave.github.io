# What eBPF Is, and Why It Matters

*eBPF lets you run your own sandboxed programs inside the Linux kernel, safely, without changing kernel source or loading a risky module — and that quietly unlocks a new generation of observability, networking, and security tools. It's one of the most consequential systems technologies of the last decade, and it's worth understanding from first principles. This series builds eBPF up from the problem it solves.*

If you've used a modern observability tool that traces syscalls with near-zero overhead, a Kubernetes networking layer that routes packets in the kernel, or a runtime-security agent that watches every process — there's a good chance eBPF is underneath. It has become foundational infrastructure, yet it's often described in jargon. This opening post answers the plain question: what is eBPF, and why does it matter so much?

## The one-sentence definition

**eBPF (extended Berkeley Packet Filter) lets you run small, sandboxed programs inside the Linux kernel, loaded at runtime, without changing kernel source code or loading a kernel module.** You write a program, the kernel *verifies* it's safe, and then runs it — attached to events like a function being called, a packet arriving, or a syscall being made.

That's the whole idea, and every capability flows from it. The name is a historical accident — the original "BPF" was a mechanism for filtering network packets (`tcpdump` uses it) — but "extended BPF" grew into something far larger: a general-purpose way to safely extend what the kernel does, at runtime, for almost any kind of event. The "packet filter" name undersells it; think of eBPF as *programmable kernel*.

## Why running code in the kernel is a big deal

To see why this matters, you need to appreciate what the kernel is: the privileged core of the operating system that sees *everything* — every syscall, every packet, every process, every file access. Code running in the kernel has a vantage point and a power that user-space code simply doesn't have.

Historically, getting custom logic into that privileged position meant one of two bad options (the subject of the next post): change the kernel source (impractical — you don't control the kernel, and changes take years to ship) or write a kernel module (dangerous — a bug crashes the whole machine, and it's tied to kernel versions). Both are why kernel-level customization was the domain of a few experts and shipped slowly.

eBPF changes this fundamentally: it gives you the kernel's vantage point **safely and at runtime.** You get to run logic at the most powerful observation and control point in the system — seeing and acting on kernel events — without the risk of crashing the kernel and without rebuilding or rebooting anything. That combination — kernel-level power, user-level safety and agility — is why eBPF is transformative rather than incremental.

## What makes it safe (and why that's the key)

The natural objection to "run your program in the kernel" is: isn't that insanely dangerous? A bug in kernel code can panic the whole system. The answer, and eBPF's central innovation, is the **verifier**: before the kernel runs an eBPF program, it statically analyzes it and *proves* it's safe — that it will terminate (no infinite loops), won't access invalid memory, and won't crash the kernel. If the verifier can't prove safety, the program is rejected and never runs.

This is the trick that makes the whole thing possible (post 4 goes deep). Running arbitrary code in the kernel is dangerous; running *verified-safe* code is not. The verifier is what lets ordinary developers safely extend the kernel — it moves the safety guarantee from "trust the programmer" to "the kernel mathematically checks it before running." Without the verifier, eBPF would just be kernel modules with extra steps; *with* it, kernel programming becomes safe enough to be mainstream.

## Why it's everywhere now

eBPF's "safe programmable kernel" unlocks three domains at once, each a post in this series, and it's dominating all three:

- **Observability** (post 5) — trace and profile *anything* the kernel sees (syscalls, functions, network events) with very low overhead and *no code changes* to the applications being observed. This is a leap over traditional instrumentation, which requires modifying apps or accepting heavy overhead.
- **Networking** (post 6) — process packets in the kernel at high speed (XDP), implementing load balancing, filtering, and routing far faster than user-space networking. This is why eBPF underpins modern cloud-native networking (Cilium).
- **Security** (post 7) — monitor and enforce security policy from the kernel's all-seeing vantage: watch every syscall, detect anomalous behavior, block malicious actions in real time (Falco, and LSM-based enforcement).

The common thread is that all three benefit enormously from kernel-level visibility and speed that *used* to be inaccessible without dangerous kernel hacking. eBPF made that vantage point safe and programmable, so a wave of powerful tools became possible — which is why it went from niche to foundational in just a few years.

## What this series covers

The series builds eBPF from the ground up:
- **The kernel/user-space boundary** and the old kernel-module-vs-userspace dilemma eBPF resolves (post 2).
- **How eBPF actually works** — programs, hooks, maps, the load path (post 3).
- **The verifier and safety** — the innovation that makes it all possible (post 4).
- The three domains: **observability** (5), **networking** (6), **security** (7).
- **The ecosystem and building with it** — bcc, libbpf, CO-RE, Cilium, and where it's heading (post 8).

The mental model to carry: eBPF is a *safe, runtime-loadable, event-driven way to run your own programs inside the Linux kernel* — kernel power without kernel danger. That single capability is why it has quietly become one of the most important technologies in modern infrastructure. Everything ahead builds on it.

## Key takeaways

- **eBPF lets you run small, sandboxed programs inside the Linux kernel**, loaded at runtime, without changing kernel source or loading a kernel module — attached to events (function calls, packets, syscalls). Think "programmable kernel," not just its historical "packet filter" name.
- Kernel code has a **unique vantage point and power** (it sees every syscall, packet, process) — historically accessible only via changing kernel source (impractical) or kernel modules (dangerous, version-tied); eBPF gives that vantage **safely and at runtime**.
- The **verifier** is the central innovation: it statically *proves* a program is safe (terminates, no invalid memory access, won't crash) *before* running it, rejecting anything unprovable — turning "trust the programmer" into "the kernel checks it," which is what makes kernel programming mainstream.
- eBPF unlocks three domains at once with kernel-level visibility and speed that used to require dangerous kernel hacking: **observability** (trace anything, low overhead, no app changes), **networking** (in-kernel packet processing, XDP/Cilium), and **security** (all-seeing runtime monitoring/enforcement, Falco).
- The through-line: eBPF is **kernel power without kernel danger** — a safe, runtime, event-driven way to extend the kernel — which is why it went from niche to foundational infrastructure in a few years.

## Further reading

- [ebpf.io — What is eBPF?](https://ebpf.io/what-is-ebpf/)
- [Brendan Gregg — eBPF](https://www.brendangregg.com/ebpf.html)
