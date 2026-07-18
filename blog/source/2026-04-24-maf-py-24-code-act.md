# Code Act

*Letting the agent write and run one Python program instead of looping tool-by-tool.*

---

## What this lesson demonstrates

CodeAct collapses the "model -> tool -> model -> tool" loop. Instead of the model picking one tool per turn, a connector adds a single `execute_code` tool: the model writes one short Python program that combines control flow, data transforms, and tool calls, and the sandbox runs it once. Provider-owned tools registered on the connector are not exposed directly to the model — the generated code reaches them via `call_tool("name", ...)` inside the sandbox.

The documented Python connector is Hyperlight (`agent-framework-hyperlight`), attached to a Foundry agent through `context_providers=[...]`.

## The core shape

```python
from agent_framework.hyperlight import HyperlightCodeActProvider

codeact = HyperlightCodeActProvider(
    tools=[fetch_users, compute],
    approval_mode="never_require",
)
agent = Agent(
    client=client,
    name="CodeActAgent",
    instructions="Prefer orchestrating work in a single execute_code block "
                 "using call_tool(...). End generated code with print(...).",
    context_providers=[codeact],
)
```

## The gotcha

Install with `pip install agent-framework-hyperlight --pre`; it ships separately from core and needs a supported Linux/Windows sandbox backend, so `execute_code` fails on unsupported platforms — the lesson wraps construction in a `try/except` and falls back to direct tool calling. To surface text, the generated code must end with `print(...)`; Hyperlight does not return the last expression. In-memory state does not persist across separate `execute_code` calls, and `call_tool(...)` runs the host callback in the host process (with host filesystem, network, and creds), not re-implemented in the sandbox.

## The Azure / MAF mapping

The agent is a `FoundryChatClient`-backed `Agent` with `AzureCliCredential`. Tools on the provider are hidden from the model as direct tools (reached via `call_tool`), while tools on `Agent(tools=...)` stay first-class. `approval_mode` controls whether `execute_code` pauses for user approval.

## Run it

`uv run tutorial/02-agents/16_code_act.py` — needs Foundry credentials via `az login`.

---

Next: [Session](/blog/posts/maf-py-25-session.html)
