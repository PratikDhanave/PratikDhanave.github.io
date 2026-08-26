# What an Operating System Does

*You write applications that run on top of an operating system every day, and mostly you can ignore it — until a performance mystery, a concurrency bug, or a resource limit forces you to understand what's underneath. The OS is doing two jobs for you constantly: managing the hardware's finite resources, and giving you clean abstractions over messy reality. Understanding those two jobs is understanding the machine your code actually runs on.*

Most application and backend engineers treat the operating system as an invisible layer — and mostly can, until something goes wrong at a level their framework doesn't explain. This series covers OS concepts *for engineers who build on top of it* — not to write an OS, but to understand the machine your code runs on, so you can reason about performance, concurrency, and resources. This first post covers the OS's two fundamental jobs (resource management and abstraction) and the user/kernel boundary that structures everything. It's the foundation the rest builds on.

## The two jobs of an OS

An operating system does two fundamental things, and almost everything it provides serves one of them:

- **Resource management** — the hardware has *finite* resources (CPU cores, memory, disk, network, devices) that *many* programs want to use at once. The OS *arbitrates*: it decides which program runs on the CPU when (scheduling), how memory is divided (memory management), who accesses the disk and network, and so on. The OS is the referee that shares limited hardware among competing programs fairly and safely.
- **Abstraction** — raw hardware is messy, complex, and varies by machine. The OS provides *clean, uniform abstractions* over it: instead of manipulating disk sectors, you use *files*; instead of managing physical memory addresses, you use a *virtual address space*; instead of driving a network card, you use *sockets*. The OS hides the hardware's complexity behind simple, consistent interfaces your programs use.

```text
Your programs
     │  (use clean abstractions: files, processes, sockets, virtual memory)
┌────▼─────────────────────────────────────┐
│ Operating System                          │
│  - manages resources (CPU, memory, I/O)   │  referee + abstraction layer
│  - provides abstractions over hardware    │
└────┬─────────────────────────────────────┘
     │
  Hardware (CPU, RAM, disk, network, devices)
```

These two jobs — **manage the finite hardware, and abstract its messiness** — are the lens for the whole series. Processes and threads (abstractions over "a running program") plus scheduling (managing the CPU); virtual memory (abstraction over physical RAM) plus memory management (managing it); files and I/O (abstraction over storage/devices). Every OS concept is either an abstraction it provides or a resource it manages, usually both. Hold that framing and OS concepts stop being a disconnected list.

## Kernel mode and user mode

The OS's ability to *manage* and *protect* resources rests on a hardware feature: two privilege levels, **kernel mode** and **user mode**:

- **Kernel mode** — privileged. Code running in kernel mode (the OS *kernel* — the core of the OS) can do *anything*: access all memory, control hardware directly, execute privileged instructions. The kernel runs here.
- **User mode** — restricted. Your applications run in user mode, where they *cannot* directly access hardware, other programs' memory, or privileged instructions. They're sandboxed.

This split is *why* the OS can protect and manage resources: applications *can't* directly touch hardware or each other's memory (that would break isolation and safety), so they *must* go through the OS for anything privileged. A buggy or malicious program in user mode can't crash the machine or read another program's memory, because the hardware forbids it — only the trusted kernel has that power. This is the foundation of OS protection: **untrusted applications run restricted (user mode), and only the trusted kernel runs privileged (kernel mode).** It's the same isolation principle you saw in containers (which use kernel features to isolate processes) and it's enforced by the CPU itself.

## System calls: the boundary

If applications run restricted in user mode but need to *do* privileged things (read a file, send network data, create a process), how? Through **system calls (syscalls)** — the controlled interface by which user-mode programs request services from the kernel:

