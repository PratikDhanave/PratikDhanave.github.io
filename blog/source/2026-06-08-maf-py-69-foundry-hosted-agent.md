# Foundry Hosted Agent

*Packaging an agent as a container on Foundry Agent Service with ResponsesHostServer.*

---

## What it demonstrates

A "hosted agent" is your Agent packaged as a container and run on Microsoft Foundry Agent Service's managed infrastructure. You wrap the agent in a host server that exposes it over the OpenAI-compatible Responses protocol (a `/responses` HTTP endpoint); Foundry then handles scaling, session state, and a dedicated Entra identity for you. Locally you drive it with `azd ai agent`; for real you deploy with `azd provision && azd deploy`.

## One real excerpt

```python
from agent_framework_foundry_hosting import ResponsesHostServer

agent = Agent(
    client=client,
    name="hosted-helper",
    instructions="You are a helpful AI assistant. Keep your answers brief.",
    default_options={"store": False},  # the host persists history; don't double-store
)

server = ResponsesHostServer(agent)
server.run()  # blocking; listens on http://localhost:8088, exposes POST /responses
```

## The gotcha

Install the extra package `agent-framework-foundry-hosting` and import `ResponsesHostServer` from `agent_framework_foundry_hosting`. Set `store` to `False` in `default_options` — the hosting layer persists conversation history itself, so storing again on the model side duplicates it. `server.run()` is blocking and, when scaffolded via `azd ai agent init`, listens on `http://localhost:8088` exposing `POST /responses`. This program is meant to be launched by the Foundry host (`azd ai agent run`), not `uv run` directly — running it just starts the server process locally with no visible output.

## Azure / MAF mapping

The hosted agent is a plain `Agent` over `FoundryChatClient` (`project_endpoint` + `model` + `AzureCliCredential`). The doc uses `DefaultAzureCredential`; this repo standardizes on `AzureCliCredential` (your `az login` session) — both satisfy the same auth. Foundry supplies the container, scaling, and Entra identity around that unchanged agent.

## Run it

`uv run tutorial/04-hosting/05_foundry_hosted_agent.py` — needs Foundry creds (`az login`). Worked if there are no prints: `server.run()` blocks, serving `/responses` on port 8088.

---

Next: [Devui Discovery](/blog/posts/maf-py-70-devui-discovery.html)
