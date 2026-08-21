# Scaling Across GPUs

*At some point a model doesn't fit on one GPU, or the traffic doesn't, and you have to spread inference across many. The choices — which kind of parallelism, how to place replicas, when to autoscale — are governed by one unforgiving resource (GPU memory) and one expensive one (inter-GPU communication). Get the memory math right and most scaling decisions follow.*

The serving-engine post got a model running fast on a GPU. This one asks what happens when *one* GPU isn't enough — because the model is too big to fit, or the request volume is too high to serve. Scaling LLM inference across GPUs is its own discipline, dominated by GPU memory limits and the cost of moving data between GPUs. This post covers the memory math, the kinds of parallelism, and how to scale for traffic.

## Start with the memory math

Every scaling decision begins with GPU memory, because it's the hard limit. Three things consume it, and you must budget all three:

- **Model weights** — the dominant fixed cost. Roughly: parameters × bytes-per-parameter. A 70-billion-parameter model in FP16 (2 bytes) needs ~140 GB *just for weights* — more than any single current GPU. In INT4 (~0.5 bytes) that drops to ~35 GB, which may fit on one large GPU. (This is why quantization, from the earlier post, is often what determines whether you need multiple GPUs at all.)
- **KV cache** — grows with concurrency and context length (the KV cache post); this is what's left after weights and it sets your batch size.
- **Activations and overhead** — working memory for the forward pass, plus framework overhead.

The first question is always: *does the model fit on one GPU with enough room left for a useful KV cache?* If yes, you scale by **replication** (more copies). If no, you must split the model across GPUs with **model parallelism**. These are fundamentally different, and conflating them is a common mistake.

## Scaling for capacity: replication

If the model fits on one GPU, scaling for more traffic is the easy case: run **multiple independent replicas**, each a full copy of the model on its own GPU (or group), behind a **load balancer** that distributes requests across them.

```text
                    ┌─ GPU 1: full model  ← requests
   load balancer ───┼─ GPU 2: full model  ← requests
                    └─ GPU 3: full model  ← requests
   (each replica serves independently; add replicas for more throughput)
```

