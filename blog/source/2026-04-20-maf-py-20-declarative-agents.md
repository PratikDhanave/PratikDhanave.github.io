# Declarative Agents

*Defining a Microsoft Agent Framework agent from a YAML spec instead of code.*

---

## What this lesson demonstrates

Instead of constructing an agent in code, you describe it in a YAML spec — kind, name, instructions, model plus connection — and let `AgentFactory` build a runnable agent from that text. This makes agents easy to version, share, and edit without touching Python: the same spec drives dev, test, and prod.

The `agent-framework-declarative` package provides `AgentFactory`, with two entry points: `create_agent_from_yaml(<yaml str>)` and `create_agent_from_yaml_path(<path>)`. Both return an async context manager.

## The core call

```python
async with (
    AzureCliCredential() as credential,
    AgentFactory(client_kwargs={"credential": credential}).create_agent_from_yaml(
        YAML_DEFINITION,
        safe_mode=False,
    ) as agent,
):
    response = await agent.run("What is a declarative agent, in one sentence?")
    print("Agent response:", response.text)
```

In the YAML, `=Env.NAME` pulls values from environment variables at load time, so the `model.connection.endpoint` resolves to `=Env.FOUNDRY_PROJECT_ENDPOINT`.

## The gotcha

The chat client is not built by hand here. The YAML's `model.connection` block plus `AgentFactory(client_kwargs={"credential": ...})` build it, and `safe_mode=False` is required to let the spec instantiate a live client and tools. Note the async credential import: `from azure.identity.aio import AzureCliCredential`.

## The Azure / MAF mapping

This is the one Foundry lesson that does not use the usual `Agent(client=FoundryChatClient(...))` shape — declarative agents intentionally move client construction into the spec. The connection still targets Azure AI Foundry via `FOUNDRY_PROJECT_ENDPOINT`, so it stays Foundry-only.

## Run it

`uv run tutorial/02-agents/12_declarative_agents.py` — needs Foundry credentials via `az login`.

---

Next: [Evaluation](/blog/posts/maf-py-21-evaluation.html)
