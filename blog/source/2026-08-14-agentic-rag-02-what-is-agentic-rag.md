# What Is Agentic RAG?

*Agentic RAG is what you get when retrieval stops being a fixed pipeline step and becomes a set of decisions an agent reasons through — whether to retrieve, what to search for, from where, how many times, and whether to trust the result.*

The previous post diagnosed naive RAG's failures as symptoms of one missing capability: reasoning about retrieval. Agentic RAG supplies it. Instead of a fixed retrieve-then-generate pipeline, an agent treats retrieval as something to plan, execute, evaluate, and repeat. This second post defines agentic RAG properly — the decisions it introduces, the loop that structures them, and the spectrum from naive to fully agentic — so the technique-specific posts that follow have a clear frame.

## From pipeline to agent

The core shift is from a *pipeline* to an *agent*. A pipeline runs fixed steps in fixed order. An agent has a goal (answer the question well), tools (retrieval, possibly several), and the ability to decide what to do next based on what it has seen so far. Agentic RAG applies that agent stance to retrieval: the model reasons about the information it needs, acts to get it, observes what came back, and decides whether it now has enough or must act again.

Concretely, agentic RAG introduces decisions naive RAG lacked:

- **Whether to retrieve at all** — some questions need no external lookup.
- **What to search for** — transforming the user's question into an effective query (or several).
- **Which source to use** — routing among multiple indexes, databases, or the web.
- **How much to retrieve** — adapting the amount to the question.
- **Whether the results are good enough** — grading retrieved content and deciding to accept, re-retrieve, or fall back.
- **Whether to retrieve again** — iterating for multi-hop questions until the answer is assembled.

Each is a decision the model makes by reasoning, not a constant baked into a pipeline. Restoring these decisions is exactly what fixes the failure modes from the previous post.

## The agentic RAG loop

Where naive RAG is a straight line, agentic RAG is a loop:

1. **Reason** about what information the question needs.
2. **Decide and act** — formulate a query and retrieve (from the right source), or decide no retrieval is needed.
3. **Observe and grade** — look at what came back and judge whether it is relevant and sufficient.
4. **Iterate or answer** — if insufficient, refine the query, switch sources, or retrieve again; if sufficient, generate the grounded answer.

This is the same reason-act-observe loop that underlies agents generally — the [ReAct pattern (Yao et al., 2022)](https://arxiv.org/abs/2210.03629) formalized interleaving reasoning and acting, and agentic RAG is that pattern applied specifically to retrieval as the action. The loop is what gives the system its adaptivity: it can respond to *what it actually found* rather than committing to a single blind fetch.

## A spectrum, not a binary

Agentic RAG is not one thing you switch on; it is a spectrum of how much retrieval reasoning you add, and you can adopt as much as your problem needs:

- **Naive RAG** — no decisions; retrieve once, always, with the raw query.
- **+ Query transformation** — the agent reasons about *what to search for* before retrieving.
- **+ Routing** — the agent chooses *which source* and *whether* to retrieve.
- **+ Self-correction** — the agent grades results and re-retrieves when they are inadequate.
- **+ Multi-hop iteration** — the agent retrieves repeatedly, reasoning between steps, for questions that need chaining.
- **Fully agentic** — the agent plans a retrieval strategy, uses multiple tools, corrects itself, and iterates, treating retrieval as one capability among several.

You do not jump to the far end. Each step up the spectrum adds capability *and* cost/latency (more model calls, more retrievals), so you add the reasoning your questions actually require and no more. A system whose questions are single-hop but poorly-phrased might need only query transformation; one answering research-style questions across sources needs most of the spectrum.

## The cost the loop introduces

Agentic RAG is more capable and, unavoidably, more expensive than naive RAG. Every decision is typically a model call, every iteration is another retrieval and another generation, and grading results costs tokens. A naive RAG answer is one retrieval and one generation; an agentic answer might be several of each. That is the trade: you spend more per query to handle queries the cheap pipeline gets wrong. This is why the spectrum matters — you want the *least* agentic approach that answers your questions well, because each increment up the ladder is real cost. The evaluation post treats how to measure whether the added capability is worth the added spend; keep the trade in mind throughout.

## Agentic RAG versus "just a bigger context"

A tempting alternative to agentic retrieval is to skip retrieval reasoning and stuff everything into a long context. It does not solve the same problems. A big context still cannot decide which source to consult, cannot chain multi-hop facts it was not given, cannot judge whether it has the right information, and pays for a huge input on every call while burying the relevant content in the low-attention middle. Agentic RAG is about *getting the right information through reasoning*, which a large window does not provide. The two compose — an agentic system still benefits from a capable model — but throwing context at the problem is not a substitute for reasoning about retrieval.

## Key takeaways

- Agentic RAG replaces naive RAG's fixed pipeline with an agent that reasons about retrieval — deciding whether, what, from where, how much, and how often to retrieve, and whether to trust the results.
- It runs a reason → act → observe/grade → iterate-or-answer loop, the ReAct pattern applied with retrieval as the action, giving it adaptivity naive RAG lacks.
- It is a spectrum: add query transformation, routing, self-correction, and multi-hop iteration incrementally, adopting only as much retrieval reasoning as your questions require.
- Each step up the spectrum adds capability and cost/latency (more model calls and retrievals), so prefer the least-agentic approach that answers your questions well.
- A bigger context is not a substitute — it cannot route, chain multi-hop facts, or judge relevance; agentic RAG is about getting the right information through reasoning.

## Further reading

- [ReAct: Synergizing Reasoning and Acting in Language Models — Yao et al., 2022](https://arxiv.org/abs/2210.03629)
- [Self-RAG: Learning to Retrieve, Generate, and Critique through Self-Reflection — Asai et al., 2023](https://arxiv.org/abs/2310.11511)
- [Corrective Retrieval Augmented Generation — Yan et al., 2024](https://arxiv.org/abs/2401.15884)
