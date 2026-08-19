# The Context Window as a Budget

*Every token in the window costs money, adds latency, and competes for the model's attention, so the first skill of context engineering is treating context as a scarce budget to be spent deliberately.*

The context window has a fixed size, and everything the model needs for a call has to fit inside it. That makes the window a budget — a finite resource that many things compete to consume. The engineer who treats it as effectively infinite ("the model has a huge context, just put everything in") pays for it in cost, latency, and, surprisingly, accuracy. This second post in the context engineering series is about seeing the window as a budget: what spends it, what the spending buys, and why more is not always better.

## What competes for the space

On any given call, the context window is shared by several claimants, and they add up faster than people expect:

- **The system prompt** — instructions, role, rules, output format. Durable, present on every call.
- **Tool definitions** — the name, description, and input schema of every tool the model can call. A dozen richly-described tools can consume a substantial chunk of the window before the task even starts.
- **Conversation history** — every prior user and assistant turn you carry forward, which grows without bound in a long session.
- **Retrieved content** — the documents or chunks a retriever pulled in for this query.
- **The current input** — the user's actual request.
- **Output space** — the tokens reserved for the model's response, including any hidden reasoning. Output is part of the same budget; a large intended answer leaves less room for input.

The trap is that most of these grow independently. History grows with the conversation, retrieved content grows if you widen retrieval, tools grow as you add capabilities. Without a budget mindset, they collectively creep toward the limit until something important gets truncated — usually silently.

## What spending the budget buys, and what it costs

Every token you add is a trade. Including a document *might* give the model the fact it needs; it also costs money (you pay per input token), adds latency (more tokens take longer to process), and — critically — dilutes the model's attention across more material. The question for each candidate piece of context is not "could this possibly help?" but "does the expected benefit justify the cost?" Almost anything *could* help; that is exactly why "include everything" fails. A budget forces the sharper question.

The cost side is concrete and worth internalizing:

- **Money** scales with input tokens; a bloated context is a bill you pay on every single call, multiplied across all your traffic.
- **Latency** scales with tokens processed; a window stuffed to the brim is a slower response, which for interactive agents is a real product cost.
- **Quality** does not scale up with tokens the way intuition suggests — which is the most important and least obvious part.

## More context is not uniformly better

The intuitive model — "a bigger context means the model has more to work with, so it does better" — is wrong in an important way. Models do not attend to a long context uniformly. The research on this is clear: in "Lost in the Middle," Liu et al. (2023) found that models use information best when it appears at the **beginning or end** of the context, and performance **degrades when the relevant information is buried in the middle** of a long input. A fact that would have been used if it were near the top can be effectively ignored if it is stranded in the middle of a large window.

The practical consequences are direct. Padding the context with marginally-relevant material does not just cost money and time — it can actively *hurt*, by pushing the genuinely important content into the low-attention middle and surrounding the signal with noise. A tight, well-ordered context of the *right* 4,000 tokens routinely beats a sprawling, unordered 40,000. Position matters, density matters, and relevance matters more than volume.

## Budgeting in practice

Treating the window as a budget turns into a few concrete habits:

- **Set a target, not the max.** Decide how much of the window a task *should* use and aim well under the hard limit, leaving margin for output and variation. Running near the ceiling is fragile.
- **Allocate by claimant.** Roughly apportion the budget: this much for the system prompt, this much for retrieved context, this much reserved for output. When a claimant wants more, something else must give.
- **Rank and cut.** When candidate content exceeds the budget, rank by expected relevance and drop the tail rather than truncating arbitrarily. Arbitrary truncation is how the one important line gets cut.
- **Put the important things at the edges.** Given the lost-in-the-middle effect, place the most critical instructions and the most relevant retrieved content near the start or end, not buried in the center.
- **Account for growth.** History and accumulated tool output grow every turn; budget for the fact that a context which fits now may not in ten turns, and plan compaction before it overflows.

## The mindset

The shift is from "how much can I fit?" to "what is the smallest, best context that lets the model succeed?" Scarcity is a feature here: the constraint forces you to identify what actually matters, and a context built that way is cheaper, faster, and — because of how models use long inputs — often more accurate than a maximal one. Every later topic in this series (retrieval, memory, compaction) is ultimately a technique for spending this budget well.

## Key takeaways

- The context window is a fixed budget shared by the system prompt, tool definitions, conversation history, retrieved content, the current input, and reserved output space — and most of these grow independently.
- Every token traded into the context costs money and latency and dilutes attention, so the right question is "does the benefit justify the cost?" — not "could this possibly help?"
- More context is not uniformly better: models use information best at the beginning and end and degrade on information buried in the middle of long inputs (Liu et al., "Lost in the Middle").
- Padding with marginal content can actively hurt by stranding key information in the low-attention middle; a tight, well-ordered context often beats a sprawling one.
- Budget in practice: target well under the max, allocate by claimant, rank-and-cut rather than truncate, place critical content at the edges, and plan for growth.

## Further reading

- [Lost in the Middle: How Language Models Use Long Contexts — Liu et al., 2023](https://arxiv.org/abs/2307.03172)
- [OpenAI Cookbook](https://github.com/openai/openai-cookbook)
- [Anthropic documentation](https://docs.anthropic.com)
