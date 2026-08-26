# Processes

*A process is the OS's answer to "what is a running program?" — and it's more than the code: it's the code plus its own private memory, its own resources, and its own isolated view of the machine, as if it owned the computer. That isolation is what lets many programs run at once without corrupting each other, and understanding it explains a huge amount of how systems behave.*

The OS's central abstraction for a running program is the **process**. This post covers what a process actually is — a program in execution with its own isolated address space and resources — its lifecycle, how processes are created (fork/exec), and the isolation that keeps them from interfering. Processes are the unit the OS schedules and protects, and understanding them underpins threads, memory, and much of system behavior. It's the abstraction over "a program is running."

## What a process is

A **process** is a *program in execution* — but crucially, it's much more than the program's code. A process bundles everything needed to run that program as an independent, isolated entity:

- **The code** (the program instructions) being executed.
- **Its own address space** — a private region of memory the process sees as its own (containing its code, data, heap, and stack — the memory posts detail this). Critically, this address space is *virtual* and *isolated*: the process sees what looks like its own private memory, separate from every other process (the virtual-memory post explains how).
- **Its resources** — open files (file descriptors), network connections, and other OS resources the process holds.
- **Its execution state** — where it is in execution (the program counter, registers, stack) so the OS can pause and resume it.

```text
Process = code + private address space (code/data/heap/stack) + resources (open files, sockets) + execution state
   → an isolated, independent running instance of a program
```

The key idea: a process is an *isolated container for a running program* — it has its own memory and resources, separate from other processes, and behaves as if it owned the machine (thanks to the OS's abstractions). This isolation is fundamental: process A cannot read or corrupt process B's memory (the OS and hardware prevent it — the user/kernel protection from the last post, plus virtual memory). That's *why* you can run many programs at once safely — each is a walled-off process. (This is also the foundation containers build on: a container is a process with *extra* isolation via namespaces — the Kubernetes containers post.)

## The address space

The most important part of a process to understand is its **address space** — the memory the process sees, which is *virtual* (the next-but-one post covers virtual memory in depth, but the layout matters here). Every process has an address space laid out in regions:

```text
High addresses
┌──────────────┐
│   Stack      │  ← function calls, local variables (grows down)
│      ↓       │
│              │
│      ↑       │
│   Heap       │  ← dynamically allocated memory (malloc/new; grows up)
├──────────────┤
│   Data       │  ← global/static variables
├──────────────┤
│   Code (text)│  ← the program instructions
└──────────────┘
Low addresses
```

- **Code (text)** — the program's instructions.
- **Data** — global and static variables.
- **Heap** — dynamically allocated memory (what `malloc`/`new` give you), grows as the program allocates.
- **Stack** — function call frames and local variables, grows and shrinks as functions are called and return.

Two things matter for engineers here. First, the **stack vs heap** distinction is fundamental across languages (from the Rust series' `Box` — heap allocation — to why deep recursion causes a *stack overflow*, and why heap allocation is more expensive than stack). Second, this address space is *private per process* — each process has its own, isolated from others, which is the isolation that makes processes safe. When you understand a program's memory as this structured, private address space, a lot of behavior (memory layout, allocation cost, stack overflows, memory isolation) becomes clear.

## The process lifecycle

A process moves through **states** as the OS manages it, which is key to understanding scheduling (next post):

```text
      created → READY ⇄ RUNNING → terminated
                  ↑        │
                  └─ BLOCKED ┘  (waiting on I/O or an event)
```

- **Ready** — the process is able to run and waiting for the CPU (the scheduler will pick it).
- **Running** — the process is currently executing on a CPU core.
- **Blocked (waiting)** — the process is waiting for something (I/O to complete, a lock, an event) and *can't* use the CPU until it's unblocked. A blocked process isn't scheduled — it's waiting.
- **Terminated** — the process has finished (or been killed).

The important insight: a process is *not* running most of the time — it cycles between Ready (wants CPU), Running (has CPU), and Blocked (waiting on something, usually I/O). This is why "my program is slow" is often "my process is Blocked on I/O, not actually computing" — understanding the states explains where time goes. The OS scheduler (next post) manages the Ready↔Running transitions (which ready process runs when), and I/O drives the Blocked state (a process reading a file blocks until the read completes). This state model is the foundation for scheduling and for reasoning about concurrency and performance.

## Creating processes: fork and exec

How are processes created? On Unix-like systems, via two syscalls that are worth understanding because they reveal the model:

- **`fork()`** — creates a new process by *duplicating* the current one. The new (child) process is a copy of the parent — same code, a copy of the address space, the same open files. After `fork`, there are two nearly-identical processes (parent and child) continuing from the same point (distinguished by `fork`'s return value).
- **`exec()`** — *replaces* the current process's program with a *different* one. The process keeps its identity (and some resources) but its code/data are replaced by a new program.

The classic pattern is **fork then exec**: to run a new program, a process `fork`s (creating a child copy of itself) and the child `exec`s the new program (replacing itself with it). This is how a shell runs a command, how servers spawn workers, how one program launches another:

```text
shell process → fork() → child (copy of shell) → exec("ls") → child is now running ls
   → parent (shell) waits for the child to finish
```

Understanding fork/exec demystifies process creation (it's copy-then-replace, not create-from-nothing) and explains things like why child processes inherit the parent's open files and environment, and how process hierarchies (parent/child trees) form. It's also the mechanism underneath higher-level "run a program" APIs in every language. (Modern variants optimize the copy — e.g. copy-on-write memory so the fork is cheap until modified.)

## Processes as the unit of isolation

The takeaway: a process is the OS's abstraction for a running program — code plus a *private, isolated address space* (structured into code/data/heap/stack) plus resources plus execution state — cycling through Ready/Running/Blocked states as the OS manages it, and created by fork/exec (copy-then-replace). The defining property is *isolation*: each process is walled off from others (can't touch their memory), which is what lets many programs run safely at once and is the foundation containers extend. For engineers, processes explain memory layout (stack/heap), where time goes (Blocked on I/O vs Running), and how programs launch each other — the concrete reality behind "my program is running." The next post covers what happens when a process wants to do *multiple things at once* within its single address space: threads.

## Key takeaways

- A process is a program in execution — but much more than code: it bundles the code, its own private (virtual, isolated) address space, its resources (open files, sockets), and its execution state, into an independent running instance that behaves as if it owned the machine.
- The defining property is isolation: a process can't read or corrupt another process's memory (OS + hardware enforce it), which is what lets many programs run safely at once — and is the foundation containers extend with extra namespace isolation.
- A process's address space is laid out in regions — code (instructions), data (globals), heap (dynamic allocation, grows up), stack (call frames/locals, grows down) — explaining stack-vs-heap, stack overflows, allocation cost, and per-process memory isolation.
- A process cycles through states — Ready (wants CPU), Running (has CPU), Blocked (waiting on I/O/event, not scheduled), Terminated — so a process isn't running most of the time; "slow" is often "Blocked on I/O," which the scheduler and I/O drive.
- Processes are created via fork (duplicate the current process into a child) and exec (replace a process's program with another), classically fork-then-exec (a shell forks and the child execs the command) — demystifying process creation as copy-then-replace and explaining inheritance and process hierarchies.

## Further reading

- [What an operating system does (previous post)](/blog/posts/os-01-what-an-os-does.html)
- [Operating Systems: Three Easy Pieces — processes](https://pages.cs.wisc.edu/~remzi/OSTEP/)
- [Rust: Ownership — stack vs heap and allocation](/blog/posts/rust-04-ownership.html)
