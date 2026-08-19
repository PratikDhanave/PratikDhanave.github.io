# What Is Context Engineering?

*Prompt engineering was about wording a single instruction well; context engineering is the broader discipline of deciding everything a model sees at inference time — and for agents, it is the discipline that matters most.*

For a while, "prompt engineering" was the whole conversation: find the magic wording, add "think step by step," tweak until the output improved. That skill still matters, but it describes a shrinking slice of what actually determines an LLM's behavior in a real system. The larger discipline — the one that separates agents that work from agents that flail — is **context engineering**: deliberately curating everything the model sees in its context window on each call. This post opens a series on that discipline; here we define it, contrast it with prompt engineering, and explain why it has become the central skill of building with LLMs.

## From prompt to context

A prompt, in the narrow sense, is the instruction you write. But a modern model call is far more than an instruction. Into the context window go the system prompt, the conversation history, definitions of the tools the model can call, documents retrieved for this query, examples, structured data, and the space left for the model's own output. The model does not distinguish "your clever prompt" from "the six chunks your retriever pulled" — it sees one context, and it responds to the whole of it.

Context engineering is the practice of governing that whole. It asks: given a task, what is the *right* set of information to place in the window, in what form, in what order, and what should be left out? Prompt engineering optimizes the wording of one piece; context engineering optimizes the *composition* of all the pieces. As systems moved from single clever prompts to agents that loop, call tools, retrieve knowledge, and hold long conversations, the composition became the dominant factor — and the wording, while still important, became one input among many.

## Why it became the central skill

Three shifts pushed context engineering to the center.

First, **agents accumulate context**. An agent that runs for many turns — reading files, calling tools, getting results — piles up material. Left unmanaged, that pile overflows the window, buries the signal, and degrades every subsequent step. Someone has to decide what stays, what is summarized, and what is dropped. That someone is the context engineer.

Second, **retrieval put the model's knowledge under your control**. The moment you use retrieval-augmented generation, *you* choose which documents enter the context. Good choices make the model authoritative; bad ones make it confidently wrong. The quality of the answer is often set before the model runs a single token, by what you retrieved.

Third, **more context is not free, and not always better**. Every token in the window costs money and latency, and — as we will see — models do not use a long context uniformly well. Simply stuffing everything in is a losing strategy on cost, speed, *and* quality. Deciding what to include is a real optimization, not a formality.

## The model does not read your mind — it reads the window

The core mental shift is this: an LLM has no memory, no awareness of your database, no knowledge of the conversation beyond what is in the current context window. Everything it "knows" for this call is either baked into its weights (general, frozen, sometimes outdated) or present in the context (specific, current, and entirely your responsibility). If the relevant fact is not in the weights and not in the context, the model cannot use it — it will guess, and often guess plausibly and wrongly.

That reframes debugging. When an agent gives a bad answer, the first question is rarely "was the prompt worded better?" It is "what was actually in the context when it answered?" More often than not, the failure is a context failure — the needed information was missing, or the needed information was there but drowned by noise, or stale history contradicted the current task. Context engineering is, in large part, the practice of making sure the window contains what the task needs and little else.

## What the discipline covers

The rest of this series works through the components of a well-engineered context, each of which is a lever:

- **The context window as a budget** — treating tokens as the scarce resource they are, and understanding what competes for the space.
- **System prompts and instructions** — structuring the durable guidance that shapes every response.
- **Retrieval** — bringing in exactly the external knowledge a query needs, and no more.
- **Memory and history** — managing what a multi-turn conversation carries forward.
- **Tools and structured context** — the often-overlooked cost of tool definitions and structured data, and how to format them.
- **Compaction and long context** — compressing, summarizing, and coping with the fact that long contexts are not used uniformly.
- **Building a context pipeline** — assembling all of it into an architecture that composes the right window on every turn.

## The through-line

If prompt engineering was a craft of language, context engineering is a discipline of *information logistics*: getting the right information to the model, in the right form, at the right time, within a fixed budget, and keeping everything else out. It is less about clever phrasing and more about curation, retrieval, compression, and assembly. Master it and your agents become reliable; ignore it and no amount of prompt wording will save them. The following posts turn each component into concrete practice.

## Key takeaways

- Context engineering is the discipline of curating everything a model sees at inference — system prompt, history, tools, retrieved docs, examples, and output space — not just the wording of one instruction.
- Prompt engineering optimizes one piece; context engineering optimizes the composition of all pieces, which became dominant as systems moved to agents, tools, and retrieval.
- A model knows only what is in its weights (frozen) or its context (your responsibility); missing or buried information causes confident, plausible errors.
- Bad agent answers are usually context failures — needed information absent, drowned in noise, or contradicted by stale history — so debugging starts with "what was in the window?"
- The discipline covers the token budget, system prompts, retrieval, memory/history, tools/structured data, compaction/long-context, and assembling it all into a pipeline.

## Further reading

- [Lost in the Middle: How Language Models Use Long Contexts — Liu et al., 2023](https://arxiv.org/abs/2307.03172)
- [OpenAI Cookbook](https://github.com/openai/openai-cookbook)
- [Anthropic documentation](https://docs.anthropic.com)
