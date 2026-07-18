# Observability

*Turning an agent run into OpenTelemetry spans you can read in the console or ship to a collector.*

---

## What it demonstrates

An agent run is a tree of operations: the run, each model call, each tool call. Observability turns that tree into OpenTelemetry **spans** so you can see latency, token counts, and tool activity — printed to the console here, or exported to Jaeger / Azure Monitor in production. There is one entry point, called once at startup before any agent runs:

```python
from agent_framework.observability import configure_otel_providers
configure_otel_providers(enable_console_exporters=True, enable_sensitive_data=True)
```

`enable_sensitive_data=True` additionally captures prompt/response/tool-arg **content** in the spans; setting `OTEL_EXPORTER_OTLP_ENDPOINT` and dropping the console flag exports to a real collector instead.

## The code

```python
async def main() -> None:
    configure_otel_providers(enable_console_exporters=True, enable_sensitive_data=True)
    agent = build_agent()
    result = await agent.run("Name three Indian classical dance forms.")
    print(f"\nAgent: {result}\n")
```

The console exporter then prints JSON span objects around the answer — one for the run, one for the model call.

## The gotcha

Call `configure_otel_providers(...)` **once, first**, before constructing or running any agent — it wires up the global tracer providers, and later agents won't be traced if you configure after they run. And treat `enable_sensitive_data=True` with care: it's handy while learning, but it puts raw prompt and response text into your spans, which you likely don't want leaving the process in production.

## Azure / MAF mapping

The traced agent is a plain `FoundryChatClient` agent on Azure AI Foundry with `AzureCliCredential`. Observability is orthogonal to the client — the same spans emit whichever provider backs the agent, and the OTLP endpoint can point at Azure Monitor.

## Run it

`uv run tutorial/02-agents/04_observability.py` — needs Foundry creds. It worked if JSON span objects print around the answer.

---

Next: [Security](/blog/posts/maf-py-13-security.html)
