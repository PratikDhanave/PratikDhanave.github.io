# checkpoint · Checkpoint and Resume

*How to snapshot a workflow after every super-step, then rewind the same live run to an earlier checkpoint and replay from it.*

---

## What this lesson demonstrates

A tiny two-node graph plays "guess the number" by binary search. What makes it a *checkpointing* lesson is the runner: `inproc.Default.WithCheckpointing(mgr)` snapshots the entire workflow at each super-step boundary, and every executor persists its own slice of state (`OnCheckpoint`) and rehydrates it after a rewind (`OnCheckpointRestored`). The program collects the emitted `CheckpointInfo` values on the first pass, then **rewinds the live run** back to the 6th checkpoint and lets it play forward again to the same answer.

Like the rehydrate lesson, this one has no model, no credential, and no network — it always runs.

## Rewinding the same run

The key difference from `checkpoint_and_rehydrate`: instead of building a fresh workflow, you call `RestoreCheckpoint` on the *same* run object and drain its stream again.

```go
savedCheckpoint := checkpoints[checkpointIndex]      // checkpointIndex == 5
if err := run.RestoreCheckpoint(ctx, savedCheckpoint); err != nil {
	fail(err)
}
for evt, err := range run.WatchStream(ctx) {
	// … replay continues from super-step 6 to the same "42 found in N tries!"
}
```

## What to notice

- **Checkpointing is a runner decoration, not a graph change.** The same `buildWorkflow()` graph runs with or without checkpoints; you opt in with `inproc.Default.WithCheckpointing(mgr)`, and snapshots land after every super-step.
- **Each executor owns its state.** `OnCheckpoint` calls `ctx.QueueStateUpdate(key, "", v)` to write; `OnCheckpointRestored` calls `ctx.ReadState(key, "")` to read it back. The guesser persists its `{LowerBound, UpperBound}`; the judge persists its `tries` counter. A `nil` read means "no snapshot for this key" — fall back to `Reset()`.
- **Rewinding mutates the live run.** `run.RestoreCheckpoint(ctx, checkpoints[5])` re-seeds the executors from the snapshot and you drain `WatchStream` again — the replay continues exactly where checkpoint 6 left off, contrasted with the rehydrate lesson which builds a brand-new instance.
- **Checkpoints ride on `SuperStepCompletedEvent`.** Its `CompletionInfo.CheckpointInfo` is the handle you later pass to `RestoreCheckpoint`.

## How it maps to the Agent Framework Go SDK

`RestoreCheckpoint` on a `*inproc.StreamingRun` is the SDK's in-flight rewind: the same run, re-seeded from a prior snapshot. Paired with `checkpoint.NewInMemoryManager()` (swappable for a durable store) and the executor `OnCheckpoint` / `OnCheckpointRestored` hooks, it lets a workflow undo work and re-decide from a chosen point — the basis for retries, branch exploration, and time-travel debugging of agent graphs.

## Run it

```bash
go run  ./tutorial/03-workflows/checkpoint/checkpoint_and_resume
go test ./tutorial/03-workflows/checkpoint/checkpoint_and_resume
```

There's no live model path; the offline test asserts a full run produces the expected checkpoints and that a rewind replays to the same answer.

---

Next: [checkpoint · Human-in-the-Loop with Checkpoint & Restore](/blog/posts/maf-go-73-checkpoint-with-human-in-the-loop.html)
