# Conditional Edges: Routing with a Function and a Path Map

*How one router function plus a `path_map` dict lowers to exactly one edge firing per step.*

---

So far in this series the graph has been a straight line: `START → a → b → END`. Every edge is unconditional, so the next node is fixed at build time. Real workflows need to *decide* at runtime — validate input, then either format the result or send it back for a retry. In LangGraph that decision is a **conditional edge**: a **router** function reads the state and returns a key, and a **`path_map`** dict maps that key to the next node.

This post covers branching *without* a back-edge — a fork where control flows forward down exactly one of several arms. Add a back-edge to one of those arms and you get a cycle (the agent loop), which is the next post.

## The API

```python
graph.add_conditional_edges(source, router, path_map)
```

Three arguments:

- **`source`** — the node whose output triggers the routing decision.
- **`router`** — a function `router(state) -> str`. It inspects the whole state and returns a string key. It runs *after* `source` has updated the state, so it sees the fresh values.
- **`path_map`** — a `dict` mapping each key the router can return to a target node name.

Here is a real branching example. A `check` node sets a `failed` flag; we route to `format` on success or `retry` on failure:

```python
from typing import Annotated, TypedDict
from langgraph.graph import StateGraph, START, END, add_messages

class State(TypedDict):
    messages: Annotated[list, add_messages]
    failed: bool

def check(state: State) -> dict:
    ok = validate(state["messages"][-1])
    return {"failed": not ok}

def route(state: State) -> str:
    return "retry" if state["failed"] else "format"

graph = StateGraph(State)
graph.add_node("check", check)
graph.add_node("format", format_node)
graph.add_node("retry", retry_node)

graph.add_edge(START, "check")
graph.add_conditional_edges("check", route, {"retry": "retry", "format": "format"})
graph.add_edge("format", END)
graph.add_edge("retry", END)
```

The keys `"retry"` and `"format"` are the strings `route` can return; the values are the node names those keys resolve to. The keys are *labels*, decoupled from node names — they happen to match here, but `{"bad": "retry", "good": "format"}` with a router returning `"bad"`/`"good"` works identically. That indirection is the whole point of the `path_map`: the router speaks in intents, the map turns intents into targets.

### The router may return `END` directly

A common shortcut: you don't always need a real terminal node on a branch. `END` is a valid `path_map` target, so a branch can finish the run:

```python
graph.add_conditional_edges("check", route, {"retry": "retry", "format": END})
```

Now a successful check ends the graph immediately, while a failure goes to `retry`. `END` is the virtual terminal sentinel — routing to it yields the final state and stops.

## How it works: one guarded edge per branch

The mental model that makes conditional edges click is that **there is no special "conditional edge" primitive at the execution layer.** A conditional edge is *lowered* at compile time into one ordinary edge per entry in the `path_map`, and each of those edges carries a **`condition`** that wraps the router. Exactly one condition passes, so exactly one edge fires.

You can see this precisely in a minimal from-scratch StateGraph. Its `compile()` step walks the `path_map` and emits a guarded edge per key:

```python
for source, router, path_map in self._branches:
    for key, target in path_map.items():
        # One edge per branch; the condition re-runs the router and checks
        # whether IT picked this key. Only the matching edge passes.
        builder.add_edge(
            resolve(source),
            resolve(target),
            condition=lambda state, r=router, k=key: r(state) == k,
        )
```

So `add_conditional_edges("check", route, {"retry": "retry", "format": "format"})` becomes two guarded edges:

```python
check ──[ route(state) == "retry" ]──▶ retry
check ──[ route(state) == "format" ]──▶ format
```

When `check` finishes, the engine evaluates every outgoing edge's condition against the current state. Because the router is a pure function of the state, exactly one of `route(state) == "retry"` and `route(state) == "format"` is true — so exactly one target is activated. The `k=key` default-argument binding is the load-bearing detail: it captures each key by value in the closure, so all the lambdas don't accidentally share the last loop variable.

> **Why it works this way.** The underlying engine only knows about edges with optional conditions — the same guarded-edge machinery that a plain `add_edge` uses with no condition. "Conditional edges" are a builder-level convenience that expands into that primitive. Once you see the lowering, there is nothing magic left: a router is just shared code across a set of mutually-exclusive edge guards.

### A note on exclusivity

The contract is that the router returns *one* key, so *one* edge fires. If your router could logically pick several targets — genuine fan-out — that is a different construct (LangGraph's `Send` API / map-reduce), not a conditional edge. Conditional edges are for *choosing*, not for *splitting*. Keep the router total over its `path_map`: return a key that's always present, or you'll route to nowhere and stall the branch.

## Mental model

Think of a conditional edge as a `switch` statement compiled into wiring:

- The **router** is the `switch (expr)` — it computes the discriminant from state.
- The **`path_map`** is the `case` table — it maps each discriminant value to a destination.
- At runtime the engine evaluates the guard on every outgoing edge and fires the single match — like the `case` that matches falling through to its branch.

The difference from a real `switch` is that the branches are *nodes*, not code blocks, and the engine — not a program counter — is what advances to the chosen one at the next superstep.

That's forward branching. The moment one of those chosen targets loops back to an earlier node, the same guarded-edge mechanism produces a **cycle** — and a cycle plus a router that says "keep going or stop" is exactly the ReAct agent loop.

**Next in the series:** cycles and the agent loop — adding the back-edge that turns branching into iteration, and the recursion limit that keeps it from running forever.
