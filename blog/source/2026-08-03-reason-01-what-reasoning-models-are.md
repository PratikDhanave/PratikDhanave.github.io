# What Reasoning Models Are

*For years, the way to make a language model better was to make it bigger — more parameters, more training data. Reasoning models represent a different bet: instead of only scaling what the model knows, scale how much it thinks before answering. A reasoning model spends extra computation at inference time working through a problem step by step before committing to an answer — and on hard problems, that changes what's possible.*

This series is about **reasoning models** and **test-time compute** — the shift, crystallized by models like OpenAI's o1 and DeepSeek-R1, from "generate an answer immediately" to "think, then answer." It's one of the most significant changes in how large language models are built and used since instruction tuning. This first post frames what a reasoning model actually is, how it differs from a standard model, and why "thinking before answering" is a genuinely different capability rather than a prompting trick.

## The standard model: answer immediately

To see what's new, start with how a standard (non-reasoning) large language model works. An LLM generates text one token at a time, each token predicted from the preceding context. When you ask a question, it begins emitting the answer *immediately* — the first token of its response is the first token of its answer. Its "thinking," such as it is, happens implicitly inside the forward pass that produces each token; there's no separate deliberation phase.

This has a consequence for hard problems. If a question requires several steps of reasoning — a multi-step math problem, a logic puzzle, a tricky piece of code — the model has to get the whole chain right while committing to tokens from the start, with no room to work through intermediate steps unless it writes them out. For simple questions this is fine; for genuinely hard ones, answering immediately is a real limitation. The model can't "stop and think" — it just produces the next token, then the next, with a fixed amount of computation per token and no mechanism to spend *more* effort on a harder problem.

The insight behind reasoning models is that this immediacy is the bottleneck: on hard problems, the model would do better if it could *work through* the problem before answering — and that working-through can itself be generated as text.

## The reasoning model: think, then answer

A **reasoning model** is trained to do exactly that: before producing its final answer, it generates an extended internal **chain of thought** — a sequence of intermediate reasoning steps — and only then gives the answer. The key differences from a standard model:

- **It generates reasoning tokens before the answer.** The model produces a (often long) stream of intermediate steps — working through the problem, considering approaches, checking itself — and this reasoning is generated text, just not the final answer. Only after this thinking does it emit the answer the user sees.
- **It spends variable, often large, amounts of compute per problem.** Because the reasoning can be short or very long, the model effectively spends *more computation on harder problems* — the longer chain of thought is more forward passes, more tokens generated. This is the crucial shift: compute is no longer fixed per query; it scales with problem difficulty.
- **It's trained to reason, not just prompted to.** While you *can* prompt a standard model to "think step by step" (the chain-of-thought prompting the next post covers), a reasoning model is *trained* — typically with reinforcement learning — to produce effective reasoning natively, making its thinking far more capable than prompted step-by-step from a standard model.

So a reasoning model reframes inference from "predict the answer" to "generate a reasoning process that leads to the answer." The extended thinking is where the extra capability comes from — and generating that thinking is what "test-time compute" means: using more computation at inference (test) time to get a better result.

## Why thinking is a different capability

It's tempting to see this as a small tweak — "the model writes out its work" — but it represents a genuinely different capability, for a few reasons:

- **It converts a fixed-compute problem into a variable-compute one.** A standard model has a roughly fixed amount of computation to produce each token, so a hard problem gets no more "effort" than an easy one. A reasoning model can spend arbitrarily more compute (a longer chain of thought) on a hard problem — matching effort to difficulty. This is the difference between a fixed budget and an adjustable one.
- **Intermediate steps make hard problems tractable.** Many problems are hard to solve in one leap but straightforward step by step — each step is easy given the previous ones, but the whole is hard all at once. Writing out intermediate steps lets the model decompose a hard problem into a sequence of easy ones, which is why chain-of-thought dramatically improves performance on multi-step tasks (math, logic, planning). The reasoning *is* the mechanism, not decoration.
- **It enables self-correction.** With an extended thinking process, a reasoning model can catch its own mistakes mid-stream — notice an approach isn't working, backtrack, try another — something impossible when answering immediately. This ability to reconsider within a single response is a qualitatively new behavior.

The result is that reasoning models are dramatically better at exactly the tasks standard models struggle with: competition math, hard coding problems, multi-step logic, and complex planning. On simple factual or conversational tasks the difference is small (there's nothing to reason through), but on hard, multi-step problems the gap is large. Reasoning isn't a better way to phrase answers — it's a mechanism for solving problems that immediate answering can't.

## The new scaling axis

The deepest implication, which the series develops, is that reasoning models open a **new axis for improving AI performance**:

- **The old axis: training-time scale.** For years, better models came from *training* scale — more parameters, more data, more training compute. This "scaling laws" era made models more knowledgeable and capable, but it scales what the model has *learned*.
- **The new axis: test-time (inference) scale.** Reasoning models add a second axis: spend more compute *at inference* — let the model think longer, generate more reasoning, explore more — to get better answers *without retraining*. Research has shown that scaling test-time compute can, on some problems, improve results more effectively than scaling model parameters (the test-time-compute post covers this). It's a fundamentally different lever: you can dial up performance per-query by spending more thinking.

This is why reasoning models matter beyond a benchmark bump: they establish that inference-time computation is a first-class way to improve AI, complementary to training-time scale. It changes how models are built (training them to use thinking well), how they're used (deciding how much to let them think), and how they're priced (thinking tokens cost money). The rest of the series unpacks each of these: where chain-of-thought came from, what test-time compute really means, how reasoning models are trained, the inference techniques that spend compute for accuracy, the economics, how to use these models well, and where the frontier is.

A reasoning model, then, is a model that thinks before it answers — generating an extended chain of thought that spends variable compute to work through hard problems step by step, trained (not just prompted) to do so, opening inference-time computation as a new axis for capability. Next: chain-of-thought, the idea that started it all.

## Key takeaways

- A standard LLM answers *immediately* — it begins emitting the answer from the first token, with roughly fixed compute per token and no separate deliberation phase — which is a real bottleneck on hard, multi-step problems.
- A reasoning model is trained to *think, then answer*: it generates an extended internal chain of thought (intermediate reasoning steps) before the final answer, spending variable and often large compute that scales with problem difficulty.
- "Thinking" is a genuinely different capability, not a phrasing trick: it converts fixed-compute inference into variable-compute (effort matches difficulty), decomposes hard problems into sequences of easy steps (why CoT helps on math/logic/planning), and enables mid-response self-correction.
- Reasoning models are dramatically better at the tasks standard models struggle with (competition math, hard coding, multi-step logic/planning) but little different on simple factual/conversational tasks where there's nothing to reason through.
- The deepest implication is a new scaling axis: beyond training-time scale (more parameters/data), test-time compute (letting the model think longer at inference) is a first-class lever for capability — sometimes more effective than adding parameters — changing how models are built, used, and priced.

## Further reading

- [Chain-of-Thought Prompting Elicits Reasoning in Large Language Models (Wei et al., 2022)](https://arxiv.org/abs/2201.11903)
- [DeepSeek-R1: Incentivizing Reasoning Capability in LLMs via RL](https://arxiv.org/abs/2501.12948)
- [LLM Inference and Serving — how token generation works](/blog/series/llm-inference-and-serving/)
