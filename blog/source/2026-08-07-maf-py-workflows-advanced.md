# Advanced Workflows in Microsoft Agent Framework (Python)

*Once you can wire a chain of executors, the graph earns its keep: concurrency, durable state, composition, and control — the patterns that turn a toy pipeline into a system that survives a crash.*

---

A core workflow in Microsoft Agent Framework (MAF) is a graph: you build it with `WorkflowBuilder`, connect typed **executors** with `.add_edge(...)`, and the engine advances the graph one **superstep** at a time, routing each executor's output message to the next. If that sentence reads cleanly, you've done the basics. This guide is about everything that comes after a straight chain — running work concurrently, threading data around the edges, wrapping agents so you control their context, persisting state so a run can be resumed, composing whole workflows as nodes, and gating what the graph is allowed to do.

Most examples below embed an AI agent, and every one of those agents is the same shape: an ordinary `Agent(client=...)` over a `FoundryChatClient` on Azure AI Foundry, authenticated with `AzureCliCredential()` — so `az login` first. One property matters for testing throughout: **construction is offline and lazy**. Building the client, the agent, and the whole graph touches no network; only `.run()` calls the model. That's why the credential-free plumbing patterns (parallelism, checkpointing) run entirely offline, and why you can unit-test graph shape without a Foundry endpoint.

---

## 1. Parallelism: fan out, then synchronize

This is the payoff of choosing a graph over a chain. A chain's wall-clock time is the *sum* of its steps; a graph's can be the *slowest single branch*, because independent work runs concurrently. Two edge builders express the entire shape:

- `add_fan_out_edges(source, [a, b, ...])` **broadcasts** the source's output — an identical copy — to every worker in the list, which then run concurrently.
- `add_fan_in_edges([a, b, ...], join)` hands the joiner a **list** of all the workers' outputs, and fires it exactly once, only after *every* source has completed.

```python
workflow = (
    WorkflowBuilder(start_executor=dispatch)
    .add_fan_out_edges(dispatch, [shout, reverse])  # parallel branches
    .add_fan_in_edges([shout, reverse], join)       # synchronized merge
    .build()
)
result = await workflow.run("agent framework")
print(result.get_outputs()[0])
```

The joiner's handler is typed to receive the aggregate, not a single message:

```python
async def run(self, results: list[str], ctx: WorkflowContext[Never, str]) -> None:
    await ctx.yield_output(" | ".join(sorted(results)))
```

**The gotcha:** worker completion order is not guaranteed. The `list` handed to the joiner reflects concurrent completion order, so it can vary run to run. The excerpt calls `sorted(results)` precisely to get a stable output — if you need deterministic ordering, sort or key the results yourself rather than assuming input order.

Doing this first on pure string workers (zero credentials) makes the synchronization barrier obvious before latency and model cost enter the picture. But the shape is exactly how you parallelize *agent* calls later: broadcast one task to several agents, then merge their answers in a joiner. Fan-in is a genuine barrier — the merge waits for the slowest branch, which is the whole point.

---

## 2. Sharing data without threading it through every edge

Edges carry a message from one executor to the next, but pipelines routinely need data that a downstream node was never directly handed — a large document, an intermediate artifact, a side output three steps back. Threading a big payload through every intervening message is wasteful and couples nodes that shouldn't care about it. Shared workflow **state** is the escape hatch: `ctx.set_state(key, value)` writes into state keyed by a string; `ctx.get_state(key)` reads it back in a later executor (returning `None` if the key is absent).

Here a Drafter stashes its output in state and sends only a tiny "go" signal down the edge; a Reporter reads the keys back to assemble the final report:

