# Serving Engines and PagedAttention

*You don't assemble the KV cache, continuous batching, quantization, and speculative decoding by hand — you use a serving engine that has already solved the hard parts. And the idea that ties them together, PagedAttention, is a borrowed operating-systems trick: manage the KV cache like virtual memory, in pages, and the waste that throttled everything disappears.*

The previous posts covered the individual optimizations. In practice you get them through an **inference serving engine** — vLLM, TGI, TensorRT-LLM, and others — purpose-built systems that turn a model file into a high-throughput, production-grade API. This post explains what a serving engine does, and dwells on **PagedAttention**, the memory-management idea that made modern high-throughput serving possible and that unifies the KV cache and batching stories.

## What a serving engine does

Naively, you could load a model with a basic library and call it in a loop — and get terrible throughput, because you'd be missing every optimization in this series. A **serving engine** is the layer that implements them together and exposes a clean API. Its responsibilities:

- **KV cache management** — allocating, sharing, and freeing KV cache efficiently (via PagedAttention, below) so batches stay large.
- **Continuous batching** — the iteration-level scheduler that keeps the GPU full by admitting and retiring requests every step.
- **Optimized compute kernels** — fast, fused GPU implementations of attention and other operations (e.g. FlashAttention-style kernels) that the framework ships so you don't write CUDA.
- **Quantization support** — loading and running GPTQ/AWQ/FP8 models.
- **Request scheduling** — queueing, prioritization, prefill/decode interleaving, and handling of prefix caching and speculative decoding.
- **A production API** — streaming responses (usually OpenAI-compatible), token counting, stop sequences, and observability hooks.

The point of a serving engine is that all of this is *hard* and *coupled* — continuous batching needs dynamic KV cache allocation, which needs PagedAttention, which needs custom kernels — and the engine solves it as an integrated whole so you don't have to.

## PagedAttention: the key idea

The KV cache post described the waste problem: because a request's final length is unknown, naive systems pre-allocate one contiguous block per request for the maximum length, and the resulting internal/external fragmentation wastes most of the KV cache memory — capping batch size and throughput. **PagedAttention**, introduced with vLLM, solves this by borrowing the oldest trick in operating systems: **virtual memory and paging.**

The idea: instead of one contiguous block per request, divide the KV cache into small, fixed-size **blocks** (pages), and allocate them to a request **on demand**, one block at a time as its sequence grows. A request's tokens no longer need to live in contiguous memory — a lookup table (like an OS page table) maps the request's logical token positions to wherever the physical blocks actually are.

```text
Naive (contiguous, per request):
  [■■■□□□□□□□□□□□□□]  reserved for max length; most unused → wasted

PagedAttention (paged, on demand):
  Req A tokens → [blk 7][blk 2][blk 9]      allocated as it grows
  Req B tokens → [blk 3][blk 5]             no over-reservation
  free blocks reused instantly by any request
```

The consequences map directly onto the problems earlier posts raised:

- **Near-zero waste.** Blocks are allocated only as needed, so there's almost no internal fragmentation (only the last partial block) and no external fragmentation (fixed-size blocks fit anywhere). The memory that naive management wasted now holds *more concurrent requests*.
- **Bigger batches → more throughput.** Because KV cache is the batch-size ceiling, eliminating its waste lets far more requests fit in the same GPU memory — the mechanism behind vLLM's large throughput gains.
- **Dynamic allocation enables continuous batching.** Admitting and freeing requests every iteration requires allocating and releasing KV cache on the fly — which paging makes cheap. PagedAttention and continuous batching are two halves of one design.

## Prefix sharing: paging's bonus

Paging unlocks a second win that's hard to get with contiguous allocation: **sharing KV cache blocks across requests.** Because the cache is in blocks with a mapping layer (like an OS sharing memory pages between processes), two requests with a *common prefix* — say, the same long system prompt, or the same document — can **share the physical blocks** for that shared prefix instead of each storing its own copy.

