# Nodes: Functions That Read State and Return Partial Updates

*A LangGraph node is just a function — it reads the whole state and returns only the channels it changed.*

---

In the previous post we defined the graph's *state*: a set of named channels, each with a reducer that decides how updates merge. This post is about the thing that actually produces those updates — the **node**. If state is the shared blackboard, a node is a worker who reads the whole board and writes only the cells it cares about. Everything else about LangGraph — edges, branching, the agent loop — is just plumbing that decides *which* node runs *when*.

## What a node is

A node is a plain function (sync or async) with one signature: it takes the current state and returns a **partial update** — a dict of only the channels it changed.

```python
def agent(state: State) -> dict:
    return {"messages": [llm.invoke(state["messages"])]}
```

That's the whole contract. You register it on the graph with a name:

```python
from langgraph.graph import StateGraph

graph = StateGraph(State)
graph.add_node("agent", agent)
```

The name is how edges refer to the node (`add_edge("agent", "tools")`). The function is what runs when control reaches that name. Node functions can be `async def` too — LangGraph awaits them — which matters the moment you call a real model or hit a network tool.

## Return only what you changed

The most important habit: **return only the channels you touched**, not the whole state.

```python
def summarize(state: State) -> dict:
    return {"summary": state["draft"][:280]}   # not: {**state, "summary": ...}
```

Two reasons this is idiomatic, not just terse:

1. **Reducers need the delta, not the total.** A channel like `messages` uses an append reducer (`add_messages`). If you return the *whole* accumulated list, the reducer appends it to itself and you get duplicates. Returning just the new message lets the reducer do its one job — merge old + new — correctly.
2. **It documents intent.** The return value is an exact statement of this node's side effects. A reader sees `{"summary": ...}` and knows nothing else moved.

Returning `{}` — or `None` — means "I changed nothing." That's a completely valid node: a logging node, a guard that only inspects state, or a branch that defers all its work to a conditional edge. The framework merges an empty update into a state that comes out unchanged.

```python
def observe(state: State) -> dict:
    logger.info("turn %d", len(state["messages"]))
    return {}   # no channels changed
```

## The immutable-snapshot guarantee

Here is the part that makes nodes safe to reason about. When a node runs, it is handed a **snapshot** of the state. It does not mutate that snapshot in place — it *returns* an update, and the framework produces a **new** state by running each returned channel through its reducer.

This is Bulk Synchronous Parallel (BSP) discipline, the model LangGraph inherits from Pregel: within a step, there is no shared mutable state to race on. A node reads a fixed input; its output is merged after it returns. Even if two nodes run in the same superstep, neither sees the other's half-finished writes — they each get the state as it was at the start of the step, and the reducers combine their updates deterministically at the barrier.

The merge is a copy, not a mutation. Conceptually:

```python
def reduce(channels, state, update):
    new_state = dict(state)                 # copy — never touch the old one
    for key, value in update.items():
        reducer = channels.get(key)
        if reducer is None:
            new_state[key] = value                       # overwrite channel
        else:
            new_state[key] = reducer(state.get(key), value)  # reduced channel
    return new_state
```

Because the old state is copied rather than edited, the input a node was invoked with is never altered under it. That's why a node can be a pure function of its input — and why you can retry it, checkpoint before it, or run it in parallel without fear.

> **Mental model.** Think of each superstep as a database transaction. Nodes read a consistent snapshot; their updates are staged; the reducers "commit" them into a new snapshot at the barrier. Nobody reads dirty writes.

## Two real nodes

An **agent node** calls the model and appends its reply. With an `add_messages` reducer on the `messages` channel, returning a one-element list is enough — the reducer appends it:

```python
from langgraph.graph import StateGraph, add_messages
from typing import Annotated, TypedDict

class State(TypedDict):
    messages: Annotated[list, add_messages]

def agent(state: State) -> dict:
    reply = llm.invoke(state["messages"])     # an AIMessage, maybe with tool calls
    return {"messages": [reply]}              # reducer appends it to the history
```

A **tool node** reads the last message, runs whatever tools the model asked for, and appends the results:

```python
def tools(state: State) -> dict:
    last = state["messages"][-1]
    outputs = []
    for call in last.tool_calls:
        result = TOOLS[call["name"]].invoke(call["args"])
        outputs.append(ToolMessage(result, tool_call_id=call["id"]))
    return {"messages": outputs}              # append all tool results at once
```

Neither node knows what runs next. `agent` doesn't call `tools`; it just leaves a state with tool calls in it, and a conditional edge (a later post) decides whether to route to `tools` or to `END`. That separation — nodes do work, edges decide flow — is what lets the same two functions form a linear pipeline *or* a cyclic agent loop with no change to their bodies.

## The ~10-line executor that turns a function into a node

How does a plain function become something the engine can schedule? A thin wrapper. Under the hood each node is an executor whose whole job is: call your function, normalize its return, reduce it into a fresh state, and forward that state to the next step.

```python
class StateNode:
    def __init__(self, name, fn, channels):
        self.name, self.fn, self.channels = name, fn, channels

    async def run(self, state, ctx):
        result = self.fn(state)
        if inspect.isawaitable(result):        # support async node functions
            result = await result
        update = result or {}                  # None / {} → no-op update
        new_state = reduce(self.channels, state, update)
        await ctx.send(new_state)              # hand the new state to the next node
```

That is the entire bridge between "a function you wrote" and "a node the graph runs." (A node may also return a `Command` to combine an update with a control-flow jump — we'll unpack that when we get to branching.) Everything else — supersteps, the barrier, edge routing — is the same engine underneath. Seeing how little the wrapper does is the moment `add_node("agent", agent)` stops being magic: you're registering a function, and the framework snapshots the state, calls it, and reduces the result.

## Why it works this way

The partial-update-plus-reducer design is what makes LangGraph composable. Because a node only declares deltas and never mutates shared state, the framework — not you — owns *when* updates apply and *how* they merge. That's what buys you deterministic parallelism, clean checkpointing, and the ability to swap a node's routing (linear vs. cyclic) without rewriting the node. See the official [LangGraph concepts overview](https://langchain-ai.github.io/langgraph/concepts/low_level/) for the reference definitions of nodes, state, and reducers.

Next in the series: **Edges** — how a node's output actually reaches the next node, and how `START`/`END` bookend the flow.