- **A syscall is a request to the kernel** — when your program calls `read()`, `write()`, `open()`, sends on a socket, or allocates memory, it's (directly or via a library) making a *system call*: asking the kernel to do the privileged operation on its behalf.
- **It crosses the user/kernel boundary** — a syscall transitions the CPU from user mode to kernel mode (in a controlled way, at a defined entry point), the kernel does the requested work (with its privileges), then returns to user mode with the result. This controlled transition is the *only* way user code gets privileged operations done — you can't bypass it.

```text
User program: read(fd, buf, n)
   → syscall → CPU switches to kernel mode → kernel reads from the device → 
   → returns data + control back to user mode
```

System calls are *the* interface between your applications and the OS — everything your program does that touches the outside world (files, network, processes, memory, time) ultimately goes through syscalls. They're the boundary between the abstraction layer you use and the resource management/hardware access the kernel controls. Understanding that "my program does X" often means "my program makes a syscall to ask the kernel to do X" is key: it explains where the cost of I/O comes from (crossing the boundary), why some operations are expensive, and how tools like `strace` (which shows a program's syscalls) let you see what a program is *really* doing. The syscall boundary is where your code meets the OS.

## Why this matters for engineers

You don't write operating systems, so why learn this? Because the OS's behavior *leaks* into your applications, and understanding it makes you a better engineer at diagnosing and designing:

- **Performance** — why is my app slow? Often the answer is OS-level: too many syscalls, I/O blocking, context-switching overhead, memory pressure, cache misses. You can't diagnose these without understanding processes, scheduling, memory, and I/O (the coming posts).
- **Concurrency** — threads, race conditions, and synchronization (a coming post) are OS concepts; concurrency bugs and performance depend on how the OS schedules and how threads share memory.
- **Resources** — memory limits (OOM kills), CPU throttling, file-descriptor limits, and other resource constraints are OS-managed; understanding them explains mysterious failures (and connects to the containers/Kubernetes resource limits, which are OS cgroups).
- **Reasoning about the machine** — knowing what's actually happening beneath your framework — that a process has an address space, that the scheduler shares the CPU, that memory is virtual, that I/O crosses the syscall boundary — lets you reason about your system's real behavior rather than treating it as magic.

The goal of this series is exactly that: not to make you an OS developer, but to give you the mental model of the machine your code runs on, so the OS stops being an invisible mystery and becomes something you can reason about when it matters. The next post starts with the OS's central abstraction for "a running program": the process.

## Key takeaways

- An OS does two fundamental jobs: resource management (arbitrating finite hardware — CPU, memory, disk, network — among competing programs) and abstraction (providing clean, uniform interfaces like files, processes, sockets, and virtual memory over messy hardware) — every OS concept is one or both.
- Hardware provides two privilege levels: kernel mode (privileged — the trusted kernel can access all memory and hardware) and user mode (restricted — applications can't directly touch hardware or others' memory), which is what lets the OS protect and manage resources by forcing untrusted apps through it.
- System calls are the controlled interface by which user-mode programs request privileged services from the kernel (read/write/open, sockets, memory, processes) — a syscall crosses from user to kernel mode, the kernel does the work, and returns; it's the only way user code gets privileged operations done, and the boundary where your code meets the OS.
- Everything your program does touching the outside world ultimately goes through syscalls, which explains I/O cost (crossing the boundary), why some operations are expensive, and how tools like `strace` reveal what a program really does.
- OS knowledge matters for engineers (not to write an OS) because OS behavior leaks into apps: diagnosing performance (syscalls, I/O, context switches, memory, cache), concurrency (threads, races, scheduling), and resource limits (OOM, throttling, fd limits — the OS features behind container limits) all require understanding the machine your code runs on.

## Further reading

- [Operating Systems: Three Easy Pieces (free textbook)](https://pages.cs.wisc.edu/~remzi/OSTEP/)
- [Kubernetes: Containers from First Principles — namespaces/cgroups are OS features](/blog/posts/k8s-02-containers-from-first-principles.html)
- [Computer Networking for Backend Engineers — the OS's network abstractions](/blog/series/computer-networking-for-backend-engineers/)