Replication scales throughput nearly linearly (double the replicas, roughly double the capacity) and improves availability (one replica failing doesn't take you down). It needs no inter-GPU communication *within* a request, so it's simple and efficient. This is the default way to handle traffic growth when the model fits — and because each replica runs its own continuous-batching serving engine, you're really scaling "how many batching engines" you run. Prefer replication whenever the model fits; it's the cheapest, most robust axis.

## Scaling for size: model parallelism

When the model is too big for one GPU, you must split the model *itself* across GPUs. This introduces inter-GPU communication into every forward pass, which is the cost you're managing. The main kinds:

- **Tensor parallelism** — split individual layers (their weight matrices) *across* GPUs, so each GPU computes part of every layer and they combine results. This spreads both weights and compute, and is the common way to run a model too big for one GPU. But it requires *high-bandwidth communication every layer*, so it's used *within* a single machine where GPUs are connected by fast interconnects (e.g. NVLink) — not across slow network links.
- **Pipeline parallelism** — split the model *by layers* into stages, each stage on a different GPU; a request flows through stage 1, then stage 2, and so on. Communication happens only at stage boundaries (less than tensor parallelism), so it tolerates slower interconnects and scales across machines — but naively it leaves GPUs idle (a "pipeline bubble") unless multiple requests are in flight to keep all stages busy.
- **Expert parallelism** — for Mixture-of-Experts models, distribute the "experts" across GPUs, routing each token to the GPUs holding its selected experts.

These are often **combined** (tensor parallelism within a machine, pipeline parallelism across machines) to run very large models. The key trade-off to internalize: **model parallelism buys you the ability to run a bigger model at the cost of inter-GPU communication overhead**, and that overhead grows with how "tightly" you split (tensor > pipeline). You split only as much as you must to fit the model, because every split adds communication latency.

## Data parallelism vs. model parallelism

It's worth stating the distinction crisply because the terms get muddled:

- **Data (replica) parallelism** — full model copies, each handling *different requests*. Scales **capacity/throughput**. No per-request cross-GPU communication. Use when the model fits.
- **Model parallelism** (tensor/pipeline/expert) — one model *split* across GPUs, all cooperating on the *same requests*. Scales **model size** (lets a too-big model run). Adds per-request communication. Use when the model doesn't fit.

The typical production topology combines them: split the model across a small group of GPUs *just enough to fit it* (model parallelism), then run *many such groups* as replicas behind a load balancer (data parallelism). Fit first, then replicate.

## Scaling for traffic: autoscaling

Real traffic is spiky, and GPUs are expensive, so you don't run peak capacity 24/7 — you **autoscale** the number of replicas to demand. But LLM serving makes autoscaling harder than a typical web service:

- **Slow cold starts.** Loading tens of GB of weights onto a GPU and warming the engine takes significant time, so you can't spin up a replica instantly when a spike hits. You must scale *ahead* of demand (predictive/proactive scaling) or keep warm capacity.
- **Scale on the right signal.** CPU utilization is meaningless here; scale on GPU-relevant signals — queue depth / pending requests, time-to-first-token latency, or GPU utilization — that actually reflect saturation.
- **Expensive, coarse units.** Each replica is a whole GPU (or several), so scaling granularity is coarse and each unit is costly — over-provisioning wastes real money, under-provisioning drops latency SLOs.
- **Batching interacts with scaling.** Because continuous batching lets one replica absorb more load by growing its batch (up to its KV cache limit), you scale out replicas only once existing ones are batch-saturated — not at the first sign of load.

The practical pattern: keep enough warm replicas to meet baseline latency SLOs, scale out proactively on queue-depth/latency signals with headroom for cold-start lag, and use the cheaper axes first (quantize to fit on fewer GPUs, batch to fill each replica) before adding hardware.

## Bringing scaling together

- **Do the memory math first** — weights (× bytes/param) + KV cache + overhead — to decide whether you replicate or must split.
- **Fit first, then replicate** — use the least model parallelism needed to fit (tensor within a box, pipeline across boxes), then scale capacity with replicas behind a load balancer.
- **Quantize to avoid splitting** — shrinking weights can turn a multi-GPU model into a single-GPU one, which is dramatically simpler and cheaper.
- **Autoscale on the right signals with cold-start headroom** — and exhaust batching and quantization before buying more GPUs.

Scaling is where inference meets infrastructure economics. The final post pulls the whole series together into the numbers that matter — latency, throughput, and cost — and how to tune the balance.

## Key takeaways

- Every scaling decision starts with GPU memory: weights (params × bytes/param — e.g. 70B ≈ 140 GB FP16, ~35 GB INT4) + KV cache + overhead; the question is whether the model fits one GPU with room for a useful KV cache.
- If it fits, scale capacity by replication — independent full-model copies behind a load balancer — which scales throughput nearly linearly, improves availability, and needs no per-request cross-GPU communication.
- If it doesn't fit, use model parallelism: tensor parallelism (split layers, heavy communication, within a fast-interconnect machine), pipeline parallelism (split by layer stages, less communication, across machines, needs in-flight requests to avoid bubbles), or expert parallelism (MoE) — trading the ability to run a bigger model for communication overhead.
- Data/replica parallelism scales capacity (model fits, different requests per copy); model parallelism scales size (model split, cooperating on same requests) — the typical topology splits just enough to fit, then replicates those groups.
- Autoscaling is hard for LLMs: slow cold starts (scale ahead of demand), scale on GPU signals (queue depth, TTFT, GPU util) not CPU, coarse expensive units, and exhaust quantization + batching before adding GPUs.

## Further reading

- [Quantization (earlier post) — often decides whether you need multiple GPUs](/blog/posts/llmserve-04-quantization.html)
- [Serving engines and PagedAttention (previous post)](/blog/posts/llmserve-06-serving-engines.html)
- [Distributed Systems from First Principles series](/blog/series/distributed-systems-from-first-principles/)
