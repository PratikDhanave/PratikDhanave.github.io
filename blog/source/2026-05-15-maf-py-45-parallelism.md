# Parallelism

*The reason to reach for a graph over a chain: fan out work to run concurrently, then fan in to merge — wall-clock is the slowest worker, not the sum.*

---

## What this lesson demonstrates

This is the payoff of a graph. `add_fan_out_edges` broadcasts the *same* message to several workers that run concurrently; `add_fan_in_edges` gives a joiner a *list* of all their outputs, and the joiner fires only once every source has completed. Here one phrase fans out to a `Shout` worker and a `Reverse` worker, then a `Join` merges both — pure executors, zero credentials.

## The code

Two edge calls express the whole parallel-then-merge shape:

```python
workflow = (
    WorkflowBuilder(start_executor=dispatch)
    .add_fan_out_edges(dispatch, [shout, reverse])  # parallel branches
    .add_fan_in_edges([shout, reverse], join)       # synchronized merge
    .build()
)
result = await workflow.run("agent framework")
print(result.get_outputs()[0])
```

The fan-in target's handler is typed to receive the aggregate:

```python
async def run(self, results: list[str], ctx: WorkflowContext[Never, str]) -> None:
    await ctx.yield_output(" | ".join(sorted(results)))
```

## What to notice

- **Fan-out broadcasts the same message.** Every worker in the list receives an identical copy of the source's output — this is a broadcast, not a split.
- **The joiner receives a `list`.** Its handler signature is `list[str]`, the aggregated outputs of all sources, and it runs exactly once.
- **Fan-in is synchronized.** The join only fires after *every* source completes, so wall-clock time is the slowest worker, not their sum.

## The gotcha

Worker completion order is not guaranteed. The `list` handed to the joiner reflects concurrent completion, so its order can vary run to run. This lesson calls `sorted(results)` to get a stable output; if you need deterministic ordering, sort or key the results yourself rather than assuming input order.

## How it maps to MAF and Foundry

Fan-out / fan-in is credential-free graph plumbing, but it's exactly how you parallelize *agent* calls later: broadcast a task to several agents, then merge their answers in a joiner. Running it on pure string workers first makes the synchronization barrier obvious before latency and model cost enter the picture.

## Run it

```bash
uv run tutorial/03-workflows/02_parallelism.py
```

Runs offline — no Azure creds. Success: one line containing both a `REVERSE:` and a `SHOUT:` segment from the two workers.

---

Next: [Checkpointing](/blog/posts/maf-py-46-checkpointing.html)
