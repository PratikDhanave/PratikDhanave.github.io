# Building a Knowledge Graph — Construction and Entity Resolution

*The hardest part of a knowledge graph isn't querying it or designing the ontology — it's building it from messy, real-world data. Most of your knowledge lives in databases that don't connect, documents that don't parse, and records that refer to the same thing by different names. Construction is the engineering of turning that mess into a clean, connected graph, and its central, unglamorous challenge is entity resolution: deciding when two records are actually the same thing. This post is about the work that makes or breaks a knowledge graph.*

Posts 1–4 assumed the graph exists. This post is where it comes from. The uncomfortable truth of knowledge-graph projects is that the ontology and the queries are the easy 20%; the 80% is *populating* the graph correctly from sources that were never designed to connect. We'll cover the construction pipeline, the entity-resolution problem at its heart, and why "the same node for the same thing" is where graphs succeed or fail.

## The construction pipeline

Building a knowledge graph means transforming heterogeneous sources into entities and typed relationships that conform to your ontology. The pipeline, roughly:

1. **Ingest from many sources** — relational databases, spreadsheets, APIs, and increasingly unstructured text (documents, web pages). Structured sources map fairly directly; unstructured ones need extraction (below).
2. **Extract entities and relationships** — from structured data, map rows/columns to the ontology's classes and properties (a `customers` table becomes `Person` nodes with attributes). From *unstructured* text, use **named-entity recognition** to find the entities ("Acme Corp," "London," "Dr. Smith") and relation extraction to find how they connect ("Dr. Smith *works at* Acme"). LLMs have made this extraction step dramatically more capable, which is a big reason knowledge-graph construction is having a moment.
3. **Map to the ontology** — align the extracted types and relationships to your ontology's vocabulary (post 1), so everything speaks the same language. Source A's "firm" and source B's "company" both become the ontology's `Organization`.
4. **Resolve entities** — the crux: merge records that refer to the *same real-world thing* into one node (next section).
5. **Load, validate, enrich** — write the triples, check them against the ontology's rules (a reasoner flags violations, post 2), and derive inferred relationships.

Steps 1–3 and 5 are real engineering, but they're tractable. Step 4 is the one that quietly determines whether you have a *knowledge graph* or just a pile of disconnected fragments wearing a graph costume.

## Entity resolution: the make-or-break problem

A knowledge graph's whole value is that everything about an entity connects to *one* node (post 3). But real data refers to the same entity in many ways: "Acme Corp," "Acme Corporation," "ACME Inc.," and "acme" may be four records of one company; "Dr. Jane Smith," "J. Smith," and "Jane Smith, MD" one person. **Entity resolution** (also called record linkage, deduplication, or entity matching) is the task of deciding which records are the same entity and merging them into a single node. Get it right and the graph connects beautifully; get it wrong in either direction and the graph breaks:

- **Under-merging** (missing that two records are the same) leaves the entity *fragmented* — facts about Acme scatter across four nodes, so a query about Acme sees only a quarter of the truth and the graph's integration promise fails silently.
- **Over-merging** (wrongly fusing two different entities) is worse — now two different people named John Smith are one node, and the graph confidently asserts false connections. This is the error that erodes trust, because the graph *looks* authoritative while being wrong.

Entity resolution is hard because identity is genuinely ambiguous — names collide, data has typos and gaps, and the same string can mean different things in different contexts. The techniques form a familiar ladder:
- **Deterministic matching** — exact or rule-based matches on strong identifiers (same tax ID, same email). High precision when a reliable key exists; most real data lacks one for most records.
- **Probabilistic / fuzzy matching** — score similarity across multiple fields (name edit-distance, address overlap, fuzzy dates) and merge above a threshold. This handles the messy majority and is the workhorse.
- **ML and embedding-based matching** — learn what "same entity" looks like from examples, or embed records into a vector space where the same entity's records sit close together — the modern scalable approach for large, messy datasets.
- **Context/graph-based matching** — use the *relationships* to disambiguate: two "John Smith" records are more likely the same if they share an employer and a city. The graph structure itself becomes evidence for resolution — a neat loop where the graph helps build the graph.