```python
class Drafter(Executor):
    @handler
    async def run(self, topic: str, ctx: WorkflowContext[str]) -> None:
        result = await self._agent.run(f"Write a short two-sentence blurb about: {topic}")
        ctx.set_state(DRAFT_KEY, result.text)
        await ctx.send_message("draft-ready")   # the draft itself never travels the edge

class Reporter(Executor):
    @handler
    async def run(self, _signal: str, ctx: WorkflowContext[Never, str]) -> None:
        draft = ctx.get_state(DRAFT_KEY)
        word_count = ctx.get_state(WORD_COUNT_KEY)
        await ctx.yield_output(f"Draft ({word_count} words):\n{draft}")
```

**The gotcha:** `set_state` / `get_state` are plain (non-async) methods — only `send_message` and `yield_output` are awaited. A writer sees its own update immediately within the same handler, but **other** executors only observe it from the *next* superstep onward — which is exactly why pipeline order matters when you rely on shared state. Guard against missing keys since `get_state` returns `None`. And state lives on the workflow **instance**, so build a fresh workflow per task or state will leak between runs — a warning that becomes a whole pattern in section 6.

---

## 3. Wrapping agents as executors

A workflow graph routes typed messages between executors, but an AI agent is not an executor on its own — the engine can't feed it messages or manage its session until it's wrapped in an `AgentExecutor`. When you pass a bare agent as `WorkflowBuilder(start_executor=agent)`, the framework wraps it *implicitly*. Do it **explicitly** and you gain three knobs: the executor's `id`, its context mode, and the ability to chain agents deliberately.

```python
writer = AgentExecutor(writer_agent, id="writer")
translator = AgentExecutor(translator_agent, id="translator", context_mode="last_agent")

workflow = (
    WorkflowBuilder(start_executor=writer)
    .add_edge(writer, translator)
    .build()
)

request = AgentExecutorRequest(
    messages=[Message(role="user", contents=["a lighthouse at dawn"])],
    should_respond=True,
)
result = await workflow.run(request)
```

**The gotcha:** `context_mode` is the key knob — `AgentExecutor(agent, id=..., context_mode="full"|"last_agent"|"custom")`. Setting `"last_agent"` makes a downstream agent consume **only** the previous agent's reply, not the whole conversation — ideal for translate/refine pipelines where the translator should see the writer's sentence, not the original topic prompt. The canonical input is an `AgentExecutorRequest(messages=[Message(role="user", contents=[...])], should_respond=True)`. Each executor emits an `AgentExecutorResponse` carrying `.agent_response`, `.full_conversation` (what chaining consumes), and `.executor_id`. A non-streaming `run` returns terminal outputs via `result.get_outputs()`, each an `AgentResponse`. (Upstream docs sometimes show `client.as_agent()`; `Agent(client=...)` produces the same executor.)

---

## 4. Consuming a run: streaming vs. not

A workflow is *defined* once, but you can **consume its run two ways** without touching the graph. Non-streaming — `result = await workflow.run(msg)` — runs to completion, then you read collected outputs off the result. Streaming — `workflow.run(msg, stream=True)` — returns an async stream you iterate with `async for`, receiving `output` and `intermediate` events as each superstep produces them.

```python
stream = workflow.run(topic, stream=True)
async for event in stream:
    if event.type in ("intermediate", "output") and isinstance(event.data, AgentResponseUpdate):
        label = "FINAL" if event.type == "output" else "step "
        print(f"[{label}] {event.executor_id}: {event.data.text}")

# After draining the stream, the same WorkflowRunResult is available.
result = await stream.get_final_response()
print(f"final state : {result.get_final_state()}")
```

**The gotcha:** if you're coming from `.NET`, its "OffThread" vs. "Lockstep" execution modes **do not apply to Python**. Python has a single execution model driven by an async generator — the consumer must keep pulling events for supersteps to advance. Streaming vs. non-streaming is *just* the `stream=` flag, not a separate engine. Non-streaming hands back a `WorkflowRunResult`: `.get_outputs()` for terminal outputs, `.get_intermediate_outputs()` for progress emissions, `.get_final_state()` for run state. In streaming mode, `await stream.get_final_response()` after the loop hands you that same result object. Reach for streaming when wiring a UI or progress bar; non-streaming fits batch jobs where only the terminal output matters.

