# Batching and Throughput

*A single request leaves an expensive GPU almost entirely idle. Batching is how you fill it — and the leap from naive static batching to continuous batching is the single biggest throughput improvement in modern LLM serving, often several times more requests from the exact same hardware.*

The first post showed that decode is memory-bandwidth-bound: each step reads the whole model from memory to produce one token, so one request barely uses the GPU's compute. **Batching** is the technique that exploits this — serve many requests together so the weights loaded from memory are reused across many tokens at once. This post covers why batching works, why the naive version wastes most of its promise, and how **continuous batching** captures it.

## Why batching works

The key fact from post one: in decode, the GPU spends most of its time *loading model weights from memory*, and the arithmetic for a single token barely dents its compute capacity. Those loaded weights are the same for every request. So if you process **many requests' decode steps together**, you load the weights *once* and apply them to many tokens — turning near-idle memory-bound work into efficient, compute-utilizing work.

The payoff is dramatic and slightly counterintuitive: **batching increases throughput at almost no latency cost per request**, up to a point. Because the GPU was mostly idle serving one request, adding a second, fifth, or twentieth request to the batch costs little extra time per step — you're using capacity that was being wasted. This is why LLM serving is fundamentally a *batching* problem: the difference between serving one user and twenty on the same GPU can be nearly free until you saturate compute or run out of KV cache memory.

The limits are exactly the two resources from earlier posts:

- **KV cache memory** — every request in the batch needs its own KV cache, so the KV cache budget (GPU memory minus weights) caps how many requests fit. This is usually the binding constraint.
- **Compute saturation** — once the batch is large enough to actually saturate the GPU's arithmetic units, decode stops being memory-bound and adding more requests *does* slow each one.

## Static batching and why it wastes the GPU

The naive approach is **static batching** (or synchronous batching): collect a batch of requests, run them together through generation, wait for *all* of them to finish, then start the next batch. It's simple, and it's how batching worked in early serving systems — but it wastes most of the benefit because of a property unique to LLMs: **requests in a batch finish at wildly different times.**

Recall that each request generates a different number of tokens — one user asks for a one-line answer, another for a five-paragraph essay. In static batching, the whole batch is locked together until the *longest* request completes:

```text
Static batching (batch of 4):
  Req A: ▓▓▓ done, then IDLE ────────────────  (waits)
  Req B: ▓▓▓▓▓▓▓▓▓▓▓▓▓ done (longest) ────────
  Req C: ▓▓▓▓ done, then IDLE ─────────────────  (waits)
  Req D: ▓▓ done, then IDLE ───────────────────  (waits)
         └── finished slots sit idle until B ends ──┘
```

The short requests finish early and their GPU slots sit **idle**, doing nothing, until the longest request in the batch completes. New waiting requests can't take those freed slots because the batch is fixed until it fully drains. On realistic traffic where response lengths vary a lot, this wastes an enormous fraction of the GPU — the very resource batching was supposed to fill — and it also hurts latency, because a new request must wait for the entire current batch to finish before it can even start.

## Continuous batching: the big win

**Continuous batching** (also called *in-flight* or *iteration-level* batching) fixes this by operating at the granularity of a *single decode step* rather than a whole request. Instead of locking a batch until everyone finishes, the scheduler makes decisions **every iteration**:

- When a request in the batch **finishes**, its slot is freed *immediately*, that same iteration.
- A **waiting** request is admitted into the freed slot right away — it doesn't wait for the whole batch to drain.
- The batch composition changes continuously as requests come and go.

```text
Continuous batching:
  Req A: ▓▓▓ done → slot instantly reused by Req E ▓▓▓▓▓...
  Req B: ▓▓▓▓▓▓▓▓▓▓▓▓▓ (long, keeps running)
  Req C: ▓▓▓▓ done → slot reused by Req F ▓▓▓...
  Req D: ▓▓ done → slot reused by Req G ▓▓▓▓...
         └── no idle slots: freed capacity is refilled every step ──┘
```

The effect is that the GPU stays *full* — freed slots are refilled the instant they open, so almost no capacity is wasted on finished-but-waiting requests. This is why continuous batching delivers such a large throughput gain over static batching (the vLLM work reported several-times improvements) on the same hardware: it eliminates the idle-slot waste that static batching's all-finish-together model creates. Continuous batching is now the default in every serious serving engine, and it's inseparable from good KV cache management — freeing and admitting requests every iteration requires being able to allocate and release KV cache dynamically, which is exactly what paged KV cache enables.

## The throughput/latency trade-off

Batching is powerful but not free of trade-offs, and tuning it is central to serving:

- **Larger batches → higher throughput, but eventually higher per-request latency.** Once the batch saturates compute, each decode step takes longer, so every request's TPOT rises. You're trading individual speed for aggregate capacity.
- **Prefill vs. decode interference.** A new request's prefill (compute-heavy) can momentarily slow the decode of requests already streaming, causing a latency "hiccup" for active users. Serving engines schedule prefill and decode carefully (e.g. chunked prefill) to smooth this out.
- **Batch size limits come from KV cache first.** In practice you usually hit the KV cache memory ceiling before compute saturation, so techniques that shrink KV cache (paging, quantization, prefix sharing) directly raise the achievable batch size and throughput.

The practical guidance is to use continuous batching (non-negotiable), size the maximum batch to your memory and latency SLOs, and recognize that most "how many users per GPU" questions are really "how much KV cache fits, and how full does continuous batching keep the GPU." Batching turns the GPU's structural idleness into served users — the highest-leverage lever in the whole stack.

## Key takeaways

- In decode the GPU is memory-bound and mostly idle for a single request; batching serves many requests together so weights loaded from memory are reused across many tokens, raising throughput at little per-request latency cost until compute saturates or KV cache runs out.
- Static batching runs a fixed batch until all requests finish, but LLM responses vary greatly in length, so short requests' slots sit idle waiting for the longest — wasting most of the GPU and delaying new requests.
- Continuous (in-flight/iteration-level) batching schedules every decode step: finished requests free their slots immediately and waiting requests are admitted at once, keeping the GPU full — the single biggest throughput win in modern serving (several-fold on the same hardware).
- Continuous batching is inseparable from dynamic KV cache management (paging), because admitting/freeing requests each iteration requires allocating and releasing KV cache on the fly.
- Tuning is a throughput/latency trade-off: bigger batches raise throughput but eventually per-request latency; the batch ceiling is usually KV cache memory, so shrinking KV cache directly increases how many users a GPU serves.

## Further reading

- [Efficient Memory Management for LLM Serving with PagedAttention (vLLM paper)](https://arxiv.org/abs/2309.06180)
- [The KV cache (previous post)](/blog/posts/llmserve-02-the-kv-cache.html)
- [Hugging Face — Text Generation Inference (TGI)](https://huggingface.co/docs/text-generation-inference/)
