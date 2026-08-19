# Batching, Async, and Throughput

*Not all AI work needs an answer this second, and for the work that can wait, batching and asynchronous processing buy meaningfully cheaper tokens in exchange for latency you were not using anyway.*

Much of the cost conversation assumes interactive, real-time requests — a user waiting for a response. But a large fraction of AI workloads are not interactive at all: overnight document processing, bulk classification, enrichment pipelines, evaluation runs, content generation jobs. For this work, latency is cheap and throughput is what matters, and that opens a lever the interactive path cannot use: **batching**. This sixth post in the AI cost optimization series is about trading latency you do not need for cost you would rather not pay.

## Separate the real-time from the deferrable

The first move is a classification of your own workload: which requests truly need an immediate answer, and which merely need an answer *eventually*? A chat reply is real-time; generating summaries for ten thousand documents overnight is not. Teams often run everything through the same synchronous, interactive path out of habit, paying interactive prices for work that had no deadline. Recognizing the deferrable portion is what unlocks the cheaper options — you cannot batch what a user is staring at, but you can batch almost everything else.

This is an architectural decision worth making explicitly. Route deferrable work to a different, throughput-oriented path rather than the low-latency one. The two paths have different cost profiles, and mixing them wastes the savings the deferrable path could capture.

## Batch APIs: cheaper tokens for patient work

Providers commonly offer a **batch processing mode** for exactly this situation: you submit a large set of requests to be processed asynchronously over some window rather than immediately, and in exchange the tokens are billed at a reduced rate compared to the synchronous, real-time path. The provider can schedule the work when it has spare capacity, and passes some of that efficiency back as a lower price.

The trade is explicit and favorable when it fits: you accept that results arrive later — not in milliseconds but over minutes or hours — and you pay less per token for the same work. For bulk jobs with no user waiting, this is close to free money: the latency you gave up was latency you were not using. The pattern is to accumulate deferrable requests, submit them as a batch, and collect the results when they complete. Any workload you can express as "here are many requests, tell me when they are all done" is a candidate.

## Concurrency versus batching

It is worth distinguishing two things that both sound like "doing more at once." **Concurrency** is issuing many synchronous requests in parallel to improve *throughput* and wall-clock time — useful for getting a large job done faster, but it does not change the per-token price; you are still on the real-time path, just using it in parallel. **Batching** in the provider's batch mode changes the *price* in exchange for latency. They solve different problems: concurrency for speed on the interactive path, batch mode for cost on the deferrable path. A well-built bulk pipeline often uses batch mode for the cost, and concurrency is what you reach for when a job must be fast but you cannot wait for a batch window.

Concurrency also comes with its own discipline: providers enforce rate limits, so parallel request floods must respect those limits with backoff and queuing, or you trade cost problems for reliability problems. Getting throughput right is as much about staying within limits gracefully as about firing requests fast.

## Aggregating small requests

A subtler form of batching is combining many small tasks into fewer, larger calls where the task allows. If you need to classify a hundred short snippets, one call that classifies a batch of them can be cheaper than a hundred calls that each re-pay the fixed overhead of a system prompt and setup. This has limits — very large aggregated inputs run into context-size and quality trade-offs, and combining unrelated tasks can confuse the model — but for uniform, small, independent items, thoughtful aggregation reduces per-item overhead. The judgment is balancing the fixed-cost savings of fewer calls against the context-size cost and quality risk of bigger ones.

## When batching does not fit

Batching is not a universal answer, and forcing it where it does not belong creates worse problems than it solves. Interactive, user-facing requests cannot be deferred without hurting the product. Work with hard, near-real-time deadlines cannot wait for a batch window. And workloads that are genuinely low-volume may not have enough deferrable requests to make a batch worthwhile. The technique shines specifically for high-volume, latency-tolerant, bulk processing — and for that class it is one of the cleanest savings available, because it costs you nothing you were actually using. Match the tool to the workload: interactive work stays on the fast path, deferrable bulk work moves to the cheap one.

## Key takeaways

- Classify your workload into real-time (needs an immediate answer) and deferrable (needs an answer eventually); deferrable work unlocks cheaper processing that interactive work cannot use.
- Provider batch modes process requests asynchronously over a window at a reduced per-token rate — trading latency you were not using for a lower price, close to free for bulk jobs.
- Concurrency (parallel synchronous requests) improves throughput and speed but not price; batch mode changes price for latency — they solve different problems and are often used together.
- Respect rate limits with backoff and queuing when running concurrently, and consider aggregating many small uniform tasks into fewer calls to cut per-call overhead (within context and quality limits).
- Batching fits high-volume, latency-tolerant bulk work; keep interactive and hard-deadline requests on the fast path rather than forcing them into a batch.

## Further reading

- [OpenAI Cookbook](https://github.com/openai/openai-cookbook)
- [Anthropic documentation](https://docs.anthropic.com)
- [Hugging Face documentation](https://huggingface.co/docs)
