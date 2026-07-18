# Devui Tracing

*Rendering the OpenTelemetry spans an agent already emits as a timeline with serve(tracing_enabled=True).*

---

## What it demonstrates

DevUI can capture and display the OpenTelemetry (OTel) traces Agent Framework already emits during execution. DevUI does NOT create its own spans — it collects the GenAI spans the framework produces (LLM calls, tool calls, agent runs) and renders them as a timeline in its debug panel. This lesson launches DevUI programmatically with tracing turned on, so a browser session against the agent shows the full span hierarchy: run the agent in the UI, then open the debug panel.

## One real excerpt

```python
from agent_framework.devui import serve

agent = await build_agent()  # a Foundry agent with a get_weather tool (a nice span to inspect)

print("Starting DevUI with tracing enabled at http://localhost:8080")
serve(
    entities=[agent],
    tracing_enabled=True,  # wires OTel span capture into the debug panel
)
```

## The gotcha

The programmatic flag is `tracing_enabled`, not `tracing` — the CLI equivalent is `devui ./agents --tracing`. Without an OTLP collector, traces are captured locally and shown only in the DevUI debug panel; to export elsewhere (Jaeger, Zipkin, Azure Monitor, Datadog) set the `OTLP_ENDPOINT` env var, e.g. `OTLP_ENDPOINT=http://localhost:4317`. `serve()` starts a blocking web server and is a normal synchronous call, so build the agent asynchronously in `main()` first, then hand the finished agent to `serve()`.

## Azure / MAF mapping

The traced agent is a plain `Agent` over `FoundryChatClient` (`project_endpoint` + `model` + `AzureCliCredential`) with a local `get_weather` tool. The spans DevUI shows are the GenAI spans the Foundry client and tool execution already emit — tracing is observability layered on top, not a change to how the agent runs.

## Run it

`uv run tutorial/04-hosting/07_devui_tracing.py` — needs Foundry creds (`az login`) and the hosting extra. Worked if it prints "Starting DevUI with tracing enabled…" then the server blocks; open the URL, run the agent, and inspect the trace timeline.

---

Next: [Getting Started](/blog/posts/maf-py-72-getting-started.html)