---

## 5. Durability and clean reuse: two sides of state across runs

Sections 1–4 assumed a run completes in one process, once. Real orchestrations violate both assumptions — they crash, they wait hours for a human, and the same workflow object gets reused for the next task. Two features address the two failure modes, and they're mirror images: one **persists** state so you can resume, the other refuses to **share** state so runs stay independent.

### Checkpointing — snapshot each superstep so a run can resume

Hand `WorkflowBuilder` a `CheckpointStorage` and it snapshots state after each superstep; later you can list what was saved and resume from a checkpoint id. Storage is a single constructor argument, and the snapshots are queryable:

```python
storage = FileCheckpointStorage("./checkpoints")
workflow = (
    WorkflowBuilder(start_executor=s1, checkpoint_storage=storage, name=WORKFLOW_NAME)
    .add_edge(s1, s2)
    .build()
)
result = await workflow.run(5)
print(f"output: {result.get_outputs()}")  # (5+1)*10 = 60

checkpoints = await storage.list_checkpoints(workflow_name=WORKFLOW_NAME)
for cp in checkpoints:
    print(f"  • {cp.checkpoint_id[:8]}…  iteration={cp.iteration_count}")
```

There are two backends: `FileCheckpointStorage("./checkpoints")` persists JSON to disk; `InMemoryCheckpointStorage()` keeps snapshots in memory for tests. A `name` is **required** to find checkpoints again — `list_checkpoints(workflow_name=...)` keys on the name you passed the builder, and without it you can't locate the snapshots. Each snapshot carries `checkpoint_id`, `iteration_count`, and `timestamp`, so you can pick which superstep to resume from.

**The gotcha:** snapshots happen **per superstep, not per handler call**. State is captured at superstep boundaries, so resuming via `workflow.run(checkpoint_id=<id>)` lands you at the *start of the next superstep* — never partway through an executor. Design executors to be idempotent from a superstep boundary, because a resumed run replays from there. Checkpointing is the durability layer under everything hard: a human-in-the-loop gate suspends a workflow that may sit idle for hours, and long agent orchestrations can die mid-run — persisted supersteps mean the workflow survives process death and resumes exactly where it stopped.

### Resettable executors — never share mutable state across runs

The opposite hazard: executors are often **stateful** — they accumulate messages, count turns, cache results. Reuse *one* workflow instance across independent runs and that leftover state leaks into the next. In `.NET` the fix is the `IResettableExecutor` interface (a `ResetAsync()` the runtime calls between runs). Python has no such interface — the doc says the concept "does not apply." The Pythonic answer is simpler and stricter: never share state; build a **fresh** workflow and executors from a factory for every independent run.

```python
def build_workflow(client: FoundryChatClient):
    agent = Agent(client=client, name="Summarizer",
                  instructions="You write terse, factual one-sentence summaries.")
    summarize = SummarizeExecutor(agent)
    history = HistoryExecutor()        # self.seen = [] — mutable, must be fresh per run
    return WorkflowBuilder(start_executor=summarize).add_edge(summarize, history).build()

# The fix: a fresh workflow per run — each run sees "seen 1".
for topic in topics:
    workflow = build_workflow(client)
    result = await workflow.run(topic)
```

**The gotcha:** a `Workflow` instance **preserves state across calls** to `run()` — reuse it for two unrelated tasks and they share mutable executor state (the demo's counter climbs to "seen 2" instead of staying at "seen 1"). Builders are mutable, workflows are immutable; call `build()` again for independent instances. Crucially, executors handed to `WorkflowBuilder` are **shared objects**, so instantiate them *inside* the factory too — reusing one executor across builds still shares its state. There is no runtime reset hook; executor state is just plain instance attributes. The `FoundryChatClient` itself is fine to reuse across builds (it's stateless per call) — it's the executor's own lists and counters you must not share. This is the same lesson section 2 raised about workflow-level shared state, now generalized to every stateful node.

