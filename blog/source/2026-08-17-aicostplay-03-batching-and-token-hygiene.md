# Batching and Token Hygiene

*The second-largest cost lever is almost embarrassingly simple: if no one is waiting on a response, run it in a batch for half off — and the discount is identical across all three major clouds, which makes it a safe architectural assumption. Then comes token hygiene, where the wins are real but one popular technique quietly costs more than it saves.*

After prompt caching, two levers: **batch processing** (a flat ~50% discount, universal across providers) and **token hygiene** (trimming what you send and receive). This post covers both, including a genuinely counter-intuitive finding about context editing that's worth internalizing. As always, the figures are the vendors' own directional numbers — verify on your workload.

## Batch processing: 50% off, universally

The most reliable discount in AI is the batch discount, and its reliability comes from being *identical across all three major providers* — which makes routing to batches a safe architectural default:

- **Anthropic Message Batches API** — ~50% off every token, with results within 24 hours. It stacks with prompt caching (on Anthropic).
- **Amazon Bedrock batch mode** — ~50% below on-demand.
- **Google Vertex AI batch** — ~50% cheaper; and Vertex's Flex option also offers ~50% off standard pay-as-you-go for latency-tolerant, non-critical work.

The mechanism: you submit requests that don't need an immediate answer, and the provider processes them within a window (typically up to 24 hours) at half price, because it can schedule them on spare capacity. The consistency of the ~50% figure across clouds is what makes it architecturally useful — you can *assume* batch is half price regardless of provider and design accordingly.

**The rule that follows is simple:** route *every request no one is waiting on* through a batch. That includes evaluations, backfills, scheduled jobs, nightly report generation, bulk classification, embedding large corpora — any workload where a result in hours is fine. Keep the interactive, someone's-waiting path on real-time inference, and push everything else to batch for half off. Anthropic calls batching the second-largest free lever after caching, and the framing to adopt is: **latency-tolerant work is batch work, and batch work is half price.** Most estates have more deferrable work than they realize.

## The stacking caveat

Whether batching stacks with caching (the previous post's lever) depends on the provider, and it affects your architecture:

- **On Anthropic**, batching and prompt caching stack — both discounts apply, so a cached prompt run in a batch gets both savings.
- **On AWS Bedrock**, batch inference does *not* support prompt caching — so on AWS these two levers don't stack, and you choose which applies per request.

The practical implication: on a stacking provider, batch your cacheable deferrable work for compounded savings; on a non-stacking one, weigh which single discount wins for a given workload. Don't assume both apply — check your provider.

## Token hygiene: measure the net effect

The third lever is **token hygiene** — reducing the tokens you send and receive, since you pay per token. AWS formalizes this as its GENCOST03 "cost-aware prompting" practice, with four sub-practices worth naming as a checklist:

- Optimize prompt token length (send less input).
- Control model response length (generate less output).
- Implement prompt caching (the previous lever).
- Annotate user input for cost-aware content filtering (filter what you feed in).

The measured wins are real and compound with caching. Anthropic reports caching alone got ~83%, and adding *input trimming* took the total to ~88%. Specific techniques it measured: dynamic filtering of fetched web-page content (don't feed the model the whole page), right-sizing image inputs (don't send needlessly large images), and programmatic tool calling — which it reports cut input tokens ~24% *with a higher* score on agentic search. The theme: send the model what it needs and no more, and much of the input you reflexively include is trimmable without hurting (sometimes helping) quality.

## The counter-intuitive finding: context editing is not free

Here's the finding worth internalizing, because it cuts against intuition. **Context editing** — clearing or rewriting parts of the context during a run to free up space — is *not* a cost-saving technique, and can cost *more* than it saves. The reason ties directly to caching: every clearing/editing pass **rewrites the cached prefix**, which invalidates the cache and forces a re-write (and re-processing). In Anthropic's measured run, **context editing cost more than it saved**, because the cache invalidation outweighed the tokens removed.

The correct mental model: **use context editing to make room in the context window, not to save money.** It's a *capacity* tool (fitting more into a finite window), not a *cost* tool — and if you must edit, do it in a *few large batches* rather than many small passes, so you pay the cache-rewrite penalty rarely. This is a subtle interaction between two techniques (editing and caching) that pull against each other, and getting it wrong means "optimizing" your way to a higher bill. Contrast this with **compaction** (summarizing/condensing the conversation), which Anthropic reports cut a long run's bill a further ~38% — but only fires on sessions long enough to trigger it. So: compaction saves on long sessions; context editing spends to make room. Don't confuse them.

## The token-hygiene discipline

Pulling it together, token hygiene done well is:

- **Trim input** — filter fetched content, right-size images, remove boilerplate the model doesn't need; measured wins around ~24% fewer input tokens without quality loss are achievable.
- **Control output** — don't let the model generate more than needed (this connects to the budgets/stopping-conditions lever later, and note that capping output naively has a trap covered there).
- **Compound with caching** — trimming plus caching together reach higher totals (~88%) than either alone.
- **Use editing for capacity, not cost** — and batch edits to minimize cache invalidation; use compaction (not editing) to actually cut long-session cost.
- **Measure the net effect** — the post's title point: token techniques interact (especially with caching), so measure the *net* result, not the local reduction. Removing tokens that invalidate a cache can net negative. Always check the whole bill, not the piece you optimized.

Batching gives you a reliable half-off for deferrable work; token hygiene compounds with caching for real savings — provided you measure the net effect and don't fall into the context-editing trap. The next post covers the most commonly-botched cost decision: model selection, and the prompt audit that often beats it.

## Key takeaways

- Batch processing is a reliable ~50% discount identical across Anthropic, AWS Bedrock, and Google Vertex (results typically within 24h), which makes "batch is half price" a safe architectural assumption — route every request no one is waiting on (evals, backfills, scheduled jobs, nightly reports) through a batch.
- Batching stacks with prompt caching on Anthropic but not on AWS Bedrock (batch inference doesn't support caching there) — check your provider before assuming both discounts apply.
- Token hygiene (AWS GENCOST03) reduces tokens sent/received — optimize input length, control output length, cache, and filter input — with measured wins like ~24% fewer input tokens (via filtering fetched content, right-sizing images, programmatic tool calling) without quality loss, compounding with caching to higher totals (~88% vs ~83%).
- The counter-intuitive trap: context editing is NOT free — every clearing pass rewrites the cached prefix and can cost more than it saves; use it to make room in the context window (a capacity tool), not to save money, and batch edits to minimize cache invalidation.
- Compaction (condensing the conversation) genuinely cuts long-session cost (~38% further in one measured run) — distinct from context editing; the overarching discipline is to measure the *net* effect because token techniques interact, especially with caching.

## Further reading

- [Prompt caching: the single largest lever (previous post)](/blog/posts/aicostplay-02-prompt-caching.html)
- [Anthropic — Message Batches API](https://docs.anthropic.com/en/docs/build-with-claude/batch-processing)
- [Context Engineering series — compaction and managing context](/blog/series/context-engineering/)
