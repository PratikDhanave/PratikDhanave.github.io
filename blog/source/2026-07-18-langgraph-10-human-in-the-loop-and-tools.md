# Human-in-the-Loop, Tools, and the Send API

*The higher-level building blocks LangGraph stacks on top of the graph engine — pausing for a human, running an agent loop, calling tools, and fanning out dynamically.*

---

By now the series has covered the whole engine: `StateGraph`, channels and reducers, conditional edges, cycles, streaming, `Command`, and checkpointing. This post covers the *ergonomic* layer on top — the pieces you reach for when building an agent: human-in-the-loop with `interrupt()`, the prebuilt ReAct agent and `ToolNode`, tools, and the `Send` API for dynamic fan-out. Each is built from primitives you have already seen.

## 1. Human-in-the-loop: `interrupt()`

A long-running graph often needs to stop and ask a person something — approve a transaction, confirm a destructive tool call, or fill in a missing value. LangGraph's [`interrupt()`](https://langchain-ai.github.io/langgraph/concepts/human_in_the_loop/) does exactly that: it pauses the graph mid-node, surfaces a payload to the caller, and — because the run is checkpointed — the entire state is durably saved. Later you resume by re-invoking with a `Command(resume=...)`, and execution picks up *inside the same node* with the human's answer as the return value of `interrupt()`.

```python
from langgraph.graph import StateGraph, START, END
from langgraph.types import interrupt, Command
from langgraph.checkpoint.memory import MemorySaver
from typing import TypedDict

class State(TypedDict):
    draft: str
    approved: bool

def review(state: State) -> dict:
    # Pauses here. The value below is shown to the caller.
    decision = interrupt({"question": "Approve this draft?", "draft": state["draft"]})
    return {"approved": decision == "yes"}

graph = StateGraph(State)
graph.add_node("review", review)
graph.add_edge(START, "review")
graph.add_edge("review", END)
app = graph.compile(checkpointer=MemorySaver())

cfg = {"configurable": {"thread_id": "t1"}}
first = app.invoke({"draft": "ship it", "approved": False}, cfg)
# first["__interrupt__"] carries the payload — the graph is now paused.

resumed = app.invoke(Command(resume="yes"), cfg)   # picks up inside review()
# resumed == {"draft": "ship it", "approved": True}
```

The critical detail: `interrupt()` **requires a checkpointer**. Without one there is nowhere to durably park the state, so the resume half of the round-trip has nothing to restore. This is why the previous post on checkpointing was a prerequisite — HITL is checkpointing plus a "wait for the outside world" signal.

In a minimal StateGraph the same effect is a request-info node that emits a human request and suspends the run; the reply is fed back at resume as a `{request_id: response}` mapping, and the node's downstream edge branches on it. `interrupt()` is the sugar; "save state, emit a request, resume with the reply" is the mechanism.

> **Mental model.** `interrupt()` is a `yield` that survives process restarts. The graph is a coroutine; the checkpointer is what lets that coroutine be frozen to JSON and thawed hours later on another machine.

## 2. Prebuilt ReAct agent + `ToolNode`

You rarely hand-wire the agent graph. LangGraph ships [`create_react_agent`](https://langchain-ai.github.io/langgraph/reference/prebuilt/), which builds the canonical two-node loop for you: a model node that decides what to do, and a tool node that executes whatever the model asked for.

```python
from langgraph.prebuilt import create_react_agent

def get_weather(city: str) -> str:
    """Return the weather for a city."""
    return f"It's sunny in {city}."

agent = create_react_agent(model="anthropic:claude-opus-4-20250514",
                           tools=[get_weather])

result = agent.invoke({"messages": [("user", "What's the weather in Pune?")]})
print(result["messages"][-1].content)
```

Under the hood this is a `StateGraph` whose state is `{"messages": Annotated[list, add_messages]}` (the append-reducer from earlier in the series). It wires an `agent` node (the model) to a `ToolNode`, with a **conditional edge** that inspects the last message: if the model emitted tool calls, route to the tools node; otherwise route to `END`. The tools node loops back to the model. That loop-until-no-tool-calls is the entire ReAct pattern in graph terms you already know.

`ToolNode` is worth naming on its own: it is the node that *executes* the tool calls the model requested. It reads the `tool_calls` on the last AI message, runs each matching function, and appends a `ToolMessage` per call back onto `messages` — which, thanks to `add_messages`, accumulates rather than overwrites.

## 3. Tools

A **tool** is just a Python function the model is allowed to call. You bind functions and LangChain derives a JSON schema from the signature and docstring — parameter names, type hints, and the docstring become the tool's `name`, `args_schema`, and `description` that the model sees.

```python
from langchain_core.tools import tool

@tool
def search(query: str, limit: int = 5) -> list[str]:
    """Search the knowledge base and return up to `limit` snippets."""
    ...
```

The tool-loop is only four steps: **call the model → it returns tool calls → execute them → feed the results back as messages → repeat until the model answers with no tool calls.** A from-scratch agent is exactly this `while` loop over a chat client and a `{name: function}` registry; `create_react_agent` and `ToolNode` are that loop reshaped as a graph so it composes with checkpointing, streaming, and interrupts for free. The schema-from-signature trick is the only "magic," and it is plain reflection over the function's annotations.

## 4. The `Send` API — dynamic fan-out

The edges you have seen so far are *static*: you know the successors at build time. But sometimes the number of parallel branches depends on the data — split a document into an unknown number of sections and summarize each in parallel. That is a **map step**, and static edges can't express it. LangGraph's [`Send`](https://langchain-ai.github.io/langgraph/concepts/low_level/#send) solves it: a conditional edge returns a *list* of `Send(node_name, state)` objects, and the runtime dispatches one parallel copy of that node per item — each with its own private slice of state.

```python
from langgraph.types import Send

def fan_out(state):
    # Dispatch one "summarize" run per section — count known only at runtime.
    return [Send("summarize", {"section": s}) for s in state["sections"]]

graph.add_conditional_edges("split", fan_out, ["summarize"])
```

The fan-*in* half uses machinery from post 2: each `summarize` copy returns an update to a channel whose **reducer** appends, so the N independent results merge back into one list automatically. That is the whole map-reduce: `Send` is the map (dynamic dispatch of N node-runs), and a reducer channel is the reduce (deterministic merge of the results). No aggregator node to hand-write — the channel does the joining.

> **Why it works this way.** `Send` decouples *which* node runs from *what state* it runs on. A normal edge carries the whole shared state forward; a `Send` carries a hand-built payload to a named node. That is what makes data-dependent parallelism expressible without knowing N in advance.

## Where this leaves us

None of these four are new engine capabilities — they are compositions of primitives from earlier posts. `interrupt()` is checkpointing plus a suspend signal. `create_react_agent` is a two-node graph with a conditional edge and an `add_messages` reducer. Tools are functions with a reflected schema. `Send` is a dynamic conditional edge whose results fan back through a reducer channel. Once the engine is solid, the agent framework on top is a thin, readable layer.

Next in the series: the final post ties the engine together and looks at what LangGraph deliberately leaves to its surrounding ecosystem.
