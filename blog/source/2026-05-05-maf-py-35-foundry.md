# Foundry

*The two ways to reach a model in an Azure AI Foundry project.*

---

## What it demonstrates

Microsoft Foundry gives you two doors to a model deployed in a Foundry project, and picking the right one decides who owns the agent's behavior:

1. **`FoundryChatClient`** — direct inference against the Foundry Responses endpoint. *Your* app owns the instructions, tools, and conversation loop; you wrap the client in a plain `Agent(client=...)`. This is the Foundry-first path the whole tutorial uses.
2. **`FoundryAgent`** — a service-managed agent whose definition (instructions + tools) lives in the Foundry portal. You connect by name and version; the server is the source of truth.

This lesson runs variant #1 end to end, non-streaming then streaming, from the same client.

## The code

```python
from agent_framework import Agent
from agent_framework.foundry import FoundryChatClient
from azure.identity import AzureCliCredential

client = FoundryChatClient(
    project_endpoint=os.environ["FOUNDRY_PROJECT_ENDPOINT"],
    model=os.environ["FOUNDRY_MODEL"],
    credential=AzureCliCredential(),
)
agent = Agent(client=client, name="FoundryJoker",
              instructions="You are good at telling short, clean jokes.")
```

Then `await agent.run(...)` for one full response, or `async for update in agent.run_stream(...)` for token-by-token.

## The gotcha

`FoundryChatClient` uses the **project** endpoint (`https://<project>.services.ai.azure.com`), *not* an Azure OpenAI resource endpoint (`*.openai.azure.com` — that's the OpenAI provider). All Foundry clients now live under `agent_framework.foundry`; the older `agent_framework.azure` surfaces were removed. And note the behavioral split: with `FoundryChatClient` the loop is local so per-run instructions and tools are honored, but with `FoundryAgent` the Foundry-side definition wins and run-time overrides are mostly ignored.

## Azure / MAF mapping

Auth is credential-based — `AzureCliCredential()` reads your `az login` session, no API keys. Hosted tools are class-method factories like `FoundryChatClient.get_web_search_tool()` passed via `tools=[...]`; they build without a client instance.

## Run it

`uv run tutorial/02-agents/providers/01_foundry.py` — needs Foundry creds. You get a joke via `run`, then another streamed under `== run_stream ==`.

---

Next: [Custom Provider](/blog/posts/maf-py-36-custom-provider.html)
