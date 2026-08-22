# Prompt Caching: The Single Largest Lever

*Of every AI cost lever, one dominates the rest, and all the major vendors agree on it: prompt caching. On long prompts and agentic workloads the reported savings are the largest anywhere — because caching attacks the specific way agent costs explode. If you optimize one thing, optimize this.*

Ranked by the size of the effect the vendors have measured, **prompt caching** is the single largest inference cost lever. This post covers what it is, the figures the major providers report (directional, on their own benchmarks — verify on your workload), *why* it dominates agentic applications specifically, and the practices that make it work. It's the first and most important lever in the playbook.

## What prompt caching is and what vendors report

When you send a prompt, the model processes ("reads") all of its input tokens. **Prompt caching** stores the processed state of a prompt *prefix* so that a later request reusing that exact prefix skips re-processing it — you pay a small fraction for the cached portion instead of the full input cost again. The reported effects are the largest on the page, and they're consistent across providers:

- **Anthropic** reports up to **90% cost** and **85% latency** reduction on long prompts. Its pricing shape: a cache *write* costs ~1.25× the base input, and a cache *read* costs ~0.1× — so you pay a small premium to write the cache and a tenth to read it. In its own measured runs, agent-loop cost fell by a factor of **2.5–3.7×**, a triage agent's bill fell **83%**, and measured cache hit rates were **81–90%**.
- **AWS Bedrock** reports up to **90% cost** and **85% latency** reduction — with an important caveat: on Bedrock, prompt caching is for on-demand endpoints and is **not** available with the batch inference API (so on AWS, caching and batching don't stack — more in the batching post).
- **OpenAI**: cached tokens bill at ~**0.1×** the uncached input rate, cache writes at ~1.25× on recent models; it's automatic (no code change), with a minimum cacheable prefix (on the order of ~1,024 tokens) and cache hits occurring in fixed token increments.

The consistent shape across all three: **a small write premium, then reads at roughly a tenth**. That asymmetry is the whole game — caching is worth it whenever a prefix is reused enough times that the cheap reads outweigh the one write.

## Why it dominates agentic workloads

The reason caching is *the* lever — not just *a* lever — is clearest in Anthropic's explanation of agentic cost, and it's worth understanding precisely because it reframes how you think about agent bills.

In an agent loop, every turn resends the *entire growing conversation* — the system prompt, the tool definitions, and all prior turns — because the model needs the full context to produce the next step. So the first turn's content gets sent again on turn two, and again on turn three, and so on:

```text
A 40-turn agent task:
  turn 1's content is sent on turn 1, 2, 3, ... 40  → sent 40 times
  turn 2's content is sent on turn 2, 3, ... 40     → sent 39 times
  ...
  → total input grows with roughly the SQUARE of the turn count
```

This is the key insight: **agent cost grows with roughly the square of the turn count**, because early context is resent on every subsequent turn. A 40-turn task sends its first turn's content 40 times. That quadratic resending is *why* long agent runs get so expensive — and it's exactly what caching attacks. Caching doesn't stop the resending (the model still needs the context each turn); it makes each *resend* cost a tenth. So the quadratic cost explosion is cut by ~10× on the resent portion, which is most of it. That's why the measured agent-loop savings (2.5–3.7×, 83% on a triage agent) are so large: caching neutralizes the dominant cost driver of agentic workloads. If your workload is agentic, caching isn't optional — it's the difference between viable and ruinous.

## The practices that make it work

Caching only helps if you *hit* the cache, and hitting it requires deliberate practices. All the providers require an exact *prefix* match, which drives the rules:

- **Put static content at the front.** Instructions, examples, and tool definitions — the parts that don't change — go at the *start* of the prompt, with the variable parts (the user's latest input) after. Because caching matches on an exact prefix, only a stable prefix caches; anything before a change won't. Structuring prompts static-first-variable-last is the foundational practice.
- **Use a longer TTL when a loop waits on a human.** When an agent loop pauses between turns (e.g. waiting for a human), a standard short cache may expire before the next turn. Anthropic offers a 1-hour TTL that costs ~2× to write (instead of 1.25×) but pays for itself on the first prevented miss — worth it when gaps between cache hits are long.
- **Know what breaks the cache.** Several things silently invalidate the prefix and drop your cache hits: changing the effort/reasoning level mid-task, changing a task budget mid-task, and context-editing passes that rewrite earlier content (the token-hygiene post returns to this). Make such changes at *natural breaks*, and after any change, verify your cache reads didn't drop.
- **Use routing keys where offered.** OpenAI's `prompt_cache_key` helps route traffic that shares a common prefix to where the cache lives, improving hit rates for shared-prefix traffic.

The recurring discipline: caching is a *prefix* optimization, so design prompts and agent loops to keep a large, stable prefix, avoid mid-run changes that invalidate it, and **measure your actual cache hit rate** (the 81–90% figure is achievable, but only if you structure for it). A caching setup you don't measure may be quietly missing.

## Stacking and the caveats

Two practical notes that matter for architecture:

- **Caching stacks with batching on some providers, not others.** On Anthropic, prompt caching and the batch API stack (both discounts apply). On AWS Bedrock, batch inference doesn't support caching, so they *don't* stack — you choose one per request. Know your provider's stacking rules before assuming both apply (the batching post covers this).
- **The write premium means caching isn't free for one-shot prompts.** Because a cache write costs more than a normal read, caching a prefix used only *once* is a slight loss. Caching pays when a prefix is reused — which is almost always true for agents and shared system prompts, and rarely true for genuinely one-off prompts. Cache what's reused.

## The lever in one line

Prompt caching is the single largest AI cost lever because it directly attacks the quadratic cost explosion of agentic workloads — turning the expensive resending of growing context into cheap cache reads — with vendor-reported savings up to ~90% on long prompts and multi-fold on agent loops. Realize it by keeping a large stable prefix (static content first), using longer TTLs when loops wait, avoiding mid-run changes that invalidate the cache, and measuring your hit rate. If you do one thing from this playbook, cache your prompts. The next post covers the second-largest free lever — batching — and the token hygiene that compounds with caching.

## Key takeaways

- Prompt caching is the single largest inference cost lever, with consistent vendor-reported figures — up to ~90% cost and ~85% latency reduction on long prompts (Anthropic, AWS Bedrock), cached reads at ~0.1× and writes at ~1.25× across Anthropic/OpenAI — all directional, verify on your workload.
- It dominates agentic workloads because agent cost grows with roughly the square of the turn count (early context is resent on every turn); caching doesn't stop the resending but makes each resend cost ~a tenth, neutralizing the dominant cost driver (measured agent-loop savings of 2.5–3.7×, 83% on a triage agent).
- Caching requires an exact prefix match, so put static content (instructions, examples, tool definitions) at the front and variable content last — a stable prefix is what caches.
- Protect cache hits: use a longer TTL when loops wait on humans, avoid mid-run changes that invalidate the prefix (changing effort or task budget mid-task, context-editing passes), use routing keys where offered, and measure your actual hit rate (81–90% is achievable only if you structure for it).
- Know stacking rules (caching + batching stack on Anthropic, not on AWS Bedrock batch) and that the write premium means caching pays for *reused* prefixes (agents, shared system prompts), not genuinely one-off prompts.

## Further reading

- [The four governing frameworks (previous post)](/blog/posts/aicostplay-01-governing-frameworks.html)
- [Anthropic — prompt caching documentation](https://docs.anthropic.com/en/docs/build-with-claude/prompt-caching)
- [Context Engineering series — why context grows and how to manage it](/blog/series/context-engineering/)
