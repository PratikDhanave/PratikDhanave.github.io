# Prompt and Context Optimization

*Since you pay for every input token, the fastest way to cut the cost of a call without changing the model is to send fewer tokens — and most production prompts are carrying far more than they need.*

Once you have right-sized the model, the next lever is the size of each call. You pay for every input token, so a prompt and context carrying twice the necessary tokens costs twice as much on input, on every single request, forever. This fourth post in the AI cost optimization series is about spending fewer input tokens per call — trimming prompts, pruning context, and controlling output — without losing the quality those tokens were buying. It is context engineering viewed through the cost lens.

## The prompt is a recurring cost, so trim it

The system prompt and instructions are present on every call, which means every wasted token in them is paid on every request across your entire traffic. That makes prompt bloat one of the most quietly expensive things in an AI system, and one of the easiest to fix. Long, rambling instructions; redundant restatements; verbose examples that a shorter example would match; boilerplate that no longer earns its place — all of it multiplies out across millions of calls.

Trimming is not about being terse for its own sake; it is about removing tokens that do not change the output. A prompt that says the same thing in half the tokens costs half as much on that portion of every call, with identical behavior. Review prompts specifically for cost: for each section, ask whether it measurably improves results, and cut what does not. Fewer, higher-quality examples often beat many mediocre ones on both quality and cost.

## Context is where the tokens hide

The system prompt is usually the smaller problem. The larger one is the *dynamic* context: conversation history, retrieved documents, and tool definitions, all of which can dwarf the prompt and all of which grow. The techniques from the context engineering discipline are, seen through this lens, cost optimizations:

- **Retrieve less, better.** Sending top-20 chunks when top-4 would answer the question is paying for 16 chunks of input on every retrieval-augmented call. Precision retrieval — hybrid search, reranking down to the few that matter — cuts input cost and, as a bonus, often improves quality by not burying the answer.
- **Compact history.** Carrying a full verbatim transcript forward means input tokens that grow every turn. Summarizing older history and keeping recent turns verbatim bounds the growth and the cost.
- **Prune tool definitions.** Exposing every tool on every call spends input tokens on tool schemas the task will not use. Present only the tools the task needs.
- **Distill tool results.** Feeding a raw multi-thousand-token API response back into context, then carrying it forward, is expensive; keep the distilled result the model needed.

Each of these is a token reduction on the largest, fastest-growing part of the input. For agent and RAG systems, context optimization typically dwarfs prompt trimming as a source of savings — go where the tokens are.

## Control the output side too

Input is only half the bill. Output is often priced higher per token, so controlling generated length is a direct saving. Ask for the response you actually need: if downstream code uses three fields, request three fields, not an essay. Constrain format and length explicitly in the prompt ("answer in one sentence," "return only the JSON"), because a model left to its own verbosity will often generate far more than the task requires. For tasks with heavy internal reasoning, consider whether that reasoning depth is warranted for this task or whether a lighter approach suffices — reasoning tokens are billed even when unseen. Concise, well-specified output requirements cut the output half of the cost while usually making the result easier to consume.

## Optimize without degrading quality

The trap in all of this is cutting tokens that were actually doing work. A prompt line that seemed like boilerplate may have been preventing a failure mode; a retrieved chunk that seemed marginal may have contained the answer for a subset of queries. So token reduction, like model routing, must be validated against an evaluation. Cut, then measure that quality held on representative cases. When it holds, you have a pure win — same behavior, lower cost. When it drops, you have learned those tokens were load-bearing and should stay. This measure-as-you-cut loop is what separates cost optimization from quality erosion.

## The compounding payoff

Token reduction has a compounding quality that makes it especially worth the effort: the savings apply to *every call*, and they stack with everything else. A leaner context is cheaper on a cheap model and cheaper on an expensive one; it makes caching more effective (less to cache, more hits); it speeds up responses (fewer tokens to process). Unlike a one-time fix, trimming the recurring per-call token count pays out on every request for the life of the feature, across all your traffic. It is often the highest-return work available after model selection, precisely because it is recurring and universal.

## Key takeaways

- You pay for every input token, so sending fewer tokens per call cuts cost on every request without changing the model — and most production prompts and contexts carry more than they need.
- The system prompt is a recurring cost paid on every call; trim tokens that do not measurably change the output, and prefer a few strong examples over many weak ones.
- The bigger savings are usually in dynamic context: retrieve less-but-better, compact history, prune tool definitions, and distill tool results — go where the tokens are.
- Control output too: request only the response you need, constrain length and format explicitly, and question unwarranted heavy reasoning, since output (including unseen reasoning) is often priced higher than input.
- Validate every cut against an evaluation so you remove wasted tokens, not load-bearing ones; token reduction compounds — it applies to every call, stacks with caching and routing, and speeds responses too.

## Further reading

- [Lost in the Middle: How Language Models Use Long Contexts — Liu et al., 2023](https://arxiv.org/abs/2307.03172)
- [OpenAI Cookbook](https://github.com/openai/openai-cookbook)
- [Anthropic documentation](https://docs.anthropic.com)
