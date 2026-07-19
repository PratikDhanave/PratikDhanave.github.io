# Command: Update State and Pick the Next Node in One Return

*How a single `Command` object folds a state update and a routing decision together — and the tiny lowering that makes `goto` just another guarded edge.*

---

So far in this series, a node did one job: return a partial state update, and let the graph's edges decide where to go next. `Command` collapses those two jobs into one return value. A node returns `Command(update={...}, goto="next_node")` — it mutates the state **and** names its own successor, atomically, from inside the node body. This post shows when that's the right tool, what LangGraph asks of you in exchange, and how `goto` is implemented as ordinary edge machinery underneath.

## The two ways to route

LangGraph gives you two mechanisms for dynamic control flow. The older one is the **conditional edge**: you attach a router function to a node, and after the node runs, the framework calls the router with the resulting state to pick the destination.

```python
from typing import Annotated, TypedDict
from langgraph.graph import StateGraph, START, END, add_messages

class State(TypedDict):
    messages: Annotated[list, add_messages]
    tier: str

def classify(state: State) -> dict:
    return {"tier": "gold" if is_vip(state) else "standard"}

def route(state: State) -> str:          # a separate router
    return state["tier"]

builder = StateGraph(State)
builder.add_node("classify", classify)
builder.add_conditional_edges("classify", route, {"gold": "gold", "standard": "standard"})
```

Here the routing *decision* (`tier`) is computed in `classify`, stashed in state, then re-read by `route`. The logic is split across two functions and the decision has to survive a round-trip through the state dict.

`Command` lets the node that made the decision act on it directly:

```python
from langgraph.types import Command
from typing import Literal

def classify(state: State) -> Command[Literal["gold", "standard"]]:
    tier = "gold" if is_vip(state) else "standard"
    return Command(
        update={"tier": tier, "messages": [("system", f"classified as {tier}")]},
        goto=tier,          # route to "gold" or "standard"
    )

builder.add_node("classify", classify)   # no conditional edge needed
```

One function. No router. No intermediate channel whose only purpose is to carry a decision to a router that recomputes what the node already knew.

## When `Command` beats a conditional edge

Reach for `Command` when:

- **The routing decision and the state update are the same computation.** If a node already knows where to go because of work it just did (an LLM tool call, a validation result, a classification), threading that through a separate router is redundant.
- **You're doing multi-agent handoffs.** A supervisor deciding which worker runs next, or one agent handing control to another, is naturally a `goto`. This is the canonical `Command` use case in LangGraph's multi-agent guides.
- **You want to update state *across* a hierarchy on the way out.** In subgraphs, `Command(graph=Command.PARENT, goto=...)` can route to a node in the parent graph — something conditional edges can't express.

Stick with conditional edges when routing is a pure function of state that several nodes share, or when you want the branching logic visible and separate from node bodies. Neither is "better"; `Command` trades a little locality of control for less plumbing.

## The one requirement: declare your targets

Because `goto` is chosen at runtime, the graph compiler can't statically see where a `Command` node might send control. LangGraph asks you to declare the possible targets so the graph topology (and its diagram, and its validation) stays complete. In modern LangGraph that's the return annotation `Command[Literal["gold", "standard"]]`; you can also pass it explicitly. In a minimal StateGraph you can make this an argument on `add_node`:

```python
g.add_node("classify", classify, ends=["gold", "standard"])
g.add_node("gold", gold, ends=[END])
g.add_node("standard", standard, ends=[END])
```

`ends` is the list of nodes this node's `goto` is allowed to reach (including `END`). If you `goto` somewhere you didn't declare, that's a graph-construction error, not a mysterious runtime dead end.

## How `goto` is lowered

Here's the satisfying part: `Command.goto` is not a new execution primitive. It's conditional edges in disguise. A ~30-line StateGraph makes the trick obvious.

When a node returns a `Command`, the runner splits it into the update and the target, reduces the update into the state exactly as it would for a plain dict, and then **tags a private routing channel** with the chosen target:

```python
_GOTO = "__goto__"     # a private channel, hidden from the caller

# inside the node runner:
if isinstance(result, Command):
    update, goto = result.update or {}, result.goto
else:
    update, goto = result or {}, None

new_state = _reduce(channels, state, update)   # normal reduction
if goto is not None:
    new_state[_GOTO] = goto                    # stamp the chosen target
```

Then, at **compile** time, for each declared target the compiler emits one ordinary edge guarded by a condition that checks the private channel:

```python
for source, targets in command_ends.items():
    for target in targets:
        builder.add_edge(
            source, target,
            condition=lambda state, t=target: state.get(_GOTO) == t,
        )
```

So `add_node("classify", classify, ends=["gold", "standard"])` compiles into two guarded edges: `classify → gold` fires only when `__goto__ == "gold"`, and `classify → standard` fires only when `__goto__ == "standard"`. The node "picks" a successor simply by writing a value that exactly one edge's guard is watching for. The private channel is stripped before the final state is returned, so callers never see `__goto__`.

**Why it works this way:** conditional edges are already the general mechanism for "look at state, choose an edge." `Command.goto` is just the same mechanism keyed on a reserved channel that the node itself writes, instead of an external router reading application state. Same runtime, less ceremony — which is exactly why a from-scratch replica needs almost no new code to support it.

## A real handoff: supervisor routing to workers

The pattern that makes `Command` shine is a supervisor dispatching to one of several workers:

```python
from langgraph.types import Command
from typing import Literal

def supervisor(state: State) -> Command[Literal["researcher", "writer", END]]:
    decision = pick_next_worker(state)     # e.g. an LLM returns "researcher"
    if decision == "done":
        return Command(goto=END)
    return Command(
        update={"messages": [("system", f"routing to {decision}")]},
        goto=decision,
    )

def researcher(state: State) -> Command[Literal["supervisor"]]:
    return Command(update={"messages": do_research(state)}, goto="supervisor")

def writer(state: State) -> Command[Literal["supervisor"]]:
    return Command(update={"messages": draft(state)}, goto="supervisor")
```

Each worker hands control *back* to the supervisor with `goto="supervisor"`, and the supervisor loops until it decides to `goto=END`. The entire control graph — dispatch, work, return, terminate — lives inside the node functions as data. No conditional-edge wiring is needed beyond `add_edge(START, "supervisor")`, because every hop is a `Command`. That's the shape of most LangGraph multi-agent systems.

## Mental model

Think of `goto` as the node writing a single word onto a hidden slip of paper, and the graph having pre-posted one guard per possible word. The node doesn't "call" the next node; it names it, and the machinery you already have — reducers plus guarded edges — carries the flow. `Command` is a convenience layer over conditional edges, not a parallel universe. Understanding that keeps its behavior predictable: an update reduces like any update, and a `goto` fires like any conditional edge. See the official [LangGraph low-level concepts](https://langchain-ai.github.io/langgraph/concepts/low_level/) and [multi-agent](https://langchain-ai.github.io/langgraph/concepts/multi_agent/) guides for the full `Command` API.

---

**Next in the series:** streaming — how `stream(mode="values" | "updates")` turns each node step into an observable event without changing a line of node code.
