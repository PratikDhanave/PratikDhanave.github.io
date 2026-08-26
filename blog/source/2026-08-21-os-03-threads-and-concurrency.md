# Threads and Concurrency

*A thread lets one process do several things at once — and the moment you have two threads touching the same memory, you've entered the hardest territory in all of programming: concurrency. Race conditions, deadlocks, and the need for synchronization are not exotic edge cases; they're the fundamental consequences of shared mutable state, and understanding them is what separates working concurrent code from code that fails mysteriously.*

A process (last post) has one line of execution by default. **Threads** let a single process do multiple things concurrently, *sharing* its memory. That sharing is powerful and dangerous — it's the source of concurrency's hardest problems. This post covers threads vs processes, why concurrency is hard (race conditions), synchronization primitives, and deadlock. It's foundational for understanding concurrent programs, and it connects to the Rust series (fearless concurrency), distributed systems (data races), and everyday backend performance.

## Threads vs processes

A **thread** is a unit of execution *within* a process. A process starts with one thread but can have many, and the key distinction from processes is what's *shared*:

- **Processes are isolated** — each has its own private address space; they don't share memory (last post).
- **Threads within a process share** the process's address space — the same code, heap, globals, and open files. Each thread has its *own* stack and registers (its own execution state), but they *share the process's memory*.

```text
Process
├── shared: code, heap, globals, open files   ← all threads see the same memory
├── Thread 1: own stack + registers
├── Thread 2: own stack + registers
└── Thread 3: own stack + registers
```

This sharing is the whole point *and* the whole problem:

- **The benefit**: threads are lightweight (creating one is cheaper than a process) and can *cooperate* by sharing memory directly (no inter-process communication needed) — great for parallelism (using multiple CPU cores) and concurrency (doing multiple things, like handling many requests).
- **The danger**: because threads share mutable memory, they can *interfere* — two threads modifying the same data at the same time corrupt it. This is the source of the hardest bugs in programming.

