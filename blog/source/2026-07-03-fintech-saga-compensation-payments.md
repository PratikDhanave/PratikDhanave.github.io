# Moving Money Across Services Without a Distributed Transaction

*How to coordinate a multi-step payment as an orchestrated saga: compensating actions for partial failures, idempotent steps, and a guarantee that money is never left stranded.*

A payment that touches more than one service cannot be wrapped in a single database transaction. The money leaves a ledger owned by one service, lands in a ledger owned by another, and passes through a hold, a debit, and a credit along the way. Each of those lives behind its own boundary, its own datastore, its own deploy cadence. There is no `BEGIN … COMMIT` that spans all of them, and pretending otherwise with a two-phase commit coordinator just moves the failure into a component that can block indefinitely while holding locks across your entire money movement path. In practice nobody runs 2PC across payment services, because a coordinator crash at the wrong moment freezes funds.

So we give up atomicity across services and buy back correctness a different way: we make the workflow a sequence of committed local steps, and we attach to every step an action that undoes it. That is a saga. This post is about how you actually build one for payments, where "undo" is not a rollback but a second real transaction.

## The step decomposition

The unit of work is not "transfer money." It is a chain of small, independently committed operations, each of which either succeeds and stays succeeded, or is later reversed by a compensating operation. A clean four-step decomposition looks like this:

```
FORWARD:   reserve ──▶ debit ──▶ credit ──▶ notify ──▶ settled
              │          │          │
COMPENSATE:  └ release   └ refund   └ reverse   (run in reverse order)
```

> **▸ [Open the interactive diagram](/blog/diagrams/fintech-saga-compensation-payments.html)** — pan, zoom, and trace every step (light/dark, self-contained).

Each forward step commits locally the moment it runs. `reserve` places a hold on the source account so the balance cannot be spent twice. `debit` captures that hold and moves the value out. `credit` posts the value into the destination. `notify` confirms the outcome to whoever asked. Only after every step acknowledges does the workflow reach `settled`, and only then is the transfer economically complete.

The important design fact hiding in that list: there is no step at which money exists nowhere. Between `debit` and `credit`, the value is held by the orchestration itself — modeled explicitly as an in-flight or clearing balance on your ledger — not vanished. If the workflow dies right there, a recovery process can still see the funds and decide whether to finish forward or unwind.

## Orchestration over choreography

There are two ways to run these steps. In choreography, each service emits an event and the next service reacts to it; the workflow logic is smeared across every participant and exists nowhere as a whole. That is elegant for loosely-coupled fan-out, but for money it is a liability. When a payment gets stuck, you want one place to ask "where is this transfer and what happens next," not a forensic reconstruction from five event logs.

So for payments I reach for orchestration: a single coordinator owns the state machine, calls each step in turn, records the outcome, and decides on failure whether to advance or compensate. The orchestrator is itself a durable, restartable process — a state machine persisted after every transition — so a crash mid-flight resumes from the last recorded step rather than restarting from zero or, worse, replaying a debit.

```python
async def run_saga(txn):
    completed = []
    for step in (reserve, debit, credit, notify):
        try:
            await step.execute(txn)          # idempotent, keyed by txn.id
            completed.append(step)
            persist_state(txn, step.name)     # durable checkpoint
        except StepFailed:
            for done in reversed(completed):  # unwind in reverse
                await done.compensate(txn)    # idempotent, durable
            mark_failed(txn)
            return
    mark_settled(txn)
```

The shape that matters: forward steps accumulate onto `completed`, and on any failure we walk that list *in reverse* calling each step's compensator. We never compensate a step that did not run.

## Compensation is a forward transaction, not a rollback

The word "compensate" invites the wrong mental model. A database rollback discards uncommitted work; nothing durable happened. A saga compensator runs *after* the original step already committed — the hold was really placed, the money really moved — so the compensator is a brand-new committed transaction whose business effect cancels the first. `release` returns a reservation. `refund` moves debited value back to the source. `reverse` pulls a posted credit back out of the destination.

This distinction drives three requirements that are easy to miss:

- **Compensators can themselves fail.** A refund call can time out exactly like a debit can. The orchestrator must retry compensation with the same durability and idempotency it gives forward steps — an unretried compensator is how money gets stranded.
- **Some actions are not cleanly reversible.** You cannot un-send an email or un-fire a webhook, which is why `notify` sits at the end where its failure costs nothing financial and can simply be retried. Order your steps so the irreversible ones happen last.
- **Compensation runs in reverse order.** If `credit` fails, you `refund` the debit and then `release` the hold — newest completed step first — because later steps often depend on the state established by earlier ones.

For the case where a step *half-succeeds* and you have to unwind an ambiguous middle, I wrote separately about [rolling back a half-succeeded saga](/blog/posts/saga-rollback-half-succeeded.html); the short version is that ambiguity is resolved by idempotency plus status queries, never by guessing.

## Idempotency is the load-bearing wall

Every step and every compensator runs behind a network that will, sooner or later, tell you a call failed when it actually succeeded. If your retry then runs the operation a second time, you have double-debited a customer. The only defense is that every operation is idempotent, keyed by a stable identifier derived from the transfer and the step — for example `txn.id + ":" + step.name`.

Concretely, each downstream service records the idempotency key of every operation it has applied. A repeat call with a known key returns the original result instead of doing the work again. That single discipline is what lets the orchestrator retry aggressively without fear, and it is what lets a compensator be safely re-run after a crash. Without it, the whole saga model collapses, because you can no longer tell "this step needs to run" apart from "this step ran and the ack was lost."

Two rules keep the keys honest. Generate the key once, at the point the transfer is created, and thread the same key through every retry — never regenerate it per attempt. And make the key deterministic from the transfer, so a recovery process reconstructing state after a crash arrives at exactly the same keys the original run used.

## Guaranteeing money is never stranded

Put the pieces together and the guarantee falls out. Every forward step that moves value has a compensator that moves it back. The orchestrator durably records which steps completed, so after any crash it knows precisely how far it got. Retries are safe because every operation is idempotent. Compensation is retried with the same guarantees as the forward path, so an unwind cannot be abandoned halfway.

The one thing left is a sweeper: a background process that scans for transfers stuck in a non-terminal state past a deadline and drives them to resolution — forward if the downstream steps actually succeeded, backward through compensation if not. This is the safety net that converts "almost always correct" into "eventually always correct," and it is the reason a saga tolerates the failures a distributed transaction would have tried to prevent. You do not avoid partial failure; you make partial failure a state the system knows how to leave.

A payment saga is not the simplest thing you can build, but it is honest about the world it runs in. Services fail independently, networks lie about outcomes, and no lock spans your whole money path. Committed local steps plus idempotent compensators plus a durable orchestrator plus a sweeper give you a system where every dollar is always either where it started or where it was going — and never nowhere.
