# Checkpointing and Persistence: Pause, Resume, Time-Travel

*How a checkpointer turns a graph run into something you can stop, reload, and replay from any point in its history.*

---

Every graph we have built so far ran start-to-finish in one shot and forgot everything the moment `invoke()` returned. That is fine for a pure function, but a conversation, a long agent loop, or a workflow that pauses for a human needs **memory across calls** and **durability across crashes**. LangGraph gets both from one mechanism: a **checkpointer** that saves the graph's state at every superstep boundary. This post explains what a checkpoint actually contains, how `thread_id` keeps separate runs apart, and how the same saved snapshots give you time-travel.

## Why the superstep boundary is the right place to save

Recall the execution model: a LangGraph run advances in discrete **supersteps**, each running the active nodes concurrently, waiting at a barrier, merging their updates through the channel reducers, then routing onward. Between two supersteps the engine is **quiescent** — nothing is mid-flight. That quiet gap is exactly where a snapshot is meaningful, because the entire runtime state is just a small pile of plain data.

A **checkpoint** is one such snapshot at a superstep boundary. It captures three things:

- the **channel values** (the state dict as it stands after this step's reducers ran),
- the **pending work** (which nodes are queued to run next), and
- any **node/executor state** that lives between steps (for example a fan-in buffer that is still waiting on branches).

Because those three things are all the engine needs to keep going, saving them is enough to *stop and later continue exactly where you were* — there is no hidden call stack to preserve.

## MemorySaver: the simplest checkpointer

A checkpointer is just an object that knows how to `put` and `get` snapshots keyed by a thread. LangGraph ships several (SQLite, Postgres, Redis); the one to start with is `MemorySaver`, which holds checkpoints in a Python dict in memory. You attach it at compile time:

```python
from typing import Annotated, TypedDict
from langgraph.graph import StateGraph, START, END, add_messages
from langgraph.checkpoint.memory import MemorySaver

class State(TypedDict):
    messages: Annotated[list, add_messages]

def chat(state: State) -> dict:
    last = state["messages"][-1]
    return {"messages": [f"echo: {last}"]}

builder = StateGraph(State)
builder.add_node("chat", chat)
builder.add_edge(START, "chat")
builder.add_edge("chat", END)

app = builder.compile(checkpointer=MemorySaver())   # <- persistence, one argument
```

That single `checkpointer=` argument is the entire opt-in. With it, every superstep boundary now gets saved automatically.

## thread_id: separate conversations, one graph

A checkpointer needs to know *which* run a snapshot belongs to. That key is the **`thread_id`**, passed in the config on every invocation:

```python
cfg = {"configurable": {"thread_id": "alice"}}

app.invoke({"messages": ["hi"]}, config=cfg)
app.invoke({"messages": ["still there?"]}, config=cfg)   # same thread → remembers "hi"
```

The second call does **not** start fresh. Before running, the compiled graph asks the checkpointer for the latest snapshot on thread `"alice"`, loads its channel values as the starting state, then applies your new input. Because `messages` uses the `add_messages` reducer, the new message *appends* to the prior history — so the graph sees the whole conversation, even though you handed it one line.

Switch the `thread_id` and you get a clean, independent conversation:

```python
app.invoke({"messages": ["hi"]}, config={"configurable": {"thread_id": "bob"}})
# Bob's thread knows nothing about Alice's — different key, different history.
```

This is LangGraph's **short-term memory**: one evolving state per `thread_id`, isolated from every other thread, all living inside the same compiled graph.

## Resuming a run

Resume is just a normal `invoke` with a `thread_id` that already has checkpoints — there is no special "resume" API; you call the graph again on the same thread and it picks up from the last saved state. The durability guarantee is stronger than convenience: if the process **crashes** mid-workflow and the checkpointer wrote to durable storage (SQLite/Postgres, not in-memory), a fresh process can reattach to the same `thread_id` and continue from the last completed superstep.

Conceptually, this works because the snapshot is **serializable**. A minimal checkpoint is nothing more than a small dataclass that round-trips through JSON:

```python
import json
from dataclasses import dataclass, field

@dataclass
class Checkpoint:
    superstep: int
    channels: dict                       # the state after this step's reducers
    pending: list = field(default_factory=list)   # nodes queued for the next step

    def to_json(self) -> str:
        return json.dumps({"superstep": self.superstep,
                           "channels": self.channels,
                           "pending": self.pending})

    @classmethod
    def from_json(cls, text: str) -> "Checkpoint":
        d = json.loads(text)
        return cls(d["superstep"], d["channels"], d["pending"])
```

That `to_json` / `from_json` pair *is* durability. Once a superstep boundary can be written to bytes and read back into an identical object, "resume after a crash" and "resume in a different process" become the same operation as "keep going" — the engine cannot tell whether the state came from memory a millisecond ago or from disk after a reboot.

> **Mental model: the run is its history.** Don't picture the checkpointer as a single "current state" variable being overwritten. Picture an append-only list of snapshots, one per superstep, all tagged with the `thread_id`. The "current" state is simply the last entry. Everything else — resume, and the time-travel below — falls out of keeping the *whole* list instead of only its tail.

## Time-travel: replay and fork from an earlier checkpoint

Because every superstep boundary is saved, the newest snapshot is not special — it is just the most recent row in the thread's history. **Time-travel** means picking an *earlier* checkpoint and continuing from there:

```python
# Inspect the full checkpoint history for a thread (newest first)
history = list(app.get_state_history(cfg))

# Grab a specific earlier checkpoint by its id
past = history[3]
resume_cfg = {"configurable": {"thread_id": "alice",
                               "checkpoint_id": past.config["configurable"]["checkpoint_id"]}}

# Resume the run from that past point
app.invoke(None, config=resume_cfg)
```

Two distinct powers come out of this. **Replay**: re-run from an old checkpoint to reproduce exactly what happened — invaluable for debugging a non-deterministic agent. **Forking**: edit the state at an old checkpoint (with `app.update_state(...)`) and resume down a *different* branch, leaving the original timeline intact. You end up with a tree of runs, not a single line — the same idea as branching a git history from an earlier commit.

A from-scratch engine gets this almost for free: run one superstep at a time, keep each snapshot in a list, and to "travel" you hand any past snapshot back to the runner instead of the latest one — identical machinery to a normal resume, only a different choice of *which* checkpoint.

## Why this is the foundation for the next post

Checkpointing is not only about surviving crashes — it is the substrate that makes **human-in-the-loop** possible. Pausing a graph to wait for a person is exactly "save a checkpoint, return control, resume later when input arrives" — and that wait could last minutes or days, well past the lifetime of any single process. Durable, serializable snapshots keyed by `thread_id` are precisely what let a run sit paused and then continue as if nothing stopped.

Next in the series: **human-in-the-loop with `interrupt()`** — pausing a graph mid-run to get a human's input, then resuming from the checkpoint with their answer folded into the state.
