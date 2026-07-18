# Concurrent

*Run several agents on the same prompt in parallel, then fan their answers back in. `ConcurrentBuilder` wires the fan-out/fan-in graph — latency is max(agent), not sum.*

---

## What this lesson demonstrates

Concurrent orchestration runs several agents on the **same prompt in parallel**. Each works independently, then a built-in aggregator fans their answers back in. It fits ensemble reasoning, brainstorming, and voting — where diverse perspectives on one input are the whole point. Latency is `max(agent)`, not the sum.

`ConcurrentBuilder(participants=[...]).build()` wires the fan-out/fan-in graph for you; you just hand it a list of agents (or custom `Executor`s). The lesson runs a researcher, a marketer, and a legal reviewer on one product-launch prompt.

## One real excerpt

The default aggregator yields one `AgentResponse` holding one assistant message per participant:

```python
from agent_framework.orchestrations import ConcurrentBuilder

return ConcurrentBuilder(participants=[researcher, marketer, legal]).build()

# ...
events = await workflow.run("We are launching a budget-friendly electric bike...")
final: AgentResponse = events.get_outputs()[0]
for msg in final.messages:                       # one message per expert
    print(f"[{msg.author_name or 'assistant'}]:\n{msg.text}")
```

## The gotcha

Participants run with **no ordering** — all in parallel — and the default aggregator's single `AgentResponse` does **not** include the original user prompt, only the experts' replies (read via `events.get_outputs()[0].messages`; `msg.author_name` labels each). Pass `intermediate_output_from=[...]` to also surface each listed participant's own output as `"intermediate"` events (handy in `stream=True` mode). To replace fan-in entirely — e.g. a summarizer agent that consolidates every expert into one string — use `.with_aggregator(callback)`.

## How it maps to Azure AI Foundry

All three experts are `FoundryChatClient` + `AzureCliCredential` agents; the builder is client-agnostic. Because they run concurrently, the three Foundry calls overlap — total wall-clock time is the slowest single expert, not the sum of all three.

## Run it

```bash
uv run tutorial/03-workflows/orchestrations/02_concurrent.py
```

Needs Foundry credentials (`az login`). You should see a `===== Final Aggregated Results =====` block with one section per expert (researcher / marketer / legal).

---

Next: [Handoff](/blog/posts/maf-py-62-handoff.html)
