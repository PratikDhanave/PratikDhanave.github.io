# Virtual Memory

*Every process believes it has the whole machine's memory to itself, starting at address zero, contiguous and private — and none of that is literally true. Virtual memory is the elaborate illusion the OS and hardware maintain to make it true enough, and it's simultaneously what gives processes isolation, what lets you run programs bigger than RAM, and the reason a stray pointer segfaults instead of corrupting another program.*

The process post said each process has its own *private* address space. **Virtual memory** is how that's possible — one of the most important and elegant OS mechanisms. It gives each process the illusion of its own large, private, contiguous memory, while the OS and hardware map that onto the real physical RAM (and disk) shared by everyone. This post covers what virtual memory is, address translation and paging, why it's so valuable (isolation, the illusion of abundant memory), and what it means for engineers. It underpins process isolation and a lot of system behavior.

## The illusion: private, contiguous, large

Every process operates on **virtual addresses**, not physical ones. From the process's view (the address space from the process post), it has:

- **Its own private memory** — addresses in one process are *unrelated* to the same addresses in another; each process has an independent virtual address space. Process A's address `0x1000` and process B's `0x1000` are *different* physical memory.
- **A large, contiguous space** — the process sees a large, seemingly-contiguous address range (its code, heap, stack laid out in it), regardless of how fragmented or limited the real physical memory is.

But physical RAM is a single, finite, shared resource. Virtual memory is the mechanism that reconciles these: **each process gets its own virtual address space, and the OS + hardware map virtual addresses to physical memory** (wherever it actually is). The process uses virtual addresses; the hardware translates them to physical addresses on every access, transparently. This translation is what makes the illusion — private, contiguous, large per-process memory — real on top of shared, finite, fragmented physical RAM.

## Address translation and paging

How does the mapping work? Through **paging**. Memory (both virtual and physical) is divided into fixed-size chunks called **pages** (virtual) and **frames** (physical), typically 4KB. The OS maintains, per process, a **page table** that maps the process's virtual pages to physical frames:

```text
Process's virtual address  →  [ page table ]  →  physical address
   (virtual page number)         (per-process map)    (physical frame)

Process A: virtual page 5 → physical frame 12
Process B: virtual page 5 → physical frame 88   ← same virtual page, different physical frame
   → the page table is what makes each process's memory private and mapped independently
```

- **Every memory access is translated** — when the process reads/writes a virtual address, the hardware (the MMU — memory management unit) uses the page table to translate it to a physical address, on *every* access. This is done in hardware for speed, with a cache called the **TLB** (translation lookaside buffer) holding recent translations (a TLB miss is slower — which is why context switches, which can flush the TLB, have cost, from the scheduling post).
- **Pages can be placed anywhere** — a process's contiguous *virtual* pages can map to *scattered* physical frames, so physical memory need not be contiguous — solving fragmentation and letting the OS place pages flexibly.
- **Pages can be absent** — a virtual page might not currently be in physical RAM at all (see swapping, below); accessing it triggers a *page fault*, and the OS brings it in.

Paging with per-process page tables is the machinery: it makes each process's memory independent (separate page tables → separate mappings → isolation) and flexible (virtual contiguity over scattered physical frames). Translation on every access is the constant, hardware-accelerated work that sustains the illusion.

## Why virtual memory is so valuable

Virtual memory isn't just an implementation detail — it provides several profound benefits that shape everything above it:

