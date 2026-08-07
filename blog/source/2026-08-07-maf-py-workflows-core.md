# Building Workflows in Microsoft Agent Framework (Python): The Core Model

*From a single decorated async function to an explicit graph of executors and agent nodes — the core workflow model in Microsoft Agent Framework, and the two APIs that express it.*

---

A single agent is one request in, one answer out. Real work is rarely that shape: you draft then edit, classify then route, prepare then generate then finalize. A **workflow** is how Microsoft Agent Framework composes several steps — plain functions, branching logic, and whole agents — into one runnable unit that carries a message from start to finish.

The framework gives you two ways to express the same idea, and picking between them is most of the design decision:

1. **The functional API** — decorate an async function with `@workflow` and write orchestration as ordinary Python: `if`, `for`, and `await`. The graph is implicit in your control flow.
2. **The graph API** — declare **executors** (nodes) and wire them with **edges** using `WorkflowBuilder`. The graph is explicit, and it's what unlocks branching, streaming events, and — in the advanced guide — parallelism, checkpointing, and sub-workflows.

Both APIs run the same engine underneath. This guide walks from the gentlest entry point up to a graph of agents, keeping every mechanic visible along the way.

A note on credentials before we start: any example that calls a model drives a `FoundryChatClient` on Azure AI Foundry authenticated with `AzureCliCredential()` — so `az login` first. Construction is always offline; the client only touches the network when a workflow actually `run()`s. Several examples below have **no** model at all, and those need no credentials whatsoever — a deliberate choice, because it lets you reason about the orchestration machinery without the LLM in the way.

---

## 1. The functional API: plain Python is the orchestration

The softest entry point hides the graph completely. You write an async function, decorate it with `@workflow`, and ordinary control flow *becomes* the orchestration. To see the mechanics with nothing else in the picture, start with a workflow that has no agent and no model call at all — it classifies a string as "short" or "long":

```python
@step
async def normalize(text: str) -> str:
    return text.strip().lower()

@step
async def word_count(text: str) -> int:
    return len(text.split())

@workflow
async def summarize_input(raw: str) -> str:
    clean = await normalize(raw)
    count = await word_count(clean)
    verdict = "short" if count < 5 else "long"
    return f"{count} words ({verdict}): {clean!r}"
```

A `@step` is an async unit of work whose result is cached and checkpointed; a `@workflow` composes steps with ordinary control flow. There's no DSL to learn before the graph API arrives — sequential `await`s and a plain `if` branch are the whole program. The reason `@step` matters even here, where it just runs top to bottom, is that **checkpointing lives in the step boundary**: each step's result is cached, which is what makes workflows resumable later.

Swap the pure functions for agents and nothing about the shape changes — a WRITER drafts a paragraph and an EDITOR tightens it, one line of glue each:

```python
@workflow
async def draft_and_edit(topic: str) -> str:
    draft = await writer.run(topic)
    print(f"\n[writer draft]\n{draft.text}\n")
    final = await editor.run(draft.text)
    return final.text
```

The key thing to notice is that **the output of one step feeds the next as plain data**. `editor.run(draft.text)` consumes the writer's text directly — no message bus, no wiring, just `await`. Both agents share one `FoundryChatClient`, so this workflow makes two sequential Foundry calls, writer then editor.

Running a functional workflow looks like calling any async function, but the return type has a twist:

```python
result = await draft_and_edit.run("Deploying to production on a Friday")
print(result.get_outputs()[0])
```

**The gotcha:** `.run()` returns a `WorkflowRunResult`, **not** the value. Call `.get_outputs()` to get a list — a workflow can yield more than one output — and `[0]` is the returned string. The other thing to expect: the functional workflow API is marked experimental in this SDK build, so you may see an experimental-feature warning at runtime. That is expected, not an error.

The functional API is ideal when your orchestration is a straight line or simple branch you can read top-to-bottom. The moment you need data-driven routing, live progress events, or fan-out, you want the graph to be a real object you can inspect and wire — which is the graph API.

---

## 2. The graph model: executors and edges

Under the functional sugar, a workflow is a set of **executors** (nodes) joined by **edges**. A message enters the start executor and flows along the edges; each executor either forwards a message with `ctx.send_message` or emits a final result with `ctx.yield_output`. Making that graph explicit is the graph API's whole job.

