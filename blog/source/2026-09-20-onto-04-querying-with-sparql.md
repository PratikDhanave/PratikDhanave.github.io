# Querying a Knowledge Graph — SPARQL and Graph Patterns

*A knowledge graph you can't query is just a diagram. The power of the graph is realized when you can ask it questions — and querying a graph is fundamentally different from querying tables. Instead of joining rows, you describe a pattern of connections and ask the graph to find every place that pattern occurs. This post covers SPARQL, the standard query language for RDF graphs, and the graph-pattern-matching mindset that makes graph queries so expressive for connected questions.*

Posts 1–3 built the graph; this post is about interrogating it. The key mental shift is from *SELECT-FROM-WHERE over tables* to *match this shape in the graph*. Once you think in graph patterns, questions that would be monstrous SQL joins become short, readable queries — and that expressiveness is a big part of why knowledge graphs are worth building.

## Querying by pattern, not by join

The core idea of graph query languages is **pattern matching**. You write down a small template of nodes and edges — a *graph pattern* — with some parts fixed and some left as variables, and the engine finds every subgraph that matches, binding the variables.

In **SPARQL** (the W3C standard for RDF), the pattern is written as triples (post 2) with `?variables` in some positions:

```sparql
SELECT ?person ?company WHERE {
  ?person   rdf:type      :Person .
  ?person   :worksFor     ?company .
  ?company  :locatedIn    :London .
}
```

Read it as a shape: *find every `?person` who is a `Person`, who `worksFor` some `?company`, where that `?company` is `locatedIn` London.* The engine searches the graph for every binding of `?person`/`?company` that makes all three triple patterns true simultaneously. You didn't specify *how* to find them (no join order, no indexes) — you described *what shape you want*, and the engine figures out the traversal. That declarative, shape-based style is the heart of graph querying.

A SPARQL query is really just *more triples with holes in them*, which is elegant: the same triple model that stores the data expresses the questions. Beyond basic `SELECT`, SPARQL offers the operations you'd expect — `FILTER` (constrain values), `OPTIONAL` (match if present, like a left join), `UNION` (alternatives), aggregation (`COUNT`, `GROUP BY`), and `CONSTRUCT` (build *new* triples from a pattern, i.e. query a graph into a new graph). Property graphs have an analogous language, **Cypher**, where the pattern is written visually — `(person:Person)-[:WORKS_FOR]->(company)-[:LOCATED_IN]->(:City {name:'London'})` — the same pattern-matching idea in ASCII-art form.

## Why pattern-matching beats joins for connected questions

The advantage shows up the moment a question involves *chains* of relationships. Consider "find people connected to X through any chain of up to five `knows` relationships." In SQL that's five self-joins, written out explicitly, and six hops would mean rewriting the query. In a graph language it's a **path expression**:

```sparql
SELECT ?reachable WHERE {
  :X (:knows)+ ?reachable .
}
```

The `+` means "one or more `knows` edges" — variable-length traversal in a single operator. This is the thing relational queries genuinely can't express cleanly: **arbitrary-depth connection**. Friends-of-friends, supply-chain dependencies to any depth, ancestry, reachability, shortest paths — all become compact path patterns instead of unbounded join cascades. For questions whose essence is "how is A connected to B, possibly through many steps," the graph query is not just faster to run but dramatically simpler to *write*, which is often the greater win.

The pattern mindset also composes naturally with the ontology. Because `worksFor` and `Person` are defined in the ontology (post 1), queries are written in the domain's own vocabulary, and with a reasoner (post 2) a query for `Person` can *automatically include* `Physician`s and `Engineer`s (subclasses) without naming them — the query inherits the ontology's logic. Querying and meaning stay connected.

## Querying meets reasoning — and a note on scale

Two things make graph querying more than a different syntax for the same questions:

- **Inference-aware queries.** With an OWL reasoner (post 2), a query can match facts that were never explicitly stored but are *entailed* — ask for everyone `locatedIn` Europe and get people stored as `locatedIn Paris` because the ontology knows Paris is in France is in Europe. The query sees the *reasoned* graph, not just the asserted one. This is a capability relational databases simply don't have, and it's where ontologies pay off at query time.
- **The honest scaling caveat.** Deep, unbounded traversals and full reasoning can be expensive on large graphs — a `(:knows)+` across a billion-edge graph is a real workload, and naive queries can explode. Production knowledge-graph engineering involves indexing, bounding path lengths, and sometimes materializing inferred triples ahead of time rather than reasoning at query time. The expressiveness is real, but so is the need to write queries that the engine can execute efficiently — the same discipline as avoiding pathological SQL, just with new failure modes.

The throughline: graph querying lets you *ask about connections directly*. You describe a pattern in the domain's own vocabulary, optionally over the reasoned graph, and the engine finds every match — turning questions that are awkward or impossible in SQL into natural expressions of the shape you're looking for. That expressiveness, matched to connection-shaped problems, is what makes the whole knowledge-graph investment pay off at query time.

The takeaway: querying a knowledge graph is **pattern matching**, not joining — in **SPARQL** you write triples with `?variables` (a *graph pattern*) and the engine finds every subgraph that matches, declaratively (you describe the shape, not the traversal); a query is literally "triples with holes," composable with `FILTER`/`OPTIONAL`/`UNION`/aggregation/`CONSTRUCT` (and property graphs do the same via **Cypher**'s visual patterns). It beats joins for **connected questions** because **path expressions** (`(:knows)+`) express arbitrary-depth traversal in one operator — friends-of-friends, reachability, ancestry — that SQL can't write cleanly. Querying stays tied to meaning: patterns use the ontology's vocabulary and, with a **reasoner**, automatically match **entailed** facts and subclasses never explicitly stored. The caveat: deep traversal and full reasoning are expensive at scale, so production work bounds paths, indexes, and sometimes pre-materializes inferences.

## Key takeaways

- Graph querying is **pattern matching**: you write a *graph pattern* (nodes/edges with variables) and the engine finds every matching subgraph — **declarative** (describe the shape, not the join order).
- In **SPARQL**, patterns are RDF triples with `?variables` ("triples with holes"), composed with `FILTER`, `OPTIONAL` (left-join), `UNION`, aggregation (`COUNT`/`GROUP BY`), and `CONSTRUCT` (query a graph into a new graph); **Cypher** expresses the same idea as visual `(a)-[:REL]->(b)` patterns for property graphs.
- **Path expressions** (e.g. `(:knows)+` = one-or-more hops) express **arbitrary-depth connection** in a single operator — friends-of-friends, supply chains, reachability, shortest paths — which SQL can only do as unbounded, hand-written join cascades; the greater win is often *simplicity of expression*, not just speed.
- Queries use the **ontology's vocabulary**, and with an **OWL reasoner** they match **entailed** facts and subclasses never explicitly stored (ask for `locatedIn Europe`, get `locatedIn Paris`) — a capability relational DBs lack.
- The scaling caveat is real: deep traversals and full reasoning are expensive on large graphs, so production engineering **bounds path lengths, indexes, and pre-materializes inferences** — expressiveness with the discipline to keep queries executable.

## Further reading

- [SPARQL — the RDF query language](https://en.wikipedia.org/wiki/SPARQL)
- [Cypher (query language) — pattern queries for property graphs](https://en.wikipedia.org/wiki/Cypher_(query_language))
