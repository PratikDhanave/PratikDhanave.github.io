<!-- Markdown version for AI agents and readers. Canonical: https://pratikdhanave.com/blog/posts/fdfg-02-building-agents-and-ai-systems.html -->

# Building Agents & AI Systems

*This is the theme people picture when they hear "AI engineer" — the actual building of agents and AI systems. But a forward-deployed engineer builds differently: on the customer's real data, inside their constraints, with cost and latency treated as first-class from day one. This post maps the building theme of the field guide.*

Second in [The Forward Deployed Field Guide](/blog/posts/fdfg-01-understanding-customers-and-driving-ai-adoption.html). Once you understand the customer, you build — but building for a specific customer's production reality is a different craft than building a demo. This is the technical heart of the discipline, and the one changing fastest.

## The topics in this theme

- **Agents and orchestration.** Moving from a single prompt to systems that plan, call tools, and act — single-agent loops, multi-agent orchestration, routing, durable execution, and human-in-the-loop. The architecture decisions here determine whether the system is debuggable and trustworthy.
- **MCP and connectors.** An agent is only as useful as what it can reach. The Model Context Protocol and the broader connector layer are how agents get safe, governed access to a customer's tools and data — the plumbing that turns a clever model into a system that acts in the real workflow.
- **Context engineering.** What you put in front of the model — retrieval, memory, system instructions, examples — matters more than most prompt tricks. Getting the right context to the model at the right time is the discipline that most separates reliable AI systems from flaky ones.
- **Data and grounding.** Retrieval-augmented generation over the customer's data, done right: ingestion, chunking, embeddings, a permissioned store, retrieval and reranking, and grounding with citations. Most "bad AI answers" are retrieval failures, not model failures.
- **Cost and latency.** In production these are features, not afterthoughts — token economics at volume, caching, model routing, and latency budgets. A system that is accurate but too slow or too expensive doesn't ship.

## The new AI topics reshaping it

This theme is where "new AI topics" land thickest:

- **MCP as a standard.** The emergence of a shared protocol for connecting agents to tools and data is reshaping how systems are built — portable connectors instead of bespoke integrations.
- **Agent memory and long context.** Longer context windows and explicit agent memory change what context engineering means — what to retrieve vs. what to hold in memory vs. what to put in the window.
- **Cost/latency engineering as a discipline.** Model routing (cheap model for easy calls, strong model for hard ones), prompt caching, speculative decoding, and distillation are now core to making agentic systems affordable — the subject of deeper series.

## Where to go deep

This theme has the most supporting material on the blog: [AI Engineering in Go](/blog/series/ai-engineering-in-go/) for building from scratch, [Agentic RAG](/blog/series/agentic-rag/) and [Vector Search Internals](/blog/series/vector-search-internals/) for grounding, [LLM Inference & Serving](/blog/series/llm-inference-and-serving/) and [The AI Cost Optimization Playbook](/blog/series/the-ai-cost-optimization-playbook/) for cost and latency, and [LangGraph, Concept by Concept](/blog/series/langgraph-concept-by-concept/) for orchestration. For how all of this gets deployed *at a customer*, see [The AI Forward Deployed Engineer](/blog/series/the-ai-forward-deployed-engineer/).

## The forward-deployed difference

The thing that makes this *forward-deployed* building rather than generic AI engineering: you build on the customer's real, messy data from the start, you treat their security and cost constraints as design inputs, and you build so their team can run it — not a black box only you understand. The cleverest agent that only works on clean demo data, or that no one but you can operate, has failed the brief. Building here always serves [finding the right problem](/blog/posts/fdfg-03-finding-the-right-problem-and-proving-value.html) and [shipping to production](/blog/posts/fdfg-04-shipping-ai-production-security-reliability.html).

## Key takeaways

- This theme is the **technical heart** of the discipline — building agents and AI systems — but forward-deployed building is distinct: **on the customer's real data, inside their constraints, with cost and latency first-class**, built so their team can run it.
- The topics: **agents & orchestration** (planning, tool use, multi-agent, human-in-the-loop), **MCP & connectors** (safe governed access to the customer's tools/data), **context engineering** (the right context at the right time — often more important than prompt tricks), **data & grounding** (RAG done right; most bad answers are retrieval failures), and **cost & latency** (features, not afterthoughts).
- **New AI dynamics:** **MCP as a standard** (portable connectors over bespoke integrations), **agent memory & long context** (reshaping what context engineering means), and **cost/latency engineering** (model routing, caching, distillation) as a core discipline.
- Go deep via the blog's richest cluster: AI Engineering in Go, Agentic RAG, Vector Search Internals, LLM Inference & Serving, the AI Cost Optimization Playbook, and LangGraph.
- The **forward-deployed difference**: real-data-first, constraints-as-design-inputs, and buildable-for-handover — a clever agent that only works on clean data or that only you can operate has failed the brief.

## Further reading

- [Software agent — the foundation of agentic AI systems](https://en.wikipedia.org/wiki/Software_agent)
- [Retrieval-augmented generation — grounding models on the customer's data](https://en.wikipedia.org/wiki/Retrieval-augmented_generation)

---

Author: Pratik Dhanave (https://pratikdhanave.com) | Published: 2026-10-29
Canonical: https://pratikdhanave.com/blog/posts/fdfg-02-building-agents-and-ai-systems.html
Attribution: please link the canonical URL when citing or quoting this post.
