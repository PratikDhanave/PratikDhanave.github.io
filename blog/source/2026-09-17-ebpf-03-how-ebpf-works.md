# How eBPF Works: Programs, Hooks, Maps

*An eBPF program's journey — from code you write to logic running in the kernel — has a few distinct pieces: the program itself, the hook it attaches to, the maps it uses to share data, and the load path that gets it safely into the kernel. Once you can name these four things and see how they fit together, eBPF stops being magic and becomes a system you can reason about.*

The previous posts covered why eBPF exists; this one is the mechanics. We'll walk the anatomy — programs, hooks, maps — and the path a program takes from user space into the running kernel. This is the concrete model everything else (the verifier, and the observability/networking/security applications) builds on.

## The load path: from bytecode to running in the kernel

An eBPF program doesn't run like a normal application. Here's how it gets from your source into the kernel and executes:

```
 User Space                          Linux Kernel
 ┌─────────┐  load    ┌──────────┐   if safe   ┌──────────────┐
 │ Loader  │ bytecode │ Verifier │────────────▶│ JIT Compiler │
 │libbpf/  │─────────▶│ proves   │             │ (to native)  │
 │  bcc    │          │  safety  │             └──────┬───────┘
 └────┬────┘          └──────────┘                    │ attach
      │ read results                                  ▼
 ┌────▼──────┐   ◀── results ──   ┌──────┐     ┌──────────────┐
 │ User App  │                    │ Maps │◀───▶│ eBPF Program │──▶ hooks
 └───────────┘                    └──────┘     └──────────────┘  (kprobe/XDP/LSM)
```

> **▸ [Open the interactive architecture diagram](/blog/handbook-diagrams/ebpf-architecture.html)** — pan, zoom, and trace the load path, hooks, and maps (light/dark, self-contained).

The steps: you write the program (in a restricted subset of C, typically) and compile it to **eBPF bytecode**; a **loader** (a user-space library like libbpf or bcc) submits that bytecode to the kernel; the **verifier** analyzes it and either accepts or rejects it (post 4); if accepted, the kernel **JIT-compiles** the bytecode to native machine code for speed; and the program is **attached** to a hook, where it runs whenever that hook fires. Data flows back to user space through **maps**. Four moving parts — program, hooks, maps, load-path — which we'll take in turn.

## eBPF programs

An **eBPF program** is the code you write to run in the kernel. It's not arbitrary C — it's a *restricted* subset, precisely because it must pass the verifier:
- **No unbounded loops** (the verifier must prove termination), though bounded loops are allowed.
- **Limited size and complexity** (the verifier must be able to analyze it).
- **Restricted operations** — it can only call a specific set of kernel-provided "helper functions" (not arbitrary kernel functions), and can only touch memory it's allowed to.

You usually write eBPF in C and compile it to bytecode (with Clang/LLVM), or use higher-level tools that generate it (post 8). The program is *event-driven*: it doesn't run on its own; it runs when the hook it's attached to fires. Think of an eBPF program as a small, safe, event handler that the kernel invokes — fast, bounded, and confined.

## Hooks: where programs attach

A **hook** is a point in the kernel where an eBPF program can be attached to run when a specific event occurs. The variety of hooks is what makes eBPF so broadly useful — you can attach to many kinds of kernel events:
- **kprobes / kretprobes** — attach to (almost) any kernel function's entry or return. Enormous observability power: trace what the kernel is doing internally.
- **Tracepoints** — stable, predefined instrumentation points in the kernel (more durable across versions than kprobes).
- **uprobes** — attach to user-space function calls, for tracing applications.
- **XDP (eXpress Data Path)** — attach at the earliest point a packet arrives at the network driver, for the fastest possible packet processing (post 6).
- **tc (traffic control)** — attach in the networking stack for packet manipulation.
- **LSM (Linux Security Modules)** — attach to security hooks to enforce policy (post 7).
- **socket, cgroup, and more** — many other attachment points.

The key insight: **the same eBPF program model attaches to wildly different events** — a function call, a packet arrival, a security decision — which is why one technology spans observability, networking, and security. You write a small verified program and attach it wherever you need visibility or control; the hook determines *when* it runs and *what context* it gets.

## Maps: sharing data

An eBPF program runs in the kernel, but you usually need to get data *out* (to a user-space app) or keep state *between* invocations. That's what **maps** are for: key-value data structures, living in the kernel, that both eBPF programs and user-space programs can access.

Maps solve two problems:
- **Kernel-to-user communication.** The eBPF program writes results into a map; the user-space app reads them. This is how a tracing tool gets its data from the in-kernel program to the dashboard — without copying the kernel's entire state out, just the specific results the program chose to record.
- **State across invocations.** Because an eBPF program is invoked per-event and doesn't retain local state between calls, maps hold persistent state — counters, histograms, tables (e.g. a map of per-process syscall counts that accumulates across many invocations).

Maps come in many types (hash maps, arrays, per-CPU variants for performance, ring buffers for streaming events to user space, and more). They're the shared memory that connects the kernel-side program to the user-side application, and the accumulator for stateful logic. Without maps, an eBPF program could observe but couldn't report or remember; with them, it becomes a full data-collection and stateful-processing tool.

## Putting it together

The four pieces compose into eBPF's whole model:
1. You write a **program** (restricted, verifiable) and compile it to bytecode.
2. A **loader** submits it; the **verifier** proves it safe; the kernel JITs it.
3. It **attaches to a hook** — a kernel event of your choosing.
4. When the hook fires, the program runs, using **maps** to store state and share results with user space.

That's eBPF, mechanically. A tracing tool is an eBPF program on a kprobe writing counts to a map that a user-space tool displays. A load balancer is an eBPF program on XDP rewriting packets using a backend table in a map. A security agent is an eBPF program on an LSM hook checking actions against policy in a map. Same four-part model, different hooks and logic. Understanding these parts — and the verifier that guards the load path, next — is understanding eBPF; every application in the rest of the series is a variation on this anatomy.

## Key takeaways

- An eBPF program's **load path**: write it (restricted C) → compile to **bytecode** → a **loader** (libbpf/bcc) submits it → the **verifier** proves it safe → the kernel **JIT-compiles** it to native code → it **attaches to a hook** and runs on that event, sharing data via **maps**.
- **eBPF programs** are a *restricted* subset (no unbounded loops, bounded size/complexity, only specific helper functions and allowed memory) precisely so they can pass the verifier — small, safe, **event-driven** handlers the kernel invokes when their hook fires.
- **Hooks** are the huge variety of attachment points — kprobes/kretprobes (any kernel function), tracepoints (stable), uprobes (user functions), XDP/tc (networking), LSM (security), socket/cgroup — and the *same program model* attaches to all of them, which is why one technology spans observability, networking, and security.
- **Maps** are kernel-resident key-value structures shared with user space: they carry results **kernel→user** (report just what's recorded, not the whole kernel state) and hold **state across invocations** (counters, histograms, tables) — without them a program could observe but not report or remember.
- The whole model composes into **program + hook + maps** (guarded by the verifier on the load path): a tracing tool, a load balancer, and a security agent are all the *same* four-part anatomy with different hooks and logic.

## Further reading

- [Linux kernel BPF documentation](https://docs.kernel.org/bpf/)
- [ebpf.io — What is eBPF? (architecture)](https://ebpf.io/what-is-ebpf/)
