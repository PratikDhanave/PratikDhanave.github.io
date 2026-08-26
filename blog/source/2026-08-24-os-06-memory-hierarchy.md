# The Memory Hierarchy and Caching

*The single most counterintuitive fact in performance engineering: accessing memory is not one speed. A value in the CPU cache is hundreds of times faster to reach than one in main memory, which is thousands of times faster than disk. Your code's speed often depends less on how many operations it does than on where the data lives — and understanding the memory hierarchy is what lets you see that.*

The virtual-memory post hinted that memory access cost varies. This post makes that central: the **memory hierarchy** — the layered structure of storage from fast-tiny (CPU registers/cache) to slow-huge (disk) — and why **locality** and caching dominate real-world performance. This is one of the highest-leverage things an engineer can understand about performance, because it explains why two programs doing the same *amount* of work can differ enormously in speed. It's the "why" behind a lot of performance mysteries.

## Memory is not one thing

The mental model most people start with — "memory is memory, accessing it takes some fixed time" — is wrong and hides most of performance. Real machines have a **hierarchy** of storage, each level trading speed for size and cost:

```text
            Speed        Size         (rough relative access time)
Registers   fastest      tiny         ~1x        (in the CPU)
L1 cache    very fast    ~KBs         ~a few x
L2 cache    fast         ~hundreds KB ~10x
L3 cache    fast-ish     ~MBs         ~tens of x
Main memory faster       ~GBs         ~hundreds of x   (RAM)
SSD/disk    slow         ~TBs         ~thousands+ x
Network     slowest      vast         ~much more
```

The key facts (the *ratios* matter more than exact numbers, which vary by hardware):

- **Each level down is much bigger but much slower** — registers are tiny and instant; caches are small and fast; RAM is large and moderate; disk is huge and slow. The differences are *orders of magnitude*, not small percentages.
- **The gap between CPU and memory is enormous** — a CPU cache hit is *dramatically* faster than a main-memory access, which is *dramatically* faster than disk. Reaching data in L1 cache vs main memory can differ by ~100x; memory vs disk by ~1000x or more.

So "accessing memory" is not one speed — it's a spread of speeds spanning many orders of magnitude, depending on *which level* the data is in. This single fact — that memory access cost varies by orders of magnitude by level — is the foundation of performance engineering, because it means *where your data lives* dominates.

## Caching and locality

Because the fast levels are small and the slow levels are large, the system can't keep everything fast — so it **caches**: keep the *most-likely-to-be-used* data in the faster levels. The CPU automatically caches recently- and nearby-accessed memory in L1/L2/L3, so that if you access the same or nearby data again, it's served fast (a cache *hit*) instead of slow (a cache *miss* going to main memory). This works because real programs exhibit **locality**:

- **Temporal locality** — data accessed recently is likely to be accessed again soon (a loop variable, a hot object). So caching recently-used data pays off.
- **Spatial locality** — data *near* recently-accessed data is likely to be accessed soon (the next element of an array, the next field of a struct). So the cache fetches data in *chunks* (cache lines, ~64 bytes), pulling in neighbors — which pays off when you access memory sequentially.

Caching + locality is why the hierarchy works: programs *don't* access memory randomly; they access recent and nearby data repeatedly, so keeping that in fast caches gives most accesses fast. When your program has good locality, most accesses hit the cache (fast); when it has poor locality (random, scattered access), most accesses miss (slow, going to main memory). **This is why the *pattern* of memory access, not just the amount, determines speed.**

## Why this dominates performance

Here's the counterintuitive, high-leverage consequence: **two programs doing the same number of operations can differ enormously in speed based purely on their memory-access patterns (locality).** Because a cache miss costs ~100x a cache hit, a program that constantly misses the cache spends most of its time *waiting for memory*, not computing — even if it does the same arithmetic as a cache-friendly version. Real examples of this principle:

