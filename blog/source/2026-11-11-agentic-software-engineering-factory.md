# Agentic Software Engineering in Go: Software Factory Orchestration

*Designing always-on, self-sustaining Orchestrator-Worker-Validator systems*

---

## The Problem: Ad-Hoc Agent Orchestration

Every workflow in this series so far has one launch mode: a developer types a command and waits. That ceiling is low. Agent calls that fail mid-run lose their work; nothing survives a process restart; two tasks can't run concurrently without two terminals; and there is no record of what ran last week, let alone metrics on it.

The factory is the answer: a long-running orchestration process that owns a durable task queue, a worker pool, and the verification machinery — so that agent work becomes something you *submit* and *query*, not something you babysit.

## The Triad

The design splits into three roles. The **Orchestrator** owns the queue, the worker pool, and persistence. **Workers** are stateless goroutines that pull a task, execute it (generate, verify, review, refactor, evaluate), and report a result. The **Validator** is the verification engine from [post 4](/blog/posts/agentic-software-engineering-verification.html), invoked by workers rather than by a human.

```text
            ┌──────────────────────────────────────────┐
            │              Orchestrator                │
 submit ──► │  task queue (buffered chan)  ──► dispatch │
            │        │                          │      │
            │   SQLite (.asf/factory.db)   worker pool │
            └────────┼──────────────────────────┼──────┘
                     ▼                          ▼
              crash recovery:           worker-N: generate │ verify
              running → pending            │
              re-queued on boot            ▼
                                    LLM client + judge
                                    verification engine
```

Every lifecycle in the system is a declared state machine — not scattered string comparisons. `asf factory states` prints them from the running declarations; this is actual output:

```text
=== task (initial: pending) ===
    pending --> running
    running --> completed
    running --> failed
    running --> pending      ← crash recovery / retry edge

=== worker (initial: idle) ===
    idle --> busy
    busy --> idle
    busy --> error
    error --> idle

=== verification (initial: build) ===
    build --> test --> lint --> constraints --> passed
    (each phase may also --> failed)
```

That `running --> pending` edge on tasks is the whole durability story in one line, and we'll come back to it.

## Workers: Pull, Don't Push

Workers don't get tasks assigned; they pull from a shared channel. This is the standard Go worker-pool shape, and it's worth showing because nothing about it is exotic:

```go
func (fo *FactoryOrchestrator) workerLoop(ctx context.Context, worker *Worker) {
	defer fo.wg.Done()

	for {
		select {
		case <-ctx.Done():
			return
		case <-fo.shutdown:
			return
		case <-worker.stop:
			return
		case task := <-fo.taskQueue:
			fo.executeTask(ctx, worker, task)
		}
	}
}
```