There are two ways to write an executor: subclass `Executor` and mark a method with `@handler`, or decorate a module-level async function with `@executor`. A minimal two-node graph — uppercase, then reverse — shows both, wired with `WorkflowBuilder`:

```python
class Upper(Executor):
    @handler
    async def process(self, text: str, ctx: WorkflowContext[str]) -> None:
        await ctx.send_message(text.upper())

@executor(id="reverse")
async def reverse_text(text: str, ctx: WorkflowContext[Never, str]) -> None:
    await ctx.yield_output(text[::-1])

workflow = WorkflowBuilder(start_executor=up).add_edge(up, reverse_text).build()
```

The subtlety worth internalizing is that **the type hint carries routing intent**. `WorkflowContext[str]` means the node will `send_message(str)` onward; `WorkflowContext[Never, str]` marks the node **terminal** — it sends no further message and only `yield_output(str)`. That distinction is the entire routing contract, declared in the annotation.

**The gotcha:** `send_message` versus `yield_output` is the whole distinction — one forwards to the next edge, the other ends the workflow. Get them backwards and your graph either never terminates or terminates too early.

The fluent builder scales to longer chains the same way. Here three nodes run in sequence — a plain function executor prepares a prompt, a Foundry agent wrapped in an `Executor` writes, and a final node yields the output:

```python
@executor(id="prepare")
async def prepare(topic: str, ctx: WorkflowContext[str]) -> None:
    await ctx.send_message(f"Write a two-sentence explainer about: {topic}")

@executor(id="finalize")
async def finalize(draft: str, ctx: WorkflowContext[Never, str]) -> None:
    await ctx.yield_output(draft.strip())

return (
    WorkflowBuilder(start_executor=prepare, output_from=[finalize])
    .add_edge(prepare, writer)
    .add_edge(writer, finalize)
    .build()
)
```

**The gotcha:** `WorkflowBuilder` takes `start_executor=...` as a **keyword** arg, not positional. Handlers must be async and **type-annotated** — the framework reads the annotations to route messages. And *which* executor's `yield_output` counts as the terminal answer is a **build-time** choice: pass `output_from=[...]` to the builder to name it. A non-streaming `run` returns a `WorkflowRunResult`, read with `result.get_outputs()`, exactly like the functional API.

The pattern to carry forward: an agent drops into a graph as an ordinary node by wrapping it in an `Executor` subclass. The Foundry client only touches the network when that node runs — construction stays offline.

---

## 3. Where agents plug in: the agent pipeline

Before wiring agents directly into graphs, it helps to know what an `Agent` actually *is*, because that tells you exactly where you can intervene. An `Agent` is not a single function call — it's a layered pipeline every request flows through, built by class composition:

```
Agent (outer)                     ← what you construct
  ├─ Agent Middleware + Telemetry ← wraps run(); logging/validation/spans
  ├─ RawAgent                     ← core logic; invokes context providers
  └─ Context Providers            ← history + extra context, per-run
ChatClient (separate, swappable)
  ├─ FunctionInvocation           ← the tool-calling loop
  ├─ Chat Middleware + Telemetry  ← runs per model call
  └─ RawChatClient                ← provider-specific LLM comms (Foundry here)
```

A request descends the Agent layers, crosses into the ChatClient pipeline, hits the model, and the response flows back up. You hook the outermost layer with middleware:

```python
@agent_middleware
async def tracing_middleware(context: AgentContext, call_next) -> None:
    print("  [agent-middleware] entering pipeline — request handed to RawAgent")
    await call_next()  # descend: context providers -> ChatClient -> LLM -> back up
    print("  [agent-middleware] leaving pipeline — response has flowed back up")
```

Wiring it together, `Agent(..., middleware=[tracing_middleware], context_providers=[InMemoryHistoryProvider()])` attaches the outermost layer and the context layer. With a history provider in place, turn 1 stores a name and turn 2 recalls it, because the provider replays turn 1 into the request before it reaches the ChatClient.

**The gotcha:** middleware is attached at construction (`Agent(..., middleware=[fn])`), and both history and RAG/context providers live in **one** unified `context_providers=[...]` list — there's no separate history argument. Providers run in list order and can even attach per-invocation chat/function middleware, which the agent flattens before entering the ChatClient pipeline.

