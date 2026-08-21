# The KV Cache

*The KV cache is the optimization that makes LLM generation fast enough to be practical — and the memory hog that makes it expensive. Almost every hard problem in LLM serving, from how many users you can batch to why long contexts cost so much, traces back to this one data structure.*

The last post established that decode generates tokens one at a time, each step needing all prior tokens as context. The obvious implementation — re-process the entire sequence from scratch at every step — would be catastrophically slow. The **KV cache** is what avoids it, and it's the single most important data structure in LLM inference. Understanding what it stores, why it's necessary, and what it costs is the foundation for batching, PagedAttention, and long-context economics.

## The problem: recomputing the past

Inside a transformer, generating each token involves an **attention** step where the new token "looks back" at every previous token. Attention works with three vectors per token — a **query**, a **key**, and a **value**. To generate the next token, the model computes a query for the current position and compares it against the **keys** of all prior tokens, then combines their **values** accordingly.

Here's the crucial observation: the keys and values for tokens already in the sequence **don't change** as generation continues. Token 5's key and value are the same whether you're generating token 6 or token 600. So recomputing them at every decode step — which naive generation would do — is pure waste, and it gets quadratically worse as the sequence grows: step N would reprocess all N-1 prior tokens, making a long generation astronomically expensive.

## The solution: cache the keys and values

The **KV cache** stores the key and value vectors for every token already processed, so each decode step only computes the K and V for the *one new* token and reuses the cached K/V for all the rest:

```text
Without KV cache: each new token recomputes K,V for ALL prior tokens  → O(n²) work
With KV cache:    each new token computes K,V for itself, reuses cache → O(n) work

Decode step for token t:
   compute Q,K,V for token t
   append K_t, V_t to the cache
   attention(Q_t, all cached K) → combine cached V → next token
```

This turns generation from quadratic to linear in sequence length — the difference between practical and impossible. The KV cache is *why* LLM chat is fast enough to use. It's not an optional optimization; every production inference system relies on it.

## The catch: the KV cache eats memory

The KV cache trades computation for memory, and the memory cost is large and, importantly, **grows with every token generated**. The cache must hold a key and value vector for *every token, in every layer, for every attention head, for every request in flight*. That product is big:

- It scales with **sequence length** — every token added to the context adds to the cache. A long conversation or document steadily grows its cache.
- It scales with **model size** — more layers and heads mean more K/V per token.
- It scales with **batch size** — every concurrent request has its *own* KV cache.

The consequences dominate serving economics:

- **The KV cache, not the model weights, often limits how many requests you can serve at once.** Weights are loaded once and shared; the KV cache is *per request* and grows per token. GPU memory left after loading the weights is spent on KV cache, and that remaining budget caps your batch size — hence your throughput.
- **Long contexts are expensive in memory, not just compute.** Doubling the context roughly doubles the KV cache per request, which can halve how many requests fit. This is a big part of why long-context requests cost more.
- **Memory management of the KV cache is the central engineering problem** of a serving engine — which is exactly what PagedAttention (a later post) was invented to solve.

## Wasted memory: fragmentation

Beyond sheer size, *how* the KV cache is stored matters enormously, and the naive approach wastes a shocking amount. Because a request's final length is unknown when it starts (you don't know how long the answer will be), simple systems **pre-allocate a contiguous block** of memory for the maximum possible sequence length per request. This causes severe waste:

- **Internal fragmentation** — a request that could generate 2,000 tokens but stops at 50 still holds the whole reserved block; the unused remainder is wasted.
- **Reserved-but-unused** — space reserved for tokens not yet generated sits idle.
- **External fragmentation** — variable-sized blocks leave unusable gaps between them.

Studies behind modern serving engines found that naive KV cache management could waste the majority of the memory allocated to it — memory that could otherwise have held *more concurrent requests*. Since KV cache capacity caps batch size and batch size caps throughput, this waste directly throttles how many users a GPU can serve. That realization motivated the paged approach: manage the KV cache in small fixed-size blocks (like OS virtual-memory pages) allocated on demand, nearly eliminating the waste — the subject of the PagedAttention post.

## What this means in practice

The KV cache reframes several practical realities of running LLMs:

- **Your GPU memory budget is: weights + KV cache + overhead.** After the (fixed) weights, the remaining memory divided by per-request KV cache size determines your maximum batch — and thus your cost per token.
- **Context length is a memory decision.** Supporting very long contexts means reserving far more KV cache per request, reducing concurrency. There's a real trade-off between context length and throughput.
- **KV-cache-aware techniques compound.** Sharing cache across requests with a common prefix (e.g. a shared system prompt), quantizing the cache itself, and paging it are all ways to fit more requests in the same memory — each multiplying throughput.
- **Prefix caching is a big win.** Because the KV cache for a given prefix is identical across requests, caching and reusing it for a shared system prompt or a repeated document avoids re-running prefill — saving both compute and memory.

The KV cache is the hinge of LLM serving: it makes generation fast, and its memory appetite is what the rest of the series works to tame. Next: how batching turns the GPU's decode-time idleness into throughput.

## Key takeaways

- Transformer attention needs the key and value vectors of all prior tokens each step, but those don't change — so recomputing them (naive generation) is O(n²) waste that grows quadratically with length.
- The KV cache stores each K/V once and reuses them, making generation linear instead of quadratic — it's not optional; it's why LLM generation is fast enough to be usable.
- The cost is memory: the KV cache holds K/V for every token × layer × head × request, growing with sequence length, model size, and batch size — so it, not the weights, usually caps how many requests you can serve at once.
- Naive contiguous pre-allocation (for the max possible length) wastes most of the KV cache memory to internal/external fragmentation, throttling batch size and throughput — the problem PagedAttention solves with on-demand paged blocks.
- Practically: your batch (and cost) is set by (GPU memory − weights) ÷ per-request KV cache; long context trades off against concurrency; and prefix/cache sharing plus paging multiply how many requests fit.

## Further reading

- [Efficient Memory Management for LLM Serving with PagedAttention (vLLM paper)](https://arxiv.org/abs/2309.06180)
- [How LLM inference works (previous post)](/blog/posts/llmserve-01-how-inference-works.html)
- [vLLM documentation](https://docs.vllm.ai/)
