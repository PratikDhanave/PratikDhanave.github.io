# Control Flow

*A workflow isn't always a straight line — route the next executor by the data with a switch-case edge group, no model required.*

---

## What this lesson demonstrates

Often the *next* executor depends on the *data*. That's a switch-case edge group: from one source, a message is routed to the first `Case` whose predicate is true, else to the `Default`. This lesson routes even numbers to a "fast lane" executor and odds to a "review lane" — pure executors, so it runs with zero credentials. It's the first branching primitive after the straight-line graph workflow.

## The code

The branching lives entirely in `add_switch_case_edge_group`:

```python
workflow = (
    WorkflowBuilder(start_executor=intake)
    .add_switch_case_edge_group(
        intake,
        [
            Case(condition=lambda x: x % 2 == 0, target=even),
            Default(target=odd),
        ],
    )
    .build()
)
result = await workflow.run(n)
return result.get_outputs()[0]
```

Each executor is a small class with a `@handler`; the even/odd handlers call `ctx.yield_output(...)` with a routed message.

## What to notice

- **Cases are evaluated in order.** The message goes to the *first* `Case` whose `condition` returns true; if none match, `Default` catches it. Order matters when predicates overlap.
- **Predicates are plain callables.** `lambda x: x % 2 == 0` — the condition is ordinary Python over the message, so routing logic stays in your code, not the model's.
- **Output types are declared on the context.** `WorkflowContext[Never, str]` says a terminal executor yields a `str` and sends no further messages; `WorkflowContext[int]` says it forwards an `int`.

## The gotcha

Every switch-case group needs a `Default`. Cases are not exhaustive on their own — a message that matches no `Case` and has no `Default` has nowhere to go. Always terminate the group with a `Default(target=...)` so the routing is total.

## How it maps to MAF and Foundry

This is graph-workflow plumbing that sits *below* the agent layer — no `FoundryChatClient`, no credentials. But the same edge groups carry agent executors in later lessons: swap the even/odd handlers for agents and the switch-case decides which agent handles a message. Learning routing on pure functions first keeps the mechanics visible before models enter the graph.

## Run it

```bash
uv run tutorial/03-workflows/01_control_flow.py
```

Runs offline — no Azure creds. Success: `4` and `10` route to the fast lane, `7` routes to the review lane.

---

Next: [Parallelism](/blog/posts/maf-py-45-parallelism.html)
