# Workflow Observability

*Turn a workflow run into a tree of OpenTelemetry spans — workflow.build, workflow.run, executor.process, edge_group.process, message.send — with one setup call.*

---

## What this lesson demonstrates

Observability turns a workflow run into a tree of OpenTelemetry spans you can inspect. On top of the usual GenAI agent spans, a workflow emits its own: `workflow.build` when `.build()` runs, `workflow.run` around the whole execution, `executor.process {id}` per node, `edge_group.process` per routing decision, and `message.send` per hop. Turning it on is a **single setup call** — the framework instruments the builder and the run for you.

## One real excerpt

Enable instrumentation, then wrap the run in a root span so every workflow span shares one parent:

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

## The gotcha

`configure_otel_providers()` (from `agent_framework.observability`) both **enables** instrumentation and wires trace/log/metric providers from env vars. Enabling is env-driven: `ENABLE_INSTRUMENTATION=true` activates AF code paths, `ENABLE_CONSOLE_EXPORTERS=true` prints spans to your console (no backend needed), and `OTEL_EXPORTER_OTLP_ENDPOINT=http://localhost:4317` ships them to an Aspire Dashboard. `ENABLE_SENSITIVE_DATA=false` by default — message content and executor inputs/outputs are only populated when it's true, so keep it off in prod. Agent Framework does **not** auto-load `.env`, so `load_dotenv()` must run *before* the setup call.

## How it maps to Azure AI Foundry

The traced graph is the Writer→Reviewer pipeline, both agents backed by one `FoundryChatClient` (with `AzureCliCredential`). The printed `trace_id` lets you find the whole span tree — spanning the Foundry model calls and the workflow routing — in your OpenTelemetry backend.

## Run it

```bash
ENABLE_CONSOLE_EXPORTERS=true uv run tutorial/03-workflows/11_workflow_observability.py
```

Needs Foundry credentials. You'll see a Trace ID and `[output]` lines, plus the spans if the console exporter is on.

---

Next: [Visualization](/blog/posts/maf-py-55-visualization.html)
