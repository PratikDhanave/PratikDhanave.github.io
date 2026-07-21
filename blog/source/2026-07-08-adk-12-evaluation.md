# Google ADK Evaluation: Scoring the Trajectory, Not Just the Answer
*How ADK turns "did the agent behave correctly?" into a number you can gate a merge on.*

---

You can't improve what you can't measure, and for agents "measure" is subtler than it looks. An LLM agent can produce a perfectly plausible answer by taking completely the wrong actions — calling no tool and hallucinating, or calling the wrong tool and getting lucky. A test that only checks the final text will wave that through. Google's [Agent Development Kit](https://google.github.io/adk-docs/) treats evaluation as a first-class concern: you record cases, then score each one along **two** axes — the **trajectory** (did it call the right tools, with the right arguments, in the right order?) and the **final response** (is the answer close enough to a reference?).

This post is the thirteenth in a series walking through ADK concept by concept. It's also the one place where the Python and Go stories diverge sharply, so I'll be honest about the gap.

## Two metrics, two questions

ADK's built-in metrics split cleanly:

| Metric | Question | Default gate |
|--------|----------|--------------|
| `tool_trajectory_avg_score` | Did it take the *right tool path*? | `1.0` (exact match) |
| `response_match_score` | Is the *answer* close to the reference? | `0.7` (ROUGE-1 overlap) |

The trajectory metric is usually the more important of the two, and its threshold reflects that: a single wrong tool call is a real defect even when the answer reads fine, so the bar is an exact `1.0`. The response metric is deliberately lenient — wording varies, so it uses ROUGE-1 (unigram overlap) and passes around `0.7`.

Both are simple enough to reason about directly. Here's a faithful, simplified version of what each computes — trajectory match is a position-by-position comparison of name **and** args:

```python
def tool_trajectory_avg_score(expected, actual) -> float:
    """Fraction of tool calls matching by name AND args, position by position."""
    if not expected and not actual:
        return 1.0
    if not expected:
        return 0.0
    matches = sum(
        1 for i, exp in enumerate(expected)
        if i < len(actual)
        and actual[i]["name"] == exp["name"]
        and actual[i]["args"] == exp["args"]
    )
    # Divide by the longer sequence so extra spurious calls are penalized too.
    return matches / max(len(expected), len(actual))


def response_match_score(reference: str, actual: str) -> float:
    """ROUGE-1 recall: fraction of the reference's tokens present in the answer."""
    ref = tokens(reference)
    if not ref:
        return 1.0
    got = set(tokens(actual))
    return sum(1 for t in ref if t in got) / len(ref)
```

Note that dividing by `max(len(expected), len(actual))` means a spurious *extra* tool call drags the score down too — the agent that does the right thing *and then* an unnecessary follow-up call is not a `1.0`. The real ADK metric uses ROUGE-1 F-measure with multiple references; this recall-only form keeps the mechanics visible.

The Go form is the same arithmetic — worth showing because ADK is dual-language and the metric functions port cleanly even where the surrounding tooling does not:

```go
func ToolTrajectoryAvgScore(expected, actual []ToolCall) float64 {
    if len(expected) == 0 && len(actual) == 0 {
        return 1.0
    }
    if len(expected) == 0 {
        return 0.0
    }
    matches := 0
    for i, exp := range expected {
        if i < len(actual) && actual[i].Name == exp.Name &&
            reflect.DeepEqual(actual[i].Args, exp.Args) {
            matches++
        }
    }
    denom := len(expected)
    if len(actual) > denom {
        denom = len(actual) // penalize spurious extra calls
    }
    return float64(matches) / float64(denom)
}
```

## The eval set is a behavioral spec

An **eval set** is a JSON file of recorded cases. Each case carries the user query, the expected final response, and — crucially — the expected tool trajectory:

