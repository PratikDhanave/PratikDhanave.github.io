# Agentic Software Engineering in Go: Production Operations & Metrics

*Observability, continuous improvement, and scaling beyond the individual*

---

## The Problem: The Black-Box Factory

The [previous post](/blog/posts/agentic-software-engineering-factory.html) left us with a factory that runs unattended. That immediately creates the operator's question: unattended *doing what?* A system that calls LLMs in a loop without observability degrades quietly — output quality drifts as context goes stale, costs creep as prompts bloat, and nobody can say whether last month's config change helped or hurt, because nothing was measured before or after.

This post covers what the factory actually exposes for operations today, what the evaluation data looks like from a real run, and — honestly — which parts of the observability story are wired versus still scaffolding.

## The Metrics You Get for Free

Because every task transition is persisted, the basic operational questions are answerable from the status endpoint with no extra instrumentation:

```text
$ curl -s localhost:8080/api/factory/status
```

```json
{
  "llm_enabled": true,
  "llm_provider": "ollama",
  "llm_model": "qwen3.6:latest",
  "max_workers": 4,
  "tasks_completed": 4,
  "tasks_failed": 2,
  "tasks_pending": 0,
  "workers_busy": 0,
  "workers_idle": 2
}
```

That's a real response, and the completed/failed counts span process restarts — they come from SQLite, not process memory. The Next.js dashboard renders this same data live (worker states, recent activity, per-task verdicts), but the dashboard is a *view*; the system of record is the task store, which means your existing monitoring stack can poll one JSON endpoint and alert on `tasks_failed` without caring that an AI system sits behind it.

Per-task visibility comes from the SSE stream, which emits every state transition until the task is terminal:

```text
$ curl -N localhost:8080/api/tasks/$ID/stream
data: {"id":"8f3d...","status":"running","terminal":false, ...}
data: {"id":"8f3d...","status":"completed","terminal":true,
       "result":{"attempts":1,"context_items":37,"model":"qwen3.6:latest",
                 "evaluation":{"score":0.91,"passed":true, ...}}}
```

## Evaluation: The Quality Signal

The deepest operational signal is not whether tasks complete — it's whether their output is any good. Every LLM-backed generate task is scored by an LLM-as-a-judge evaluator against five weighted criteria. These are the actual defaults from `pkg/eval`:

```go
func DefaultEvaluationCriteria() EvaluationCriteria {
	return EvaluationCriteria{
		Correctness:    0.35,
		CodeQuality:    0.25,
		SpecCompliance: 0.20,
		Security:       0.15,
		Documentation:  0.05,
		Threshold:      0.75,
	}
}
```

Below-threshold output is regenerated with the judge's feedback folded into the prompt (bounded by `ASF_EVAL_MAX_ATTEMPTS`, default 2), and the final verdict rides along on the task record. Here is the verdict from a real generate task — the authentication package the [case study](/blog/posts/agentic-software-engineering-case-study.html) dissects:

```json
"evaluation": {
  "score": 0.91,
  "passed": true,
  "criteria": {
    "correctness": 0.90,
    "code_quality": 0.95,
    "spec_compliance": 0.85,
    "security": 0.95,
    "documentation": 0.90
  },
  "improvements": [
    "Add table-driven tests per execution plan step 5 ...",
    "Correct the RefreshTokenStore.StoreDigest interface comment which
     references returning ErrAlreadyExists, but the method signature only
     declares error. ..."
  ]
}
```

Two things make this operationally useful. The per-criterion breakdown localizes problems — this artifact's weakest score was spec compliance, and the judge's improvement list says exactly why (a required test step was skipped). And because verdicts are persisted per task, "is quality drifting" becomes a query over scores instead of a feeling.

One warning the case study earns the hard way: a judge score is *not* a compile check. That same 0.91-scored artifact did not build — the judge (the same model that wrote the code) praised an API that doesn't exist. Judge scores are a trend signal; the compiler is the gate. Operate with both.