The payoff for workflow design is the bottom of the diagram: **the ChatClient is a separate, interchangeable component.** Swapping Foundry (`FoundryChatClient` + `AzureCliCredential`) for another provider changes only `RawChatClient` — every outer Agent layer, and therefore every workflow that wraps the agent, is unchanged. That's why an agent behaves like any other node once it's in the graph.

---

## 4. Agents as nodes, directly

Wrapping an agent in an `Executor` subclass works, but for the common case you don't even need the wrapper — **an agent can be a graph node directly.** Here a Writer agent drafts content and a direct edge hands its output to a Reviewer agent that critiques it:

```python
return (
    WorkflowBuilder(start_executor=writer_agent)
    .add_edge(writer_agent, reviewer_agent)
    .build()
)
```

The agents *are* the executors — the Writer is the start node, an edge feeds the Reviewer, output flows down the pipeline, and latency is sequential (Writer, then Reviewer). Both share one `FoundryChatClient`, so the whole pipeline runs against a single Foundry model deployment. This is how you compose multi-agent behavior — draft → review → edit — without ever leaving the workflow graph.

Reading streamed output from a multi-agent graph takes a little care, because tokens from different agents interleave:

```python
async for event in workflow.run(prompt, stream=True):
    if event.type == "output" and isinstance(event.data, AgentResponseUpdate):
        update = event.data
        if update.author_name != last_author:
            print(f"\n{update.author_name}: {update.text}", end="", flush=True)
            last_author = update.author_name
        else:
            print(update.text, end="", flush=True)
```

**The gotcha:** `workflow.run(prompt, stream=True)` yields `WorkflowEvent`s — filter `event.type == "output"` **and** check `isinstance(event.data, AgentResponseUpdate)` to read streamed agent tokens. Each update carries `.author_name` (which agent) and `.text` (the token chunk), so you group consecutive chunks by author to reconstruct each agent's message. (Upstream docs sometimes build agents via `client.as_agent(...)`; this repo's house style uses the `Agent(client=...)` constructor — same resulting executor.)

---

## 5. Branching: routing by the data

A pipeline that always runs the same nodes in the same order is only half the story. Often the *next* executor depends on the *data*, and the graph API expresses that with a **switch-case edge group**: from one source, a message is routed to the first `Case` whose predicate is true, else to the `Default`. This is the first branching primitive beyond a straight line — and, like the base graph, it needs no model, so it runs credential-free.

The branching lives entirely in `add_switch_case_edge_group`. This example routes even numbers to a "fast lane" executor and odds to a "review lane":

```python
workflow = (
    WorkflowBuilder(start_executor=intake)
    .add_switch_case_edge_group(
        intake,
        [
            Case(condition=lambda x: x % 2 == 0, target=even),
            Default(target=odd),
        ],
    )
    .build()
)
result = await workflow.run(n)
return result.get_outputs()[0]
```

Two properties govern the routing. **Cases are evaluated in order** — the message goes to the *first* `Case` whose `condition` returns true, so order matters when predicates overlap. And **predicates are plain callables**: `lambda x: x % 2 == 0` is ordinary Python over the message, which keeps routing logic in your code rather than the model's. Each target executor is a small class with a `@handler` that calls `ctx.yield_output(...)` on the routed message, its output type declared on the context as before (`WorkflowContext[Never, str]` for a terminal node, `WorkflowContext[int]` for one that forwards).

**The gotcha:** every switch-case group needs a `Default`. Cases are **not** exhaustive on their own — a message that matches no `Case` and has no `Default` has nowhere to go. Always terminate the group with a `Default(target=...)` so the routing is total.

This is graph plumbing that sits *below* the agent layer, but the same edge groups carry agent executors: swap the even/odd handlers for agents and the switch-case decides which agent handles a message. Learning routing on pure functions first keeps the mechanics visible before models enter the graph.

---

## 6. Watching a run: events and streaming

A workflow doesn't have to be a black box. As it runs, it **emits events** at every step, and `workflow.run(x, stream=True)` hands them to you one at a time as an async iterator — so you can show progress, log diagnostics, or relay domain data live instead of only seeing the final output.

The design choice that shapes everything here: the Python SDK has **no per-kind event classes**. Every event is a single `WorkflowEvent` discriminated by a `.type` string — `"executor_invoked"`, `"executor_completed"`, `"output"`, `"intermediate"`, `"error"`. Executors can also emit **custom** events with any `type=` string plus a `data=` payload. An executor emits a custom `"progress"` event, and the caller filters on `.type`:

