# Resolving Ultimate Beneficial Ownership as a Graph Problem

*Model corporate ownership as a graph, propagate percentages through the chains, handle the cycles that break naive traversal, and surface every natural person who controls more than 25 percent — with the evidence path attached.*

Ask a compliance analyst who really owns a company and, for a sole trader, the answer takes a second. Ask the same question about a holding company that sits behind two intermediate entities incorporated in different jurisdictions, one of which owns a slice of another that loops back into the first, and the answer takes an afternoon of spreadsheet archaeology. Ultimate beneficial ownership (UBO) resolution is the engineering problem of doing that afternoon of work deterministically, in milliseconds, and reproducibly enough that you can defend the result to a regulator two years later.

The regulatory shape is consistent across most regimes: identify every natural person who, directly or indirectly, owns or controls more than a threshold — commonly 25 percent — of an entity. The word *indirectly* is where the engineering lives. This is not a lookup; it is a graph traversal with weighted edges, and treating it as anything simpler is how firms end up onboarding a shell whose real owner is three hops away.

## Ownership is a weighted directed graph

The right data model is a directed graph. Nodes are parties: legal entities and natural persons. Edges are ownership relationships carrying a percentage weight and, separately, a control flag — because control is not always proportional to shareholding.

```
        ┌──────────────┐
        │  Person A     │  (natural person, UBO candidate)
        └──────┬────────┘
          60%  │
        ┌──────▼────────┐        30%      ┌──────────────┐
        │  HoldCo X     ├────────────────▶│  OpCo Target  │
        └──────┬────────┘                 └──────▲────────┘
          40%  │                             50% │
        ┌──────▼────────┐                 ┌──────┴────────┐
        │  HoldCo Y     ├────────────────▶│  (same target)│
        └───────────────┘      (via X)    └───────────────┘
```

> **▸ [Open the interactive diagram](/blog/diagrams/fintech-ubo-graph-resolution.html)** — pan, zoom, and trace every step (light/dark, self-contained).

Edges point from owner to owned. A natural person is a terminal node — ownership chains bottom out at humans, government bodies, or listed entities whose free float is treated as diffuse. The graph is built by ingesting corporate registry filings, shareholder registers, and declared-ownership forms, then normalizing wildly inconsistent party records into stable entity identifiers. Entity resolution is its own hard problem: "ACME HOLDINGS LTD", "Acme Holdings Limited", and a registration number that matches both must collapse to one node, or the percentages will never add up.

Keep the graph edges immutable and versioned. Ownership changes, and a UBO determination is only meaningful as of a point in time. When you store an edge, stamp it with the source document, the effective date, and the ingest batch, so that any later result can be replayed against the exact graph state that produced it.

## Propagating percentages through the chain

Direct ownership is the edge weight. Indirect ownership is the product of weights along a path, summed across all distinct paths from a candidate person to the target entity.

For Person A above: the direct path A → HoldCo X → OpCo is 60% × 30% = 18%. The second path A → HoldCo X → HoldCo Y → OpCo is 60% × 40% × 50% = 12%. Person A's effective ownership is 18% + 12% = 30%, which clears the 25% threshold even though no single chain does. A naive "largest single path" heuristic would have missed them entirely.

The computation is a recursive propagation from each candidate root, multiplying edge weights down and accumulating at the leaves:

```python
def effective_share(owner, target, graph, path_weight=1.0, seen=None):
    seen = seen or set()
    if owner == target:
        return path_weight
    if owner in seen:            # cycle guard, see below
        return 0.0
    seen = seen | {owner}
    total = 0.0
    for edge in graph.out_edges(owner):
        total += effective_share(
            edge.to, target, graph,
            path_weight * edge.weight, seen)
    return total
```

Two engineering notes. First, floating point will bite you: percentages that should sum to exactly 1.0 across a company's cap table will drift, and a UBO sitting at 24.9999% versus 25.0001% is a compliance decision. Compute in fixed-point basis points (integers) or a decimal type, never binary floats. Second, the number of distinct paths can explode combinatorially in densely cross-held structures; memoize partial results per (owner, target) pair, and cap traversal depth with an explicit limit that raises an alert rather than silently truncating.

## Cycles are not corruption — they are structure

The tempting assumption is that ownership graphs are acyclic. They are not. Cross-shareholdings, where X owns part of Y and Y owns part of X, are legal and common, especially in older corporate groups. A recursion that does not expect cycles will loop forever or, worse, converge to an inflated ownership figure that double-counts the circular slice.

There are two defensible strategies. The pragmatic one, shown above, is a visited-set guard on each path: once a node appears on the current path, that branch contributes nothing further, which terminates traversal without inflating the sum. The rigorous one treats the strongly connected components of the graph as the real unit of analysis. Collapse each SCC with an algorithm like Tarjan's, solve the ownership within the component as a system of linear equations (the "integrated ownership" approach used in economic network analysis), then propagate across the resulting acyclic condensation. The linear-algebra route is more correct for tightly circular structures but heavier to run and harder to explain to an auditor; most onboarding systems ship the path-guard version and flag detected cycles for human review.

Whichever you choose, detecting the cycle is not optional. A structure engineered specifically to obscure ownership will often contain a deliberate loop, so a cycle is a risk signal in its own right, not just a traversal edge case.

## Control is a separate axis from ownership

Ownership percentage is necessary but not sufficient. Most regimes define a beneficial owner as someone who owns *or controls* the entity, and control can exist with little or no equity: a person holding board-appointment rights, a golden share, a voting agreement, or a senior managing official position when no owner clears the threshold.

Model control as a distinct edge type with its own predicate, evaluated in parallel with the percentage propagation. A candidate becomes a UBO if the effective ownership clears the threshold *or* a control edge grants qualifying influence. And when no natural person qualifies on either axis — a genuinely diffuse ownership structure — the regime typically requires you to fall back to a senior managing official as the beneficial owner of record. Encode that fallback explicitly; an empty UBO list is almost never an acceptable output.

## The output is a decision plus its evidence

A UBO engine that returns a list of names has done half the job. The other half is the control path: for each surfaced owner, the exact chain of edges and weights that produced the determination, serialized alongside the result. When a regulator asks why you cleared a customer, "our system said so" is not an answer; "Person A holds 30 percent through two documented chains, sourced from these two filings dated on these days" is.

Concretely, the engine emits, per beneficial owner: the effective percentage, whether the qualification was ownership or control, every contributing path with per-edge provenance, and the graph version the run executed against. That payload is what makes the whole thing auditable, replayable, and defensible — which, for a compliance control, is the actual product. The names are easy; the evidence is the engineering.