So threads trade processes' safe isolation for shared-memory efficiency and cooperation — and that trade is where concurrency's difficulty comes from. (Processes vs threads is a real design choice: processes for isolation/safety, threads for shared-memory efficiency; and there are lighter models still, like async/coroutines, and Rust's ownership-checked threads.)

## Why concurrency is hard: race conditions

The fundamental problem of concurrency is the **race condition** — when the correctness of the result depends on the *timing* of how threads interleave, and some interleavings produce wrong results. The classic example: two threads incrementing a shared counter:

```text
counter = 0; two threads each do: counter = counter + 1   (expect final counter = 2)

But "counter = counter + 1" is really THREE steps: read counter, add 1, write counter.
If the threads interleave:
   Thread A reads counter (0)
   Thread B reads counter (0)      ← both read 0 before either writes!
   Thread A writes 1
   Thread B writes 1               ← final counter = 1, not 2. One increment LOST.
```

The bug: `counter = counter + 1` is not *atomic* — it's read-modify-write, and if two threads interleave between the read and the write, one update is lost. The result depends on *timing* (which is nondeterministic), so the bug is *intermittent* — it might work a million times and fail once, under load, unreproducibly. This is what makes concurrency bugs so hard: they're timing-dependent, nondeterministic, and rarely reproduce on demand.

The general problem is **shared mutable state accessed concurrently**. Any time multiple threads read and write the same data without coordination, and at least one writes, you have a potential race. This is *exactly* the data-race problem from the distributed-systems and Rust series — and it's why Rust's ownership rules (one writer XOR many readers) exist: to prevent it at compile time. The **critical section** is the piece of code that accesses shared data and must not be run by two threads simultaneously; protecting critical sections is what synchronization is for.

## Synchronization primitives

To make concurrent access to shared data safe, you use **synchronization primitives** that coordinate threads. The main ones:

- **Mutex (mutual exclusion / lock)** — ensures only *one* thread at a time can hold the lock and enter a critical section. A thread *locks* the mutex before accessing shared data and *unlocks* after; other threads *wait* for the lock. This serializes access, preventing races: the counter increment, done while holding a mutex, can't interleave. The mutex is the fundamental tool — "only one thread in here at a time."
- **Atomic operations** — hardware-supported operations (like atomic increment) that happen *indivisibly*, so no interleaving is possible. For simple operations (a counter), an atomic is faster than a mutex (no locking). They're limited to specific operations but very efficient.
- **Semaphores** — a generalization allowing *up to N* threads (rather than one), for limiting concurrency to a resource.
- **Condition variables** — let threads *wait* for a condition and be *signaled* when it's met, for coordinating "wait until X happens" between threads.

The core idea: synchronization *coordinates* threads' access to shared state so races can't happen — most fundamentally by *mutual exclusion* (a mutex ensuring one-at-a-time access to a critical section). But synchronization has costs: it *serializes* (threads waiting on a lock aren't running in parallel — reducing the concurrency benefit), and it introduces new failure modes (deadlock, below). Concurrency is a balance: enough synchronization for correctness, not so much that you lose the parallelism you wanted.

## Deadlock and the cost of synchronization

Synchronization prevents races but creates its own hazard: **deadlock** — when threads are stuck forever, each waiting for a resource another holds. The classic case: two threads, two locks, acquired in opposite orders:

```text
Thread A: locks X, then wants Y
Thread B: locks Y, then wants X
   → A holds X waiting for Y; B holds Y waiting for X → both wait forever. DEADLOCK.
```

Deadlock is a real, common concurrency bug, and avoiding it requires discipline (e.g. always acquire locks in a consistent order, minimize lock scope, avoid holding multiple locks). More broadly, synchronization has costs that shape concurrent design:

- **Contention** — when many threads compete for the same lock, they spend time *waiting*, not working; a heavily-contended lock becomes a bottleneck that serializes your program (killing the parallelism benefit).
- **Overhead** — locking/unlocking has cost; over-synchronizing slows things down.
- **Complexity and bugs** — deadlocks, missed locks (races), and subtle ordering issues make concurrent code hard to get right — the reason concurrency is considered one of the hardest areas of programming.

This is *why* modern languages and systems offer safer concurrency models: Rust's ownership-based *fearless concurrency* (compile-time race prevention — the Rust series), message-passing (share by communicating, not by sharing memory — Go's model, and the actor model), and lock-free/immutable-data approaches. All are responses to "shared mutable state with locks is hard and error-prone." Understanding the fundamentals here — races, mutexes, deadlock, contention — is what lets you use those higher-level models well and diagnose concurrency problems when they arise.

## Threads and concurrency, understood

The takeaway: threads let one process do multiple things concurrently by *sharing* its memory — powerful (lightweight, cooperative, parallel) but dangerous, because shared mutable state accessed concurrently causes *race conditions* (timing-dependent, intermittent, nondeterministic bugs — the hardest kind). Synchronization primitives (mutexes for mutual exclusion, atomics, semaphores, condition variables) coordinate access to prevent races, but at the cost of serialization, contention, and new hazards like deadlock. This fundamental difficulty is why safer models exist (Rust's fearless concurrency, message passing, lock-free structures) — and understanding the fundamentals is what makes those models and your concurrent code comprehensible. Concurrency is genuinely hard, and this is *why*. The next post covers how the OS decides which thread/process runs when: scheduling.

## Key takeaways

- A thread is a unit of execution within a process; threads share the process's memory (code, heap, globals, files) while each has its own stack/registers — versus processes, which are isolated with private memory. Sharing makes threads lightweight and cooperative but is the source of concurrency's hardest problems.
- Race conditions are the fundamental concurrency problem: when correctness depends on thread timing, some interleavings produce wrong results (e.g. `counter = counter + 1` is read-modify-write; interleaving loses updates) — timing-dependent, intermittent, nondeterministic bugs that rarely reproduce, arising from shared mutable state accessed concurrently.
- Synchronization primitives coordinate access to shared state: mutexes (mutual exclusion — one thread at a time in a critical section, the fundamental tool), atomics (indivisible operations, fast for simple cases), semaphores (up to N), and condition variables (wait/signal) — most fundamentally preventing races via mutual exclusion.
- Synchronization has costs and hazards: deadlock (threads stuck waiting on each other's locks — e.g. locks acquired in opposite orders), contention (threads waiting on a hot lock, serializing the program), and overhead/complexity — making concurrency one of the hardest areas of programming.
- These difficulties are why safer models exist — Rust's ownership-based fearless concurrency (compile-time race prevention), message passing (share by communicating), and lock-free/immutable approaches — and understanding races, mutexes, deadlock, and contention is what lets you use them well and diagnose concurrency problems.

## Further reading

- [Processes (previous post)](/blog/posts/os-02-processes.html)
- [Rust: Borrowing and references — how ownership prevents data races at compile time](/blog/posts/rust-05-borrowing-and-references.html)
- [Distributed Systems — data races and the difficulty of concurrency](/blog/series/distributed-systems-from-first-principles/)
