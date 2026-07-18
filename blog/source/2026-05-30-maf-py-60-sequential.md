# Sequential

*Wire agents into a pipeline where each runs in turn and feeds the next. Hand a list to `SequentialBuilder`, call `.build()`, run it once — draft then review, extract then summarize.*

---

## What this lesson demonstrates

Sequential orchestration wires agents into a **pipeline**: each agent runs in turn and passes its output to the next. It fits any "each step builds on the last" job — draft then review, extract then summarize, translate then proof-read. You hand a list of participants to `SequentialBuilder`, call `.build()`, and run it once with a prompt.

The lesson chains a copywriter (drafts a marketing sentence) into a reviewer (critiques the draft), showing how order in the list *is* the execution order.

## One real excerpt

The builder lives in `agent_framework.orchestrations`; participants run strictly in list order:

```python
from agent_framework.orchestrations import SequentialBuilder

return SequentialBuilder(participants=[writer, reviewer]).build()

# ...
events = await workflow.run("Write a tagline for a budget-friendly eBike.")
final: AgentResponse = events.get_outputs()[0]   # ONLY the last agent's messages
for msg in final.messages:
    print(f"[{msg.author_name or 'assistant'}]\n{msg.text}\n")
```

## The gotcha

By default each agent sees the **full prior conversation** (inputs + all responses). Pass `chain_only_agent_responses=True` so each agent consumes only the previous agent's reply — handy for translation or progressive-refinement chains. Also, `events.get_outputs()[0]` is an `AgentResponse` holding **only the last agent's messages**, not the whole chat; use `msg.author_name` to tell which agent produced each message.

## How it maps to Azure AI Foundry

Both participants are `FoundryChatClient` + `AzureCliCredential` agents; `SequentialBuilder` is client-agnostic, so the same pipeline works with any provider. Construction is offline — only `.run()` calls the model, once per participant in order.

## Run it

```bash
uv run tutorial/03-workflows/orchestrations/01_sequential.py
```

Needs Foundry credentials (`az login`). You should see a `===== Final Response =====` block with each participant's messages labelled by name.

---

Next: [Concurrent](/blog/posts/maf-py-61-concurrent.html)