- **Isolation and protection** — because each process has its own page table (its own mapping), a process *cannot* access another process's memory: there's simply no mapping from its virtual addresses to another's physical frames. This is *how* process isolation (the process post) is enforced — the hardware won't translate an address the process isn't allowed to touch. It's also why a bad pointer causes a **segfault** (accessing an unmapped/forbidden address is caught by the hardware and the process is killed) *instead of* silently corrupting another program. Virtual memory is the foundation of memory safety between processes.
- **The illusion of abundant memory (swapping)** — because pages can live on disk when not in use, the total virtual memory across processes can *exceed* physical RAM. The OS keeps active pages in RAM and moves inactive ones to disk (**swapping/paging to disk**), bringing them back on demand (a page fault). So programs can use more memory than physically exists — the OS pages between RAM and disk. (The catch: if the working set exceeds RAM and the system pages heavily — **thrashing** — performance collapses, because disk is vastly slower than RAM. This is why a machine "runs out of memory and grinds to a halt.")
- **Simplicity for programs** — each program gets a clean, private, contiguous address space and doesn't have to know about physical memory layout, other processes, or fragmentation. The OS handles all of it. This is the abstraction job (post one): hide the messy shared physical reality behind a clean per-process illusion.
- **Flexibility** — the OS can do clever things via the mapping: share read-only pages between processes (e.g. the same library loaded once, mapped into many processes — and copy-on-write, which makes `fork` cheap, from the process post), memory-map files, and more.

So virtual memory gives isolation (safety), the appearance of more memory than exists (via disk), simplicity, and flexibility — a lot of value from one mechanism. It's arguably the OS's most important single abstraction.

## What it means for engineers

Virtual memory explains a range of real behaviors:

- **Segfaults** — accessing an invalid/unmapped address (a null or dangling pointer) is caught by the hardware via the page table and kills the process — that's what a segmentation fault *is*. It's virtual memory protecting the system (and why Rust's compile-time memory safety, avoiding such bugs, is valuable — the Rust series).
- **Out-of-memory and thrashing** — when a process's working set exceeds RAM, the OS pages to disk; heavy paging (thrashing) causes severe slowdowns, and eventually the OS may kill processes (the OOM killer). "The server got slow then died" under memory pressure is often thrashing then OOM — and it's why memory *limits* (containers/Kubernetes) and right-sizing matter.
- **Performance and locality** — TLB misses and page faults cost; programs with good *memory locality* (accessing nearby memory) get more TLB/cache hits and run faster (the next post, on the memory hierarchy, develops this). Virtual memory's translation cost is part of why locality matters.
- **Memory measurement is subtle** — because of virtual vs physical, shared pages, and paging, "how much memory is my process using?" has several answers (virtual size vs resident set), which explains confusing memory metrics.

Virtual memory is the elegant illusion — private, contiguous, large per-process memory over shared, finite physical RAM — maintained by per-process page tables and hardware translation, giving isolation, the appearance of abundant memory, and simplicity. It's foundational to process isolation and explains segfaults, OOM/thrashing, and memory-performance behavior. The next post drills into *why memory performance varies so much* — the memory hierarchy and caching.

## Key takeaways

- Virtual memory gives each process the illusion of its own private, contiguous, large address space, while the OS + hardware map virtual addresses to shared, finite, fragmented physical RAM — reconciling "every process thinks it owns memory" with physical reality.
- The mechanism is paging: memory is divided into fixed-size pages/frames, and a per-process page table maps virtual pages to physical frames; the hardware (MMU) translates virtual→physical on *every* access (cached in the TLB), and pages can be scattered in physical RAM or absent (on disk).
- Virtual memory provides isolation/protection (separate page tables mean a process can't access another's memory — enforcing process isolation, and why bad pointers segfault instead of corrupting others), which makes it the foundation of inter-process memory safety.
- It creates the illusion of abundant memory via swapping (inactive pages moved to disk, so total virtual memory can exceed RAM) — but heavy paging (thrashing, when the working set exceeds RAM) collapses performance because disk is far slower than RAM, explaining OOM slowdowns and why memory limits/right-sizing matter.
- For engineers it explains segfaults (hardware catching invalid accesses via the page table), OOM/thrashing behavior, why memory locality matters for performance (TLB/page-fault costs), and why memory measurement is subtle (virtual vs resident, shared pages) — foundational and constantly relevant.

## Further reading

- [CPU scheduling (previous post)](/blog/posts/os-04-cpu-scheduling.html)
- [Operating Systems: Three Easy Pieces — virtual memory](https://pages.cs.wisc.edu/~remzi/OSTEP/)
- [Rust: Ownership — compile-time memory safety avoids segfaults and use-after-free](/blog/posts/rust-04-ownership.html)
