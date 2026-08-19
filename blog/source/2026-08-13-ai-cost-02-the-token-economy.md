# Understanding the Token Economy

*You cannot optimize what you cannot price, and pricing an AI system starts with understanding the token — what counts as one, why input and output cost differently, and how to compute the true cost of a request.*

Every lever in this series ultimately moves one number: tokens. LLM pricing is denominated in them, so before optimizing anything you need a clear model of the token economy — what a token is, how input and output are priced, what drives the count, and how to translate all of it into the cost of a real request. This second post in the AI cost optimization series builds that foundation. Once you can compute cost per request from first principles, every later technique becomes a measurable trade rather than a guess.

## What a token is

A token is the unit a model reads and writes — not a word and not a character, but a chunk produced by the model's tokenizer, roughly a common word or word-piece. As a rough intuition, a token corresponds to a few characters of English text, so a page of prose is on the order of hundreds of tokens; but the exact count depends on the tokenizer and the content. Code, punctuation-heavy text, and non-English languages tokenize differently — often less efficiently — than plain English prose. The practical point is that token count is *countable*: for any given text and tokenizer you can measure exactly how many tokens it is, which means you can measure cost exactly rather than estimate it.

## Input tokens and output tokens are priced separately

The single most important fact of the token economy is that a request has two token counts, priced independently:

- **Input tokens** — everything you send: the system prompt, conversation history, retrieved context, tool definitions, and the user's message.
- **Output tokens** — everything the model generates in response, including any hidden reasoning tokens the model produces before its visible answer.

These are billed at different rates, and **output is commonly more expensive per token than input**. That asymmetry has real design consequences: a request that sends a lot of context but asks for a short answer has a very different cost profile from one that sends little but generates a long response. You need both counts to know what a call costs; optimizing only one can miss where the money actually goes.

The hidden-reasoning wrinkle matters too. Models that produce internal reasoning before answering bill those reasoning tokens as output even though you never see them. A concise final answer can still be an expensive call if the model reasoned at length to produce it. When you measure output cost, measure the total generated tokens, not just the visible response.

## What drives the counts

Knowing what inflates each count tells you where to aim later optimizations:

- **Input is driven by context.** History that grows every turn, retrieved documents, verbose tool definitions, long system prompts — these are the input-token drivers, and they are exactly what the context-engineering discipline governs. Input cost is largely a context-size problem.
- **Output is driven by response length and reasoning.** How much you ask the model to generate, and how much it reasons internally, drives output tokens. Asking for concise output, constraining format, and choosing whether to invoke heavy reasoning are the output levers.
- **Call count multiplies both.** As the first post covered, agents and retries turn one user action into many calls, each re-incurring its input and output cost.

## Computing cost per request

Put together, the cost of a single request is straightforward to compute:

```text
request_cost = (input_tokens  × input_price_per_token)
             + (output_tokens × output_price_per_token)
```

And the cost of a *feature* is that request cost summed over all the calls a user action triggers, multiplied by traffic:

```text
feature_cost ≈ avg_request_cost × calls_per_action × actions_per_user × users
```

This little model is worth internalizing because it tells you where optimization pays off. If input tokens dominate (large context, short answers), context reduction and caching are your biggest levers. If output dominates (long generations, heavy reasoning), response-length control and model choice matter more. If call count dominates (deep agent loops, retries), reducing steps beats shaving tokens. You cannot know which case you are in without measuring the token counts — which is why measurement, not guessing, is the starting point of cost work.

## Measure before you optimize

The recurring discipline: instrument your calls to record input and output token counts (providers return these with each response), attribute them to features and requests, and look at where the tokens actually go before changing anything. Teams routinely optimize the wrong thing — shaving a system prompt while the real cost is a retry loop generating thousands of output tokens, or compressing output while a giant retrieved context dominates input. The token economy gives you the vocabulary; measurement tells you which term in the equation is large. Every subsequent post — model routing, context trimming, caching, batching — is a way to shrink one of these terms, and you should aim them at the term the data says is biggest.

## A note on prices changing

Model prices move over time, generally downward, and vary widely by model. This series deliberately reasons about cost in *relative* terms — input vs output, more tokens vs fewer, big model vs small — rather than absolute prices, because the relationships are stable even as the numbers change. Always check current provider pricing for real figures, but optimize against the structure: fewer tokens and fewer, right-sized calls are cheaper regardless of what this month's per-token price happens to be.

## Key takeaways

- A token is the tokenizer's unit (roughly a word-piece); token counts are exactly countable, so cost is measurable rather than estimated — and code and non-English text tokenize less efficiently than English prose.
- Every request has separate input and output token counts, priced independently, with output commonly more expensive per token — and hidden reasoning tokens bill as output.
- Input cost is driven by context size (history, retrieval, tools, system prompt); output cost by response length and reasoning; call count multiplies both.
- Compute request cost as input×input_price + output×output_price, and feature cost as request cost × calls per action × traffic — this reveals which term to optimize.
- Measure input and output tokens per call and attribute them before optimizing; reason about cost in relative terms since absolute prices change but the relationships do not.

## Further reading

- [OpenAI Cookbook](https://github.com/openai/openai-cookbook)
- [Anthropic documentation](https://docs.anthropic.com)
- [Hugging Face — tokenizers](https://huggingface.co/docs/tokenizers)
