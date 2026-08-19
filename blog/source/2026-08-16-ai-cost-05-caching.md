# Caching: Not Paying Twice for the Same Work

*A large share of what an AI system processes is repeated — the same system prompt, the same documents, the same questions — and caching is how you stop paying full price for work you have already done.*

AI systems repeat themselves constantly. The same long system prompt rides on every call. The same reference documents get sent to the model over and over. The same or similar user questions arrive again and again. Every repetition, by default, is billed at full price as if it were new. Caching is the family of techniques for recognizing repetition and charging less — or nothing — for it. This fifth post in the AI cost optimization series covers the main forms of caching and where each pays off.

## Prompt caching: reuse the expensive prefix

The most impactful caching for LLM applications is **prompt caching** (also framed as context or prefix caching). The idea exploits how models process input: a long, stable prefix — your system prompt, tool definitions, a big reference document — is the same on call after call, and the provider can cache the processed representation of that prefix so it does not have to be reprocessed each time. Requests that reuse the cached prefix are billed at a reduced rate for that portion.

The economics are compelling precisely because the repeated part is often the *large* part. If every call carries a big fixed context and only a small variable suffix (the user's actual question), prompt caching turns the expensive fixed part into a cheap cache hit and you effectively pay full price only for the small variable part. To benefit, structure your prompts so the stable content comes *first* and the variable content *last* — a cache keyed on the prefix only hits if the prefix is byte-stable, so anything that changes per request (timestamps, the user message) must go at the end, after the cacheable block. This ordering discipline is the main thing you do to make prompt caching work, and it is nearly free to adopt.

## Response caching: skip the call entirely

Prompt caching still makes a call; **response caching** avoids the call altogether when you have seen the exact request before. If a request is deterministic and identical to one you have already answered, you can store the response and return it directly — zero tokens, zero model latency. This is classic caching applied to model calls, and it is a total saving when it hits.

Exact-match response caching works best where the same inputs recur: common FAQ-style questions, repeated tool calls with identical arguments, idempotent lookups. It requires that returning a stored answer is acceptable (the answer is stable and not personalized in a way that makes reuse wrong). Where those conditions hold, it is the cheapest possible outcome — you answered without asking the model at all.

## Semantic caching: match similar, not just identical

Exact-match caching misses when two requests *mean* the same thing but are worded differently — "what's your refund policy?" versus "how do I get a refund?". **Semantic caching** closes that gap by matching on meaning: it embeds the incoming request, searches for a semantically similar prior request in the cache, and if a close-enough match is found, returns that answer. It is retrieval applied to the cache itself.

Semantic caching can dramatically raise hit rates for natural-language queries that cluster around common intents, but it carries a risk exact-match caching does not: a match that is *close but not close enough* returns a subtly wrong answer. The similarity threshold is the safety dial — too loose and you serve answers to the wrong question, too tight and you rarely hit. Semantic caching is powerful for high-volume, repetitive query patterns, but it must be tuned and monitored so it never trades a cost saving for a correctness bug.

## What not to cache, and cache invalidation

Caching's classic hard problem is knowing when a cached answer has gone stale. If the underlying data changes — a policy update, a new document, fresh pricing — cached responses can become wrong. So caching is safe in proportion to how stable the answer is. Highly dynamic, personalized, or freshness-critical responses are poor caching candidates; stable, general, reference-style answers are excellent ones. Plan invalidation deliberately: tie cache lifetimes to how often the source truth changes, and invalidate when it does. A cache that serves stale wrong answers has converted a cost problem into a trust problem, which is a far worse trade.

## Layering the caches

These techniques are not exclusive — a well-built system layers them. Exact-match response caching catches the identical repeats for free; semantic caching catches the reworded repeats; and prompt caching reduces the cost of everything that does make it through to the model by reusing the stable prefix. The order of the wins is: answer without a call if you can (response cache), answer from a similar prior if you safely can (semantic cache), and pay a reduced rate on the fixed context for the calls you do make (prompt cache). Together they attack repetition at every level, and because AI workloads are so repetitive, the combined effect on the bill is often among the largest available — second only to model selection for many systems.

## Key takeaways

- AI systems repeat constantly — same prompts, documents, and questions — and by default every repetition is billed at full price; caching charges less for work already done.
- Prompt (prefix) caching reuses the processed representation of a stable prefix at a reduced rate; put stable content first and variable content last so the prefix is byte-stable and hits.
- Response caching skips the call entirely for identical, deterministic requests — the cheapest possible outcome — where returning a stored answer is acceptable.
- Semantic caching matches on meaning to catch reworded-but-equivalent requests, raising hit rates but requiring a tuned similarity threshold so it never returns a close-but-wrong answer.
- Cache in proportion to answer stability, plan invalidation against how often the source truth changes, and layer the caches (response → semantic → prompt) to attack repetition at every level.

## Further reading

- [Anthropic documentation](https://docs.anthropic.com)
- [OpenAI Cookbook](https://github.com/openai/openai-cookbook)
- [Lost in the Middle: How Language Models Use Long Contexts — Liu et al., 2023](https://arxiv.org/abs/2307.03172)