- **Sequential vs random access** — iterating an array in order (great spatial locality — each cache line's worth of neighbors is used) is *far* faster than accessing it randomly (each access a likely cache miss), even though the same number of elements is touched. This is why array-of-structs vs struct-of-arrays layout, and traversal order, matter for performance.
- **Data structure layout** — a contiguous array (cache-friendly, neighbors prefetched) often beats a linked list (nodes scattered in memory, each traversal a likely cache miss) for iteration, despite the same big-O — because the array has locality and the linked list doesn't. Big-O counts operations; the memory hierarchy counts *misses*, and misses can dominate.
- **Working set size** — if your hot data fits in cache, it's fast; if it spills to main memory (or, worse, the working set exceeds RAM and pages to disk — the thrashing from the virtual-memory post), performance drops off a cliff. Keeping the working set small enough to fit a fast level is a real optimization.

The lesson: **performance is often about memory, not computation.** When code is slower than its operation count suggests, the cause is frequently cache misses — poor locality, bad data layout, or a working set that overflows a cache level. This is why performance-conscious engineers think about *data layout and access patterns*, not just algorithms. It's also why the same big-O algorithm can be 10x faster with cache-friendly data structures. Understanding the hierarchy lets you *see* this hidden dimension of performance.

## What this means for engineers

You don't manage the CPU cache directly (the hardware does), but understanding the hierarchy guides real decisions:

- **Prefer sequential access and contiguous data** — arrays over linked structures for hot iteration, access memory in order, lay out data so related fields are together — to get spatial locality and cache hits.
- **Keep hot data small and local** — a working set that fits in cache is dramatically faster; reducing the size of frequently-accessed data (or restructuring so hot data is together) can hugely speed things up.
- **Recognize memory-bound vs compute-bound** — if a program is slow but not doing much computation, suspect it's *memory-bound* (waiting on cache misses / memory), which points you to locality and data layout rather than algorithmic changes. (This connects to the LLM-inference series: decode is *memory-bandwidth-bound*, not compute-bound — the same principle at the hardware level.)
- **The hierarchy extends up and down** — the same "keep likely-used data in a faster tier" principle appears everywhere: application caches (Redis, the caching-systems series), CDN caching, database buffer pools (the database-internals series), and even the KV cache and prefix caching in LLM serving. The memory hierarchy is the hardware instance of a universal pattern: *cache what you'll reuse in a faster, smaller tier.*

The memory hierarchy — orders-of-magnitude speed differences by level, made to work by caching and locality — is why *where data lives and how you access it* often matters more than how much computation you do. It's a hidden but dominant dimension of performance, and understanding it turns "why is this slow?" from a mystery into a question about cache misses and locality. The next post covers the OS's handling of the slowest common tier: I/O.

## Key takeaways

- Memory is not one speed: there's a hierarchy — registers, L1/L2/L3 cache, main memory (RAM), SSD/disk, network — each level much bigger but much slower than the one above, with differences of *orders of magnitude* (a cache hit vs main memory ~100x, memory vs disk ~1000x+).
- Because fast levels are small, the system caches likely-used data in them, which works due to locality: temporal (recently-used data reused soon) and spatial (nearby data used soon — so caches fetch neighbors in cache lines) — real programs have locality, so caching makes most accesses fast.
- The counterintuitive, high-leverage consequence: two programs doing the same number of operations can differ enormously in speed based on memory-access patterns, because a cache miss costs ~100x a hit — sequential/contiguous access (arrays) crushes random/scattered access (linked lists) despite equal big-O.
- Performance is often about memory, not computation: slow code with modest operation counts is frequently memory-bound (waiting on cache misses from poor locality, bad data layout, or a working set overflowing cache/RAM), so think about data layout and access patterns, not just algorithms.
- The "cache what you'll reuse in a faster, smaller tier" principle is universal — appearing in CPU caches, database buffer pools, application caches (Redis), CDNs, and LLM KV/prefix caching — so understanding the hardware memory hierarchy illuminates caching everywhere.

## Further reading

- [Virtual memory (previous post)](/blog/posts/os-05-virtual-memory.html)
- [Database Internals: pages and the buffer pool — caching in a database](/blog/posts/dbint-03-pages-and-the-buffer-pool.html)
- [LLM Inference and Serving — decode is memory-bandwidth-bound](/blog/posts/llmserve-01-how-inference-works.html)
