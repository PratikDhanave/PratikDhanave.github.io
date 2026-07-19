# State, Channels, and Reducers: How LangGraph Merges Updates
*The one idea that makes everything else in LangGraph click: nodes don't pass messages, they update a shared state — and reducers decide how.*

---

If you understand exactly one thing about LangGraph, make it this: a LangGraph app is a **shared state** that nodes read from and write to, and the framework merges each write using a per-field rule called a **reducer**. Nodes don't send payloads to each other; they return a partial update, and the engine folds that update into the running state. Once this mental model is in place, conditional edges, cycles, and the whole agent loop are just consequences.

## State is a typed dict of named channels

In LangGraph, the state is a `TypedDict`. Each field is a **channel** — a single named slot with its own update behavior. Here is the canonical shape:

```python
from typing import Annotated, TypedDict
from langgraph.graph import StateGraph, add_messages
import operator

class State(TypedDict):
    name: str
    messages: Annotated[list, add_messages]
    count: Annotated[int, operator.add]

graph = StateGraph(State)
```

Three channels, three different merge behaviors:

- `name` — a plain `str`, **no reducer**. Writes overwrite: last write wins.
- `messages` — `Annotated[list, add_messages]`. The `add_messages` reducer **appends**, so the channel accumulates a conversation.
- `count` — `Annotated[int, operator.add]`. The reducer is `operator.add`, so writes **sum**.

The `Annotated[T, reducer]` syntax is the key piece of vocabulary. Python's `Annotated` lets you attach metadata to a type without changing the type itself: `messages` is still just a `list` to a type checker, but LangGraph reads the second argument (`add_messages`) as "the function that merges this channel." No annotation means no reducer means overwrite.

## What a reducer actually is

The word "reducer" sounds heavier than the thing it names. Mechanically, a reducer is a two-argument function: it takes the channel's **existing** value and the **incoming** update, and returns the new value. That's the whole contract:

```python
Reducer = Callable[[Any, Any], Any]   # (old_value, new_value) -> merged_value
```

You can see the whole merge step in about 15 lines. A minimal `StateGraph` implementation keeps a dict mapping each channel to its reducer (or `None`), and applies it like this:

```python
def reduce(channels, state, update):
    # channels: {channel_name: reducer_fn_or_None}
    # state:    the current full state dict
    # update:   the partial dict a node just returned
    new_state = dict(state)                     # copy — never mutate under a node
    for key, value in update.items():
        reducer = channels.get(key)
        if reducer is None:
            new_state[key] = value              # no reducer: overwrite (last write wins)
        else:
            old = state.get(key)
            new_state[key] = reducer(old, value)  # reducer: combine old + new
    return new_state
```

That is the core idea in full. Every merge in LangGraph is this loop: for each key a node returned, either overwrite it or call the channel's reducer with `(old, new)`. Everything else — checkpointing, streaming, human-in-the-loop — is machinery around this one operation.

Note the copy on the first line. The function builds a **new** state dict rather than mutating the one the node was handed. That preserves the guarantee that a node's input never changes underneath it while it runs — important once nodes can run concurrently in the same superstep.

## Nodes return partial updates

A node is a function from the current state to a **partial update** — a dict containing only the channels it touched. It does not return the whole state:

```python
def agent(state: State) -> dict:
    reply = call_model(state["messages"])
    return {"messages": [reply], "count": 1}    # only the channels that changed

graph.add_node("agent", agent)
```

When `agent` returns `{"messages": [reply], "count": 1}`, the engine runs the merge loop above. `messages` has the `add_messages` reducer, so `[reply]` is appended to the existing list. `count` has `operator.add`, so `1` is added to the running total. Any channel the node didn't mention — `name`, here — is left exactly as it was. This is why nodes stay small and composable: each one declares only its own effect on the world, and the reducers handle integration.

## Watching overwrite vs. append

A tiny two-node graph makes the difference concrete. Given a state with an overwrite channel (`name`) and an append channel (`steps`):

```python
def greet(state):  return {"name": state["name"].title(), "steps": ["greeted"]}
def excite(state): return {"name": state["name"] + "!",    "steps": ["excited"]}
```

Running `greet` then `excite` starting from `{"name": "alice", "steps": []}`:

```
name:   "alice" -> "Alice"  -> "Alice!"          # overwritten twice
steps:  []      -> ["greeted"] -> ["greeted", "excited"]   # appended twice
```

Same nodes, same writes — the *channel's reducer* is the only thing that decides whether history accumulates or gets replaced. That's the whole lever LangGraph gives you over how state evolves.

## The canonical `add_messages` reducer

`add_messages` deserves a closer look because nearly every LangGraph agent uses it. It is LangGraph's built-in append reducer for a `messages` channel, and the real implementation does more than a raw list concatenation: it coerces dicts into message objects and, critically, **deduplicates by message ID** — if an update carries a message with an ID that already exists in the list, it replaces that message instead of appending a duplicate. That is what lets an agent update a streamed-in message in place.

The essence, though, is still just append. A minimal version captures the shape:

```python
def add_messages(existing, update):
    base = list(existing) if existing else []
    tail = update if isinstance(update, list) else [update]
    return base + tail
```

`Annotated[list, add_messages]` on the `messages` channel is what turns a bare list into a conversation buffer that grows across every node in the graph.

### Mental model

Think of the state as a spreadsheet row and each channel as a column with its own paste rule. Most columns use "paste over" (overwrite). A few columns use "paste-and-append" (`add_messages`) or "paste-and-sum" (`operator.add`). A node hands the framework a few cell values; the framework applies each column's paste rule to fold them in. Nodes never see or touch each other — they only ever read and write the shared row. That indirection is exactly what makes graphs with branches and loops tractable: there is one place state lives, and one rule per channel for how it changes.

## Why it works this way

Shared-state-plus-reducers is what makes **fan-in** and **cycles** sane. When two branches both write `messages`, you don't want the second to clobber the first — the `add_messages` reducer merges them. When an agent loops, each pass appends to the same `messages` channel and increments the same `count`, without any node needing to know how many times it has run. The reducer encodes the accumulation policy once, at the channel level, so every node — and every future node — inherits it for free.

Real LangGraph docs describe channels and reducers under the [low-level concepts](https://langchain-ai.github.io/langgraph/concepts/low_level/) and [graph API](https://langchain-ai.github.io/langgraph/concepts/) pages; `add_messages` and the `Annotated` syntax are covered there as well.

Next in the series: **Nodes and edges** — how those partial updates actually flow from one node to the next.
