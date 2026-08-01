# EXHAUSTED Is Not Failure: Bounding Agent Runs
*An agent that burns its turn budget without finishing is neither a success nor an error. Give it a distinct outcome and a typed event stream.*

The scariest failure mode of an autonomous agent is not a crash. A crash is loud, it has a stack trace, and your on-call rotation already knows what to do with it. The scariest failure mode is the runaway loop: an agent that keeps taking turns, keeps calling tools, keeps spending tokens, and never converges on a final answer. It doesn't error. It doesn't finish. It just... continues.

Most agent frameworks model exactly two terminal states: success and failure. A runaway fits neither. So it hides. To the caller it looks like the agent is "still working," which is technically true and operationally useless. If you do eventually kill it on a timeout, the kill gets lumped into a generic error bucket, and now a cost problem is masquerading as a reliability problem. You end up debugging the wrong thing at 3am.

I hit this building a governed multi-agent system for operational incident triage on the Microsoft Agent Framework. The fix was not smarter prompts or a bigger context window. It was admitting there is a third outcome and giving it a name.

## Three outcomes, not two

Every specialist agent in that platform runs under a uniform runtime I call the harness layer. There is exactly one interface — a `SpecialistRunner` protocol — and everything that runs an agent implements it, independent of the engine behind it. The single most important method is `run_bounded()`, and its contract is this: **every run is capped at `max_turns`, and every run resolves to one of three outcomes.**

- `COMPLETED` — the agent produced a final answer within budget. Success.
- `FAILED` — something errored: a tool threw, a policy check rejected, the model call blew up. This is the bucket everyone already has.
- `EXHAUSTED` — the agent hit `max_turns` without producing a final answer.

`EXHAUSTED` is the one people skip, and it is the whole point. It is not a failure — nothing errored, no exception, no policy violation. It is also not a silent success — there is no answer to return. It is a first-class third outcome, and because it is distinct, you can route on it.

That routing is where the operational value lives. When a run comes back `EXHAUSTED`, the caller gets to decide, programmatically:

- escalate to a human with the partial work attached,
- fall back to a cheaper deterministic path,
- or surface the partial result with an honest "incomplete" flag.

None of those are available to you if a runaway is indistinguishable from "still working."

## The run state machine

The lifecycle of a bounded run is small enough to draw, and drawing it is worth doing because the shape is the contract:

```
                          +-----------------------------+
                          |                             |
                          v                             |  turn < max_turns
   [ started ] ------> [ turn ] ---------------+--------+   and no final answer
                          |                    |
        final answer      |                    | error raised
        produced          |                    |
                          v                     v
                    [ completed ]          [ failed ]

   turn == max_turns and still no final answer:
                          |
                          v
                    [ exhausted ]
```

> **▸ [Open the interactive diagram](/blog/diagrams/exhausted-is-not-failure-bounded-agent-runs.html)** — pan, zoom, and trace every step (light/dark, self-contained).

`started` fires once. `turn` is the loop, bounded above by `max_turns`. From the loop you can only leave through one of three doors: `completed`, `exhausted`, or `failed`. There is no fourth door, and critically there is no way to stay in the loop forever — the bound is structural, not a hopeful timeout bolted on the outside.

## A typed event stream, not log strings

The second half of the design is how the runner reports progress. It does not print. It emits a **typed event stream**: `started`, then zero or more `turn` events, then exactly one terminal event that is `completed`, `exhausted`, or `failed`.

Typed events instead of log lines matters more than it sounds. A log string is for a human reading a file after the fact. A typed event is something a caller can `match` on and react to *while the run is happening* — update a UI, increment a per-outcome metric, trip a circuit breaker after N exhaustions on the same route. You get clean observability for free because the terminal event *is* the metric dimension. "How many runs exhausted this hour" stops being a grep and becomes a counter.

Here is the shape of the loop, generically:

```python
def run_bounded(agent, task, max_turns):
    yield Started(task=task)
    for turn in range(max_turns):
        try:
            step = agent.take_turn(task)
        except Exception as err:
            yield Failed(turn=turn, error=err)
            return
        yield Turn(index=turn, action=step.action)
        if step.is_final:
            yield Completed(turn=turn, answer=step.answer)
            return
    # loop fell through: budget spent, no final answer
    yield Exhausted(turns=max_turns, partial=agent.partial())
```

Three `return` points, three terminal events, one hard bound. The `Exhausted` case carries the partial work so the caller has something to escalate or salvage. Nothing about this requires a particular model or framework — it is a protocol, and the protocol is what your callers depend on.

## Two runners behind one protocol

Because `SpecialistRunner` is just an interface, I ship two implementations and callers cannot tell them apart.

The first is a **deterministic runner**. Given a route, it serves a canned plan — no model, no tools, no network, zero dollars. It emits the exact same typed event stream as a real run, including the ability to return `EXHAUSTED` if you configure it to. This is what most of the test suite runs against, and it is what handles cheap, known cases in production without ever waking a model.

The second is the **live-model harness runner**, which wraps a real function-calling agent and is gated on a live model actually being configured. Same protocol, same events, same `max_turns` contract — it just happens to spend tokens.

Being able to swap a $0 deterministic runner for a live one, behind an identical outcome-and-event contract, is what makes the whole thing testable. You assert on the outcome and the event sequence, not on model output.

## Bounding is not an escape hatch

One objection I take seriously: does capping runs create an ungoverned back door? If bounding lets an agent "just stop," does it also let it skip policy? No — and the reason is that governance sits below the runner, not above it. Any runner that can call tools does so through a gateway-wrapped agent, so **every** tool call still passes policy checks regardless of how many turns are left in the budget. Bounding controls *how long* an agent may run; the gateway controls *what* it may do. Cutting a run short at `max_turns` never lets a single tool call slip past the policy layer. Governance is preserved by construction.

## Why it matters

Two-outcome thinking is why runaway agents feel scary: a cost-and-latency problem with no name gets to hide inside "still working" or "generic error," and by the time you notice, it has already spent the money and paged the human. Name the third outcome. Cap every run at `max_turns`, make `EXHAUSTED` a distinct value your callers can branch on, and emit a typed terminal event so it shows up on a dashboard the instant it happens. Do that and the most frightening thing an autonomous agent can do — loop forever, burning tokens, never finishing — stops being an incident. It becomes a routine, observable, recoverable event that routes itself to a human, a fallback, or a partial, on its own, before anyone's phone rings.
