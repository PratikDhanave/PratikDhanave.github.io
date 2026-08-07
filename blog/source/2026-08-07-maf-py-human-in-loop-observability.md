# Human-in-the-Loop & Workflow Observability in Microsoft Agent Framework (Python)

*How to pause a workflow for a human decision, package a whole workflow as an agent, and see exactly what a run did — through OpenTelemetry spans and a rendered graph — in Microsoft Agent Framework.*

---

A workflow that runs start to finish untouched is the easy case. The hard cases are the ones every real system hits: a step that can't proceed without a person's sign-off, a workflow you want to reuse wherever an agent is expected, and a run whose behavior you need to *see* — before it executes and after. Microsoft Agent Framework answers all three with the same small vocabulary you already use to build workflows: `request_info` to suspend for a human, `as_agent()` to repackage, and a one-call setup for tracing plus `WorkflowViz` for drawing.

The two workflows that touch a real model below drive a `FoundryChatClient` on Azure AI Foundry authenticated with `AzureCliCredential()` — so `az login` first. The rest run entirely offline with plain executors and zero credentials; the mechanics are provider-agnostic either way.

---

## 1. Suspending a workflow for a human

Approvals, clarifications, sign-offs — some steps simply can't proceed without a person. `RunContext.request_info` is Microsoft Agent Framework's uniform way to put one in the loop: it **suspends** the workflow and returns a pending request to your code. You gather the human's answer and **resume** by re-running with that answer keyed by `request_id`.

The suspend point is a single awaited call inside a `@workflow`. Here an `approval_flow` asks whether to publish a release note, suspends, and on resume either publishes or rejects:

```python
@workflow
async def approval_flow(draft: str, ctx: RunContext) -> str:
    decision = await ctx.request_info(
        {"draft": draft, "question": "Approve this release note? (approve/reject)"},
        response_type=str,
        request_id="review",
    )
    if decision.strip().lower().startswith("approve"):
        return f"PUBLISHED ✅ — {draft}"
    return "REJECTED ❌ — sent back for edits."
```

Driving it is two runs — one that suspends, one that resumes:

```python
result = await approval_flow.run(draft)
pending = result.get_request_info_events()          # what the human must answer
final = await approval_flow.run(responses={"review": "approve"})  # resume, no new message
```

Three things make this read cleanly. First, **`request_info` returns the human's answer on resume**: on the first run it suspends, and on the resume run the same `await` returns the supplied value directly, so the function body reads like straight-line code. Second, **pending requests are events** — `result.get_request_info_events()` lists each suspension with its `request_id` and the `data` payload you showed the human. Third, **resume passes `responses`, not a message**: `run(responses={"review": human_answer})` carries no new draft, just the keyed answer.

**The gotcha:** the resume key must exactly match the `request_id` from the suspend call — `"review"` on both sides. A mismatched key and the workflow won't find the answer it's waiting on. Note too that functional workflows are experimental in this build, so the API may shift.

This builds directly on checkpointing: because a suspended workflow's state can be snapshotted, it can be persisted and resumed hours later, across process restarts. The same `request_info` gate underlies tool-approval flows where a human authorizes a side effect before an agent proceeds — the client-side pause and the human-in-the-loop workflow are the same mechanism at different altitudes.

---

## 2. Packaging a workflow as an agent

Both a workflow and an agent expose `.run(...)`. That shared contract is the whole trick: wrap a complete workflow with `workflow.as_agent(name=...)` and it drops in anywhere an agent is expected — inside another workflow, behind DevUI, or as a tool for a third agent. The workflow vocabulary vanishes at the call site.

Build an ordinary workflow, then wrap it so it quacks like an agent:

```python
workflow = WorkflowBuilder(start_executor=Headline(id="headline"), name="Headliner").build()
agent = workflow.as_agent(name="HeadlinerAgent")
response = await agent.run("the quick brown fox jumps over the lazy dog")
print(f"agent.run() → {response.text!r}")
```

The call site is indistinguishable from the very first agent lesson — `agent.run("...")` with a plain string. What makes that work is the input contract on the *start* executor, which must be typed to accept what the wrapper feeds it:

```python
async def run(self, messages: list[Message], ctx: WorkflowContext[Never, str]) -> None:
    text = messages[-1].text  # the latest user turn
    await ctx.yield_output(text.strip().title())
```

The wrapper **normalizes every agent-shaped input to `list[Message]`** — a string, a `Message`, or a list of messages all arrive at the start node the same way — so you read the latest turn with `messages[-1].text` and treat earlier entries as prior context.

**The gotcha:** the one hard rule is that the workflow's start executor must accept `list[Message]` as its input type. Because `as_agent()` converts every input to `list[Message]` before handing it off, a start node typed for `str` or `int` will simply fail to receive the message.

This unifies the two abstractions the workflow model builds separately. Anything that consumes an agent can now consume a full multi-step workflow through the same `.run()` contract, and composition scales cleanly: workflows nest inside agents inside workflows, all speaking one interface, with or without a Foundry model behind any given node.

---

## 3. Tracing a run: workflow spans over OpenTelemetry

Once workflows suspend, resume, and nest, "what actually happened in that run?" stops being answerable by reading code. Observability turns a run into a tree of OpenTelemetry spans you can inspect. On top of the usual GenAI agent spans, a workflow emits its own:

