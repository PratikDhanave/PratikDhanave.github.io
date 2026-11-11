# Structured and Graph Memory — When Facts Need Shape

*Embeddings are a marvel of forgiving representation: throw anything in, get approximate recall out. But some of what an agent must remember isn't approximate — who reports to whom, which service depends on which, what the user decided and when they reversed it. For facts with structure, similarity search is the wrong instrument, and the fix is as old as databases: give the facts a shape. This post is about entity-centric and graph-shaped memory, and when the extra machinery pays.*

Post [4](/blog/posts/agmem-04-retrieval-memory.html) built retrieval over an embedding store and ended with structure as metadata. This post promotes structure to the representation itself — the semantic-memory layer post 2 promised — drawing on ideas covered deeply in [Ontologies and Knowledge Graphs](/blog/series/ontologies-and-knowledge-graphs/), here applied specifically to what an agent remembers.

## Where similarity search stops working

Vector recall fails predictably on a class of memory queries — and the failures share a cause: the answer depends on *exact identity and relations*, not on textual resemblance.

- **Aggregation**: "every decision we made about the payments service" — similarity returns the five most similar mentions, not *all* of them; completeness isn't a nearest-neighbor concept.
- **Multi-hop**: "who owns the service that calls the API that broke?" — the answer traverses relations; no single stored text resembles the question.
- **Identity**: "Dana's preferences" must not blur into a different Dana, however similar the embeddings; and "the orders service," "orders-svc," and "that Go service Dana owns" must resolve to one thing.
- **Current state**: "what's the approved vendor *now*?" — embeddings of five successive answers all look alike; only explicit versioning knows which one is live.

Each failure is an agent acting on vibes where the situation demanded a ledger.

## Entity-centric memory: the 80% solution

Short of a full graph, the highest-value structure is simply **entities as first-class records**. The memory system maintains a registry — people, projects, services, clients, tools — and each entity accumulates a profile: attributes (role, timezone, preferences), related facts with dates and confidence, and pointers into the episodic store where each fact was learned. Three mechanics make it work: **extraction** (at consolidation time — post 6 — a pass pulls entity mentions and attribute claims from new episodes), **resolution** (mapping mentions to existing entities — the aliasing problem — using exact match, then embedding similarity over entity names, then asking-when-unsure; silent mis-resolution is this design's worst failure, because facts about one person quietly attach to another), and **revision** (attribute claims carry timestamps, so a new claim about the same attribute *supersedes* rather than coexists — this is where post 2's semantic-update discipline becomes concrete).

The payoff is a retrieval pattern embeddings can't offer: when the task involves Dana, *load Dana's profile* — complete, current, and compact — instead of hoping the right five chunks surface.

## Graph memory: when relations are the content

Entity records hold facts *about* things; a **knowledge graph** holds facts *between* them — edges with types: `dana —owns→ orders-service`, `orders-service —depends_on→ auth-api`, `decision-42 —supersedes→ decision-17`. The graph earns its machinery exactly when the queries from the first section dominate: multi-hop traversal ("everything downstream of this API"), temporal edges carrying valid-from/valid-to (the clean solution to current-state queries — close the old edge, open the new one, and history survives without ambiguity about "now"), and relationship-aware injection (pull the *subgraph around the task's entities* into the window — a neighborhood, not a similarity sample).

The honest costs: extraction of typed relations is harder and noisier than attribute extraction; the schema (what entity and edge types exist) needs ownership and restraint; and a wrong edge is more damaging than a wrong chunk, because traversal *compounds* errors across hops. The pragmatic guidance: most agents should go entity-centric first, and add graph edges only for the two or three relation types their domain actually queries — `owns`, `depends_on`, `supersedes` cover a remarkable share of real agent workloads.

## Hybrid is the end state

Mature memory systems converge on a layered design, because each representation covers the others' failures: the **episodic store** (post 4) holds full-fidelity history and answers "what happened"; the **entity/graph layer** holds current, resolved, versioned state and answers "what is true and how things relate"; and **embeddings index both** — including entity profiles and edge descriptions — so fuzzy natural-language recall still reaches structured facts. Retrieval composes them: resolve the task's entities, load their profiles and local subgraph, then vector-search episodes for texture, all under post 4's budget and provenance rules. The structured layer answers precisely; the episodic layer keeps the receipts — every structured fact linking back to the episodes that taught it, so confidence is always auditable.

The takeaway: similarity search fails on aggregation, multi-hop, identity, and current-state queries — the memory that needs **shape**. The 80% answer is entity-centric memory: a registry of first-class entities with extracted, resolved, *superseding* attribute claims; the full answer adds a knowledge graph with typed, temporal edges for the relation types the domain actually traverses. The end state is hybrid — structured layer for truth and relations, episodic store for history and receipts, embeddings over both — each layer covering the others' blind spots.

## Key takeaways

- Vector recall breaks on **aggregation** (all, not top-k), **multi-hop** (traversal), **identity** (aliases, same-name collisions), and **current state** (versioning) — queries where exactness is the content.
- **Entity-centric memory** is the highest-value structure: extract claims at consolidation, **resolve** mentions to canonical entities (mis-resolution is the worst silent failure), and let timestamped claims **supersede** — then "load Dana's profile" replaces "hope the right chunks surface."
- **Graph memory** adds typed, temporal edges (`owns`, `depends_on`, `supersedes`) for traversal and clean "what's true now" semantics — worth it only for relation types actually queried; wrong edges compound across hops.
- The end state is **hybrid**: entities/graph for current truth, episodic store for history (every fact keeps receipts), embeddings over both for fuzzy access — composed at retrieval under budget + provenance.

## Further reading

- [Knowledge graph — facts as entities and typed relations](https://en.wikipedia.org/wiki/Knowledge_graph)
- [Ontology (information science) — deciding what types of things and relations exist](https://en.wikipedia.org/wiki/Ontology_(information_science))