Because perfect resolution is impossible, the practical posture is to *tune the precision/recall trade-off to the stakes* (bias toward under-merging when false connections are dangerous), keep humans in the loop for ambiguous high-impact merges, and keep `sameAs` links (post 2) reversible so a bad merge can be undone. Entity resolution is never "done" — it's an ongoing quality process.

## Quality is the whole game

Zoom out and the lesson is that a knowledge graph is only as valuable as it is *correct and connected*, and both properties are won or lost in construction:

- **Garbage in is worse in a graph.** In a pile of documents, a wrong fact sits inert. In a knowledge graph, a wrong relationship *propagates* — reasoners infer new false facts from it, queries traverse through it, and GraphRAG (post 6) feeds it confidently to an LLM. The graph's connectivity, its great strength, also amplifies its errors.
- **Provenance matters.** Serious knowledge graphs track *where each fact came from* and *how confident* they are, so you can audit, debug, and decide which source wins when two disagree. A fact without provenance is hard to trust or fix.
- **It's continuous, not a one-off load.** Sources change, new data arrives, and resolution improves — so construction is a maintained pipeline with monitoring and re-resolution, not a migration you run once.

The honest framing for anyone considering a knowledge graph: the ontology is a weekend of modeling, the queries are a pleasure, and the construction-and-resolution is where the real cost and the real value both live. Teams that respect that — investing in extraction, entity resolution, provenance, and ongoing quality — get a graph they can trust and ground an AI on. Teams that treat construction as a data-dump get a fragmented, error-propagating graph that looks impressive and misleads quietly.

The takeaway: the hard part of a knowledge graph is **construction** — turning heterogeneous, messy sources into ontology-conformant entities and relationships — through a pipeline of **ingest → extract** (mapping structured data, and using **named-entity/relation extraction**, now LLM-boosted, on text) **→ map to the ontology → resolve entities → load/validate/enrich**. The crux is **entity resolution**: merging records that denote the same real-world thing into one node, where **under-merging** fragments an entity (graph sees partial truth) and **over-merging** asserts false connections (erodes trust) — handled by a ladder of **deterministic, probabilistic/fuzzy, ML/embedding, and graph-context** matching, tuned to the stakes with humans in the loop and reversible merges. Ultimately a graph is only as good as it is **correct and connected**: connectivity amplifies errors, so **provenance** and **continuous quality** are essential — construction is where a knowledge graph's cost and value both live.

## Key takeaways

- The hard, valuable part of a knowledge graph is **construction**, not ontology design or querying — populating the graph correctly from sources never meant to connect is the 80%.
- The pipeline: **ingest** (DBs, APIs, text) → **extract** entities/relationships (map structured data; use **NER** + relation extraction on unstructured text, now dramatically better with LLMs) → **map to the ontology** (align vocabularies) → **resolve entities** → **load, validate against the ontology's rules, enrich**.
- **Entity resolution** (record linkage/dedup) — deciding which records are the *same* real-world entity and merging to one node — is make-or-break: **under-merging** fragments an entity (silent partial truth); **over-merging** fuses distinct entities (confident false connections, trust-destroying).
- Resolution techniques ladder up: **deterministic** (exact keys like tax ID/email — high precision, rarely available), **probabilistic/fuzzy** (multi-field similarity thresholds — the workhorse), **ML/embedding** (scalable for big messy data), and **graph-context** (shared relationships disambiguate — the graph helps build the graph). Tune precision/recall to the stakes, keep humans in the loop, keep merges reversible.
- A graph is only as good as it is **correct and connected**: connectivity **amplifies errors** (reasoners and GraphRAG propagate a wrong edge), so track **provenance** (source + confidence) and treat construction as a **continuous, monitored** process — not a one-off dump.

## Further reading

- [Record linkage — matching records that refer to the same entity](https://en.wikipedia.org/wiki/Record_linkage)
- [Named-entity recognition — extracting entities from text](https://en.wikipedia.org/wiki/Named-entity_recognition)
