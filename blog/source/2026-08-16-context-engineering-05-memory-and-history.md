# Memory and Conversation History

*A conversation that never forgets eventually overflows, so managing what history an agent carries forward — and how it remembers across sessions — is one of the defining problems of context engineering.*

Every multi-turn interaction accumulates history, and history is context that grows without bound. Ten turns in, the transcript is manageable; a hundred turns in, it no longer fits, or it fits but drowns the current task in stale detail. Meanwhile, useful things a user told the agent last week are gone entirely unless you did something to keep them. Managing this — what to carry forward within a conversation, and what to remember across conversations — is a core context-engineering skill. This fifth post in the series covers conversation history and memory.

## The two problems: too much and too little

History poses opposite failures at once. **Too much:** raw transcripts grow past the budget, and long histories bury the current turn's relevant content in the low-attention middle, degrading responses. **Too little:** a stateless agent that only sees the current turn cannot follow references ("do that again for the other account"), and an agent that forgets everything between sessions cannot build on what it learned about a user. Good memory management threads between these — keeping enough to stay coherent, dropping enough to stay focused.

It helps to separate the timescales:

- **Short-term memory** is the current conversation's working context — the recent turns the agent needs to stay coherent right now.
- **Long-term memory** is what persists across conversations — facts about the user, past decisions, accumulated preferences — stored outside the window and retrieved when relevant.

They call for different techniques, so treat them separately.

## Managing short-term history

Within a single conversation, the job is to keep the working context coherent without letting it grow unbounded. A few strategies, often combined:

- **Keep a recency window.** Retain the last N turns verbatim — recent context is usually the most relevant, and this alone handles many conversations.
- **Summarize the older tail.** When history grows long, replace the older turns with a running summary that preserves decisions, facts, and open threads while shedding the verbatim back-and-forth. The agent then sees "a summary of earlier + the recent turns verbatim." This is compaction, which the next post treats in depth.
- **Preserve pinned facts.** Some things established early must survive no matter how long the conversation runs — the user's stated goal, a constraint, an ID. Keep these explicitly rather than trusting them to survive summarization by luck.
- **Prune tool noise.** Long tool outputs (a full API response, a big file) balloon history fast. Keep the distilled result the agent needed, not the raw dump, once it has been used.

The aim is a working context that stays roughly bounded turn over turn: recent turns in full, older material compressed, critical facts pinned, noise trimmed.

## Long-term memory across sessions

Long-term memory is a different mechanism. Because it must persist beyond the window and beyond a single session, it lives in external storage and is *retrieved* into context when relevant — which makes it, structurally, a retrieval problem (previous post) applied to the agent's own history. The loop:

- **Write:** after (or during) a conversation, extract durable facts worth remembering — preferences, decisions, stable attributes — and store them, ideally distilled into clean statements rather than raw transcript.
- **Retrieve:** at the start of, or during, a later interaction, pull the memories relevant to the current task and place them in context.

The design questions mirror retrieval's. *What* is worth writing (durable and useful, not every passing remark)? *When* to write (avoid storing noise)? *How* to retrieve (surface what is relevant to now, not everything ever stored)? And crucially, *how much* to inject — long-term memories compete for the same budget as everything else, so bring in the few that matter, not the whole store.

## Memory is lossy on purpose

The instinct to "just remember everything" fails for the same reasons stuffing the context fails: unbounded memory overflows, and undistilled memory is noise. Good memory is *lossy by design* — it keeps the signal (the decision, the preference, the fact) and discards the rest (the exact wording, the small talk, the intermediate steps). Deciding what to forget is as much a part of the discipline as deciding what to keep. An agent that remembers the three things that matter about a user will out-perform one that retains a verbatim log it cannot effectively search or fit.

## Tie it back to the budget

Everything here serves the budget mindset from earlier in the series. History and memory are two more claimants on the fixed window, and both grow. Left unmanaged, they are the claimants most likely to quietly consume the budget until the current task is starved. Managing them — recency windows, summarization, pinned facts, distilled long-term memories retrieved sparingly — is how a long-running or returning agent keeps a focused, affordable, high-quality context instead of an ever-growing transcript. The next post takes the compaction techniques these strategies lean on and treats them directly.

## Key takeaways

- Conversation history grows without bound, posing opposite failures: too much (overflow, buried signal) and too little (incoherence, forgetting across sessions).
- Separate short-term memory (the current conversation's working context) from long-term memory (facts that persist across conversations, stored externally).
- Manage short-term history with a recency window, summarizing the older tail, pinning critical facts, and pruning raw tool output.
- Long-term memory is a retrieval problem applied to the agent's own history: write distilled durable facts, retrieve the few relevant to the current task, and mind the budget.
- Good memory is lossy by design — keep the signal, discard the rest; deciding what to forget is as much the discipline as deciding what to keep.

## Further reading

- [Lost in the Middle: How Language Models Use Long Contexts — Liu et al., 2023](https://arxiv.org/abs/2307.03172)
- [Anthropic documentation](https://docs.anthropic.com)
- [OpenAI Cookbook](https://github.com/openai/openai-cookbook)