## A/B Testing Configurations

Which model should handle generation? Does a bigger context budget actually improve output? The factory's answer is the benchmark suite in `pkg/eval`: run the same specs under two configurations, score both with the same judge criteria, compare.

```go
suite := eval.NewBenchmarkSuite(client, criteria)
suite.RunBenchmark(ctx, "qwen-local", specID, specContent, codeA, contextContent)
suite.RunBenchmark(ctx, "sonnet-cloud", specID, specContent, codeB, contextContent)
comparison, _ := suite.CompareConfigs("qwen-local", "sonnet-cloud")
best := suite.GetBestConfig() // highest average score across runs
```

The dashboard exposes a slice of this as the "Run Benchmark" card, backed by the `evaluate` task type: judge the most recent completed generate output for a spec, on demand. The honest caveat: `BetterThan` here means "higher mean judge score" — there is no significance testing, so treat small deltas across few specs as noise and re-run before acting on them.

The knobs this machinery is built to compare are the ones that matter operationally:

- **Model routing** — `specs/factory.yaml` assigns a model per agent role, so a cheap model can verify while a stronger one generates; benchmarks tell you when the cheap one is good enough.
- **Context budget** — prompts carry a provider-aware cap (`ASF_CONTEXT_MAX_CHARS`: ~24K chars for local models, ~400K for large-context cloud models) so a small local window isn't drowned in prefill. The budget is a quality/cost dial you can benchmark directly.
- **Judge strictness** — threshold and criteria weights change how often the regeneration loop fires, which is a direct cost lever.

## Logs and Tracing: The Honest Inventory

Operational logging exists where it earns its keep — provider selection, judge outcomes, task failures all log with task IDs, like this line from a real boot:

```text
2026/11/20 11:00:28 factory: LLM enabled (provider ollama, model qwen3.6:latest,
    max 2 concurrent calls, judge threshold 0.75, context budget 24000 chars)
```

Tracing is scaffolding: an OpenTelemetry tracer provider is configured, but no exporter is wired, so spans are sampled and dropped. That is a deliberately honest state — the instrumentation points exist, and OTLP wiring is a config change, not a redesign. Until then, the task store is the trace: every attempt, verdict, and failure is already recorded per task, which for a system of this size answers most "what happened" questions without distributed tracing.

The same inventory honesty applies across the repo: constraint verification in the pipeline is a stub, and the integration adapters (Slack, Teams, GitHub, Linear) model connection state but aren't wired to live credentials. Knowing precisely which signals are real is itself an operational practice — the failure mode this post exists to prevent is believing a dashboard that was never plumbed.

## The Improvement Loop Is a Practice, Not a Daemon

The first draft of this post sketched a `RunImprovementCycle()` that auto-applied config changes. No such daemon exists, and having operated the factory while writing this series, I now think that's the right call at this scale. The working loop is human-paced and data-fed:

1. **Collect** — judge scores, attempt counts, and failure types accumulate in the task store as a side effect of normal operation.
2. **Notice** — a score trending down, attempts trending up, or one spec repeatedly needing regeneration. Each points at its own fix: stale context, a vague spec, or an underpowered model, respectively.
3. **Change one thing** — a model assignment in `factory.yaml`, a context budget, a judge weight.
4. **Benchmark** — same specs, old config vs. new, judged identically.
5. **Keep or revert** — the comparison is a number, so the decision is reviewable.

What makes this different from ordinary service tuning is step 4: because specs are machine-readable and evaluation is automated, every proposed change to the factory can be scored against the same work before it's adopted. Configuration changes stop being vibes.

The [case study](/blog/posts/agentic-software-engineering-case-study.html) closes the series by running the entire stack — spec, factory, judge, verification, and the gaps between them — on one real feature, with nothing cleaned up.

---

*All command output, JSON, and code in this post is from the companion factory codebase (Go 1.23+) and real sessions against it.*