```python
class Summarize(Executor):
    @handler
    async def run(self, text: str, ctx: WorkflowContext[str]) -> None:
        await ctx.add_event(WorkflowEvent(type="progress", data="summarize: calling model"))
        reply = await agent.run(text)
        await ctx.send_message(reply.text.strip())

async for event in workflow.run(ARTICLE, stream=True):
    if event.type == "executor_invoked":
        print(f"  → invoked   : {event.executor_id}")
    elif event.type == "progress":            # our custom event
        print(f"  · progress  : {event.data}")
    elif event.type == "output":              # terminal, from ctx.yield_output
        print(f"  ★ output    : {event.data!r}")
```

**The gotcha:** streaming is `workflow.run(x, stream=True)` — there is **no** `run_stream()`. And the types `"started"`, `"status"`, and `"failed"` are **reserved** for framework lifecycle: if an executor tries to emit one, the event is silently dropped and a warning logged. Mind the output distinction too — `"output"` is terminal output (via `ctx.yield_output`, read with `result.get_outputs()`) while `"intermediate"` is observational (read with `result.get_intermediate_outputs()`); `"data"` is a deprecated alias for `"intermediate"`.

The event plumbing is client-agnostic, but when an executor wraps a `FoundryChatClient` agent the streamed `executor_invoked` / `progress` / `executor_completed` / `output` sequence wraps a real model call. In production you'd forward the same events to a UI or an OpenTelemetry pipeline.

---

## 7. Choosing an approach

| Need | Reach for | Model call? |
|---|---|---|
| Straight-line or simple-branch orchestration you read top-to-bottom | Functional API (`@workflow` / `@step`) | Optional |
| Resumable steps with cached results | `@step` boundaries (functional) | Optional |
| An explicit, inspectable graph you wire node-by-node | Graph API (`WorkflowBuilder` + edges) | Optional |
| Compose several agents (draft → review → edit) | Agents as executor nodes | Yes |
| Route the next node by the data | `add_switch_case_edge_group` (`Case` / `Default`) | Optional |
| Watch progress live / relay custom domain events | `run(x, stream=True)` + `WorkflowEvent.type` | Optional |
| Intercept every agent request | Agent middleware + context providers | Yes |
| Fan-out parallelism, checkpointing, sub-workflows | *See the advanced workflows guide* | — |

---

## Key takeaways

- **Two APIs, one engine.** The functional API (`@workflow` over plain `await`) is the gentlest entry point; the graph API (`WorkflowBuilder` + executors + edges) makes the graph an explicit object — and that explicitness is what unlocks branching, streaming, and the advanced features.
- **`.run()` returns a `WorkflowRunResult`, never the value.** Read terminal output with `result.get_outputs()` — it's a list because a workflow can yield more than one output.
- **`send_message` forwards, `yield_output` terminates**, and the `WorkflowContext[...]` type hint declares which a node does. `WorkflowContext[Never, T]` marks a terminal node that only yields.
- **Agents are nodes.** Wrap one in an `Executor`, or drop the agent straight into `WorkflowBuilder` as a node — the layered Agent pipeline (middleware → context providers → swappable ChatClient) is why it composes cleanly.
- **Branching needs a `Default`.** Switch-case groups evaluate `Case`s in order and are not exhaustive on their own.
- **Events are one type, discriminated by `.type`.** Stream with `run(x, stream=True)` (there is no `run_stream()`); `"started"`, `"status"`, and `"failed"` are reserved for the framework.

Everything here is provider-agnostic in shape: the `FoundryChatClient` + `AzureCliCredential` pairing is just the model plumbing, and swapping it changes only the innermost ChatClient layer. Your real design work is choosing between the functional and graph APIs, deciding where each node yields versus forwards, and where the data — not the model — should decide the path. When you outgrow a single graph and need parallel fan-out, resumable checkpoints, or nested sub-workflows, the advanced workflows guide picks up from here.

---

## Interactive diagrams

Explore the concepts in this guide as self-contained, pan/zoom interactive diagrams (light/dark, no dependencies):

- [Agent Pipeline](/blog/diagrams/maf-py-15-agent-pipeline.html)
