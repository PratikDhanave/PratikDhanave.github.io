# Human In The Loop

*Some steps need a person — request_info suspends the workflow and hands control back to your code, then you resume by re-running with the human's answer keyed by request_id.*

---

## What this lesson demonstrates

Approvals, clarifications, sign-offs — some steps can't proceed without a human. `RunContext.request_info` *suspends* the workflow and returns a pending request to your code. You gather the human's answer and *resume* by re-running with that answer keyed by `request_id`. Here an `approval_flow` asks whether to publish a release note, suspends, and on resume either publishes or rejects — pure functional workflow, zero credentials.

## The code

The suspend point is a single awaited call inside a `@workflow`:

```python
@workflow
async def approval_flow(draft: str, ctx: RunContext) -> str:
    decision = await ctx.request_info(
        {"draft": draft, "question": "Approve this release note? (approve/reject)"},
        response_type=str,
        request_id="review",
    )
    if decision.strip().lower().startswith("approve"):
        return f"PUBLISHED ✅ — {draft}"
    return "REJECTED ❌ — sent back for edits."
```

Driving it is two runs — one that suspends, one that resumes:

```python
result = await approval_flow.run(draft)
pending = result.get_request_info_events()          # what the human must answer
final = await approval_flow.run(responses={"review": "approve"})  # resume, no new message
```

## What to notice

- **`request_info` returns the human's answer on resume.** On the first run it suspends; on the resume run the same await returns the supplied value directly, so the function reads like straight-line code.
- **Pending requests are events.** `result.get_request_info_events()` lists each suspension with its `request_id` and `data` — the payload you showed the human.
- **Resume passes `responses`, not a message.** `run(responses={"review": human_answer})` — no draft on resume, just the keyed answer.

## The gotcha

The resume key must exactly match the `request_id` from the suspend call — here `"review"` on both sides. Pass a mismatched key and the workflow won't find the answer it's waiting on. Note also that functional workflows are experimental in this build, so the API may shift.

## How it maps to MAF and Foundry

This builds directly on checkpointing: a suspended workflow can be persisted and resumed hours later, across process restarts, once its state is snapshotted. The same `request_info` gate underlies tool-approval flows where a human authorizes a side effect before an agent proceeds — MAF's uniform way to put a person in the loop.

## Run it

```bash
uv run tutorial/03-workflows/04_human_in_the_loop.py
```

Runs offline — no Azure creds. Success: the workflow suspends, receives `approve`, and prints `PUBLISHED`.

---

Next: [Workflow As Agent](/blog/posts/maf-py-48-workflow-as-agent.html)
