# The CUDA Execution Model — Threads, Warps, and Occupancy

*To make a GPU fast you have to express your problem the way the hardware wants to run it: as thousands of near-identical threads marching in lockstep. CUDA is the programming model that exposes this, and its abstractions — threads, warps, blocks, grids — map directly onto the SMs and cores from post 1. You don't need to write kernels to be an inference engineer, but you do need this model to understand why some operations fly and others crawl.*

Posts 2 and 3 established *what* limits a GPU (memory bandwidth, arithmetic intensity). This post covers *how work is actually scheduled* onto the hardware, because the execution model explains a second class of performance problems — ones that have nothing to do with bandwidth and everything to do with keeping the thousands of units busy. Understanding warps and occupancy is understanding why a GPU can be memory-*and*-compute underutilized at the same time.

## The hierarchy of parallelism

**CUDA** (NVIDIA's platform for general-purpose GPU programming) organizes a computation as a hierarchy of parallel work that mirrors the hardware:

- **Thread** — the smallest unit; runs the *kernel* (the GPU function) on one piece of data. A matrix multiply might launch one thread per output element.
- **Warp** — a group of 32 threads that execute **in lockstep**: the same instruction at the same time, on different data. This is the true unit of execution, and it's the single most important abstraction in the model (more below).
- **Block** (thread block) — a group of warps that run together *on one SM*, can cooperate through that SM's fast shared memory (post 2), and can synchronize with each other.
- **Grid** — all the blocks for one kernel launch, distributed across all the SMs on the chip.

This hierarchy is why the model scales: you describe the work as a grid of blocks of threads, and the hardware maps blocks onto whatever SMs are available — the same code runs on a small GPU or a huge one, just with more blocks resident at once. It's the software expression of post 1's "parallelism by replication."

## SIMT: the warp runs in lockstep

The defining feature is **SIMT** — *Single Instruction, Multiple Threads*. The 32 threads of a warp don't run independently; they share one instruction pointer and execute the same instruction each cycle, on their own data. This is how the GPU gets its efficiency: one instruction-fetch drives 32 lanes of arithmetic, so the hardware spends its transistors on math rather than on per-thread control logic.

The catch — and a classic performance trap — is **branch divergence**. If threads in a warp take different paths through an `if/else`, the warp must execute *both* paths, masking off the threads that shouldn't run each one. A warp where half the threads go one way and half the other runs at half efficiency. The lesson that reaches inference engineering: GPUs love *uniform* work (every thread doing the same thing) and are punished by data-dependent branching. Well-written kernels keep warps convergent, which is one reason tensor operations — utterly uniform — are so GPU-friendly.

## Occupancy: hiding memory latency with threads

Post 2 said memory is slow, so how does a GPU *ever* stay busy if threads are constantly waiting on HBM? The answer is the execution model's cleverest trick: **latency hiding through oversubscription.** An SM holds *many more* warps than it can run in a given cycle, and whenever a warp stalls waiting for memory, the SM instantly switches to another warp that has its data ready. With enough warps in flight, the memory latency of one warp is hidden behind the computation of others, and the arithmetic units stay fed.

**Occupancy** is the ratio of active warps on an SM to the hardware maximum. Higher occupancy means more warps available to hide latency — so low occupancy is a common, subtle cause of slowness: the GPU isn't bandwidth-bound or compute-bound, it just doesn't have enough work resident to hide the stalls. Occupancy is limited by *resources per block* — registers and shared memory are finite per SM, so a kernel that uses a lot of either can fit fewer warps and leave the SM underfed. This is the fundamental tension of kernel optimization: using shared memory to cut memory traffic (good) can lower occupancy (bad), and the art is balancing the two. You don't tune this by hand as an inference engineer, but it's why "use a better kernel/library" is real advice — those kernels are the ones that got this balance right.

The takeaway: **CUDA** expresses a computation as a hierarchy mirroring the hardware — **threads** (one kernel instance per data element) grouped into **warps** of 32 that execute in lockstep, grouped into **blocks** (one SM, sharing fast shared memory), grouped into a **grid** across all SMs. The execution style is **SIMT**: one instruction drives 32 lanes, which is efficient but punishes **branch divergence** (threads taking different paths run serially). And the trick that keeps a memory-slow GPU busy is **latency hiding** — an SM oversubscribes warps and switches to a ready one whenever another stalls; **occupancy** (active warps vs. max) measures how much latency can be hidden, and it's limited by per-block registers and shared memory, making occupancy-vs-reuse the core kernel-tuning tension.

## Key takeaways

- **CUDA** organizes work as a hierarchy that maps onto the hardware: **thread** (per-data-element kernel instance) → **warp** (32 threads in lockstep) → **block** (warps on one SM, sharing shared memory, able to synchronize) → **grid** (all blocks, across all SMs) — which is what lets the same code scale from a small GPU to a huge one.
- **SIMT** (Single Instruction, Multiple Threads): the 32 threads of a warp share one instruction stream — efficient because one fetch drives 32 arithmetic lanes, but **branch divergence** (threads in a warp taking different `if/else` paths) forces both paths to run, cutting efficiency; GPUs reward *uniform* work.
- A GPU hides slow memory via **latency hiding**: each SM holds far more warps than it runs at once and switches to a ready warp whenever one stalls on memory, keeping the arithmetic units fed.
- **Occupancy** = active warps ÷ hardware max; higher occupancy hides more latency, so low occupancy is a subtle slowness cause (not enough resident work). It's capped by per-block **registers and shared memory**.
- The core kernel-tuning tension: using shared memory to cut HBM traffic can *lower* occupancy — good libraries/kernels are the ones that balance reuse against occupancy, which is why "use a better kernel" is concrete advice.

## Further reading

- [CUDA — NVIDIA's GPU programming model](https://en.wikipedia.org/wiki/CUDA)
- [Single instruction, multiple threads (SIMT) — the warp execution model](https://en.wikipedia.org/wiki/Single_instruction,_multiple_threads)
