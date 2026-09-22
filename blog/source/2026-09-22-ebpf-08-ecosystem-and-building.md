# The eBPF Ecosystem and Building With It

*You rarely write raw eBPF bytecode by hand — a rich ecosystem of libraries, languages, and platforms sits on top, and one breakthrough (CO-RE) solved the portability problem that once made eBPF programs fragile across kernel versions. This closing post surveys how you actually build with eBPF, and where the technology is heading.*

The series built eBPF from the problem it solves through its three domains. This final post is practical: the tools you'd actually use, the portability innovation that made eBPF deployable at scale, and the trajectory of the ecosystem. It's the "how do I use this, and what's next" that turns understanding into application.

## The portability problem and CO-RE

Early eBPF had a serious deployment problem: programs often depended on specific kernel internals (data structure layouts that differ across kernel versions), so a program compiled for one kernel might break on another. The common workaround was **bcc**, which shipped a compiler (Clang/LLVM) *with* the tool and compiled the eBPF program *on the target machine* at runtime — portable, but heavy (a full compiler toolchain on every host, slow startup, large dependencies).

The breakthrough is **CO-RE (Compile Once – Run Everywhere)**. CO-RE lets you compile an eBPF program *once* into a portable binary that runs across many kernel versions, by:
- **BTF (BPF Type Format)** — type information about the kernel's data structures, so a program can know the layout of the kernel it's running on.
- **Relocations** — the eBPF program is compiled with placeholders for kernel-structure offsets, which are *adjusted at load time* to match the actual running kernel (using BTF), so the same compiled program adapts to different kernels.

CO-RE (with the **libbpf** library) means you compile once, ship a small portable artifact, and it runs everywhere — no on-host compiler, fast startup, small footprint. This is what made eBPF practical to *distribute* as production software (agents, tools) rather than something you compile per-machine. It resolved the last big barrier to eBPF at scale, and it's why modern eBPF tooling is libbpf + CO-RE based.

## The tooling stack

You can build with eBPF at several levels, from low-level control to high-level convenience:
- **libbpf + CO-RE (C)** — the modern low-level standard: write the eBPF program in C, compile once with CO-RE, load with libbpf. Maximum control and portability; the foundation most production eBPF is built on.
- **bcc** — the older toolkit with a large collection of ready-made observability tools and a Python/C framework. Still widely used for its tools and for scripting, though it carries the runtime-compilation weight CO-RE avoids.
- **bpftrace** — a high-level tracing language (awk-like) for quick, ad-hoc tracing without writing full programs. Ideal for interactive investigation ("count syscalls by process") and short scripts.
- **Language SDKs** — libraries to write and load eBPF programs from Go, Rust, and others (e.g. the Go and Rust eBPF ecosystems), so you can build eBPF-powered applications in your language of choice.
- **Platforms and products** — Cilium (networking/security), Falco/Tetragon (security), and many observability platforms use eBPF under the hood, so you often *consume* eBPF's power through a product without writing any eBPF yourself.

The practical guidance: for quick investigation, reach for **bpftrace**; for ready-made tools, **bcc**; for building distributable production tooling, **libbpf + CO-RE** (or a Go/Rust SDK); and for most operational needs, adopt a **platform** (Cilium, Falco) that's already built on eBPF. Most people benefit from eBPF without writing it — which is a sign of a mature ecosystem.

## Constraints to remember

Building with eBPF, keep the fundamentals from the series in mind:
- **The verifier constrains you** (post 4) — restricted language, bounded complexity, prove-it-to-the-verifier idioms. Expect to write verifiable code, not arbitrary code, and to occasionally "fight the verifier." Modern tooling and CO-RE smooth this but don't remove it.
- **Linux-centric** — eBPF is a Linux kernel technology. (Windows has an eBPF-for-Windows effort, but eBPF is fundamentally a Linux story.) Your targets need reasonably modern kernels for full capabilities (BTF/CO-RE, eBPF LSM, etc.), which is worth checking for older fleets.
- **Kernel version matters** — while CO-RE handles data-layout portability, *features* (certain hooks, helpers, LSM support) depend on kernel version, so know the minimum kernel your program needs.
- **It's powerful, so it's privileged** — loading eBPF programs requires privilege, and eBPF's power is itself a security consideration (a reason the verifier and access controls matter).

These aren't blockers — they're the shape of the technology. Knowing them keeps expectations realistic.

## Where eBPF is heading

The trajectory, described as directions rather than settled outcomes:
- **Ever more adoption as infrastructure** — eBPF is increasingly the default substrate for observability, cloud-native networking (Cilium), and runtime security (Falco/Tetragon), and that consolidation is continuing.
- **Better developer experience** — CO-RE, richer libraries, and language SDKs keep lowering the barrier; "fighting the verifier" gets less painful over time.
- **Expanding capabilities** — more hooks, more helpers, and growing use of eBPF for scheduling, storage, and other kernel subsystems beyond the original three domains.
- **Beyond Linux** — the eBPF-for-Windows effort and standardization work aim to make eBPF a cross-platform concept, though Linux remains the center of gravity.

The through-line of the whole series: eBPF is a *safe, programmable, runtime-loadable way to run your own code in the kernel*, and that single capability — kernel power without kernel danger, made portable by CO-RE and accessible by a rich toolchain — is why it became foundational to modern observability, networking, and security. You may write eBPF directly with libbpf or bpftrace, or (more often) consume it through Cilium, Falco, or an observability platform — but either way, understanding what it is and how it works (programs, hooks, maps, the verifier) lets you reason about the infrastructure that increasingly runs the systems you build on. That's the payoff: eBPF is quietly everywhere, and now it's not a black box.

## Key takeaways

- Early eBPF was **fragile across kernel versions** (programs depended on kernel-internal layouts); **bcc** worked around this by shipping a compiler and compiling on the target host at runtime — portable but heavy.
- **CO-RE (Compile Once – Run Everywhere)** solved portability: using **BTF** (kernel type info) and load-time **relocations**, a program compiled *once* adapts to different kernels — with **libbpf**, you ship a small portable artifact, no on-host compiler — which made eBPF practical to *distribute* as production software.
- The tooling stack spans levels: **libbpf + CO-RE** (production standard, max control/portability), **bcc** (ready tools + scripting), **bpftrace** (high-level ad-hoc tracing), **Go/Rust SDKs**, and **platforms** (Cilium, Falco, observability products) — most people *consume* eBPF through a platform without writing it.
- Remember the constraints: the **verifier** limits you to verifiable code (expect to "fight" it sometimes), eBPF is **Linux-centric** and **kernel-version-dependent** for features (CO-RE handles data layout, not feature availability), and loading eBPF is **privileged**.
- eBPF is heading toward **more adoption as default infrastructure**, better DX, expanding capabilities (new hooks/subsystems), and cross-platform efforts — the enduring point is *safe, programmable, runtime kernel code*, made portable (CO-RE) and accessible (rich toolchain), underpinning modern observability, networking, and security.

## Further reading

- [ebpf.io — What is eBPF? (ecosystem and CO-RE)](https://ebpf.io/what-is-ebpf/)
- [Linux kernel BPF documentation](https://docs.kernel.org/bpf/)
- [iovisor/bcc — tools and framework](https://github.com/iovisor/bcc)
