# CPU Scheduling

*Your machine runs hundreds of processes on a handful of CPU cores, and yet everything feels like it's running at once. That illusion is the CPU scheduler's doing — rapidly switching the cores between processes, dozens of times a second, deciding who runs and for how long. Understanding scheduling explains why your program isn't always running, why context switches cost, and why "add more threads" doesn't always mean faster.*

The process post showed processes cycling through Ready/Running/Blocked; the threads post showed many threads wanting to run. But there are only so many CPU cores. The **scheduler** is the OS component that decides *which* ready process/thread runs on a core, *when*, and *for how long* — creating the illusion that many programs run simultaneously on limited hardware. This post covers how scheduling works, context switching and its cost, scheduling policies, and why this matters for your programs' performance.

## The illusion of simultaneity

Your computer has, say, 8 CPU cores but runs *hundreds* of processes and threads — far more than 8 can run at literally the same instant. Yet everything appears to run concurrently. The scheduler creates this illusion through **time-sharing**: it rapidly switches each core between different ready processes, giving each a small slice of CPU time (a *time slice* or *quantum*, often milliseconds) before switching to the next. Because the switching is so fast, each program *appears* to run continuously, when really it's getting frequent small turns:

```text
1 core, 3 processes wanting to run:
  time →  [A][B][C][A][B][C][A][B][C]...   (each gets ~milliseconds, rapidly rotated)
  → to a human, A, B, and C all seem to run "at the same time"
```

This is *concurrency* (many things making progress by interleaving) versus *parallelism* (many things literally running at once — which needs multiple cores). With 8 cores you get real parallelism (8 truly simultaneous) *plus* time-sharing on each core (hundreds interleaved). The scheduler manages this: it picks which ready processes run on the available cores and rotates them. This is the resource-management job (post one) applied to the CPU — sharing a scarce resource (cores) among many competitors (processes/threads) to give everyone progress.

## Preemption and context switching

The scheduler's power comes from **preemption** — the ability to *interrupt* a running process and switch to another, even if the running process didn't voluntarily yield. Modern OSes are *preemptive*: a timer interrupt fires periodically, the scheduler regains control, and it can switch to a different process. This is essential — it means one process can't monopolize the CPU (the scheduler will preempt it after its time slice), so the machine stays responsive and fair.

Switching from one process to another is a **context switch**, and it's not free:

- **What happens** — the OS saves the current process's *context* (registers, program counter, execution state), loads the next process's saved context, and switches. For processes, this also involves switching the address space (memory mappings).
- **The cost** — a context switch takes time (saving/restoring state, and often flushing CPU caches and the TLB — the memory posts), during which no useful work happens. It's overhead.

This overhead has real consequences: **too much context switching wastes CPU on switching rather than working.** If you have far more active threads than cores, the scheduler thrashes between them, and context-switch overhead dominates — which is *why "more threads" doesn't always mean faster* (a common misconception). Beyond a point, adding threads adds context-switching cost without adding parallelism (you only have so many cores), so performance *degrades*. Understanding context-switch cost explains this and guides sizing thread/worker pools to roughly match cores for CPU-bound work. (This connects to why async I/O — a later post — can outperform many threads: it avoids the per-connection thread and its context-switch overhead.)

## Scheduling policies

*Which* ready process should the scheduler pick? That's the **scheduling policy**, and it balances competing goals — no single policy is best for everything:

- **Fairness** — every process should get a reasonable share of CPU; no process starves (waits forever).
- **Responsiveness** — interactive processes (a UI, a server handling a request) should get the CPU quickly so they feel snappy, even if that means interrupting a long-running background job.
- **Throughput** — get as much total work done as possible.
- **Priority** — some processes matter more and should get preference.

These goals conflict (maximizing throughput might starve interactive tasks; perfect fairness might hurt responsiveness), so real schedulers make trade-offs. Common ideas:

- **Round-robin** — give each ready process a time slice in turn (simple, fair).
- **Priority scheduling** — higher-priority processes run preferentially (but with care to avoid starving low-priority ones).
- **Favoring interactive/short tasks** — many schedulers boost processes that frequently block on I/O (interactive ones) so they respond quickly, while CPU-bound background tasks get longer but less frequent slices. (Linux's scheduler, for instance, aims for fairness while keeping interactive tasks responsive.)

The practical point for engineers: the scheduler is trying to balance fairness, responsiveness, and throughput across everything on the machine, using priorities and time slices — and you can *influence* it (process priority/`nice` values, CPU affinity, real-time priorities for special cases). But mostly, understanding that the scheduler exists and rotates processes explains system behavior: why your process shares the CPU, why priority matters, and why a busy machine slows everything.

## Why scheduling matters for your programs

Scheduling isn't abstract — it shapes your applications' performance:

- **Your process isn't always running** — it's scheduled in slices, and it's often *Blocked* (waiting on I/O — the process post) rather than running. "My program is slow" is frequently "it's waiting (blocked or not scheduled)," not "it's computing slowly." Understanding this directs you to the real bottleneck.
- **Thread/worker pool sizing** — because of context-switch overhead, more threads than cores doesn't help CPU-bound work (and can hurt); size pools to your workload (roughly cores for CPU-bound; more is fine for I/O-bound work that spends time blocked). This is a concrete tuning decision the scheduler dictates.
- **Latency under load** — on a busy machine, your process waits longer for the CPU (more competition), so latency rises under load partly due to scheduling contention — relevant to the tail-latency and capacity concerns from other series.
- **Priority and starvation** — a low-priority background task can be starved by higher-priority work; understanding scheduling explains such behavior and how to adjust it.

The scheduler is the OS creating the illusion of simultaneity by rapidly, preemptively rotating processes across cores — balancing fairness, responsiveness, and throughput — and its behavior (time-slicing, context-switch cost, policies) directly explains your programs' performance characteristics. The next post moves to the other great resource the OS manages and abstracts: memory.

## Key takeaways

- A machine runs far more processes/threads than it has cores, yet everything seems simultaneous because the scheduler time-shares: it rapidly rotates each core among ready processes in small time slices, creating the illusion of concurrency (interleaving) on top of real parallelism (multiple cores) — the resource-management job applied to the CPU.
- Modern OSes are preemptive: a timer lets the scheduler interrupt a running process and switch to another, so no process monopolizes the CPU and the machine stays fair and responsive.
- A context switch (saving one process's state, loading another's, switching address space, often flushing caches/TLB) is overhead — real cost with no useful work — so too much switching wastes CPU, which is why "more threads" doesn't always mean faster (beyond ~cores for CPU-bound work, context-switch overhead dominates).
- Scheduling policy balances conflicting goals — fairness (no starvation), responsiveness (interactive tasks get CPU quickly), throughput, and priority — via ideas like round-robin, priority scheduling, and favoring I/O-bound/interactive tasks; you can influence it (nice/priority, affinity).
- Scheduling shapes your programs' performance: your process isn't always running (often Blocked or waiting for CPU — "slow" is often "waiting"), thread-pool sizing should match the workload (≈cores for CPU-bound, more for I/O-bound), and latency rises under load partly from scheduling contention.

## Further reading

- [Threads and concurrency (previous post)](/blog/posts/os-03-threads-and-concurrency.html)
- [Operating Systems: Three Easy Pieces — scheduling](https://pages.cs.wisc.edu/~remzi/OSTEP/)
- [LLM Inference and Serving — why thread/worker sizing and batching matter](/blog/posts/llmserve-03-batching-and-throughput.html)
