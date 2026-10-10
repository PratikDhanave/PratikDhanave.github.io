# Memory Management for LLM Inference — The KV Cache Problem

*The single largest consumer of GPU memory during inference often isn't the model — it's the KV cache, the growing store of attention state that lets a model generate text without recomputing the past. Managing it well is the difference between serving a handful of users and serving thousands on the same hardware. This post explains what the KV cache is, why it's such a brutal memory problem, and how PagedAttention borrowed a 1960s operating-systems idea to solve it.*

Posts 2 and 5 were about the *weights* — the fixed cost of the model in HBM. This post is about the other half of inference memory: the *per-request* state that grows with every token. It's where capacity (post 2) becomes the binding constraint on how many users you can serve, and where the cleverest fix in modern serving comes from an old, familiar place: virtual memory.

## What the KV cache is and why it exists

When a transformer generates token by token, each new token attends to *all previous tokens*. Naively, generating token 1000 would require recomputing attention over tokens 1–999 from scratch — quadratic wasted work. The fix is the **KV cache**: for every token processed, store its attention *keys* and *values* in HBM, so each new token only computes its own K/V and reuses the cached ones. This turns per-token work from "reprocess the whole history" into "process one token," and it's why generation is fast enough to be practical.

The cost is memory. The KV cache stores K and V vectors for *every token, in every layer, for every attention head, for every active request.* It grows linearly with sequence length and with the number of concurrent requests, and for long contexts and many users it routinely **exceeds the size of the model weights themselves.** So inference memory has two tenants in HBM: the weights (fixed, shared across all requests) and the KV cache (per-request, growing) — and the KV cache is usually the one that runs you out of room.

## Why the KV cache wrecks naive memory management

The hard part isn't the total size — it's that each request's cache **grows unpredictably**, one token at a time, to an unknown final length. Classic serving systems handled this by pre-allocating a contiguous block of HBM per request, sized for the *maximum possible* sequence length. That's catastrophic on two counts:

- **Internal fragmentation / waste:** a request that only generates 100 tokens but was given room for 4000 wastes 97% of its reserved memory. Multiply across many requests and most of your HBM is reserved-but-empty.
- **External fragmentation:** contiguous blocks of varying sizes leave unusable gaps between them, so you can fail to fit a new request even when the free total would allow it.

The result was that GPUs ran at a fraction of their potential concurrency — not because they lacked memory, but because they *managed* it badly. The KV cache was the bottleneck on throughput, and it was a pure memory-management problem, not a compute one.

## PagedAttention: virtual memory for the KV cache

The breakthrough (from the vLLM project) was to recognize this as a problem operating systems solved decades ago. **PagedAttention** applies **paging** — the virtual-memory idea — to the KV cache:

- Split the KV cache into fixed-size **blocks** (pages) instead of one contiguous per-request allocation.
- Let a request's logical sequence map to physically **non-contiguous** blocks through a lookup table, exactly like virtual memory maps virtual pages to scattered physical frames.
- Allocate blocks **on demand** as the sequence grows, so you reserve only what's actually used — no pre-allocation for the worst case.

This near-eliminates both fragmentation problems: no waste from over-reservation (you grow block by block) and no external fragmentation (fixed-size blocks pack perfectly). The payoff is far more concurrent requests on the same GPU — often several times the throughput — because memory that used to sit reserved-but-empty is now available. It even enables **sharing**: requests with a common prefix (the same system prompt, say) can point at the *same* physical blocks, storing one copy instead of one per request.

The engineering lesson is worth more than the specific technique: a defining inference bottleneck turned out to be a *memory-management* problem, and the solution was not new math but the disciplined reuse of a classic systems idea. This is the texture of inference engineering — the wins come from treating the GPU as the memory-constrained parallel computer it is, and borrowing hard-won lessons from the rest of systems programming.

The takeaway: the **KV cache** stores each token's attention keys and values so generation processes one token at a time instead of reprocessing the whole history — essential for speed, but it grows linearly with sequence length and concurrent requests and often **exceeds the model weights** in HBM. Naive per-request *contiguous, max-length* allocation wrecks this with **internal fragmentation** (reserved-but-unused) and **external fragmentation** (unusable gaps), capping concurrency far below the hardware's potential. **PagedAttention** fixes it by applying operating-system **paging**: fixed-size KV blocks, mapped non-contiguously through a lookup table, allocated on demand — eliminating fragmentation, multiplying throughput, and even letting shared prefixes share physical blocks. The lesson: a core inference bottleneck was a memory-management problem solved by borrowing a classic systems idea.

## Key takeaways

- The **KV cache** stores attention **keys and values** for every past token so each new token reuses them instead of recomputing attention over the whole history — the reason token-by-token generation is fast.
- Its cost is **memory**: K/V for every token × layer × head × active request, growing linearly with length and concurrency — for long contexts and many users it often **exceeds the model weights** and becomes the binding HBM constraint.
- Naive **contiguous, max-length pre-allocation** per request causes **internal fragmentation** (a 100-token request reserving room for 4000 wastes ~97%) and **external fragmentation** (varying-size blocks leave unusable gaps) — so GPUs ran far below their possible concurrency for lack of *memory management*, not memory.
- **PagedAttention** (vLLM) applies virtual-memory **paging**: fixed-size KV **blocks** mapped non-contiguously via a lookup table, allocated **on demand** — eliminating both fragmentations and multiplying concurrent-request throughput.
- Paging also enables **prefix sharing** (requests with a common system prompt point at the same physical blocks); the broader lesson is that inference wins often come from **classic systems ideas**, not new math.

## Further reading

- [Paging — the virtual-memory technique PagedAttention borrows](https://en.wikipedia.org/wiki/Memory_paging)
- [Transformer (deep learning architecture) — keys, values, and attention state](https://en.wikipedia.org/wiki/Transformer_(deep_learning_architecture))
