# Idempotency and Full Resumability
*The network will time out mid-transfer. The only safe assumption is that every request runs zero, one, or many times — so make "many" behave like "one."*

Here is the uncomfortable truth about distributed money movement: the wire does not tell you the truth. A client fires a request to move funds, the server does the work, and then the connection dies before the response comes back. The client is now stuck in the worst possible epistemic state — it has no idea whether the transfer happened. Did the server commit and lose the ack on the way home? Or did the request never land at all? From where the client sits, those two outcomes are indistinguishable.

So the client does the only sane thing: it retries. And a naive server, seeing what looks like a brand-new request, cheerfully moves the money a second time. Now you have double-charged a customer because of a dropped TCP packet. This is not a hypothetical. This is the default behavior of any HTTP API that treats a `POST /transfers` as unconditionally fresh work.

## The timeout tells you nothing

Engineers new to payments often assume a timeout means failure. It does not. A timeout means *unknown*. The three possible states after any network call are: it ran zero times, it ran exactly once, or — after retries — it ran many times. Your job as a backend engineer is to collapse "zero, one, or many" down to a single guaranteed outcome: the effect happens **at most once**, and if the client keeps asking, it eventually learns that it *did* happen.

Notice the framing. We are not chasing exactly-once *delivery* — that is provably impossible over an unreliable network without an infinite retry budget. We are chasing exactly-once *effect*. Messages can arrive as often as they like; the money moves precisely once. That distinction is the whole game.

## Idempotency keys, and where the guarantee actually lives

The mechanism is a client-generated **idempotency key** — a unique token, typically a UUID, that the client mints once per *logical* operation and reuses across every retry of that same operation. It travels in a header like `Idempotency-Key: 7f3a...`. The key says "these requests are all the same intent; do the work at most once."

The subtlety that separates a correct implementation from a broken one is *where the guarantee is enforced*. The server must record `(key -> result)` in the **same database transaction** as the effect itself. If you charge the account in one transaction and write the idempotency record in another, you have opened a window: crash between the two and a retry sees no record, redoes the charge, and your dedup layer was theater. Atomicity is not a nice-to-have here; it is the entire contract.

```
                    ┌─────────────────────────────────────────┐
  FIRST REQUEST     │  key=K not found in dedup store          │
  Idempotency-Key:K │  BEGIN TX                                │
  ───────────────►  │    debit account  (the real effect)      │
                    │    INSERT (K -> result) in same TX       │
                    │  COMMIT                                   │
  ◄───────────────  │  return result, HTTP 201                 │
   201 Created      └─────────────────────────────────────────┘

                    ┌─────────────────────────────────────────┐
  REPLAY (retry)    │  key=K FOUND in dedup store              │
  Idempotency-Key:K │  ── skip the effect entirely ──          │
  ───────────────►  │  no debit, no new TX for the money       │
                    │  read stored result for K                │
  ◄───────────────  │  return SAME result, HTTP 200            │
   200 OK (replay)  └─────────────────────────────────────────┘
```

The replay path is the point of the whole design: it returns the *stored* answer and performs **no new effect**. The customer sees one debit no matter how many times the client panics and retries.

A minimal server sketch:

```python
def transfer(key, account, amount):
    with db.transaction() as tx:
        existing = tx.get_idempotency(key)
        if existing is not None:
            return existing.result          # replay: no effect
        result = do_debit(tx, account, amount)  # the real effect
        tx.put_idempotency(key, result)         # same TX as the debit
        return result
```

One more wrinkle: what if a *second* request with key `K` arrives while the first is still in flight? Take a lock or a unique constraint on the key so the concurrent caller blocks or gets a `409`, rather than racing past an as-yet-uncommitted record.

## Scoping and TTL — the boring details that bite

Two operational decisions decide whether your dedup layer is trustworthy.

**Scoping.** A key is not globally unique; it is unique *within a context*. Scope it per endpoint **and** per account. Otherwise a stray key reused across a refund endpoint and a transfer endpoint could return the wrong stored result, and a key colliding across two accounts leaks one customer's outcome to another. The dedup store's primary key should effectively be `(endpoint, account_id, idempotency_key)`.

**TTL.** You cannot keep every key forever; the dedup store would grow without bound. So you set a TTL — commonly 24 to 72 hours — long enough to outlive any realistic retry window. The trade-off is explicit: a retry that arrives *after* the TTL expires is treated as fresh and may re-run the effect. Size the TTL to your maximum client retry horizon, and make sure clients stop retrying before it. For a deeper treatment of enforcing this at more than one point in the stack, see [three layers of idempotency](/blog/posts/globe-idempotency-three-layers.html).

## Tame the retry storm

Idempotency makes retries *safe*; it does not make them *free*. A thousand clients all retrying a struggling service on a tight fixed interval will synchronize into a thundering herd and keep the service down. Retries need **exponential backoff with jitter** — each attempt waits longer, and a random component smears the retries across time so they do not all hammer the server on the same tick.

```
attempt n:  wait = random(0, min(cap, base * 2**n))
```

The jitter is not optional decoration. Without it, backoff still leaves every client firing in lockstep. With it, the load spreads and the service gets room to recover.

## Full resumability: idempotency across steps

A single debit is the easy case. Real money flows have several committed steps — reserve funds, debit the source, credit the destination, emit a ledger entry, notify downstream. If the process crashes halfway and simply *restarts from the top*, you double-apply every completed step. That is the same double-charge bug, just wearing a longer coat.

The fix is **full resumability**: persist the workflow's state to durable storage after each committed step — a checkpoint. On restart, the orchestrator reads the last checkpoint and resumes from the *next* step, not the first. Crucially, make **each individual step idempotent** (its own key, its own dedup record), so that if a crash lands right on a checkpoint boundary and a step is retried, re-running it is a safe no-op.

```
  reserve ──✓──► debit ──✓──► credit ──✗ CRASH
                                 │
                                 └─ checkpoint says: reserve✓ debit✓ credit?
  RESUME: re-run credit (idempotent → safe), then continue.
          reserve and debit are NOT repeated.
```

Checkpoint plus per-step idempotency turns a fragile multi-step flow into one that tolerates crashes anywhere without ever applying an effect twice.

## Why it matters

Money is the one domain where "eventually roughly right" is a breach of trust. A duplicated charge is not a minor glitch a user shrugs off — it is a support ticket, a chargeback, a regulator's raised eyebrow, and a customer who never comes back. Idempotency keys and resumable, checkpointed workflows are how you keep the one promise that actually matters: no matter how badly the network behaves, no matter how many times a nervous client retries, the money moves exactly once. Build it into the transaction boundary from day one. Bolting it on after the first double-charge incident is always more expensive than the incident itself.