- `workflow.build` — when `.build()` runs
- `workflow.run` — around the whole execution
- `executor.process {id}` — one per node
- `edge_group.process` — one per routing decision
- `message.send` — one per hop

Turning it on is a **single setup call** — the framework instruments the builder and the run for you. Enable instrumentation, then wrap the run in a root span so every workflow span shares one parent:

```python
configure_otel_providers()          # reads OTEL_* / ENABLE_* env vars
workflow = build_workflow()

with get_tracer().start_as_current_span(
    "Scenario: Writer-Reviewer Workflow", kind=SpanKind.CLIENT
) as root_span:
    trace_id = format_trace_id(root_span.get_span_context().trace_id)
    print(f"Trace ID: {trace_id}\n")
    async for event in workflow.run(prompt, stream=True):
        if event.type == "output":
            print(f"[{event.type}] {event.data}")
```

The traced graph here is a Writer→Reviewer pipeline, both agents backed by one `FoundryChatClient`. The printed `trace_id` is your handle: paste it into your OpenTelemetry backend to find the whole span tree — spanning the Foundry model calls *and* the workflow routing — in one place.

**The gotcha:** `configure_otel_providers()` (from `agent_framework.observability`) does two jobs at once — it **enables** instrumentation and **wires** the trace/log/metric providers from environment variables. Enabling is entirely env-driven:

- `ENABLE_INSTRUMENTATION=true` activates the Agent Framework code paths.
- `ENABLE_CONSOLE_EXPORTERS=true` prints spans straight to your console — no backend needed.
- `OTEL_EXPORTER_OTLP_ENDPOINT=http://localhost:4317` ships them to an Aspire Dashboard.
- `ENABLE_SENSITIVE_DATA=false` by default — message content and executor inputs/outputs are populated *only* when it's true, so keep it off in production.

And the trap that bites everyone: Agent Framework does **not** auto-load `.env`, so `load_dotenv()` must run *before* the setup call, or none of those variables will be seen.

---

## 4. Drawing the graph: WorkflowViz

Spans tell you what a run did; visualization tells you what a workflow *is* before it runs a single step. A graph with several executors and fan-out/fan-in edges is hard to read from code alone. `WorkflowViz` takes a built `Workflow` and renders its shape — as a Mermaid diagram, a Graphviz DOT string, or an exported image — so you can confirm the wiring matches the design you intended.

Build a fan-out/fan-in graph, wrap it, and emit the text formats:

```python
workflow = (
    WorkflowBuilder(start_executor=dispatcher)
    .add_fan_out_edges(dispatcher, [researcher, marketer, legal])
    .add_fan_in_edges([researcher, marketer, legal], aggregate)
    .build()
)

viz = WorkflowViz(workflow)
print(viz.to_mermaid())      # no extra deps
print(viz.to_digraph())      # Graphviz DOT source

try:
    svg_path = viz.save_svg("workflow.svg")   # needs graphviz pkg + binary
except Exception as exc:
    print(f"[skip] image export unavailable: {exc}")
```

The rendering carries meaning: the start executor draws as green "(Start)", fan-in nodes as a golden ellipse, and conditional edges as dashed lines — so structure is legible at a glance.

**The gotcha:** text output (`to_mermaid()`, `to_digraph()`) needs **no** extra dependencies, but image export (`export(format=...)`, `save_svg/png/pdf`) requires *both* the `graphviz` Python package **and** the GraphViz system binary — hence the `try/except` so the code still prints something without them. Crucially, `WorkflowViz` only reads the graph *shape*; it does **not** run the agents, so no model call is made just to draw the diagram. Even though the four branch nodes here are `FoundryChatClient` agents, drawing touches none of them — making this the fastest way to sanity-check a Foundry-backed graph before you spend a single token. One structural constraint surfaces while drawing: the fan-in target must be a plain `@executor` accepting a `list[AgentExecutorResponse]` — an agent-executor can't be a direct fan-in target, because its input is a single message.

---

## Key takeaways

- **`request_info` is the human-in-the-loop primitive.** It suspends the workflow and returns a pending event; you resume with `run(responses={request_id: answer})`, and the resume key must match the suspend key exactly.
- **A workflow is an agent when you need it to be.** `workflow.as_agent()` gives any workflow the `.run()` contract — the one rule is that the start executor accepts `list[Message]`.
- **Observability is one call, driven by env vars.** `configure_otel_providers()` both enables and wires OpenTelemetry; console exporters need no backend, sensitive data stays off by default, and `load_dotenv()` must run first.
- **`WorkflowViz` reads shape, not behavior.** Mermaid and DOT are dependency-free and run no agents; image export needs the GraphViz binary, and fan-in targets must be plain executors.
- **The pieces compose.** Suspend a nested workflow, wrap it as an agent, trace the whole tree by one trace ID, and draw the wiring before you run it — the same small workflow vocabulary spans design, execution, and inspection.

---

## Interactive diagrams

Explore the concepts in this guide as self-contained, pan/zoom interactive diagrams (light/dark, no dependencies):

- [Human In The Loop](/blog/diagrams/maf-py-47-human-in-the-loop.html)