---

## 6. Composition: a whole workflow as one executor

Once workflows get large, you want to reuse and test pieces in isolation — the same reason functions beat one long script. A **sub-workflow** is a whole workflow run as a single executor inside a parent. You build the inner graph, wrap it in a `WorkflowExecutor`, and drop that wrapper into the parent like any other node. The inner graph runs its own superstep loop with its own isolated state; the parent only sees messages entering and leaving through its edges.

```python
analysis_pipeline = (
    WorkflowBuilder(start_executor=analyst)
    .add_edge(analyst, validator)
    .add_edge(validator, collect)   # collect: AgentExecutorResponse -> yield_output(str)
    .build()
)
return WorkflowExecutor(workflow=analysis_pipeline, id="analysis-pipeline")
```

**The gotcha:** agents can be added to a builder directly, but a raw `Workflow` **must** be wrapped with `WorkflowExecutor(workflow=inner, id="...")` first. The wrapper inherits the inner workflow's input/output types, so the parent's edges must line up with them — which is why the inner graph ends with a `collect` adapter forcing a `str` output that the parent's next agent can consume. Two flags control how outputs and requests cross the boundary: by default (`allow_direct_output=False`) inner `yield_output` results are forwarded as messages to the next parent executor; set `allow_direct_output=True` to yield them straight to the parent's event stream. `propagate_request=True` forwards inner `request_info()` calls to the caller; the default wraps them in a `SubWorkflowRequestMessage`. Nesting works to arbitrary depth, but each level adds its own superstep loop — keep depth reasonable. From the parent's view the entire nested pipeline is a single step, and only the outermost terminal output is visible.

---

## 7. Guardrails: terminating a run before or after the model

Composition and concurrency decide *what* runs; guardrails decide what's *allowed* to run. Agent middleware wraps every `agent.run()` in a chain, and inside `process(context, call_next)` you choose whether to proceed (`await call_next()`) or stop. To stop, raise `MiddlewareTermination` — the difference between "run the agent" and "block it" is simply whether you await `call_next()` at all.

```python
class PostTerminationMiddleware(AgentMiddleware):
    def __init__(self, max_responses: int = 1):
        self.max_responses = max_responses
        self.response_count = 0

    async def process(self, context: AgentContext, call_next) -> None:
        if self.response_count >= self.max_responses:
            raise MiddlewareTermination  # cap reached
        await call_next()
        self.response_count += 1
```

This gives you two guardrail shapes. **Pre-termination** raises `MiddlewareTermination` *instead of* awaiting `call_next()`, so the model is never called at all — blocking disallowed input and saving the model call entirely. **Post-termination** (above) awaits the call but caps how many times the agent may respond.

**The gotcha:** short-circuiting means *not calling* `call_next()`. For pre-termination, set `context.result = AgentResponse(...)` first, then raise `MiddlewareTermination(result=context.result)` so the caller receives a sensible canned answer rather than an exception bubbling up. Middleware instances **carry state across runs** (like `self.response_count`), so one agent object can enforce a running quota — handy for rate limiting. The latest user turn is `context.messages[-1].text`. Register middleware with `Agent(..., middleware=[Instance(), ...])`.

---

## 8. Orchestration as data: declarative workflows in YAML

Everything so far wired the graph in Python. You can instead **declare** it in YAML and load it at runtime — the file lists ordered `actions` (set variables, call agents, branch, loop) and the framework turns them into an executable workflow. Orchestration becomes data a non-developer can edit, with agents resolved by name:

```python
factory = WorkflowFactory()
factory.register_agent("PoetAgent", poet)

with tempfile.TemporaryDirectory() as tmp:
    yaml_path = Path(tmp) / "haiku-workflow.yaml"
    yaml_path.write_text(WORKFLOW_YAML)
    workflow = factory.create_workflow_from_yaml_path(yaml_path)

result = await workflow.run({"topic": "the monsoon over Mumbai"})
```

