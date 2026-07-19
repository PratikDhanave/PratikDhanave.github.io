# Edges, START, END, and compile(): Wiring and Running a Graph
*How the four smallest pieces of the LangGraph API turn a bag of nodes into a program you can run.*

---

In the last few posts we built up state, channels, reducers, and nodes. But a pile of nodes does nothing on its own — you have to say what runs first, what runs next, and where the run stops. That wiring is done with **edges** and two sentinels, `START` and `END`; then `compile()` freezes the wiring into a runnable object and `invoke()` runs it to completion. This post walks the full lifecycle of a tiny two-node graph, end to end.

## Unconditional edges

An **edge** is a directed connection `source → target`. The unconditional form is the simplest thing in the whole API:

```python
graph.add_edge("greet", "shout")
```

That reads "after `greet` finishes, run `shout`." No condition, no branching — whenever `greet` runs, `shout` runs next with the updated state. (Branching is a separate call, `add_conditional_edges`, which is the next post.)

There is nothing magical here. In a minimal StateGraph implementation, `add_edge` just appends a `(source, target)` tuple to a list that `compile()` later reads. The whole point of the graph builder is to record your intent as plain data now and lower it into an executable structure later.

## START and END: the two sentinels

You still need to say *where the run begins* and *where it ends*. LangGraph uses two special sentinel node names for this:

```python
from langgraph.graph import START, END
```

`START` is the virtual entry sentinel. Drawing an edge **from** `START` sets the entry point — the first real node to run:

```python
graph.add_edge(START, "greet")   # entry point: greet runs first
```

`END` is the virtual terminal sentinel. Drawing an edge **to** `END` marks the end of a path: when routing reaches `END`, the run finishes and the current state becomes the result:

```python
graph.add_edge("shout", END)     # after shout, we're done
```

Neither `START` nor `END` is a node you write. They aren't functions and never see the state; they're markers the compiler understands. Under the hood `START` is just a reserved string like `"__start__"` and `END` is `"__end__"`. Edges from `START` don't add a node to run — they record the entry point. An edge to `END` maps to a tiny terminal node whose only job is to surface the final state as the run's output.

### Entry point / set_entry_point

`add_edge(START, n)` is the idiomatic way to set the entry, but there's an explicit alias:

```python
graph.set_entry_point("greet")   # exactly the same as add_edge(START, "greet")
```

They do the identical thing — one records the entry point via an edge, the other sets it directly. Use whichever reads more clearly. What matters is that **a graph must have an entry point**; compiling one without it is an error, because the engine wouldn't know which node to activate first.

## compile(): freezing the builder

Everything so far mutated a *builder*. `compile()` takes that builder and freezes it into a runnable graph:

```python
app = graph.compile()
```

This is a real phase transition, not a formality. Compilation validates the wiring (entry point exists, edges reference real nodes) and lowers the recorded nodes and edges onto the underlying execution engine. After compile, the builder's shape is fixed — you get back a `CompiledStateGraph`, a separate object you can run repeatedly. In a minimal implementation, `compile()` is where each recorded node becomes an executor, each `(source, target)` tuple becomes a real edge, and the entry point and `END` node are resolved:

```python
def compile(self):
    if self._entry is None:
        raise ValueError("no entry point set — call set_entry_point(...) "
                         "or add_edge(START, ...)")
    nodes = {name: make_executor(name, fn) for name, fn in self._nodes.items()}
    # ... build edges, wire START (entry) and END (terminal) ...
    return CompiledStateGraph(build(...))
```

The build-then-compile split is the same discipline you see in a database preparing a query or a regex engine compiling a pattern: you describe the thing once, pay the wiring cost once, then execute many times.

## invoke(): running to END

`invoke()` runs the compiled graph from the entry point, following edges superstep by superstep until routing reaches `END`, and returns the **final state dict**:

```python
final = app.invoke({"name": "ada"})
```

You pass in the initial state; you get back the state after every node that ran has merged its updates through the channel reducers. That returned dict is the whole result of the run.

## The full lifecycle, end to end

Here is a complete two-node graph in real LangGraph — build, add edges, compile, invoke:

```python
from typing import TypedDict
from langgraph.graph import StateGraph, START, END

class State(TypedDict):
    name: str
    greeting: str

def greet(state: State) -> dict:
    return {"greeting": f"hello, {state['name']}"}

def shout(state: State) -> dict:
    return {"greeting": state["greeting"].upper()}

builder = StateGraph(State)
builder.add_node("greet", greet)          # register nodes
builder.add_node("shout", shout)

builder.add_edge(START, "greet")          # entry point
builder.add_edge("greet", "shout")        # greet → shout
builder.add_edge("shout", END)            # shout → done

app = builder.compile()                   # freeze into a runnable graph
final = app.invoke({"name": "ada"})       # run to END
print(final)   # {'name': 'ada', 'greeting': 'HELLO, ADA'}
```

Trace it: `invoke` seeds the state with `{"name": "ada"}` and activates `greet` (the entry). `greet` returns a partial update `{"greeting": "hello, ada"}`, which merges into the state. The edge `greet → shout` fires, so `shout` runs on the merged state and returns `{"greeting": "HELLO, ADA"}`. The edge `shout → END` routes to the terminal, so the run finishes and the final state is returned. The same graph shape works identically against a minimal StateGraph — same `add_edge`, `START`, `END`, `compile`, `invoke` calls — because these four pieces are the irreducible core of the API.

### Mental model: sync API, async engine

LangGraph's `app.invoke(...)` is **synchronous** — you call it and get the final state back. But the engine underneath is typically **async**: nodes are dispatched concurrently within a superstep and the runner awaits them at a barrier before advancing. `invoke` is the blocking front door over that asynchronous machinery (LangGraph also exposes `ainvoke` when you want to await it directly). A from-scratch StateGraph makes this explicit — its `invoke` is a coroutine you `await` — but the model is the same: `invoke` means "run this graph to `END` and hand me the final state," and everything about how the supersteps are scheduled is an implementation detail below that line.

Four calls — `add_edge`, `START`, `END`, `compile` — plus `invoke` are enough to turn any set of nodes into a program. Everything else in LangGraph is a richer way to decide *which* edge fires.

Next in the series: **conditional edges** — routing to different nodes at runtime based on the state.
