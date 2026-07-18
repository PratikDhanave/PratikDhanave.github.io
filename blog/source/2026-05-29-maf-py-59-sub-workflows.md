# Sub Workflows

*A whole workflow run as a single executor inside a parent. Wrap the inner graph in `WorkflowExecutor`, drop it into the parent like any node, and compose big systems from small, testable pieces.*

---

## What this lesson demonstrates

A sub-workflow is a **whole workflow run as a single executor** inside a parent workflow. You build an inner workflow, wrap it in a `WorkflowExecutor`, and drop that wrapper into the parent graph like any other node. The inner graph runs its own superstep loop with its own isolated state; the parent only sees messages entering and leaving through its edges.

The lesson builds an inner analyst → validator "analysis pipeline," wraps it, and nests it between a coordinator and a reviewer in the parent — so from the parent's view the whole pipeline is a single step.

## One real excerpt

A raw `Workflow` can't be added to `WorkflowBuilder` directly — it must be wrapped first, and the inner graph ends with a `str` adapter so its output type lines up with the parent's next agent:

```python
analysis_pipeline = (
    WorkflowBuilder(start_executor=analyst)
    .add_edge(analyst, validator)
    .add_edge(validator, collect)   # collect: AgentExecutorResponse -> yield_output(str)
    .build()
)
return WorkflowExecutor(workflow=analysis_pipeline, id="analysis-pipeline")
```

## The gotcha

Wrap a `Workflow` with `WorkflowExecutor(workflow=inner, id="...")` — agents can be added to a builder directly, but a raw `Workflow` **must** be wrapped first. The wrapper inherits the inner workflow's input/output types, so the parent's edges must line up with them (hence the `collect` adapter forcing a `str` output). By default (`allow_direct_output=False`) inner `yield_output` results are forwarded as messages to the next parent executor; set `allow_direct_output=True` to yield them straight to the parent's event stream. `propagate_request=True` forwards inner `request_info()` calls to the caller; the default wraps them in a `SubWorkflowRequestMessage`. Nesting works to arbitrary depth, but each level adds a superstep loop — keep depth reasonable.

## How it maps to Azure AI Foundry

Every agent (analyst, validator, coordinator, reviewer) is a `FoundryChatClient` + `AzureCliCredential` agent. Construction is offline; only `.run()` calls the model. The sub-workflow's two agents run hidden inside a single parent step — you only see the reviewer's terminal output.

## Run it

```bash
uv run tutorial/03-workflows/advanced/04_sub_workflows.py
```

Needs Foundry credentials (`az login`). Output is the reviewer's two-sentence executive summary of the nested analysis.

---

Next: [Sequential](/blog/posts/maf-py-60-sequential.html)