The YAML's `InvokeAzureAgent` action references `agent: { name: PoetAgent }`, which resolves against that `register_agent` call — so an ordinary `FoundryChatClient` agent drops straight in, nothing declarative-specific about it. Read finished values with `result.get_outputs()` and step-by-step values with `result.get_intermediate_outputs()`.

**The gotcha:** declarative support is a **separate package** — `pip install agent-framework-declarative --pre`, imported as `from agent_framework.declarative import WorkflowFactory`. The Python declarative shape is name-based (top-level `name`, optional `inputs`, a list of `actions`) — do **not** copy the C# `kind: Workflow` / `trigger:` shape; the languages genuinely differ here. Variables are namespaced (`Local.*`, `Workflow.Inputs.*`, `Workflow.Outputs.*`), and values starting with `=` are PowerFx expressions (e.g. `=Concat(...)`) while bare values are literals. That PowerFx dependency is why Python 3.14 isn't yet supported, and why only a **path** loader ships — hence writing the YAML to a temp file before loading.

---

## Key takeaways

- **Parallelism is the reason to use a graph.** Fan-out broadcasts an identical copy; fan-in is a synchronized barrier that fires once with a `list` — wall-clock is the slowest branch, and completion order isn't guaranteed, so sort if you need determinism.
- **Shared state lets big payloads skip the edges** — but writes are visible to other executors only from the next superstep, so pipeline order still matters.
- **Wrap agents explicitly for control.** `context_mode="last_agent"` feeds a downstream agent only the previous reply, the backbone of translate/refine chains.
- **Streaming vs. non-streaming is one flag, one engine.** The `.NET` OffThread/Lockstep distinction doesn't exist in Python.
- **Persist state to resume; refuse to share it to stay clean.** Checkpointing snapshots per superstep (resume from a boundary, design idempotent executors); the factory pattern is Python's answer to `.NET`'s `IResettableExecutor` — build fresh instances, executors included.
- **Sub-workflows compose systems from testable pieces** — wrap the raw `Workflow` in a `WorkflowExecutor` and line up its input/output types with the parent's edges.
- **Guardrails are client-side control flow.** Raise `MiddlewareTermination` (pre-model to block, post-model to cap); middleware state persists across runs.
- **YAML turns orchestration into editable data** — a `--pre` package with a name-based shape and PowerFx expressions, distinct from the C# schema.

| Concern | Reach for | Runs / persists where |
|---|---|---|
| Run branches concurrently | `add_fan_out_edges` / `add_fan_in_edges` | In-process, synchronized barrier |
| Pass data without an edge | `ctx.set_state` / `ctx.get_state` | On the workflow instance |
| Control an agent's context | Explicit `AgentExecutor(context_mode=...)` | Per-node routing |
| Live progress vs. batch | `stream=True` vs. `await run()` | Same engine, different consumption |
| Survive a crash or long wait | `CheckpointStorage` | Disk (JSON) or in-memory |
| Keep runs independent | Factory that rebuilds workflow + executors | Fresh instance per run |
| Reuse a workflow as a node | `WorkflowExecutor(workflow=inner)` | Isolated inner superstep loop |
| Block or cap a run | `MiddlewareTermination` in `AgentMiddleware` | Client-side, before/after the model |
| Let non-developers edit the flow | `WorkflowFactory` + YAML (`agent-framework-declarative`) | Loaded from a file path |

The through-line: a core workflow decides message *routing*; advanced workflows decide *concurrency, durability, composition, and control*. Every pattern here is offline to construct and only touches Foundry at `run()`, so you can build and test the shape of a system long before a single model call — then swap the `FoundryChatClient` for another chat client and the graph mechanics hold.

---

## Interactive diagrams

Explore the concepts in this guide as self-contained, pan/zoom interactive diagrams (light/dark, no dependencies):

- [Parallelism](/blog/diagrams/maf-py-45-parallelism.html)
- [Checkpointing](/blog/diagrams/maf-py-46-checkpointing.html)