The pool auto-scales, but the policy is deliberately dumb: a dispatch loop ticks once per second; if every worker is busy and the pool is under its max, add one; if more than two are idle, retire one (closing its `stop` channel so the goroutine and the pool map can't drift apart). No predictive scaling, no utilization windows. For a system whose tasks take seconds to minutes, a one-second reactive loop is all the sophistication the problem deserves.

## Durability: The Part That Earns "Factory"

Every task state transition is persisted to SQLite (`.asf/factory.db`). On boot, the orchestrator replays the database into memory, and the one interesting decision is what to do with tasks persisted as `running` — they were interrupted mid-execution:

```go
// Crash recovery: a task persisted as "running" was interrupted
// mid-execution; re-queue it (explicit running -> pending transition).
if task.Status == TaskRunning {
	setTaskState(task, TaskPending)
}
```

That gives you at-least-once execution: a crashed generate task runs again rather than vanishing. Workers, by contrast, are *not* restored — they are ephemeral runtime entities recreated fresh each boot, because a persisted "busy" worker is meaningless after a restart once its task has been re-queued.

This is observable in practice. Starting the API server on a machine where the factory had run before:

```text
$ ASF_MODEL=qwen3.6:latest ./asf-web-bin localhost:8080
2026/11/20 11:00:28 factory: LLM enabled (provider ollama, model qwen3.6:latest,
    max 2 concurrent calls, judge threshold 0.75, context budget 24000 chars)
```

and the first status query already knows about history this process never saw:

```json
{
  "llm_enabled": true,
  "llm_provider": "ollama",
  "llm_model": "qwen3.6:latest",
  "max_workers": 4,
  "tasks_completed": 4,
  "tasks_failed": 2,
  "tasks_pending": 0,
  "workers_idle": 2
}
```

Those six historical tasks came out of SQLite, not memory.

## What a Generate Task Actually Does

The worker path for a `generate` task is: assemble the spec prompt and curated context, call the LLM, then hand the output to an LLM-as-a-judge evaluator. If the judge scores below threshold (0.75 by default), the worker regenerates with the judge's feedback folded into the prompt, up to `ASF_EVAL_MAX_ATTEMPTS`. The final result — artifact, attempt count, model, per-criterion verdict — is attached to the task record.

Two design details matter more than they look. First, LLM calls go through a concurrency gate (two concurrent calls by default) so four workers can't stampede a local Ollama instance. Second, a broken judge does not discard a produced artifact:

```go
evalErr = fo.withLLMSlot(ctx, func(callCtx context.Context) error {
	verdict, evalErr = fo.evaluator.EvaluateCode(callCtx, specPrompt, output, contextStr, fo.evalCriteria)
	return evalErr
})
if evalErr != nil {
	// The artifact was produced; a broken judge should not discard it.
	judgeNote = fmt.Sprintf("evaluation skipped: %v", evalErr)
	...
}
```

For honest expectations on timing: on a MacBook running qwen3.6 locally through Ollama, one generate task for a ~150-line Go package — generation plus judge pass — took 4 minutes 59 seconds. A verification task (build + test + lint of the factory's own repo) takes about 5 seconds. Cloud models compress the generate numbers dramatically; the orchestration cost is noise either way.

## Factories-as-Code

The factory's shape is itself declared in YAML — which agents exist, what they're allowed to do, and which workflows chain them. This is the actual `specs/factory.yaml` schema, matching the `pkg/factorydef` structs field for field:

```yaml
factory:
  name: "go-agentic-factory"
  version: "1.0"
  agents:
    - id: "gen-agent"
      role: "code-generator"
      capabilities: ["generate", "refactor"]
      model: "claude-sonnet-5"
    - id: "verify-agent"
      role: "validator"
      capabilities: ["verify"]
      model: "claude-haiku-4-5"
  workflows:
    - id: "code-improvement"
      steps:
        - name: "generate-code"
          agent: "gen-agent"
        - name: "run-verification"
          agent: "verify-agent"
          validation: "harness"
  runners:
    - id: "default-sandbox"
      image: "golang:1.23-alpine"
      work_dir: "/workspace"
      read_only: false
      timeout: "300s"
```

The definition is versioned next to the code it governs, so "which model reviews our PRs and with what autonomy" is a diff in review, not tribal knowledge. One wart found while dogfooding: `asf spec list` currently slurps `factory.yaml` out of `specs/` and lists it as an empty specification, because both formats live in the same directory. Real systems accumulate exactly this kind of edge.

## Access: Four Doors, One Orchestrator

The same orchestrator is reachable four ways — CLI (`asf factory ...`), HTTP API, Server-Sent Events for streaming task state, and an MCP server so other agents and tools can drive the factory programmatically:

```text
POST /api/factory/launch/{action}    launch review|bugfix|feature|eval|refactor
GET  /api/tasks/{id}                 task snapshot
GET  /api/tasks/{id}/stream          SSE until the task hits a terminal state
GET  /api/factory/status             the status JSON shown above
GET  /api/state-machines             the declared lifecycles, as data

MCP tools: submit_task, get_task_result, get_factory_status,
           list_specs, get_spec, list_agents, run_verification
```

A note on honest scope: the CLI's `asf factory submit` constructs a fresh orchestrator per invocation — fine for development, but the durable always-on mode is the API server. Run `./asf-web-bin`, keep it up, and submit over HTTP.

## Why This Layer Is Worth Building

Resilience stops being a property of your attention span: a crashed process re-queues its interrupted work from SQLite instead of losing it. Concurrency gets a policy — a worker pool with a scaling rule and an LLM gate — instead of being however many terminals you have open. And every task that ever ran leaves a queryable record with its verdict attached, which is the raw material the [next post](/blog/posts/agentic-software-engineering-ops.html) turns into operations: metrics, evaluation benchmarks, and the continuous-improvement loop.

---

*All code, configuration, and command output in this post is taken directly from the companion factory codebase (Go 1.23+) and real sessions against it.*
