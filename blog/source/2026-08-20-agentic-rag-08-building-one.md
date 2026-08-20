# Building an Agentic RAG System

*The pieces from this series — routing, query transformation, graded retrieval, multi-hop, and evaluation — assemble into one system that reasons about retrieval as carefully as it reasons about the answer, while spending only as much as each question needs.*

Across this series we restored, one at a time, the decisions naive RAG could not make: what to search for, whether and where to retrieve, whether to trust the results, and whether to retrieve again. This final post assembles them into a coherent agentic RAG system — an architecture that composes the techniques, escalates cost only when a question demands it, and stays honest through evaluation. This is the capstone.

## The design principle: escalate on demand

The organizing idea, carried from the spectrum in the second post, is **do the least agentic thing that answers the question well.** Most queries are simple and should be handled cheaply; only the hard ones should pay for the full loop. So the architecture is not "always run every technique" — it is a graduated pipeline that adds reasoning as the question and the retrieved evidence require. A greeting exits immediately; a simple lookup does one transformed retrieval; a multi-hop research question runs the whole loop. This keeps the average cost near naive RAG while handling the hard tail agentic RAG was built for.

## The architecture

Composed, the system runs this flow per query:

```text
query
  │
  ▼
[1] Route: retrieve at all? which source(s)?  ──► no-retrieve ──► answer
  │ (retrieve)
  ▼
[2] Transform: rewrite / decompose / (HyDE) the query
  │
  ▼
[3] Retrieve from chosen source(s)  ◄─────────────┐
  │                                                │
  ▼                                                │
[4] Grade: are results relevant & sufficient?     │
  │           │                                    │
  │ poor      │ insufficient (need another hop)    │
  ▼           └───► transform next query ──────────┘
  fall back / re-route
  │ (good & sufficient)
  ▼
[5] Generate grounded answer
  │
  ▼
[6] Check groundedness; regenerate or flag if unsupported
  │
  ▼
answer (+ citations)
```

Trace the techniques into the stages:

- **Stage 1 (route)** is the whether-and-where decision from the routing post — including the cheap exit for queries needing no retrieval.
- **Stage 2 (transform)** applies query rewriting, decomposition, or HyDE as the question needs.
- **Stages 3–4 (retrieve + grade)** are retrieval followed by the relevance-and-sufficiency grading from the self-correction post.
- **The loop back from stage 4** is multi-hop: insufficient results trigger another transformed retrieval; poor results trigger fallback or re-routing.
- **Stages 5–6 (generate + check)** produce the answer and verify it is grounded before returning it.

Every branch is a decision the agent makes by reasoning, and simple queries fall straight through the cheap path while hard ones exercise the loop.

## Making it cheap on the common case

The system is only affordable if the common case stays cheap, so bias every stage toward early exit:

- Let the router send trivial queries straight to an answer with no retrieval.
- For simple, well-phrased questions, skip heavy transformation — a rewrite is cheap; decomposition and HyDE are not always needed.
- Grade with a cheap model; you need a relevance judgment, not a frontier-model essay.
- Cap hops so a non-converging question fails gracefully instead of looping.
- Cache aggressively — repeated queries, and even the retrieval for repeated sub-questions, should not re-pay the full loop (the caching lessons from the cost series apply directly).

The target profile: simple questions cost about what naive RAG costs; only genuinely hard questions incur the multi-hop, self-correcting expense. That is what makes agentic RAG deployable at scale rather than a demo that is too expensive to ship.

## Keep it honest with evaluation

An agentic RAG system has many moving parts, any of which can regress, so wrap it in the evaluation from the previous post and run it continuously. Track the four core metrics (context relevance and recall; faithfulness and answer relevance) plus the agentic behaviors (routing accuracy, correction effectiveness, hop count, cost per query) against a held-out set that includes unanswerable questions. When you change a stage — a new router, a different grader, an added transformation — measure that it helps on the set rather than trusting that more sophistication is better. This is how you tune the escalate-on-demand thresholds: push cheap paths as far as they hold quality, and reserve the expensive loop for where the data shows it earns its cost.

## When to build this — and when not to

Agentic RAG is the right investment when your questions are genuinely hard: conversational and context-dependent, multi-part, multi-hop, spanning multiple sources, or asked against a knowledge base that may not contain the answer and where a confident wrong answer is costly. It is over-engineering when your questions are simple, single-hop, single-source, and well-phrased — there, naive RAG is cheaper and sufficient, and the agentic machinery adds cost and latency for no quality gain. The honest path is to start simple, measure where naive RAG fails on your real questions, and add exactly the agentic capability that fixes the failures you actually have. Built that way — incrementally, measured, escalating on demand — agentic RAG is a system that answers hard questions reliably and cheap questions cheaply, which is the whole point.

## Key takeaways

- Assemble the series into a graduated pipeline — route → transform → retrieve → grade → (loop for multi-hop / fall back) → generate → groundedness-check — where every branch is a reasoned decision.
- The organizing principle is escalate-on-demand: do the least agentic thing that answers the question well, so simple queries stay cheap and only hard ones pay for the full loop.
- Keep the common case cheap: let the router exit trivial queries with no retrieval, skip heavy transformation when unneeded, grade with a cheap model, cap hops, and cache aggressively.
- Wrap the system in continuous evaluation (the four RAG metrics plus routing accuracy, correction effectiveness, hop count, and cost) against a held-out set including unanswerable questions, and tune escalation thresholds from the data.
- Build agentic RAG for genuinely hard questions (conversational, multi-hop, multi-source, possibly-unanswerable); for simple single-source questions naive RAG is cheaper — start simple, measure failures, and add exactly the capability that fixes them.

## Further reading

- [Self-RAG: Learning to Retrieve, Generate, and Critique through Self-Reflection — Asai et al., 2023](https://arxiv.org/abs/2310.11511)
- [Corrective Retrieval Augmented Generation — Yan et al., 2024](https://arxiv.org/abs/2401.15884)
- [ReAct: Synergizing Reasoning and Acting in Language Models — Yao et al., 2022](https://arxiv.org/abs/2210.03629)
