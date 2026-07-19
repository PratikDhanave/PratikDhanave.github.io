# The LangGraph Glossary: Every Concept in One Place

*The reference capstone — each term in the series, defined in plain English and grouped by what it does.*

---

This is post 11 of 11, the finale of **"LangGraph, Concept by Concept."** Across the series we built up LangGraph one idea at a time using a minimal, dependency-free StateGraph to demystify each piece. This post collects every term into a single glossary you can bookmark: each entry is a one-or-two-sentence, plain-English definition of the concept as it exists in real [LangGraph](https://langchain-ai.github.io/langgraph/). Skim it as a map, or use it to look up anything the earlier posts left fuzzy.

A quick orientation before the tables. LangGraph is, at its heart, a **Pregel engine** running a **graph of nodes** over **shared state**, with layers bolted on for **persistence**, **human-in-the-loop**, **agents/tools**, and an **ecosystem** of tooling. The groups below follow that same arc.

## The graph model

The structural vocabulary: how you describe a workflow and how the engine runs it.

| Term | Definition |
|---|---|
| **Graph** | A workflow expressed as nodes connected by edges. You build it, `compile()` it, then run it. |
| **Pregel / BSP** | The execution model LangGraph inherits from Google's Pregel. Work advances in discrete rounds (bulk-synchronous parallel), not as free-running async tasks. |
| **Superstep** | One round of execution: every active node runs, the engine waits for all of them, then routes their outputs to the next round. |
| **Barrier** | The synchronization point that ends a superstep. No node in the next step starts until every node in the current one finishes, which is what makes reducers and parallelism deterministic. |
| **Node** | A unit of work — a function that receives the state and returns a partial update to it. Named when you call `add_node`. |
| **Edge** | A directed connection `source → target` that moves execution from one node to the next. |
| **Conditional edge** | An edge whose target is chosen at runtime by a router function that reads the state. Added with `add_conditional_edges`. |
| **START** | The virtual entry sentinel. `add_edge(START, "n")` marks `n` as where the graph begins. |
| **END** | The virtual terminal sentinel. Routing to `END` finishes the run and returns the final state. |
| **Entry point** | The first node to run, set via `set_entry_point("n")` or `add_edge(START, "n")`. |
| **Cycle / loop** | A back-edge that lets the graph revisit a node — the mechanism behind the agent loop. Unlike a plain DAG, LangGraph allows cycles. |
| **compile()** | Freezes the builder into a runnable `CompiledStateGraph`. Validates the structure and produces something you can `invoke` or `stream`. |
| **invoke()** | Runs the compiled graph to `END` and returns the final state in one call. |
| **recursion_limit** | The maximum number of supersteps before the engine raises `GraphRecursionError`, a safety valve against runaway loops. |

## State, channels, reducers

How data flows through the graph and how concurrent updates merge.

| Term | Definition |
|---|---|
| **State** | The shared, typed data every node reads and writes — usually a `TypedDict`. It is the single object threaded through the whole run. |
| **Channel** | One named field of the state, each with its own update rule. The state is a bundle of channels. |
| **Reducer** | The function that merges a channel's existing value with a node's update. With no reducer, an update overwrites; with one (e.g. `operator.add`), updates combine. |
| **add_messages** | LangGraph's canonical reducer for a `messages` channel. It appends new messages and reconciles updates by message ID rather than blindly overwriting. |
| **Partial update** | A node returns only the channels it changed; the engine merges each through its reducer. Nodes never rewrite the whole state. |
| **Command** | A return value that bundles a state **update** and a **goto** (which node runs next) into one object, letting a node update state and route in a single step. |
| **Message-passing (contrast)** | The alternative model where nodes send payloads along edges instead of updating shared state. LangGraph's shared-state model is the inverse: nodes communicate *through* the state, not by direct messages. |

## Persistence and durability

How runs survive pauses, crashes, and time.

| Term | Definition |
|---|---|
| **Checkpointer** | A backend that saves the graph's state at each superstep so a run can pause, resume, or be replayed. Passed to `compile(checkpointer=...)`. |
| **MemorySaver** | The in-memory checkpointer — the simplest one, good for tests and single-process use; state is lost when the process exits. |
| **Checkpoint** | One saved snapshot of the state at a superstep boundary, the atom persistence works with. |
| **thread_id** | The key identifying one conversation or run. Passing the same `thread_id` in the config continues that thread's saved state; a new one starts fresh. |
| **Time-travel** | Inspecting the checkpoint history and resuming (or forking) from an *earlier* checkpoint rather than the latest — replaying a run from a chosen point. |

## Human-in-the-loop

Pausing a running graph for a human, then continuing.

| Term | Definition |
|---|---|
| **interrupt()** | Called inside a node to pause the graph, surface a value to a human, and wait. Requires a checkpointer, since the paused state must be saved. |
| **resume** | Continuing an interrupted graph by invoking it again with a `Command(resume=value)`; the value becomes `interrupt()`'s return, and the node re-runs from the top. |
| **Approval gate** | A common pattern where a node interrupts to ask a human to approve or reject before a consequential action (a tool call, a write); a conditional edge then branches on the answer. |

## Agents and tools

The prebuilt ReAct agent and the pieces it loops over.

| Term | Definition |
|---|---|
| **Tool** | A function the model may call, its schema derived from the signature and docstring. Decorated with `@tool` in LangChain. |
| **ToolNode** | A prebuilt node that executes whatever tool calls the model requested and appends the results back onto the `messages` channel. |
| **create_react_agent** | The prebuilt constructor that wires a model, tools, and a `ToolNode` into a ready-made ReAct agent graph — the fast path to a working agent. |
| **Tool loop** | The cycle at the agent's core: call the model, run any tools it requested, feed the results back, and repeat until the model responds with no more tool calls. |

## Parallelism and routing

Fanning work out and merging it back in.

| Term | Definition |
|---|---|
| **Send API / dynamic fan-out** | Returning a list of `Send(node, state)` objects to spawn N parallel runs of a node — one per item — when the count is only known at runtime (map-reduce). |
| **Fan-in** | The merge step: multiple parallel branches complete and their updates combine through the target channel's reducer at the barrier. |
| **path_map** | The dict a conditional edge uses to translate the router's returned key into an actual target node, keeping router logic and graph wiring separate. |
| **Router** | The function behind a conditional edge: it reads the state and returns a key (or a node name) deciding where control flows next. |

## Streaming

Watching a run as it happens instead of waiting for the final state.

| Term | Definition |
|---|---|
| **stream()** | Runs the graph like `invoke()` but yields intermediate output as each superstep completes, rather than only the final result. |
| **stream_mode="values"** | Emits the full state after each step — the complete snapshot every time. |
| **stream_mode="updates"** | Emits only the per-node delta each step, as `{node_name: update}` — lighter than `values`. |
| **stream_mode="debug"** | Emits raw engine events (node starts, completions, checkpoints) for tracing exactly what the runtime did. |

## Ecosystem (not core graph mechanics)

These belong to the surrounding LangChain/LangGraph product world rather than the graph engine itself. Worth knowing, but distinct from the concepts above.

| Term | Definition |
|---|---|
| **LangChain messages** | The shared message types (`HumanMessage`, `AIMessage`, `ToolMessage`, ...) and model integrations LangGraph reuses so any LangChain chat model drops in. |
| **LangSmith** | Hosted tracing, evaluation, and observability. It records runs for debugging but is a separate SaaS, not part of the engine. |
| **Subgraph** | A compiled graph used as a node inside a parent graph, so you can compose and nest workflows. Structurally powerful, but a composition feature layered on the core model. |
| **LangGraph Platform** | The deployment product (Server, Studio) for hosting, scaling, and visually debugging graphs in production — infrastructure around the library, not a graph concept. |

## Why grouping matters

The reason this glossary reads cleanly in eight groups is that LangGraph *is* cleanly layered. The graph model and state/channels/reducers are the irreducible core — everything else attaches to it. Persistence is "save the state at each barrier." Human-in-the-loop is "pause at a barrier and wait." Agents are "a specific cyclic graph." Streaming is "yield at each barrier instead of only at the end." Once the superstep-and-barrier engine is clear, the rest of the vocabulary stops being a pile of features and becomes a short list of things you can do *to* that engine. The ecosystem group sits outside because it wraps the engine rather than extending it.

That is the whole point of the series: LangGraph is not a hundred disconnected APIs but one small model with a handful of layers. Keep this page open the next time you read the [official docs](https://langchain-ai.github.io/langgraph/) — every term there should now land somewhere on this map.
