# Managed API vs Self-Hosting Open Models

*This is the classic fixed-versus-marginal decision, and it has a clean answer: managed APIs win until your volume is high and steady enough to keep expensive GPUs busy — which is a much higher bar than most teams assume.*

Should you consume models through a managed API (OpenAI, Anthropic, Bedrock, Vertex) or self-host open-weight models on your own infrastructure (with a server like vLLM or NVIDIA NIM)? It's one of the biggest cost and control decisions in an AI system, and it's frequently made emotionally — "self-hosting must be cheaper" — when it's really a math problem. This sixth post in the AI Architecture Decisions series works it through.

## The two cost structures

The decision is a textbook instance of the fixed-vs-marginal shape from the first post:

- **Managed APIs are pay-per-use.** No idle cost, no infrastructure to run; you pay per token consumed, and someone else bears serving, scaling, and hardware. Cost scales linearly with usage — cheap at low volume, and it never bills you for capacity you're not using.
- **Self-hosting is mostly fixed cost.** You pay for GPUs (or reserved cloud capacity) and the operations to run them, whether or not they're busy. The *marginal* cost per token can be very low — but only if the expensive hardware stays highly utilized.

That difference is the whole decision. Managed cost is a line through the origin; self-hosting is a high fixed baseline with a shallow slope. They cross at some utilization, and which side you're on is set by your volume.

## The deciding factor: utilization at volume

Self-hosting pays off when you have **high, steady traffic that keeps expensive accelerators busy.** Then the low marginal cost overcomes the fixed cost and you beat per-token pricing. It's a poor deal at low or spiky volume, where you pay for idle GPUs and shoulder operational complexity for little benefit — a GPU sitting at 10% utilization is burning money that a pay-per-use API would never charge you.

The bar is higher than intuition suggests, for two reasons. First, keeping utilization high is *hard* — real traffic is spiky, and provisioning for peak means idle capacity off-peak. Second, the fixed cost isn't just hardware; it's the engineering and on-call to run a production inference service reliably. For most teams and most workloads, usage is variable enough that managed APIs are more economical, and the operational savings alone justify them. Self-hosting becomes compelling specifically at scale, with steady high volume, or when non-cost factors force it.

## When non-cost factors decide it

Cost isn't the only axis, and sometimes another one overrides the math:

- **Data residency and control.** If regulation or policy forbids sending data to an external API, self-hosting (open models in your own environment, e.g. via NIM) may be *required* regardless of cost. This is often the real reason enterprises self-host.
- **Customization.** Deep control over the model — specific fine-tunes, custom serving optimizations, exotic quantization — is easier when you own the serving stack.
- **Lock-in and availability.** Self-hosting open weights removes dependence on a provider's pricing, rate limits, deprecations, and availability. Some teams self-host partly to own their destiny.
- **Latency predictability.** Owning the stack can give more control over tail latency than a shared multi-tenant API, though a well-run API is usually fast enough.

When one of these is a hard requirement, it can justify self-hosting even below the cost crossover — but be honest about whether it's a genuine requirement or a preference.

## The hybrid and the honest default

It's not strictly binary. Many mature systems are hybrid: managed APIs for the frontier-quality or spiky workloads, self-hosted open models for the high-volume, steady, or sensitive ones — routing each request to the cheaper appropriate option (the routing idea from the [AI Cost Optimization](/blog/series/ai-cost-optimization/) series). This captures the low marginal cost where volume justifies it and the no-idle-cost convenience everywhere else.

The honest default for most teams, most of the time, is **start with managed APIs.** They get you to production fastest, cost nothing when idle, and require no inference ops — and they keep the model swappable, so you're not locked in. Move workloads to self-hosting deliberately, when you've measured that a specific high-volume workload is past the crossover, or when data residency/control makes it necessary. Do the math on *your* utilization before assuming self-hosting is cheaper; the low per-token number is only real if the hardware is rarely idle.

## Pick this when

- **Managed API** — variable, spiky, or low-to-moderate volume; you want fastest time-to-market, no inference ops, and no idle cost. The right default for most teams.
- **Self-hosting open models** — high, steady volume that keeps GPUs busy (past the cost crossover), *or* a hard data-residency/control/customization requirement, *and* you have the GPU/ops capability.
- **Hybrid** — route high-volume/steady/sensitive workloads to self-hosted models and everything else to managed APIs; common at scale.
- **The math first** — before self-hosting for cost, estimate your real utilization and find the crossover; below it, managed wins on both cost and operational burden.

## Key takeaways

- It's a fixed-vs-marginal decision: managed APIs are pay-per-use (no idle cost, linear with usage); self-hosting is high fixed cost with low marginal cost that only pays off at high utilization.
- The deciding factor is utilization at volume — self-hosting wins only when steady high traffic keeps expensive GPUs busy, a higher bar than intuition suggests (spiky traffic + ops cost).
- Non-cost factors can override the math: data residency/control (often the real enterprise reason), deep customization, avoiding provider lock-in, or latency predictability.
- Hybrid is common and often optimal: self-host the high-volume/steady/sensitive workloads, use managed APIs for the rest, routing per request.
- The honest default is start with managed APIs (fastest, no idle cost, no ops, swappable) and move to self-hosting deliberately after measuring your utilization against the crossover.

## Further reading

- [AI Cost Optimization series](/blog/series/ai-cost-optimization/)
- [NVIDIA AI Stack in Python series](/blog/series/nvidia-ai-stack-in-python/)
- [The AI Production Roadmap series](/blog/series/the-ai-production-roadmap/)
