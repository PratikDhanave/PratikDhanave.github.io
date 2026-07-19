# Cycles and the Agent Loop: Branch, Act, Loop Back

*The single most important pattern in LangGraph — a branch plus a back-edge, and the `recursion_limit` that keeps it from running forever.*

---

Every LangGraph agent tutorial you have ever read is the same three-line graph: enter the model, conditionally branch to tools, and loop the tools back to the model. That is not a coincidence or a starter template you outgrow — it *is* the ReAct agent. This post walks one full turn of that loop over the shared state, then explains `recursion_limit`: why a graph with a cycle needs a superstep cap, and how it differs from a hard safety ceiling.

## A branch plus a back-edge is a loop

By now the pieces are familiar from earlier in the series. An edge moves work from one node to the next. A **conditional edge** runs a router over the state and picks exactly one target. Put those together with an edge that points *backward* and you have a cycle:

```python
from langgraph.graph import StateGraph, START, END, add_messages
from typing import Annotated, TypedDict

class State(TypedDict):
    messages: Annotated[list, add_messages]

def should_continue(state: State) -> str:
    last = state["messages"][-1]
    return "continue" if last.tool_calls else "end"

graph = StateGraph(State)
graph.add_node("agent", call_model)      # the "think" step — invoke the LLM
graph.add_node("tools", run_tools)       # the "act" step — a ToolNode

graph.add_edge(START, "agent")
graph.add_conditional_edges(
    "agent",
    should_continue,
    {"continue": "tools", "end": END},   # branch: keep going, or finish
)
graph.add_edge("tools", "agent")         # the back-edge — this is the loop

app = graph.compile()
```

Three structural lines carry the whole idea: `add_edge(START, "agent")` sets the entry, `add_conditional_edges("agent", should_continue, {...})` is the branch, and `add_edge("tools", "agent")` is the back-edge that closes the cycle. The shape looks like this:

```
        START -> agent -> (should_continue?) --"continue"--> tools --+
                   ^                                                 |
                   +--------------- loop back ----------------------+
                             \--"end"--> END
```

## One turn of the loop, over the state

The important thing is that the cycle is not recursion in the call-stack sense — no node calls another node. Each hop is a **superstep**: the engine runs the active node, reduces its update into the shared state, then schedules whatever the edges point to next. Here is a full turn, channel by channel, for a "what's the weather in Paris?" question.

1. **`START -> agent`.** The `agent` node runs the model against `state["messages"]`. The model decides it needs a tool and returns an assistant message carrying `tool_calls`. Because `messages` uses the `add_messages` reducer, that message is *appended* to the history, not overwritten.

2. **Branch: `should_continue`.** The router reads the last message. It has `tool_calls`, so the router returns `"continue"`, and the `path_map` sends the state to `tools`. (Only one edge fires — the branch picks a single target.)

3. **`tools` runs.** The `ToolNode` executes each requested tool call (here, `get_weather("Paris")`) and returns the results as tool messages. Again these are appended to `messages` by the reducer. The state now holds: the human question, the assistant's tool-call message, and the tool results.

4. **Back-edge: `tools -> agent`.** The state — now richer by two messages — flows back into `agent`. The model runs again, this time *sees the tool output in its own context*, and produces a final natural-language answer with **no** `tool_calls`.

5. **Branch again, then END.** `should_continue` sees no tool calls on the last message and returns `"end"`. The state routes to `END`, which surfaces the final state as the result of `invoke`. The loop is over.

That is the entire ReAct pattern: *think → act → observe → think → answer*, expressed as supersteps over one growing `messages` channel. Every agent, no matter how many tools, is this loop with a bigger tool set and a smarter router.

> **Mental model.** The model never "keeps control" across a tool call. Each visit to `agent` is a fresh superstep that reads the whole conversation so far and adds to it. The loop is what gives the model another look at the board after the tools have moved — not a nested function call waiting on a return value.

### The minimal version, to demystify it

You can build the same loop over a ~30-line StateGraph with no LLM at all — a toy "agent" that must collect three facts, one tool call per turn:

```python
TARGET = 3

def agent(state: dict) -> dict:
    have = len(state.get("facts", []))
    return {"log": f"agent: have {have}/{TARGET} facts"}

def tools(state: dict) -> dict:
    n = len(state.get("facts", [])) + 1
    return {"facts": f"fact#{n}", "log": f"tools: fetched fact#{n}"}

def should_continue(state: dict) -> str:
    return "continue" if len(state.get("facts", [])) < TARGET else "end"

graph = StateGraph({"facts": add_messages, "log": add_messages})
graph.add_node("agent", agent)
graph.add_node("tools", tools)
graph.add_edge(START, "agent")
graph.add_conditional_edges("agent", should_continue,
                            {"continue": "tools", "end": END})
graph.add_edge("tools", "agent")           # the back-edge
```

Run it and `facts` fills to `["fact#1", "fact#2", "fact#3"]` over three trips through the loop, then the router returns `"end"`. Swap the toy `agent` for an LLM call and the toy `tools` for a real `ToolNode` and you have the production agent. Nothing else changes.

## `recursion_limit`: a runaway loop must terminate

A cycle raises an obvious danger: what if the router *never* returns `"end"`? A model that keeps proposing tool calls, or a router bug, would loop forever. LangGraph guards this with **`recursion_limit`** — a cap on the number of supersteps a single `invoke` may run. Exceed it and the run raises **`GraphRecursionError`** instead of hanging:

```python
try:
    result = app.invoke({"messages": [user_msg]}, {"recursion_limit": 25})
except GraphRecursionError:
    # the loop didn't converge within 25 supersteps — surface it, don't hang
    ...
```

The [LangGraph docs](https://langchain-ai.github.io/langgraph/concepts/low_level/) frame this as counting supersteps, not stack frames — because, as we saw, the loop isn't recursion. The mechanism is small enough to state in full. A minimal engine's run loop looks like:

```python
while state.pending:
    if max_supersteps is not None and steps_run >= max_supersteps:
        state.status = "suspended"      # bounded on purpose -> caller decides
        return
    if max_supersteps is None and steps_run >= SAFETY_CEILING:
        raise RuntimeError("exceeded safety ceiling — likely an unbounded cycle")
    steps_run += 1
    run_superstep(state)
```

Two distinct guards live here, and the difference matters:

- **`recursion_limit`** is *your* deliberate bound, passed per run. When the run hits it before reaching `END`, that is a real condition — the agent didn't converge in the budget you gave it — and it surfaces as `GraphRecursionError`. Catching it lets you fall back, ask for clarification, or fail loudly rather than silently spin.
- **The hard safety ceiling** (a very large fixed number, e.g. 10,000 supersteps) is a last-resort backstop that fires only when you *didn't* set a limit at all. It exists so a forgotten `recursion_limit` on a buggy graph fails fast instead of pinning a CPU. You should never rely on it; it is the smoke detector, not the thermostat.

So the same cycle that makes agents possible is exactly the cycle that could hang your process — and `recursion_limit` is the one line that turns "hang" into "clear, catchable error." That is why this loop, with its cap, is the single most important pattern in the whole framework: master `START -> agent -> branch -> tools -> back to agent`, and bound it with `recursion_limit`, and you understand the mechanism behind every LangGraph agent.

**Next in the series:** the `Command` object — how a node can return a state update *and* a `goto` in one move, collapsing the branch into the node itself.
