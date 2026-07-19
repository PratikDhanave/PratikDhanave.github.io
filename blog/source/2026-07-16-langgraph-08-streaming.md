# Streaming: values, updates, and debug Modes

*Watching a LangGraph run happen — the three things `.stream()` can show you, and why they fall out of the superstep model for free.*

---

`.invoke()` runs a graph to completion and hands you the final state. That's fine for a batch job, but useless for a UI that wants a progress bar, or a log that needs to show exactly what each step changed, or a trace when something goes wrong mid-run. LangGraph's answer is `.stream(input, stream_mode=...)`: same execution, but you observe it as it happens. This post walks the three core modes — `"values"`, `"updates"`, and `"debug"` — and shows why streaming is almost an afterthought once you understand how the graph steps.

## The one API, three views

```python
from langgraph.graph import StateGraph, START, END
from typing_extensions import TypedDict

class State(TypedDict):
    user: str
    answer: str

# ... build and compile as usual ...
app = graph.compile()

async for chunk in app.astream({"user": "alice"}, stream_mode="updates"):
    print(chunk)
```

The graph runs identically no matter which mode you pass. What changes is the *shape* of each chunk the stream yields. All three modes see the same underlying sequence of node executions; they just project it differently.

### `"values"` — the full state after each step

Each chunk is the entire accumulated state after a node has run and its update has been merged in. Because state accumulates, you see it grow: after node A the state has A's contribution, after node B it has A's *and* B's, and so on.

```python
async for state in app.astream(inputs, stream_mode="values"):
    render_progress(state)   # each chunk is the whole, current state dict
```

This is what you want behind a progress UI. You always have a complete, renderable snapshot — no need to stitch deltas together yourself. The tradeoff is verbosity: if the state is large, you re-receive all of it on every step.

### `"updates"` — what each node changed

Each chunk is `{node_name: partial_update}` — only the keys that *this* node returned, not the merged whole. This is the mode you reach for when logging or debugging behavior, because it answers the precise question "what did this node do?"

```python
async for chunk in app.astream(inputs, stream_mode="updates"):
    for node_name, update in chunk.items():
        log.info("node %s produced %r", node_name, update)
```

Note the difference from `"values"`: `updates` gives you the node's raw return value keyed by node name; `values` gives you the state *after* that return has been folded in by the channel reducers (see the earlier post on reducers). If a node returns `{"log": ["classified"]}` and `log` uses an append reducer, `updates` shows you `["classified"]` (the delta) while `values` shows the full accumulated list.

### `"debug"` — the raw event stream

Each chunk is a low-level engine event — the checkpoints, task starts and results the runtime emits internally. It's noisy and not meant for end-user display, but it's the right tool for tracing: reconstructing exactly what the executor did and when, or feeding a custom observability layer. Reach for it when `updates` isn't granular enough to explain a run.

LangGraph also supports `"messages"` (LLM token streaming) and lets you pass a list of modes to multiplex several at once; those are worth knowing but the three above are the load-bearing ones.

## Why streaming is nearly free

The interesting part is *how little* has to happen for streaming to exist. LangGraph executes in **supersteps**: a batch of nodes runs, each node's return is merged into the channels at a barrier, and only then does the next superstep begin. That barrier is the natural emit point. A node finishes, its update lands, and the runtime already has both the delta and the new full state in hand — so it just yields a step record before moving on.

You can see this collapse to almost nothing in a minimal StateGraph. Each node executor, at the end of its run, records a small step tuple `(node, update, new_state)` and yields it as an intermediate output:

```python
# inside a node's run, right after merging its update:
new_state = reduce(channels, state, update)      # fold delta into state
await ctx.yield_output(Step(node=self.id,        # who ran
                            update=update,        # what they returned
                            state=new_state))     # state after merge
await ctx.send_message(new_state)                 # hand off to next node
```

`.stream()` is then a thin projection over those step records — it doesn't re-run anything or hook into node internals; it just relabels each step for the mode you asked for:

```python
async def stream(self, state, *, mode="values"):
    if mode not in ("values", "updates", "debug"):
        raise ValueError(f"unknown stream mode '{mode}'")
    async for ev in self._workflow.run_stream(state):
        if is_step(ev):
            step = ev.data
            if mode == "values":
                yield clean(step.state)             # full state
            elif mode == "updates":
                yield {step.node: step.update}      # {node: delta}
            else:
                yield ev                            # raw event
        elif mode == "debug":
            yield ev                                # everything
```

That's the whole idea. `"values"` yields `step.state`, `"updates"` re-keys `step.update` by node name, and `"debug"` forwards the raw events untouched. There is no separate "streaming engine" — the same run that produces the final state produces the intermediate steps along the way, and streaming is just choosing not to throw them away.

### Mental model

Think of a run as a train stopping at stations. Each station (superstep barrier) is a chance to look out the window. `"values"` photographs the whole train each stop; `"updates"` notes only which passengers boarded at *this* station; `"debug"` records every mechanical event, doors and all. `.invoke()` is the same train — you just wait at the destination and never look out the window. Because the stops happen regardless, observing them costs essentially nothing.

## Practical picks

- Building a live UI that shows accumulating results → `"values"`.
- Structured logging or auditing "which node did what" → `"updates"`.
- Tracing a misbehaving run or wiring custom telemetry → `"debug"`.
- Streaming model tokens to the user → `"messages"` (LangGraph provides it; a from-scratch replica typically leaves it out because it needs a token-streaming chat client).

See the official [LangGraph streaming concepts](https://langchain-ai.github.io/langgraph/concepts/streaming/) for the full mode list and the sync/async (`.stream` / `.astream`) variants.

Next in the series: persistence and checkpointers — how a graph pauses, resumes, and remembers where it was.
