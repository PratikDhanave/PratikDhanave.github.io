# Routing and Retrieval as a Tool

*Real systems have more than one place to look, and the answer to "not everything should be retrieved from the same index — or retrieved at all" is to route queries and to treat retrieval as a tool the agent chooses to call.*

Naive RAG points at one index and searches it for everything. Real questions, though, span sources — product docs, a database, a ticketing system, the live web — and some questions need no retrieval at all. Agentic RAG handles this with two related ideas: **routing** (choosing which source, if any, fits the question) and **retrieval as a tool** (exposing each source as a tool the agent decides to call). This fourth post in the Agentic RAG series covers both, and the decision of when *not* to retrieve.

## The multi-source reality

Knowledge in a real system is not one homogeneous vector index. It is scattered across stores with different shapes and access patterns:

- **Unstructured documents** — best served by vector/hybrid search over a chunk index.
- **Structured data** — records in a database, best served by a query, not similarity search.
- **Live or volatile information** — current events, prices, status, best served by a web or API call.
- **Specialized indexes** — separate corpora per domain (legal, engineering, support) that should not be blended.

A question about a specific customer's plan needs the database; a question about last week's outage needs the ticketing system; a question about a competitor's latest release needs the web. Searching a single doc index for all of these fails. The system must first decide *where* the answer lives.

## Routing: choosing the source

A **router** inspects the query and directs it to the appropriate source. It is a classification-and-decision step, usually done by a model (or a cheaper classifier), that maps the question to one or more sources. "What's the balance on account 4021?" routes to the database; "how do refunds work?" routes to the policy docs; "what's the current status?" routes to the live source. Routing fixes naive RAG's inability to use the right tool for the question, and it improves both quality (searching the source that actually has the answer) and cost (not searching sources that don't).

Routing can be single-source (pick the one best source) or multi-source (fan out to several and combine), and it can be hierarchical (route to a domain, then to an index within it). The router's own cost must be justified by the savings and quality it buys — but for any system with genuinely distinct sources, routing is the difference between finding the answer and searching the wrong place.

## Retrieval as a tool

Routing generalizes naturally into the agent frame from earlier in the series: expose each source as a **tool** the agent can call. `search_docs`, `query_database`, `search_web`, `search_tickets` — each is a tool with a description of what it is for and a schema for its input. Now retrieval is not a fixed pipeline step but an action the agent chooses, exactly like any other tool. The agent reasons: this question needs the database, so I'll call `query_database`; the result is incomplete, so I'll also call `search_docs`.

This framing is powerful because it unifies retrieval with the rest of agentic behavior and composes cleanly with everything else in the series. Query transformation happens as the agent formulates the tool's arguments. Multi-hop iteration is the agent calling retrieval tools repeatedly. Self-correction is the agent evaluating a tool's result and calling another. And because tools carry descriptions, the agent's choice of *which* to call is guided by the same tool-selection reasoning that governs any tool-using agent — which is exactly what the MCP tools and context-engineering discussions covered. Retrieval-as-a-tool is what makes RAG a first-class citizen of an agent rather than a bolt-on.

## The most important decision: whether to retrieve at all

The routing frame surfaces a decision naive RAG could not make: *should we retrieve at all?* Many queries need no external lookup:

- **Greetings and chit-chat** — no retrieval, just respond.
- **Follow-ups answerable from the conversation** — the context already holds the answer.
- **General knowledge the model already has** — retrieving adds noise and cost for a fact the model knows well.
- **Meta questions about the conversation** — "summarize what we discussed" needs the history, not the knowledge base.

Retrieving on these wastes tokens and latency and can *degrade* the answer by injecting irrelevant chunks. So "no retrieval" should be an explicit route the agent can choose. This is a defining move of agentic RAG: retrieval becomes conditional, chosen when the question needs external information and skipped when it does not. The gate is a small reasoning step — does answering this well require information I don't already have? — and it saves cost on the many queries that don't.

## Keeping routing honest

Routing and tool selection add a decision that can be wrong: a misrouted query searches the wrong source and fails, and a wrongly-skipped retrieval answers from the model's memory when it should have grounded in documents. So the routing layer needs the same discipline as everything agentic — evaluate it. Measure how often queries route correctly, and watch specifically for the dangerous case of skipping retrieval when it was needed (which produces confident, ungrounded answers). Good routing is a large win; unmonitored routing quietly sends queries to the wrong place. Measure it, and route with a bias toward retrieving when genuinely uncertain, since a slightly noisy grounded answer usually beats a confident ungrounded one.

## Key takeaways

- Real knowledge is scattered across sources — documents, databases, live web, specialized indexes — each needing a different access pattern, so the system must first decide where the answer lives.
- A router inspects the query and directs it to the right source(s), fixing naive RAG's one-index limitation and improving both quality and cost.
- Generalizing routing, expose each source as a tool (`search_docs`, `query_database`, `search_web`) the agent chooses to call — unifying retrieval with agentic behavior and composing with transformation, multi-hop, and self-correction.
- The defining agentic move is making retrieval conditional: "no retrieval" is an explicit route for greetings, context-answerable follow-ups, general knowledge, and meta questions — saving cost and avoiding noise.
- Routing adds a decision that can be wrong; evaluate route accuracy, watch for wrongly-skipped retrieval (confident ungrounded answers), and bias toward retrieving when genuinely uncertain.

## Further reading

- [ReAct: Synergizing Reasoning and Acting in Language Models — Yao et al., 2022](https://arxiv.org/abs/2210.03629)
- [Self-RAG: Learning to Retrieve, Generate, and Critique through Self-Reflection — Asai et al., 2023](https://arxiv.org/abs/2310.11511)
- [Corrective Retrieval Augmented Generation — Yan et al., 2024](https://arxiv.org/abs/2401.15884)
