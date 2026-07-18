# Resettable Executors

*Executor state leaks when you reuse one workflow across independent runs. `.NET` has `IResettableExecutor`; Python's answer is simpler — never share state, build fresh instances from a factory.*

---

## What this lesson demonstrates

Executors are often **stateful** — they accumulate messages, count turns, or cache results. Reuse ONE workflow instance across independent runs and that leftover state leaks into the next run. In `.NET` the fix is the `IResettableExecutor` interface (a `ResetAsync()` the runtime calls between runs). In Python there is no such interface — the doc says the concept "does not apply."

The Pythonic answer: build a **fresh** workflow + executor instance for every independent run by wrapping construction in a factory function. The lesson proves it by running two topics through a shared workflow (state leaks — the second output reports "seen 2") and then through fresh instances (each correctly reports "seen 1").

## One real excerpt

The factory is the Python replacement for `IResettableExecutor` — instead of resetting shared state, you never share it:

```python
def build_workflow(client: FoundryChatClient):
    agent = Agent(client=client, name="Summarizer",
                  instructions="You write terse, factual one-sentence summaries.")
    summarize = SummarizeExecutor(agent)
    history = HistoryExecutor()        # self.seen = [] — mutable, must be fresh per run
    return WorkflowBuilder(start_executor=summarize).add_edge(summarize, history).build()

# The fix: a fresh workflow per run — each run sees "seen 1".
for topic in topics:
    workflow = build_workflow(client)
    result = await workflow.run(topic)
```

## The gotcha

A `Workflow` instance **preserves state across calls** to `run()` — reusing one for two unrelated tasks shares mutable executor state. Builders are mutable, workflows are immutable; call `build()` again (via the helper) for independent instances. Crucially, executors passed to `WorkflowBuilder` are shared objects, so instantiate them **inside** the factory too — sharing one executor across builds still shares its state. There is no runtime reset hook: executor state is just plain instance attributes.

## How it maps to Azure AI Foundry

The `SummarizeExecutor` wraps a real `FoundryChatClient` agent (`AzureCliCredential`); only `.run()` touches the network — construction is offline. The client can be reused across builds (it's stateless per call); it's the executor's own `list`/counters you must not share.

## Run it

```bash
uv run tutorial/03-workflows/advanced/03_resettable_executors.py
```

Needs Foundry credentials (`az login`). The reused workflow climbs to "seen 2"; the fresh instances each stay at "seen 1".

---

Next: [Sub Workflows](/blog/posts/maf-py-59-sub-workflows.html)
