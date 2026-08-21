# Latency, Throughput, and Cost

*There is no single "make it fast" for LLM serving — latency and throughput pull against each other, and both trade against cost. The job isn't to maximize one number; it's to hit your latency targets at the lowest cost per token, which means knowing exactly which knob moves which metric and in which direction.*

This final post ties the series together around the numbers that decide whether a deployment is good: the latency your users feel, the throughput that determines your cost, and the cost per token that determines whether the whole thing is viable. Every optimization in the series — KV cache, batching, quantization, speculative decoding, serving engines, scaling — is a lever on these three, and they're in tension. Serving well is managing that tension deliberately.

## The metrics, precisely

From the first post, but now the full production set:

- **Time to first token (TTFT)** — latency from request to the first output token. Set by prefill (prompt length) plus *queueing delay*. This is responsiveness — how long the user stares at nothing.
- **Time per output token (TPOT)** / inter-token latency — the gap between subsequent tokens during decode. Sets *streaming speed* — how fast text appears once it starts.
- **End-to-end latency** — total time for the full response ≈ TTFT + (TPOT × number of output tokens). Long outputs are dominated by TPOT.
- **Throughput** — total tokens/second across all concurrent requests. This is the cost driver: more throughput per GPU means lower cost per token.
- **Cost per token (or per request)** — the business metric: GPU cost ÷ tokens served. Everything ultimately serves this.

Crucially, measure latency at **percentiles, not averages**. P50 (median) hides the tail; P95/P99 is what your worst-served users experience, and tail latency is where batching and queueing effects show up. An average that looks fine can mask a P99 that's driving users away.

## The central tension: latency vs. throughput

The defining trade-off of LLM serving, which every earlier post touched: **the things that maximize throughput often raise per-request latency, and vice versa.**

- **Bigger batches → higher throughput, higher latency.** Continuous batching packs more requests onto the GPU (great for cost per token), but a fuller batch means each decode step takes longer, raising TPOT, and a request may wait longer to be admitted, raising TTFT. Throughput up, individual speed down.
- **Smaller batches → lower latency, lower throughput.** Serving fewer requests at once keeps each one fast but wastes GPU capacity, raising cost per token.

```text
        latency ▲
                │        · bigger batch (cheap, slower per request)
                │      ·
                │   ·
                │·  smaller batch (fast per request, expensive)
                └────────────────────────▶ throughput / cost-efficiency
```

There is no universally correct point on this curve — it depends on your application. An interactive chat product prioritizes low TTFT and smooth TPOT (lean toward latency); a batch document-processing job prioritizes tokens/second (lean toward throughput). The first design decision is *which end of this curve you're optimizing for*, because it dictates every other setting.

## Which knob moves which metric

The value of the whole series is knowing, when a metric is wrong, which lever to pull:

- **TTFT too high?** It's prefill + queueing. Reduce queueing (more replicas, better scheduling, chunked prefill so big prompts don't block others), enable **prefix caching** to skip prefill for shared prompts, and shorten prompts. Speculative decoding doesn't help TTFT (it's a decode optimization).
- **TPOT too high (slow streaming)?** It's decode's memory-bandwidth limit. **Quantize** the model (less data to move per token), reduce batch size if it's oversaturated, use **speculative decoding** (especially at low batch), and ensure optimized kernels.
- **Throughput too low / cost too high?** Fill the GPU: **continuous batching** (non-negotiable), shrink KV cache (paging, KV quantization, prefix sharing) to raise the batch ceiling, quantize weights to free memory for more KV cache, and right-size the model to the task.
- **Can't fit the model / scaling?** Quantize to fit on fewer GPUs, then replicate; use model parallelism only as needed (previous post).

Notice how the levers interlock: quantization helps TPOT *and* throughput (by freeing KV cache memory); prefix caching helps TTFT *and* throughput. The optimizations compound, which is why a well-tuned stack is several times better than a naive one on every axis at once.

## Cost: the metric that pays the bills

Cost per token is downstream of throughput, and the ways to lower it recap the series through an economic lens (and connect to the [AI Cost Optimization](/blog/series/ai-cost-optimization/) series):

- **Maximize throughput per GPU.** Continuous batching + PagedAttention + high KV cache utilization is the biggest lever — it directly divides your fixed GPU cost across more tokens.
- **Right-size the model.** The cheapest token is the one produced by the smallest model that meets quality. Use a smaller or quantized model, or route easy requests to a cheaper model and hard ones to a bigger one (model routing) — often the largest cost win of all.
- **Quantize.** Smaller models fit on cheaper hardware and free memory for more concurrency — cost down on two axes.
- **Cache aggressively.** Prefix caching avoids repeated prefill; response/semantic caching avoids repeated generation entirely for recurring queries — the cheapest request is the one you don't run.
- **Match hardware and utilization.** Keep expensive GPUs busy (autoscaling with headroom); an idle GPU is pure cost. Consider managed endpoints if you can't keep hardware utilized enough to beat their per-token price (the managed-vs-self-host decision).

The discipline is to optimize cost *at a fixed quality and latency SLO* — it's easy to make serving cheaper by making it worse, so cost tuning only counts when quality and latency targets still hold.

## Putting it all together

Serving an LLM well is a loop, not a one-time setup:

1. **Define SLOs.** Decide your TTFT, TPOT, and P99 latency targets from the user experience, and your cost-per-token budget from the business. Without targets, "optimization" is aimless.
2. **Pick your point on the latency/throughput curve** from the application (interactive vs. batch).
3. **Use a serving engine** with continuous batching and PagedAttention — this is the foundation, not an optimization.
4. **Apply the levers to the failing metric** — quantization and speculative decoding for latency, batching and KV cache efficiency for throughput, right-sizing and caching for cost.
5. **Measure at percentiles, under realistic load,** and iterate — tail latency and throughput only reveal themselves under production-like traffic.

That loop is the whole series in practice. LLM inference is memory-bound and sequential; every technique here works around one of those two facts; and the art is combining them to hit your latency SLOs at the lowest cost per token. Know which lever moves which metric, respect the trade-offs, and measure honestly — and you can serve large models fast and affordably.

## Key takeaways

- Serving is measured by TTFT (responsiveness, from prefill + queueing), TPOT (streaming speed, from decode), end-to-end latency (≈ TTFT + TPOT × output length), throughput (tokens/sec, the cost driver), and cost per token — measured at P95/P99 percentiles, not averages.
- The central tension is latency vs. throughput: bigger batches raise throughput and lower cost per token but raise per-request latency, and vice versa — so first decide which end of the curve your application (interactive vs. batch) needs.
- Match the lever to the failing metric: TTFT → reduce queueing + prefix caching + shorter prompts; TPOT → quantization + speculative decoding + right-sized batch; throughput/cost → continuous batching + KV cache efficiency + quantization.
- Levers interlock and compound: quantization helps both TPOT and throughput (frees KV cache memory); prefix caching helps both TTFT and throughput — a tuned stack beats a naive one on every axis at once.
- Lower cost per token by maximizing throughput per GPU, right-sizing/routing models, quantizing, caching (prefix + response/semantic), and keeping GPUs utilized — always at a fixed quality and latency SLO, iterating under realistic load.

## Further reading

- [Scaling across GPUs (previous post)](/blog/posts/llmserve-07-scaling-across-gpus.html)
- [AI Cost Optimization series](/blog/series/ai-cost-optimization/)
- [How LLM inference works — start of the series](/blog/posts/llmserve-01-how-inference-works.html)
