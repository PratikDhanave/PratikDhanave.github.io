# RDF and OWL — How Meaning Gets Written Down

*Post 1 said an ontology is meaning a machine can compute with. This post is about the notation that makes that real: RDF, the dead-simple data model that represents any fact as a three-part statement, and OWL, the language that adds the logical rules a reasoner can act on. These are the W3C standards underneath most of the semantic-web and knowledge-graph world, and their core ideas are far simpler and more elegant than the acronyms suggest.*

To store and share an ontology and its facts, you need a common way to write them down — otherwise every system invents its own format and the "shared meaning" promise collapses. The web's answer is a small stack of standards. This post covers the two that matter most: **RDF** (how you state facts) and **OWL** (how you state rules). Together they turn the abstract idea of an ontology into something concrete, interoperable, and reasoner-ready.

## RDF: everything is a triple

The foundational idea is almost startlingly simple. **RDF** (Resource Description Framework) represents *all* knowledge as **triples** — statements of the form:

```
subject  —  predicate  —  object
```

Read it like a tiny sentence: *subject* has *predicate* relating it to *object*.
- `Ada Lovelace` — `bornIn` — `London`
- `Ada Lovelace` — `isA` — `Person`
- `London` — `isA` — `City`

That's the whole data model. Any fact about anything decomposes into these subject-predicate-object statements, and a *set* of triples is automatically a **graph**: subjects and objects are nodes, predicates are the labeled edges between them. This is why "RDF" and "knowledge graph" are so tightly linked — a pile of triples *is* a graph, with no extra machinery. The elegance is that the same uniform structure represents everything, so tools, queries, and merges all work the same way regardless of domain.

Two details give RDF its reach:
- **URIs as global names.** Subjects, predicates, and (often) objects are identified by URIs — web-style global identifiers — so `Person` in your data and `Person` in mine can be *the same* URI, and merging two datasets is just unioning their triple sets. Global names are how meaning becomes genuinely shareable across systems (post 1's promise, delivered).
- **Literals for data values.** Objects can also be plain values (`birthYear` — `1815`), so attributes and relationships use the same triple form.

Because the model is so minimal, RDF has several interchangeable *serializations* (Turtle, JSON-LD, RDF/XML) — different text formats for the same triples — which is why you'll see RDF embedded in web pages as JSON-LD (the same structured-data that powers rich search results) and in big datasets as Turtle files.

## RDFS and OWL: adding rules a machine can follow

Triples state facts, but post 1's power came from *axioms* — rules that let a machine derive new facts. That's what the ontology *languages* layered on top of RDF provide:

- **RDFS** (RDF Schema) adds the basics: declare that something is a **class**, that one class is a **subclass** of another, and constrain the **domain and range** of properties (e.g. `bornIn` goes from a `Person` to a `Place`). With RDFS, stating `Physician subClassOf Person` and `Dr. Smith isA Physician` lets a reasoner *infer* `Dr. Smith isA Person` — a fact nobody wrote down.
- **OWL** (Web Ontology Language) adds genuine logical expressiveness, enough to encode the rich axioms of post 1:
  - **Property characteristics** — `worksFor`'s inverse is `employs`; `ancestorOf` is *transitive* (so ancestors-of-ancestors are inferred); `hasSpouse` is *symmetric*.
  - **Cardinality** — a `Person` has *exactly one* birth date; a `Triangle` has *exactly three* sides.
  - **Class expressions** — define `Parent` as "a Person who has at least one child," so individuals get *classified* automatically based on their relationships.
  - **Equivalence and identity** — `sameAs` to say two URIs are the same entity (crucial for merging data, post 5); `equivalentClass` to bridge two ontologies.

OWL is grounded in **description logic**, a decidable fragment of formal logic, which is the important part: its rules aren't just documentation, they're *computable*. A **reasoner** can take your OWL ontology plus your triples and mechanically derive everything logically entailed — new relationships, new class memberships, and any *contradictions* (an individual that violates a cardinality or type constraint). That's the superpower RDF+OWL buys: a knowledge base that enriches and checks itself through inference rather than requiring every fact to be stated by hand.

## Why this stack, and when it's worth it

The RDF/OWL stack exists to make meaning **interoperable and verifiable** across independent systems. Shared URIs mean shared concepts; standard serializations mean any tool can read any dataset; OWL's logic means the rules travel *with* the data and any reasoner can apply them. This is the semantic web's core bet — that if knowledge is written in a common, logic-backed format, it can be freely merged and reasoned over the way web pages are freely linked.

The honest engineering caveat: this formality has a cost. Full OWL reasoning can be computationally expensive, and modeling a domain rigorously in description logic is real work. Many practical knowledge graphs (post 3) therefore use RDF's triple model and a bit of RDFS while skipping heavy OWL, or use property-graph databases that aren't RDF at all. The judgment is to match the formality to the need: reach for OWL's full logic when correctness and automated inference genuinely pay (biomedical ontologies, regulated domains, data integration across many sources), and stay lighter when you mainly need a flexible, queryable graph. Knowing what the stack *can* do lets you choose how much of it you actually want.

The takeaway: **RDF** represents all knowledge as **triples** (*subject — predicate — object*), and since a set of triples is automatically a **graph**, RDF *is* the knowledge-graph data model; **URIs** as global names make concepts shareable (merging = unioning triples) and **literals** carry data values, with interchangeable serializations (Turtle, JSON-LD, RDF/XML). On top, the ontology *languages* add machine-followable rules: **RDFS** (classes, subclasses, property domain/range → basic inference like `Physician ⊑ Person`) and **OWL** (inverse/transitive/symmetric properties, cardinality, class expressions, `sameAs`) grounded in **description logic**, so a **reasoner** can mechanically derive entailed facts and detect contradictions. The stack makes meaning interoperable and verifiable — at a real computational/modeling cost, so match the formality to the need.

## Key takeaways

- **RDF** models all knowledge as **triples** — *subject — predicate — object* — and a set of triples *is* a labeled **graph** (nodes = subjects/objects, edges = predicates), which is why RDF and knowledge graphs are inseparable.
- **URIs** give subjects/predicates/objects global names so the same concept is literally the same identifier across datasets (merging = unioning triple sets — shareable meaning delivered); **literals** hold data values; **serializations** (Turtle, JSON-LD, RDF/XML) are interchangeable text formats (JSON-LD is the same structured data behind rich search results).
- **RDFS** adds classes, **subclass** hierarchy, and property **domain/range**, enabling basic inference (`Physician subClassOf Person` + `Dr. Smith isA Physician` ⟹ `Dr. Smith isA Person`).
- **OWL** adds real logic — inverse/transitive/symmetric properties, **cardinality**, **class expressions** (auto-classification), and `sameAs`/`equivalentClass` — grounded in **description logic**, so a **reasoner** mechanically derives entailed facts and flags contradictions (a self-enriching, self-checking knowledge base).
- The stack buys **interoperable, verifiable meaning** but at a **computational/modeling cost** — so match formality to need: full OWL where automated inference and correctness pay (biomedical, regulated, multi-source integration), lighter RDF/RDFS or property graphs otherwise.

## Further reading

- [Resource Description Framework (RDF) — the triple data model](https://en.wikipedia.org/wiki/Resource_Description_Framework)
- [Web Ontology Language (OWL) — logic-backed ontologies](https://en.wikipedia.org/wiki/Web_Ontology_Language)
