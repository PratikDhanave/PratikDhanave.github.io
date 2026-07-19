# LangGraph Is a Pregel Program: Shared State vs Message Passing

*The foundational mental model — why "the graph" is a Pregel program, and how shared state differs from message passing.*

---

Before you learn a single LangGraph API call, you need one mental model: **the graph you build is a Pregel program**. Nodes don't call each other. They take turns. Work advances in discrete rounds, and between every round the whole system stops at a barrier and synchronizes. Everything else in LangGraph — reducers, conditional edges, cycles, `recursion_limit` — is a consequence of that engine. Get this right and the rest of the series is vocabulary.

This first post does two things: contrasts **shared-state** (LangGraph's data model) with **message-passing** (the model a lot of other agent frameworks use), and explains the **Pregel / Bulk-Synchronous-Parallel (BSP)** engine both descend from.

## Two data models: what flows through the graph

The single most important distinction is *what moves between nodes*.

In a **message-passing** framework, a node emits a payload and the engine routes that payload along an edge to the next node. The node chooses what to send; the value on the wire is whatever it decided to emit. Fan-in is explicit — you write an aggregator that collects payloads and merges them.

```python
# Message-passing style: a node emits a payload onto an edge.
class Upper(Executor):
    @handler
    async def handle(self, text: str, ctx) -> None:
        await ctx.send_message(text.upper())   # emit a value; the engine routes it
```

In **shared-state** — LangGraph's model — there is one **state** object that every node reads in full. A node does *not* emit a payload. It returns a **partial update**: a dict naming only the channels it changed. The framework merges that update back into the shared state using per-channel **reducers**, and the next node sees the merged result.

```python
# Shared-state style: a node reads the whole state, returns only what changed.
def upper(state: dict) -> dict:
    return {"text": state["text"].upper()}     # a partial update, not a payload
```

Here is the difference in one table:

| | Message-passing | Shared-state (LangGraph) |
|---|---|---|
| What flows on an edge | a payload you choose | the whole state |
| A node returns | a message it emits | a partial update dict `{channel: value}` |
| How results combine | you route/merge explicitly | reducers merge each channel automatically |
| Fan-in | an aggregator node | a reducer on a channel |

### State, channels, reducers

In real LangGraph you declare the state as a `TypedDict`, and you attach a reducer to a channel with `Annotated`:

```python
from typing import Annotated, TypedDict
from langgraph.graph import StateGraph, add_messages
import operator

class State(TypedDict):
    name: str                                   # no reducer: last write wins (overwrite)
    messages: Annotated[list, add_messages]     # append: accumulate a conversation
    count: Annotated[int, operator.add]         # sum: numeric accumulation

graph = StateGraph(State)
```

A channel with **no reducer** is *overwritten* — the last node to write it wins. A channel **with a reducer** *combines* the old value and the update: `add_messages` appends, `operator.add` sums. That's the whole rule.

To demystify it, here's the merge a minimal StateGraph performs, in about six lines. Real LangGraph does more (typing, validation, versioned channels), but the essence is exactly this:

```python
def reduce(channels, state, update):
    new_state = dict(state)                     # copy — never mutate under a node
    for key, value in update.items():
        reducer = channels.get(key)
        if reducer is None:
            new_state[key] = value              # overwrite
        else:
            new_state[key] = reducer(state.get(key), value)  # combine
    return new_state
```

Note the copy. The old state a node was invoked with is never altered underneath it. That's not an optimization detail — it's a promise the execution model makes, and to see *why* it matters, we have to talk about supersteps.

## The engine underneath: Pregel and BSP

Both models above run on the same engine. LangGraph's runtime descends from **Google's Pregel**, which is an implementation of the **Bulk-Synchronous-Parallel (BSP)** model of computation. LangGraph names its core runtime `Pregel` for exactly this reason; the [conceptual docs](https://langchain-ai.github.io/langgraph/concepts/low_level/) describe execution in terms of Pregel supersteps.

BSP advances computation in discrete rounds called **supersteps**. One superstep is:

1. **Compute** — every currently-active node runs, concurrently. Each reads the state as it was at the *start* of the step and produces its update. No node sees another node's in-progress work.
2. **Barrier** — the engine waits for *all* active nodes to finish. Nothing proceeds until the slowest one is done.
3. **Route** — the updates are applied (reduced into the state), and the engine figures out which nodes are active for the *next* superstep, based on the edges.

Then it ticks again. The loop is, in essence:

```python
while active_nodes:                 # keep going while any node is scheduled
    results = run_all(active_nodes) # 1. compute — concurrently
    # 2. barrier: run_all only returns once every node has finished
    state = apply(results)          # 3. route: reduce updates, pick next nodes
    active_nodes = next_step(state)
```

That barrier is the reason shared state is safe. Because every node in a superstep reads the *same* immutable snapshot and its update isn't applied until the barrier, there's no read-write race between nodes running in the same step — even when they run in parallel. Determinism comes for free.

> **Mental model.** Think of it like turns in a board game rather than a phone call. In a phone call (message passing), whoever's talking hands the conversation directly to someone else. In a turn-based game (BSP), *everyone* who's active this turn moves at once, then the board is updated, then the next turn begins. "The graph" is the rulebook for whose turn is next; the state is the board.

This is also why LangGraph has a `recursion_limit` rather than a stack limit. A cycle in the graph — the agent loop, `agent → tools → agent` — isn't recursion in the call-stack sense. It's just supersteps that keep scheduling the same nodes. The limit caps the number of supersteps so a runaway loop becomes a clean `GraphRecursionError` instead of a hang. We'll build exactly that loop later in the series.

## Why this framing pays off

Once you see the graph as a Pregel program, the rest of LangGraph stops being a grab-bag of features and becomes a set of answers to one question — *what happens at each superstep?*

- **Reducers** answer: how do this step's updates merge into the state?
- **Edges / conditional edges** answer: which nodes are active next step?
- **Cycles** answer: nothing special — a back-edge just schedules a node again.
- **Checkpointers** answer: save the state at a superstep boundary so you can pause and resume.
- **Streaming** answer: emit the state (or the per-node delta) after each step.

Every one of those is "a thing that happens at a barrier." That's the payoff of the mental model: you're not memorizing an API, you're reading a Pregel program.

**Next in the series:** we go deep on state, channels, and reducers — the `{channel: reducer}` contract that turns partial updates into shared state.
