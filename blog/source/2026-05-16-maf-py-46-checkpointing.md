# Checkpointing

*Long or human-gated workflows can't live only in memory — hand the builder a CheckpointStorage and it snapshots state after each superstep, so you can restore and resume.*

---

## What this lesson demonstrates

A crash or a restart would lose an in-memory workflow's progress. Give `WorkflowBuilder` a `CheckpointStorage` and it snapshots state after each superstep; later you can list what was saved and resume from a checkpoint id. This lesson runs a tiny two-step counter, then lists the checkpoints it left on disk — pure executors, zero credentials, writing JSON under `./checkpoints/`.

## The code

Storage is a single constructor argument, and the snapshots are queryable:

```python
storage = FileCheckpointStorage("./checkpoints")
workflow = (
    WorkflowBuilder(start_executor=s1, checkpoint_storage=storage, name=WORKFLOW_NAME)
    .add_edge(s1, s2)
    .build()
)
result = await workflow.run(5)
print(f"output: {result.get_outputs()}")  # (5+1)*10 = 60

checkpoints = await storage.list_checkpoints(workflow_name=WORKFLOW_NAME)
for cp in checkpoints:
    print(f"  • {cp.checkpoint_id[:8]}…  iteration={cp.iteration_count}")
```

## What to notice

- **Two storage backends.** `FileCheckpointStorage("./checkpoints")` persists JSON to disk; `InMemoryCheckpointStorage()` keeps snapshots in memory for tests.
- **A `name` is required to find checkpoints again.** `list_checkpoints(workflow_name=...)` keys on the workflow name you passed the builder — without it you can't locate the snapshots.
- **Snapshots carry metadata.** Each checkpoint exposes `checkpoint_id`, `iteration_count`, and `timestamp`, so you can pick which superstep to resume from.

## The gotcha

Snapshots happen per superstep, not per handler call. State is captured at superstep boundaries, so resuming lands you at the start of the next superstep — not partway through an executor. Design executors to be idempotent from a superstep boundary, since a resumed run replays from there via `workflow.run(checkpoint_id=<id>)`.

## How it maps to MAF and Foundry

Checkpointing is the durability layer under everything that follows: human-in-the-loop suspends a workflow that may sit idle for hours, and long agent orchestrations can crash mid-run. Persisted supersteps mean a workflow survives process death and resumes exactly where it stopped — the foundation the next lesson's approval gate relies on.

## Run it

```bash
uv run tutorial/03-workflows/03_checkpointing.py
```

Runs offline — no Azure creds. Success: output `[60]` and at least one checkpoint saved under `./checkpoints/`.

---

Next: [Human In The Loop](/blog/posts/maf-py-47-human-in-the-loop.html)
