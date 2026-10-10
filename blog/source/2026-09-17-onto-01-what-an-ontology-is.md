# What an Ontology Is — Meaning You Can Compute With

*"Ontology" sounds like philosophy, and historically it was — the study of what exists. In computing it means something more concrete and more useful: a formal, explicit description of the things in a domain and how they relate, written so a machine can reason about it. As AI systems increasingly need to ground their answers in structured truth rather than guess from text, ontologies and the knowledge graphs built on them have become quietly essential. This series builds both from first principles.*

This series is for engineers who keep hearing "knowledge graph" and "ontology" — especially now, next to RAG and LLMs — and want to actually understand what they are and when to reach for them. Post 1 pins down the core idea: an ontology is a way of writing down *meaning* so that software, not just humans, can use it. Get that idea and everything else — RDF, OWL, SPARQL, GraphRAG — falls into place.

## Schema, taxonomy, ontology: a ladder of meaning

The clearest way to understand an ontology is to climb up to it from things you already know, each rung capturing more meaning than the last:

- **A schema** (like a database schema) says *what shape data has*: tables, columns, types. It captures structure but almost no meaning — it knows `customer_id` is an integer, not what a customer *is* or how a customer relates to an order beyond a foreign key.
- **A taxonomy** adds *hierarchy*: a tree of categories where each thing is a kind of its parent (a `Dog` is a kind of `Mammal` is a kind of `Animal`). This captures one relationship — "is a kind of" — and it's genuinely useful, but the world has many more relationships than subclassing.
- **An ontology** captures *things, their properties, and arbitrary relationships between them, with formal rules* — not just "a Dog is a Mammal" but "a Dog *has an* owner who is a Person," "a Person *can own* multiple Dogs," and "if X is a Dog then X is an Animal." It describes a whole domain as a web of typed concepts and relationships rich enough that software can *reason* over it.

So an ontology is a taxonomy's richer cousin: it keeps the hierarchy but adds the full graph of relationships and the logical rules that govern them. The jump that matters is from *structure* (schema) to *meaning* (ontology) — from "this field is a string" to "this thing is a Person, who works for an Organization, located in a City."

## The building blocks

Every ontology, whatever the notation, is built from a small, consistent vocabulary:

- **Classes (concepts/types)** — the kinds of things in the domain: `Person`, `Company`, `Product`, `Disease`. Classes can be arranged in a hierarchy (a `Physician` is a kind of `Person`), inheriting from their parents.
- **Individuals (instances)** — the actual things: *Ada Lovelace* is an individual of class `Person`; *Anthropic* an individual of class `Company`.
- **Properties (relationships and attributes)** — how things connect. *Relationships* link individuals (`Ada Lovelace` —worksFor→ `Analytical Engine Project`); *attributes* attach data values (`Ada Lovelace` —birthYear→ `1815`).
- **Axioms (rules)** — the formal constraints that give an ontology its power: "a Person has exactly one birth date," "worksFor's inverse is employs," "Physician is a subclass of Person, so every Physician is a Person." Axioms are what let a machine *derive* facts that were never stated explicitly (post 2's RDF and OWL make this concrete).

Notice the shape this implies: things connected by typed relationships *is a graph*. An ontology defines the *types* (the schema of the graph); the knowledge graph (post 3) is the graph of actual individuals filled in against those types. That relationship — ontology as the blueprint, knowledge graph as the populated building — is the spine of this whole series.

## Why this matters, especially now

Ontologies have quietly powered search, biomedical databases, and enterprise data integration for decades, for one core reason: **shared, explicit meaning lets independent systems and people agree on what data means.** When two databases both commit to the same ontology, "customer" means the same thing in both, and you can merge them without a human translating field by field. Meaning becomes an asset you can share, reuse, and compute over rather than re-deriving it in every application.

The reason the topic is resurgent is **LLMs and RAG**. Language models are brilliant at fluent text but weak at precise, consistent, verifiable facts — they hallucinate, and they have no stable model of *entities and their relationships*. An ontology and its knowledge graph provide exactly what an LLM lacks: a structured, queryable, authoritative source of truth about the specific entities in your domain, with explicit relationships the model can be grounded in. This is why "ontology-grounded RAG" / GraphRAG (post 6) has become a serious technique — it marries the LLM's fluency to the knowledge graph's precision. Understanding ontologies is, increasingly, understanding how to give an AI system something true to stand on.

The takeaway: in computing, an **ontology** is a formal, explicit, machine-readable description of the things in a domain and how they relate — the top of a ladder that climbs from a **schema** (shape, little meaning) through a **taxonomy** (hierarchy only) to a full web of typed concepts, relationships, and logical rules. It's built from **classes** (types), **individuals** (instances), **properties** (relationships + attributes), and **axioms** (rules that let machines *derive* unstated facts). Because things linked by typed relationships form a graph, the ontology is the *blueprint* (the types) and the **knowledge graph** is the *populated building* (the individuals) — the spine of the series. It matters because shared explicit meaning lets independent systems agree on what data means, and it matters *now* because an ontology + knowledge graph gives an LLM the precise, verifiable, relationship-aware source of truth it otherwise lacks.

## Key takeaways

- A computing **ontology** is a formal, explicit, machine-readable description of a domain's things and their relationships — written so *software*, not just humans, can reason over it.
- Climb to it: a **schema** captures structure but little meaning; a **taxonomy** adds one relationship (is-a hierarchy); an **ontology** adds the full graph of typed relationships *plus logical rules* — the jump from *structure* to *meaning*.
- It's built from **classes** (types like `Person`), **individuals** (instances like *Ada Lovelace*), **properties** (relationships linking individuals + attributes holding data), and **axioms** (rules that let a machine *derive* facts never explicitly stated).
- Things linked by typed relationships form a **graph**, so the ontology is the **blueprint** (defines the types) and the **knowledge graph** is the **populated building** (the actual individuals) — the spine of this series.
- Ontologies matter because **shared explicit meaning** lets independent systems/people agree on what data means (merge without hand-translation), and they matter *now* because they give **LLMs/RAG** the precise, verifiable, relationship-aware source of truth that language models lack (→ GraphRAG, post 6).

## Further reading

- [Ontology (information science) — formal domain descriptions](https://en.wikipedia.org/wiki/Ontology_(information_science))
- [Taxonomy — hierarchical classification](https://en.wikipedia.org/wiki/Taxonomy)
