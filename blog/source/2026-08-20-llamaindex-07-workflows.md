# Workflows

*An agent's reasoning loop is flexible but opaque and hard to control. A workflow is the opposite: you make the orchestration explicit as steps and events, trading some autonomy for the predictability, testability, and control that complex applications need.*

An agent decides its own path through a reasoning loop — powerful, but hard to constrain, test, and debug when the application grows complex. LlamaIndex's answer is **Workflows**: an **event-driven** abstraction for orchestrating steps and LLM calls explicitly. Workflows are now the modern core for building complex agentic applications in LlamaIndex. This seventh post covers what they are and why event-driven orchestration matters.

## Why not just use an agent?

A single agent works well until you need control the reasoning loop won't give you: a guaranteed sequence of stages, a branch that depends on a validation result, a human approval gate, retryable steps, parallel work that fans out and joins. Cramming all that into one agent's prompt makes it fragile and unpredictable — you're hoping the LLM follows the process. A **workflow** inverts this: *you* define the process as explicit steps, and let the LLM make decisions *within* steps. You trade some of the agent's open-ended autonomy for orchestration you can see, test, and control — the same autonomy-vs-control trade-off that runs through all agent design.

## The event-driven model

A LlamaIndex **Workflow** is built from **steps** that communicate by emitting and receiving **events**. A step is a function that receives an event and emits one or more events; the events wire the steps together. Rather than a hardcoded call sequence, the workflow *reacts*: an emitted event triggers whatever step listens for it.

```python
from llama_index.core.workflow import Workflow, step, StartEvent, StopEvent, Event

class RetrievedEvent(Event):
    nodes: list

class RAGWorkflow(Workflow):
    @step
    async def retrieve(self, ev: StartEvent) -> RetrievedEvent:
        nodes = do_retrieval(ev.query)
        return RetrievedEvent(nodes=nodes)

    @step
    async def synthesize(self, ev: RetrievedEvent) -> StopEvent:
        answer = synthesize_answer(ev.nodes)
        return StopEvent(result=answer)
```

The event types define the flow: `retrieve` emits a `RetrievedEvent`, which triggers `synthesize`. This looks like more ceremony than an agent for a two-step RAG, and it is — the payoff shows up as the process gets complex.

## Why event-driven, specifically

The event-driven design isn't decoration; it's what makes complex orchestration tractable:

- **Branching** — a step emits one of several event types (e.g. `RelevantEvent` vs. `NeedsRewriteEvent`), and different steps handle each. Conditional logic — like the corrective-RAG "if retrieval is weak, rewrite and retry" pattern — becomes explicit control flow instead of hope-the-prompt-works.
- **Loops** — a step can emit an event that routes back to an earlier step, giving bounded, visible retry/refine cycles instead of an opaque agent loop.
- **Parallelism** — emit several events at once to fan out concurrent work (retrieve from multiple sources simultaneously), then join the results when they arrive.
- **Human-in-the-loop** — a step can wait for an external event (an approval) before continuing, which is how you build approval gates and pauses.

Because the wiring is events between typed steps, the whole flow is inspectable and each step is independently testable — the two things an all-in-one agent prompt makes hard.

## Composing agents and workflows

Workflows and agents aren't opposed — they compose. A step in a workflow can *run an agent* (give the LLM autonomy for that bounded sub-problem), while the workflow enforces the overall process around it. This is the practical sweet spot for complex systems: explicit orchestration for the parts that need reliability and control (validation, gates, sequencing, error handling), delegated agent reasoning for the parts that genuinely need open-ended judgment. Rather than "agent vs. workflow," mature LlamaIndex applications use workflows as the backbone and agents as steps within them — structure where you need predictability, autonomy where you need flexibility.

## Key takeaways

- Workflows make orchestration explicit — steps and events you define — trading an agent's open-ended autonomy for predictability, testability, and control.
- Reach for a workflow over a single agent when you need guaranteed sequencing, branching, loops, parallelism, or human approval gates that a reasoning loop can't reliably enforce.
- The model is event-driven: steps are functions that receive and emit typed events, and the events wire the flow — the workflow reacts rather than following a hardcoded sequence.
- Event-driven design is what makes branching, bounded loops, fan-out/join parallelism, and human-in-the-loop waits into explicit, inspectable, independently testable control flow.
- Workflows and agents compose: use workflows as the reliable backbone and run agents inside steps for sub-problems that need open-ended judgment — structure where you need predictability, autonomy where you need flexibility.

## Further reading

- [LlamaIndex documentation](https://docs.llamaindex.ai)
- [Agentic RAG series](/blog/series/agentic-rag/)
- [LlamaIndex, Concept by Concept — start of the series](/blog/posts/llamaindex-01-what-is-llamaindex.html)
