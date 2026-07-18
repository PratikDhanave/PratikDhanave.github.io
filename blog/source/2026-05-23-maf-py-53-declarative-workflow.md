# Declarative Workflow

*Declare the orchestration in YAML instead of Python — ordered actions load at runtime via WorkflowFactory, with agents resolved by name and PowerFx expressions for logic.*

---

## What this lesson demonstrates

Instead of wiring a workflow in Python with `WorkflowBuilder`, you can **declare** it in a YAML file and load it at runtime. The YAML lists ordered `actions` (set variables, call agents, branch, loop) and the framework turns them into an executable workflow. This lets non-developers edit the flow and keeps orchestration as data rather than code.

## One real excerpt

Register a Foundry agent by name, then load the YAML into a runnable workflow:

```python
factory = WorkflowFactory()
factory.register_agent("PoetAgent", poet)

with tempfile.TemporaryDirectory() as tmp:
    yaml_path = Path(tmp) / "haiku-workflow.yaml"
    yaml_path.write_text(WORKFLOW_YAML)
    workflow = factory.create_workflow_from_yaml_path(yaml_path)

result = await workflow.run({"topic": "the monsoon over Mumbai"})
```

The YAML's `InvokeAzureAgent` action references `agent: { name: PoetAgent }`, which resolves against that `register_agent` call — so a Foundry agent drops straight in.

## The gotcha

The declarative support is a **separate package**: `pip install agent-framework-declarative --pre`, imported as `from agent_framework.declarative import WorkflowFactory`. The Python declarative shape is name-based (top-level `name`, optional `inputs`, a list of `actions`) — do **not** copy the C# `kind: Workflow` / `trigger:` shape; the languages differ. Variables are namespaced (`Local.*`, `Workflow.Inputs.*`, `Workflow.Outputs.*`), and values starting with `=` are PowerFx expressions (e.g. `=Concat(...)`) while bare values are literals. That PowerFx dependency is why Python 3.14 isn't yet supported. The doc only ships a **path** loader, so the YAML is written to a temp file first.

## How it maps to Azure AI Foundry

`PoetAgent` is an ordinary `FoundryChatClient` agent (with `AzureCliCredential`) — nothing declarative-specific. The factory bridges the YAML's `agent.name` to the real registered instance. Read finished values with `result.get_outputs()` and step-by-step values with `result.get_intermediate_outputs()`.

## Run it

```bash
uv run tutorial/03-workflows/10_declarative_workflow.py
```

Needs Foundry credentials. You should see `Loaded workflow: haiku-workflow`, then a haiku as the output.

---

Next: [Workflow Observability](/blog/posts/maf-py-54-workflow-observability.html)
