# checkpoint_and_rehydrate

*How to snapshot a running workflow at every super-step, then throw the instance away and rebuild a fresh workflow that resumes from a saved checkpoint.*

---

## What this lesson demonstrates

A cyclic **guess-the-number** workflow proves that a checkpoint is *real* by discarding the running instance and **rehydrating a brand-new workflow** from a mid-run snapshot — which then finishes the search from exactly where the snapshot left off. Two executors form a loop: `Guess` binary-searches for a hidden target inside its `[lower, upper]` bounds; `Judge` compares each guess to `42` and sends back `Above` / `Below` until the guess is exact, then yields the final string.

Crucially, this lesson has **no model, no credential, no network** — it teaches a pure in-process workflow, so it runs identically everywhere.

## First run, then rehydrate

The runtime is decorated with checkpointing; every super-step boundary produces a `CheckpointInfo` you collect. Then a *fresh* graph is built and resumed from one of them:

```go
newWorkflow := buildWorkflow()   // fresh executors, initial bounds
savedCheckpoint := checkpoints[checkpointIndex]

newCheckpointedRun, err := inproc.Default.
	WithCheckpointing(checkpointManager).
	ResumeStreaming(ctx, newWorkflow, savedCheckpoint)
```

`buildWorkflow()` is deliberately called *again* — the resume path starts from a clean slate and lets the snapshot overwrite it.

## What to notice

- **State lives in the executor; checkpointing lives in the runtime.** `Guess` and `Judge` hold plain fields (`lowerBound`, `tries`). They opt in by implementing `OnCheckpoint` (queue state via `ctx.QueueStateUpdate`) and `OnCheckpointRestored` (read it back via `ctx.ReadState`). Attach them with `Extend(&workflow.Executor{OnCheckpointFunc: ..., OnCheckpointRestoredFunc: ..., ResetFunc: ...})`.
- **Rehydration is distinct from resuming the same run.** Here you build a *new* `*workflow.Workflow`; `Reset` gives it a clean slate and `OnCheckpointRestored` overwrites it with the snapshot. A missing key falls back to the reset state. (The next lesson rewinds the *same* live run instead.)
- **The graph is cyclic and terminates by yielding.** `AddEdge(Guess→Judge)` and `AddEdge(Judge→Guess)` form the loop; `WithOutputFrom(Judge)` marks the output node. The loop ends because `Judge` *yields* (instead of sending) once the guess is correct.
- **Typed message contracts.** The zero-size `_ workflow.AttrSendsMessage[int]` / `AttrYieldsOutput[string]` marker fields declare each executor's message and output types to the builder.

## How it maps to the Agent Framework Go SDK

`inproc.Default.WithCheckpointing(manager)` plus `checkpoint.NewInMemoryManager()` and the executor's `OnCheckpoint` / `OnCheckpointRestored` hooks are the SDK's durability story for workflows. `ResumeStreaming` rebuilds a run from a `CheckpointInfo` handle — the foundation for crash recovery and long-running, resumable agent workflows.

## Run it

```bash
go run  ./tutorial/03-workflows/checkpoint/checkpoint_and_rehydrate
go test ./tutorial/03-workflows/checkpoint/checkpoint_and_rehydrate
```

There is no live path — `AF_LIVE=1` changes nothing here, since this lesson is a pure in-process workflow. The offline test drives a full checkpoint/resume round-trip.

---

Next: [checkpoint · Checkpoint and Resume](/blog/posts/maf-go-72-checkpoint-and-resume.html)