```json
{
  "eval_set_id": "weather_eval_set",
  "eval_cases": [
    {
      "eval_id": "weather_paris",
      "conversation": [{
        "user_content":   { "role": "user",  "parts": [{ "text": "What's the weather in Paris?" }] },
        "final_response": { "role": "model", "parts": [{ "text": "The weather in Paris is sunny, 22°C." }] },
        "intermediate_data": {
          "tool_uses": [{ "name": "get_weather", "args": { "city": "Paris" } }]
        }
      }]
    }
  ]
}
```

That file is not throwaway data — it's a set of **golden traces**, a machine-readable spec of *"this is what correct looks like."* Treat it the way you'd treat any test suite you commit and defend:

- **Include rejection cases.** A set of only happy paths can't catch an agent that approves everything. If a policy has *N* branches, you want ≥ *N + 1* cases.
- **Assert on arguments and order, not just names.** `check_status(id=WRONG)` is a broken agent even though the trajectory "looks right"; "check *then* purchase" must be enforced as a sequence.
- **One behavioral concern per case**, so a red build tells you *what* broke, not just *that* something did.
- **Add a case whenever you fix a bug** — the repro becomes a permanent regression guard.

> **Mental model:** the eval set is a serialized object graph, not a bespoke format. ADK models it as typed classes (`EvalSet` → `EvalCase` → `Invocation` → `IntermediateData`), and the JSON round-trips through them losslessly. The `intermediate_data.tool_uses` list *is* the expected trajectory.

## The criteria config and the `adk eval` CLI

Which metrics run, at what thresholds, and with which judge model lives in a separate **criteria config** — the same file the CLI consumes via `--config_file_path`. It replaces scattered `assert score >= 0.7` magic numbers with one place where every metric names its own bar:

```json
{
  "criteria": {
    "tool_trajectory_avg_score": { "threshold": 1.0, "match_type": "IN_ORDER" },
    "response_match_score":      { "threshold": 0.7 }
  }
}
```

Run it against your agent and eval set:

```bash
# Score an agent against an eval set, using the criteria config:
adk eval path/to/agent path/to/weather.evalset.json \
    --config_file_path=path/to/eval_criteria.json
```

Or wire the same thing into pytest for CI — this is the common gate pattern:

```python
from google.adk.evaluation.agent_evaluator import AgentEvaluator

await AgentEvaluator.evaluate(
    agent_module="weather_agent",
    eval_dataset_file_path_or_dir="weather.evalset.json",
)
```

Failing the gate blocks the merge, exactly like a broken unit test. Beyond the two lexical metrics, Python also ships model-graded ones — `final_response_match_v2` (an LLM judge that decides whether the answer *means* the reference, fixing ROUGE's paraphrase blindness), `hallucinations_v1` (groundedness), `safety_v1`, and rubric-based metrics — but those call an LLM, cost tokens, and need live credentials, so keep the lexical metrics as your fast, free, deterministic gate.

## One caveat: stochastic agents and Pass@k

A single green run can be luck, because the agent is stochastic. **Pass@k** quantifies that: run each case *n* times, count the passes *c*, and estimate the chance a sample of *k* runs contains at least one pass (the unbiased HumanEval estimator). `Pass@1` is just `c/n`; the *gap* between `Pass@1` and `Pass@5` is the agent's fragility. Gate deployment on the reliability *band*, not one lucky run.

## The Go gap, honestly

Everything above about `adk eval`, the criteria config, model-graded metrics, the typed eval object model, and multi-turn simulation is **Python-only** today. A search of the entire `adk-go` v2 tree turns up no `evaluation`, `simulation`, or `optimization` package — there is no eval CLI, and its binary only does `deploy`. What *does* port is the pure arithmetic: the two lexical metric functions and the Pass@k estimator are identical in Go, so you can drive the Go runner yourself and assert the same scores in `go test`. But the recorded-case → criteria-config → `adk eval` workflow is Python's, and the eval set JSON — being data, not code — scores a Go agent just as well as a Python one.

**Next in the series:** deploying the agent to Cloud Run, GKE, or Vertex Agent Engine.