This is a large practical win for common serving patterns:

- **Shared system prompts** — every request in an application often begins with the same instructions; sharing that prefix's KV cache across all of them saves memory *and* avoids re-running prefill for it.
- **Few-shot examples / shared documents** — repeated context (examples, a document being queried many ways) is stored once and shared.
- **Parallel sampling / beam search** — generating multiple completions of the same prompt shares the prompt's cache across the branches.

This is why **prefix caching** is such an effective optimization, and it falls out naturally from managing the KV cache as shareable pages — copy-on-write semantics (from OS virtual memory) let shared blocks diverge only when a request actually writes different tokens.

## The engine landscape

You don't need to memorize products, but knowing the shape of the field helps you choose:

- **vLLM** — the widely-used open-source engine that introduced PagedAttention; strong throughput, continuous batching, broad model and quantization support, OpenAI-compatible API. A common default for self-hosting.
- **Hugging Face TGI (Text Generation Inference)** — a production-grade server integrated with the Hugging Face ecosystem, with continuous batching and quantization support.
- **NVIDIA TensorRT-LLM** — compiles models into highly optimized engines for NVIDIA GPUs, squeezing maximum performance from the hardware at the cost of a compilation/build step and NVIDIA specificity.
- **Others and managed options** — additional engines exist, and managed endpoints (from model and cloud providers) run these optimizations for you when you'd rather not operate the serving layer yourself (the managed-vs-self-host trade-off from the [AI Architecture Decisions](/blog/posts/ai-decisions-06-managed-vs-selfhost.html) series).

The choice among self-hosted engines usually comes down to ecosystem fit, hardware, and how much performance you need versus operational simplicity — but they all share the same core: PagedAttention-style KV management plus continuous batching plus optimized kernels.

## Using a serving engine well

- **Use an engine; don't hand-roll serving.** The optimizations are coupled and hard; a mature engine gives you throughput a naive loop can't approach.
- **Turn on prefix caching for shared prompts.** If your application has a common system prompt or repeated context, prefix caching is often a large, near-free win.
- **Size for KV cache, not just weights.** After the engine loads weights, the remaining memory (managed as paged blocks) determines your concurrency — plan GPU memory accordingly.
- **Match the engine to your stack.** vLLM/TGI for flexible open-source self-hosting, TensorRT-LLM for maximum NVIDIA performance, managed endpoints when you'd rather not operate any of it.

Serving engines are where all the theory becomes a running system. What remains is operating that system at scale — spreading it across GPUs — and tuning it against latency, throughput, and cost targets, the final two posts.

## Key takeaways

- A serving engine (vLLM, TGI, TensorRT-LLM) integrates the coupled optimizations — KV cache management, continuous batching, optimized kernels, quantization, scheduling — behind a production API, so you don't assemble them by hand.
- PagedAttention manages the KV cache like OS virtual memory: fixed-size blocks allocated on demand with a mapping table, eliminating the fragmentation that made naive contiguous allocation waste most of the KV cache memory.
- Near-zero KV cache waste means far more concurrent requests fit in the same GPU memory (bigger batches → higher throughput), and on-demand allocation is what makes continuous batching possible — the two are one design.
- Paging also enables prefix sharing (copy-on-write blocks): requests with a common system prompt, few-shot examples, or shared document share KV cache, saving memory and skipping repeated prefill — the basis of prefix caching.
- Choose an engine by ecosystem/hardware/performance-vs-simplicity (vLLM/TGI self-hosted, TensorRT-LLM for max NVIDIA perf, managed endpoints to avoid operating it), enable prefix caching, and size GPU memory for KV cache concurrency.

## Further reading

- [Efficient Memory Management for LLM Serving with PagedAttention (vLLM paper)](https://arxiv.org/abs/2309.06180)
- [vLLM documentation](https://docs.vllm.ai/)
- [Speculative decoding (previous post)](/blog/posts/llmserve-05-speculative-decoding.html)
