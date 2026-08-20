# Multi-Hop and Iterative Retrieval

*Some questions cannot be answered by any single search because the answer is assembled from facts that must be found in sequence, each retrieval informed by the last — and that is what iterative, multi-hop retrieval provides.*

Consider: "Which engineers who joined after our Series B are now on the platform team?" No single similarity search returns that — you need the Series B date, *then* engineers who joined after it, *then* filter to the platform team. The answer is chained. Naive RAG's single shot structurally cannot do this, and even query decomposition only helps when the sub-questions are independent. Multi-hop retrieval handles the case where each step *depends on* the previous one. This sixth post in the Agentic RAG series covers iterative, multi-hop retrieval.

## Why one hop is not enough

Multi-hop questions have a dependency structure: you cannot form the second query until you have the first answer. "Who is the CTO of the company that acquired X?" requires first retrieving *which company acquired X*, and only then can you search for *that company's CTO*. Decomposing into independent sub-questions does not work here, because the second sub-question is unknown until the first is answered. This is fundamentally iterative — retrieve, reason about what you learned, form the next query from it, retrieve again — and it is exactly the reason-act-observe loop applied across several retrieval steps.

## The iterative retrieval loop

Multi-hop retrieval is agentic RAG's loop run more than once, with reasoning between hops:

1. **Retrieve** for the current sub-question.
2. **Reason** about what was learned and what is still missing to answer the overall question.
3. **Decide**: is there enough to answer now, or is another hop needed?
4. If another hop is needed, **form the next query** using what the previous hop revealed, and repeat.
5. When enough is gathered, **synthesize** the final answer from all hops.

The engine of this is the reasoning step between retrievals — it is what lets hop N's query depend on hop N−1's result, and it is what distinguishes true multi-hop from just retrieving several times. The [ReAct pattern (Yao et al., 2022)](https://arxiv.org/abs/2210.03629) is the natural structure: the model reasons ("I now know the acquirer is company Y; I need Y's CTO"), acts (retrieves for Y's CTO), observes, and continues until it can answer.

## Two shapes: planned and adaptive

Multi-hop comes in two flavors, useful in different situations.

**Planned (decompose-then-chain).** For questions whose hop structure is knowable up front, the agent plans the sequence of retrievals first, then executes them, feeding each result into the next. This is efficient when the decomposition is clear, and it overlaps with query decomposition from the earlier post — the difference is that the sub-queries are executed in dependency order, later ones templated on earlier results.

**Adaptive (retrieve-reason-repeat).** For questions where you don't know how many hops you'll need or what the next query is until you see the last result, the agent retrieves, reasons, and decides on the fly whether and what to retrieve next. This is more flexible and handles open-ended research questions, at the cost of being less predictable and potentially longer. Most robust systems lean adaptive, because real multi-hop questions rarely reveal their full structure in advance.

## Knowing when to stop

The defining challenge of iterative retrieval is termination: the loop must decide when it has *enough* to answer, and when to give up. Two failure modes bracket it. Stopping too early produces an incomplete answer built on a partial chain. Never stopping — retrieving hop after hop chasing more — burns cost and latency and can wander off the question. So the loop needs explicit stopping conditions:

- **Sufficiency reached** — the agent judges it can now answer the original question completely. This is the sufficiency check from the self-correction post, applied as the loop's exit test.
- **A hop budget** — a maximum number of hops, so a question that isn't converging fails gracefully instead of looping forever.
- **No progress** — if a hop adds nothing new, stop rather than retry indefinitely.

Getting termination right is most of what makes multi-hop reliable. A good loop asks after each hop, "can I answer the whole question now?" and stops the instant the answer is yes or the budget is spent.

## The cost reality

Multi-hop is the most expensive point on the agentic-RAG spectrum: each hop is a retrieval plus a reasoning step plus, often, a grading step, and a several-hop question multiplies all of that. A question that naive RAG answers (wrongly) in one call might take five or six calls to answer correctly via multi-hop. This is the steepest cost/quality trade in the series, and it argues for reserving multi-hop for the questions that genuinely need it — detected by routing or by a first hop revealing that more is required — rather than running the full iterative loop on every query. Single-hop questions should exit the loop after one retrieval; only genuinely chained questions should pay for the additional hops. Matching the number of hops to the question's actual dependency depth is the discipline that keeps multi-hop affordable.

## Key takeaways

- Multi-hop questions assemble their answer from facts found in sequence, where each query depends on the previous result — something a single search, and even independent decomposition, cannot do.
- It runs the reason-act-observe loop across several retrievals: retrieve, reason about what's missing, form the next query from what was learned, and repeat until you can answer (the ReAct pattern).
- Two shapes: planned (decompose then chain in dependency order) for known structure, and adaptive (retrieve-reason-repeat, deciding hops on the fly) for open-ended questions — robust systems lean adaptive.
- Termination is the core challenge: exit on sufficiency (can I answer the whole question now?), enforce a hop budget, and stop when a hop adds nothing — balancing incomplete-answer against endless-loop failures.
- Multi-hop is the most expensive point on the spectrum; reserve it for genuinely chained questions and match the hop count to the question's dependency depth rather than looping on every query.

## Further reading

- [ReAct: Synergizing Reasoning and Acting in Language Models — Yao et al., 2022](https://arxiv.org/abs/2210.03629)
- [Self-RAG: Learning to Retrieve, Generate, and Critique through Self-Reflection — Asai et al., 2023](https://arxiv.org/abs/2310.11511)
- [Corrective Retrieval Augmented Generation — Yan et al., 2024](https://arxiv.org/abs/2401.15884)
