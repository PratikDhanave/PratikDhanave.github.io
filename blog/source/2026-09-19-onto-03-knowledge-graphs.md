# Knowledge Graphs — The Ontology, Populated

*An ontology is the blueprint; a knowledge graph is the building. A knowledge graph is a network of real-world entities and the relationships between them, structured against an ontology so that both humans and machines can navigate it, query it, and reason over it. They power web search, recommendations, fraud detection, and increasingly the grounding of LLMs — and understanding what makes a graph a "knowledge" graph is understanding why this shape of data keeps winning for connected problems.*

Post 1 defined the ontology (the types and rules) and post 2 gave us RDF triples (the notation). This post is about what you build with them: the **knowledge graph** — the actual entities and relationships of a domain, filled in against the ontology. We'll cover what distinguishes a knowledge graph from an ordinary database, the two main technical flavors, and why graphs are the natural home for problems that are fundamentally about *connections*.

## What makes it a *knowledge* graph

A **knowledge graph** represents information as a graph: **nodes** are entities (people, places, products, concepts) and **edges** are the typed relationships between them (`worksFor`, `locatedIn`, `treats`). A set of RDF triples (post 2) is already exactly this. But two things elevate it from "a graph of data" to a *knowledge* graph:

- **It's grounded in an ontology (a schema of meaning).** The nodes and edges have *types* drawn from the ontology (post 1), so the graph doesn't just connect blobs — it says *this* `Person` `worksFor` *that* `Company`, with the types and rules that make the connection meaningful and checkable. The ontology is what lets the graph be reasoned over, not just traversed.
- **It integrates heterogeneous information into one connected whole.** A knowledge graph's superpower is merging facts from many sources — databases, documents, APIs — into a single graph where everything that refers to the same entity connects to the same node. Your CRM's "Acme Corp," your billing system's "Acme," and a news article's mention of Acme all become edges on *one* node (if entity resolution works — post 5). The graph becomes a unified view that no single source had.

So a knowledge graph is entities + typed relationships + an ontology that gives them meaning + integration across sources. The combination is what makes it *knowledge* rather than merely *data*.

## Two flavors: RDF graphs and property graphs

In practice there are two dominant technical models, and it's worth knowing the split because tools and queries differ:

- **RDF / semantic graphs** (post 2) — everything is triples, identifiers are URIs, meaning is carried by shared ontologies (RDFS/OWL), queried with SPARQL (post 4). Strengths: standards-based, interoperable, strong formal semantics and reasoning, great for merging across organizations. This is the "semantic web" lineage — the choice when *shared meaning and inference* are the point.
- **Labeled property graphs (LPGs)** — nodes and edges are typed with labels and can carry *properties* (key-value attributes) directly on both nodes *and* edges (e.g. a `KNOWS` edge with a `since: 2019` property). Queried with traversal languages like Cypher/Gremlin. Strengths: intuitive, fast for deep traversals, developer-friendly. This is the choice when *graph traversal and analytics* are the point and you don't need formal cross-org semantics.

The practical judgment: RDF when interoperability and reasoning dominate (biomedicine, government, multi-party data integration); property graphs when you're building one application that needs fast, expressive traversal (recommendations, fraud, network analysis). Both are "knowledge graphs"; they trade formal semantics against traversal ergonomics. Many teams start with a property graph for a product and adopt RDF when sharing meaning across boundaries becomes the need.

## Why graphs win for connected problems

The deeper question is *why* this shape — why not just use the relational tables most data already lives in? The answer is that for problems about **relationships**, graphs match the problem and relational databases fight it:

- **Relationships are first-class, not joins.** In a relational DB, "who are the friends-of-friends-of-friends of X?" is a cascade of expensive joins that gets worse with depth. In a graph, it's a natural traversal — you literally walk the edges. Graphs make *multi-hop* connection queries fast and expressible, and the real world is full of them: supply chains, org structures, citation networks, money flows.
- **The schema can flex.** Adding a new kind of relationship is adding a new edge type, not migrating a table. Knowledge grows by accretion — new entities and relationships attach to the existing graph — which fits messy, evolving, real-world knowledge far better than rigid tables.
- **Connections reveal meaning.** Fraud rings, influential nodes, communities, and recommendation paths are all *structural* patterns — they live in how things connect, and graph algorithms (centrality, community detection, path-finding) surface them directly. Fraud detection and recommendations are graph problems because the signal *is* the structure.
- **It's the natural grounding for AI.** Because a knowledge graph holds explicit entities and relationships, it's exactly the structured, traversable, verifiable substrate an LLM can be grounded in — walk from an entity to its related facts and feed those to the model (GraphRAG, post 6).

None of this means graphs replace relational databases — they coexist, and most organizations run both, using the graph for the connected questions and tables for the tabular ones. The skill is recognizing a *connection* problem (multi-hop, relationship-centric, integration-heavy) and reaching for the shape of data that fits it. When the questions you ask are about how things relate, a knowledge graph stops being exotic and starts being obvious.

The takeaway: a **knowledge graph** is a network of **entities (nodes)** and **typed relationships (edges)** — a populated ontology — that becomes *knowledge* (not just data) through two things: being **grounded in an ontology** (types + rules make connections meaningful and reasonable-over) and **integrating heterogeneous sources** into one connected whole where everything about an entity attaches to one node. Two flavors dominate — **RDF/semantic graphs** (URIs, OWL, SPARQL; standards, interoperability, reasoning) and **labeled property graphs** (properties on nodes and edges, Cypher/Gremlin; intuitive, fast traversal) — chosen by whether shared meaning or traversal ergonomics dominate. Graphs win for **connected problems** because relationships are first-class (multi-hop traversal vs. join cascades), the schema flexes by accretion, meaning lives in structure (fraud rings, communities, recommendations), and the graph is the natural, verifiable grounding for AI — coexisting with, not replacing, relational databases.

## Key takeaways

- A **knowledge graph** is entities as **nodes** and typed relationships as **edges** (a set of RDF triples already is one) — the ontology from post 1 *populated* with real individuals.
- It's *knowledge*, not just data, because it's **grounded in an ontology** (typed, rule-governed, reasonable-over — not blobs connected by edges) and **integrates heterogeneous sources** into one graph where all references to an entity attach to a single node (via entity resolution, post 5).
- Two technical flavors: **RDF/semantic graphs** (triples, URIs, OWL, SPARQL — standards-based, interoperable, strong reasoning; best for cross-org integration) and **labeled property graphs** (properties on nodes *and* edges, Cypher/Gremlin — intuitive, fast traversal; best for a single product needing deep traversal).
- Graphs win **connection problems** because relationships are **first-class** (multi-hop traversal beats cascading joins), the **schema flexes** by accretion, **meaning lives in structure** (fraud rings, communities, influence, recommendation paths surfaced by graph algorithms), and the graph is the **natural grounding for LLMs** (GraphRAG, post 6).
- Knowledge graphs **coexist with relational databases** rather than replacing them — the skill is recognizing a relationship-centric, multi-hop, integration-heavy problem and reaching for the graph shape.

## Further reading

- [Knowledge graph — entities and relationships as a graph](https://en.wikipedia.org/wiki/Knowledge_graph)
- [Graph database — storing and traversing graph-structured data](https://en.wikipedia.org/wiki/Graph_database)
