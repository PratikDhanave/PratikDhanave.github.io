# How LLM Inference Works

*Running an LLM is not one computation — it's two very different ones stitched together: a compute-heavy pass over your prompt, then a long, memory-bound slog generating one token at a time. Almost every serving optimization that follows makes sense only once you see that inference has these two phases with opposite bottlenecks.*

Training an LLM gets the headlines, but *serving* it — turning a trained model into fast, cheap, reliable responses — is where most engineering effort actually goes in production. This series is about that: the KV cache, batching, quantization, speculative decoding, serving engines, and scaling. It starts with the mechanics of a single generation, because every optimization later is a response to a bottleneck that lives in this post.

## Autoregressive generation: one token at a time

An LLM generates text **autoregressively**: it produces one **token** (a word or word-piece) at a time, and each new token is fed back in as input to produce the next. To generate "the cat sat," the model produces "the," then reads "the" to produce "cat," then reads "the cat" to produce "sat," and so on until it emits a stop token.

This sequential dependency is the defining constraint of inference: **you cannot generate token N+1 until you have token N**, because the model needs the previous token as input. No matter how much hardware you have, the tokens of a single response come out strictly one after another. This is why a long response takes longer than a short one in direct proportion to its length, and why generation can't be trivially parallelized within one request. Everything about LLM serving is shaped by this token-by-token loop.

## Two phases: prefill and decode

Here is the insight that unlocks the whole series. A generation request has **two distinct phases** with completely different performance characteristics:

- **Prefill** — the model processes your entire input prompt at once to produce the first output token. Because the whole prompt is available up front, this pass runs over all prompt tokens *in parallel*, doing a large amount of matrix math in one shot. Prefill is **compute-bound**: it saturates the GPU's arithmetic units, and its cost scales with prompt length.
- **Decode** — the model then generates the rest of the output one token at a time, each step reading all prior tokens to produce the next. Each decode step does comparatively *little* math (one token's worth) but must read the entire model's weights from memory to do it. Decode is **memory-bandwidth-bound**: the bottleneck is moving data (weights and cached state) to and from GPU memory, not the arithmetic.

```text
Prompt: "Summarize this article: ..."
   │
   ▼  PREFILL  — process all prompt tokens in parallel (compute-bound)
   │            → produces the 1st output token
   ▼  DECODE   — generate token 2, 3, 4, ... one at a time (memory-bound)
                 each step reads the whole model + prior context
```

This asymmetry matters enormously. Prefill is fast per token because it parallelizes; decode is slow per token because it doesn't. A request with a huge prompt and a short answer is dominated by prefill (compute); a request with a short prompt and a long answer is dominated by decode (memory bandwidth). Serving systems treat the two phases differently precisely because they stress different parts of the hardware.

## Why decode is the expensive part

Most serving pain comes from decode, and understanding why is the key to the rest of the series. In each decode step, the GPU must load the model's weights from memory to compute a *single* token. For a large model those weights are tens of gigabytes, and they must be read *every single step*. The actual arithmetic for one token is tiny by comparison, so the GPU spends most of its time *waiting on memory*, not computing — its expensive arithmetic units sit largely idle.

This has a profound consequence: **serving a single request wastes most of the GPU.** You're paying for a chip that can do enormous parallel math, but a lone decode step barely uses it because it's starved for memory bandwidth. That waste is the opening for the single most important throughput technique in the series — **batching** (a later post) — which serves many requests' decode steps together so the weights loaded from memory are reused across many tokens, finally putting the idle compute to work.

## The metrics that matter

Because inference has two phases, its performance is measured with two latency numbers plus a throughput number — and they trade off against each other:

- **Time to first token (TTFT)** — how long until the user sees the *first* token. Dominated by prefill (plus queueing), it's what makes a response feel responsive. Critical for interactive, streaming UX.
- **Time per output token (TPOT)** — the time between subsequent tokens during decode. It sets the *streaming speed* — how fast text appears once it starts. Dominated by decode's memory-bandwidth limit.
- **Throughput** — total tokens per second across *all* concurrent requests the server handles. This is what determines cost-efficiency: how many users one expensive GPU can serve.

The central tension of serving lives in these numbers: techniques that maximize **throughput** (like large batches) can raise **latency** for an individual request, and vice versa. There is rarely a single "fast" — you tune for the balance your application needs, a theme the final post returns to.

## Where the series goes

Every phase and metric here has a corresponding optimization ahead. Decode reads prior context every step — so the **KV cache** (next post) stores that context to avoid recomputing it, at a real memory cost. Decode wastes the GPU on one request — so **batching** serves many at once. The weights are huge and memory-bound — so **quantization** shrinks them. Decode is strictly sequential — so **speculative decoding** cheats it by guessing several tokens ahead. And **serving engines** like vLLM package all of this, while **scaling** spreads it across GPUs. Keep the two phases and three metrics in mind; they explain why each technique exists.

## Key takeaways

- LLMs generate autoregressively — one token at a time, each fed back as input — so a single response's tokens come out strictly sequentially and can't be parallelized within a request.
- Inference has two phases with opposite bottlenecks: prefill processes the whole prompt in parallel and is compute-bound (produces the first token); decode generates the rest one token at a time and is memory-bandwidth-bound.
- Decode is the expensive part because each step reads the entire (tens-of-GB) model from memory to compute just one token — so a single request leaves most of the GPU's compute idle, waiting on memory.
- That wasted compute is the opening for batching (serving many requests together to reuse loaded weights), the most important throughput technique in the series.
- Performance is three numbers in tension: time-to-first-token (prefill, responsiveness), time-per-output-token (decode, streaming speed), and total throughput (cost-efficiency) — you tune the balance, not a single "fast."

## Further reading

- [vLLM documentation](https://docs.vllm.ai/)
- [Hugging Face — Text Generation Inference (TGI)](https://huggingface.co/docs/text-generation-inference/)
- [AI Cost Optimization series](/blog/series/ai-cost-optimization/)
