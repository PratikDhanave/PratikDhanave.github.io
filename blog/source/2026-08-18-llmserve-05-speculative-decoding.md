# Speculative Decoding

*Decode is slow because it's sequential — one token at a time, each waiting for the last. Speculative decoding cheats that limit with a beautiful trick: let a small, fast model guess several tokens ahead, then let the big model verify them all in a single pass. When the guesses are good, you get several tokens for the price of one — with mathematically identical output.*

Every optimization so far has attacked *memory* — caching it, batching to reuse it, quantizing to shrink it. **Speculative decoding** attacks the other fundamental constraint: decode's strict *sequential dependency*, where you can't start token N+1 until token N exists. It's one of the most elegant ideas in LLM serving because it accelerates a single request's generation *without changing the output at all*. This post explains how it works and when it pays off.

## The bottleneck it targets

Recall two facts from earlier posts. First, decode generates tokens strictly one at a time. Second, decode is *memory-bandwidth-bound* — each step loads the entire model from memory to produce just one token, wasting most of the GPU's compute. Put together, these create a specific opportunity: the GPU has spare compute during decode, but the sequential dependency prevents using it, because you don't know what to compute next until the current token is done.

Speculative decoding turns that spare compute into speed. The insight: **verifying a sequence of tokens can be done in parallel, even though generating them can't.** If you could somehow *propose* the next several tokens, the big model could check all of them in one forward pass — using its idle compute — instead of one per pass. The challenge is producing good proposals cheaply, which is where a second model comes in.

## The draft-and-verify mechanism

Speculative decoding uses two models: a large **target model** (the one you actually want to sample from) and a small, fast **draft model** (a cheaper model, often a much smaller version of the same family). The loop:

```text
1. DRAFT: the small model quickly generates K candidate tokens
          (cheap, because it's small) e.g. "the cat sat on the"
2. VERIFY: the big model processes all K candidates in ONE forward pass,
           checking each against what it would have produced
3. ACCEPT: keep the longest correct prefix of the guesses;
           reject at the first divergence and take the big model's token there
4. Repeat from the accepted position.
```

Because the target model verifies all K draft tokens in a *single* pass (the same parallelism as prefill), a successful round yields multiple tokens from one expensive forward pass instead of one. When the draft model guesses well — which it often does for the "easy," predictable parts of text — you generate several tokens per target-model pass, multiplying decode speed.

The crucial property, proved in the original work: with the correct acceptance rule, **the output distribution is identical to sampling from the target model alone.** Speculative decoding is not an approximation — it produces exactly what the big model would have produced, just faster. You are trading extra compute (running the draft model and verifying) for reduced latency, with *zero* quality cost. That lossless guarantee is what makes it so attractive.

## Why it works: easy tokens are predictable

The reason draft models guess well is that not all tokens are equally hard. Much of language is highly predictable — closing a bracket, completing a common phrase, boilerplate, obvious continuations. A small model handles these easy tokens as well as a big one, so its guesses are frequently accepted. The big model's superior judgment only matters at the genuinely hard, information-rich tokens, where a divergence gets caught and corrected.

This explains the two things that govern speculative decoding's payoff:

- **Acceptance rate** — the fraction of draft tokens the target accepts. Higher acceptance means more tokens per verification pass and a bigger speedup. It depends on how well the draft model mimics the target on your workload.
- **Draft cost** — the draft model must be *much* cheaper than the target, or the overhead of running it eats the savings. A good draft model is fast enough that even partial acceptance nets a win.

The speedup is real but workload-dependent: predictable text (code with lots of boilerplate, structured output, formulaic prose) accepts more and speeds up more; highly unpredictable text accepts less. There's no quality risk to trying it — worst case, low acceptance means little speedup, not worse output.

## Variants: beyond a separate draft model

Maintaining and serving a separate draft model has costs (extra memory, another model to manage), so several variants reduce or eliminate it:

- **Self-speculation / early-exit** — use the target model's own earlier layers, or a lightweight attached head, to produce drafts, avoiding a separate model entirely.
- **Medusa-style multiple heads** — add extra prediction "heads" to the target model that propose several future tokens in parallel, then verify them together.
- **N-gram / prompt lookup** — for tasks with lots of repetition (e.g. summarization or editing where output echoes input), draft tokens by simply *copying likely continuations from the prompt or recent text* — no model needed at all, and surprisingly effective when output overlaps input.

The common thread is the same: cheaply propose multiple tokens, verify them in one parallel pass, accept the correct prefix. The variants differ only in *how* the proposals are made.

## When to use it

Speculative decoding is a **latency** optimization (faster individual generation), which shapes when it helps:

- **Best for low-latency, low-batch scenarios.** When batch sizes are small, the GPU has idle compute for verification to exploit, so speculative decoding shines — interactive single-user or latency-sensitive serving.
- **Less benefit at high batch sizes.** When continuous batching already saturates the GPU's compute with many concurrent requests, there's little spare compute for speculation, and the extra verification work can even compete with throughput. Speculative decoding and large-batch throughput serving pull in different directions.
- **Great for predictable workloads.** Code generation, structured/JSON output, and tasks where output resembles input (editing, summarization via prompt-lookup) get high acceptance and large speedups.
- **Always lossless.** Since it can't change output, it's safe to enable and measure — the only question is whether the speedup on *your* traffic justifies the added complexity and draft-model memory.

Speculative decoding rounds out the core inference optimizations: the KV cache and batching maximize throughput, quantization shrinks the model, and speculative decoding attacks single-request latency. The next post shows how a real serving engine — vLLM and its peers — packages all of these together.

## Key takeaways

- Speculative decoding attacks decode's sequential dependency (not memory) by exploiting that a sequence of tokens can be *verified* in parallel even though it can't be *generated* in parallel.
- A small fast draft model proposes K tokens; the large target model verifies all K in one forward pass and accepts the longest correct prefix — yielding multiple tokens per expensive pass when guesses are good.
- With the correct acceptance rule the output is mathematically identical to sampling from the target model alone — it's lossless, trading extra compute for lower latency with zero quality cost.
- It works because easy/predictable tokens (boilerplate, common phrases, structured output) are guessed well by a small model; the payoff depends on the acceptance rate and the draft model being much cheaper than the target.
- Variants (self-speculation/early-exit, Medusa-style heads, n-gram/prompt-lookup) reduce or remove the separate draft model; it helps most at low batch/low latency and predictable workloads, and less when large-batch continuous batching already saturates compute.

## Further reading

- [Fast Inference from Transformers via Speculative Decoding (Leviathan et al., 2022)](https://arxiv.org/abs/2211.17192)
- [Quantization (previous post)](/blog/posts/llmserve-04-quantization.html)
- [How LLM inference works — start of the series](/blog/posts/llmserve-01-how-inference-works.html)
