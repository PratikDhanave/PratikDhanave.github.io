# Evaluation

*Scoring Microsoft Agent Framework agent outputs offline with a LocalEvaluator.*

---

## What this lesson demonstrates

The evaluation framework measures agent quality, safety, and correctness. `evaluate_agent()` runs your agent once per query, turns each interaction into an `EvalItem`, and scores it with one or more evaluators. A `LocalEvaluator` runs fast, offline checks (keywords, tool calls, custom functions) with no extra API calls — ideal for CI smoke tests and inner-loop iteration.

## The core call

```python
@evaluator
def is_concise(response: str) -> bool:
    return len(response.split()) < 80

local = LocalEvaluator(keyword_check("weather"), is_concise, mentions_units)
results = await evaluate_agent(
    agent=agent,
    queries=["What's the weather in Seattle today?", "Give me the weather for Portland."],
    evaluators=local,
)
for r in results:
    print(f"{r.provider}: {r.passed}/{r.total} items passed")
```

The `@evaluator` decorator wraps a plain function; its parameter names decide what data it receives — supported names include `query`, `response`, `expected_output`, `expected_tool_calls`, `conversation`, `tools`, and `context`. Checks may return a `bool`, a `float` (>= 0.5 passes), a dict with `score`/`passed`, or a `CheckResult`.

## The gotcha

`evaluate_agent` returns one `EvalResults` per evaluator provider, each with `.provider`, `.passed`, `.total`, and `.raise_for_status()` (which raises `EvalNotPassedError`). Call `raise_for_status()` to turn evaluation into a hard gate in CI. `expected_output` is paired positionally with `queries`.

## The Azure / MAF mapping

The agent under test is a `FoundryChatClient`-backed `Agent`. Cloud LLM-as-judge scoring (FoundryEvals: relevance, coherence, groundedness, safety) is available via `agent_framework.foundry`, but it needs a Foundry project client and a judge-model deployment. This lesson uses `LocalEvaluator` so it runs with zero extra setup.

## Run it

`uv run tutorial/02-agents/13_evaluation.py` — the agent runs against Foundry, so `az login` is still required.

---

Next: [Skills](/blog/posts/maf-py-22-skills.html)
