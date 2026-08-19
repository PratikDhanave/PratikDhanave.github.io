# Building a Context Pipeline

*Everything in this series — the budget, the system prompt, retrieval, memory, tools, and compaction — comes together as a pipeline that assembles the right window on every single turn, deliberately rather than by accident.*

Across this series we treated the components of context one at a time: the token budget, the system prompt, retrieval, memory and history, tools and structured data, and compaction. In a real system they are not separate — they run together, on every turn, to produce the one context the model sees. This final post assembles them into a **context pipeline**: an explicit stage that decides what goes into the window each time the agent thinks. Making that assembly deliberate is what turns the individual techniques into a reliable system.

## The context is assembled, not accumulated

The central idea is a shift in stance. In a naive agent, context *accumulates* — each turn appends to a growing blob, and whatever is there is what the model gets. In an engineered agent, context is *assembled* — on each turn, a pipeline deliberately constructs the window from parts, within the budget, and discards the rest. The difference is control. Accumulation gives you a window that drifts toward bloat and noise; assembly gives you a window you designed for the task at hand.

Concretely, a context pipeline runs each turn and produces the final context by composing:

1. the **system prompt** — the durable policy, always present;
2. **relevant long-term memory** — retrieved facts about the user or task;
3. **retrieved knowledge** — documents fetched for this turn's query;
4. **the tools** the task needs, described precisely;
5. **compacted conversation history** — recent turns verbatim, older turns summarized, critical facts pinned;
6. the **current input** — the user's actual request;
7. reserved **output space**.

Each is drawn from an earlier post; the pipeline is where they meet.

## A sketch of the pipeline

In outline, the assembly stage looks like this:

```python
def build_context(turn, budget):
    parts = []

    # 1. Durable policy — always present, place at the top.
    parts.append(system_prompt())

    # 2. Long-term memory relevant to this turn (retrieval over memory).
    parts += retrieve_memories(turn.user_input, k=3)

    # 3. Knowledge retrieval for this query — precision over volume.
    parts += rerank(retrieve_docs(turn.user_input, k=20))[:5]

    # 4. Only the tools this task needs.
    tools = select_tools(turn)

    # 5. History, compacted to fit: recent verbatim + summary + pinned facts.
    parts += compact_history(turn.history, budget=budget.for_history)

    # 6. The current request, at the end (edges get the most attention).
    parts.append(turn.user_input)

    # Enforce the budget: rank and trim to fit, never blind-truncate.
    return assemble_within_budget(parts, tools, budget)
```

The code is schematic, but the shape is the point: every turn, the agent *rebuilds* its context from curated parts, applies the budget, and orders things so the most important content sits at the edges rather than the middle. Nothing is in the window by accident.

## Ordering and the budget, one more time

Two cross-cutting rules from the series govern the assembly. **Order for attention:** because models use the beginning and end of a context best, put the anchoring system prompt near the top and the current request near the end, and place the highest-relevance retrieved content at the edges rather than buried in the center. **Enforce the budget:** when the composed parts exceed the target, rank by expected relevance and trim the tail — drop the least valuable retrieved chunk, compress history harder — rather than truncating whatever happens to be last. The pipeline is where "treat context as a budget" stops being advice and becomes code.

## Evaluate the pipeline, not just the prompt

Because the pipeline has many moving parts, you cannot tune it by staring at one prompt. Evaluate it end to end: run representative tasks and measure whether the model gets what it needs. When an answer is wrong, inspect the *assembled context* for that turn — was the needed fact retrieved? was it buried in the middle? did stale history contradict it? did tool bloat crowd it out? This is the debugging reframe from the first post, now operational: most failures are context failures, and a pipeline gives you a single place to see and fix what the model actually saw. Log the assembled context in development; it is the most useful artifact you have.

## The discipline, in one sentence

Context engineering, assembled here, comes down to this: on every turn, deliberately compose the smallest context that contains what the task needs — durable policy, the right retrieved knowledge, the relevant memory, only the necessary tools, compacted history, and the current request — ordered so the important parts land where the model attends, and trimmed to a budget. Do that well and your agents are cheaper, faster, and markedly more reliable; the model was always capable, and the context is what let it show. That is the whole discipline, and the pipeline is how you practice it.

## Key takeaways

- Engineered agents *assemble* context each turn from curated parts rather than *accumulating* a growing blob — assembly is what gives you control over the window.
- A context pipeline composes, per turn: system prompt, relevant long-term memory, retrieved knowledge, only the needed tools, compacted history with pinned facts, the current input, and reserved output space.
- Two cross-cutting rules govern assembly: order for attention (anchors and current request at the edges, key content out of the middle) and enforce the budget by ranking and trimming, never blind-truncating.
- Evaluate the pipeline end to end and, when answers are wrong, inspect the assembled context for that turn — most failures are context failures, and the pipeline is the single place to see and fix them.
- The discipline in one sentence: each turn, deliberately compose the smallest context containing what the task needs, ordered for attention and trimmed to a budget.

## Further reading

- [Lost in the Middle: How Language Models Use Long Contexts — Liu et al., 2023](https://arxiv.org/abs/2307.03172)
- [OpenAI Cookbook](https://github.com/openai/openai-cookbook)
- [Anthropic documentation](https://docs.anthropic.com)
