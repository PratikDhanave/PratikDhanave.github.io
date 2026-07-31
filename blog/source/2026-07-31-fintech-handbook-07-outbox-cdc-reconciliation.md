# Reliable Delivery: The Outbox, CDC, and Reconciliation
*Two systems will drift. The transactional outbox stops you losing events; reconciliation is how you find the truth when they disagree anyway.*

Here is the failure that keeps fintech engineers up at night. A customer taps "send," you debit their account row in Postgres, and then you publish a `payment.initiated` event to your broker so the ledger service, the notification service, and the fraud queue all wake up. Two writes. Two systems. And absolutely no guarantee they both happen.

## The dual-write problem is not a bug you can fix by being careful

The instinct is to write the code in the obvious order: commit the database transaction, then publish the message. What happens when the process is killed in the microsecond between those two lines? You have debited the account and told no one. The money left, but the ledger never heard about it. The customer's balance is wrong and nothing downstream knows to correct it.

Flip the order — publish first, then commit — and you get the opposite disease. The broker accepts `payment.initiated`, the consumer starts moving money, and then your database transaction rolls back on a constraint violation. Now you have announced a payment that never happened. A phantom.

You cannot wrap a database transaction and a broker publish in a single atomic unit. They are two different systems with two different commit protocols. Distributed transactions (two-phase commit) exist, but in practice they are slow, brittle, and most modern brokers do not support them anyway. So the honest framing is this: **the dual-write problem has no "just be careful" solution.** Any design that treats the DB write and the publish as independent steps is one poorly-timed crash away from lying to itself.

## The transactional outbox: make the event part of the state change

The fix is to stop having two writes. Instead of publishing to the broker inside your business logic, you write the event into an `outbox` table *in the same database transaction* as the state change. One transaction, one commit. Either both the account debit and the outbox row land, or neither does. Atomicity is back, because it never left the database.

A separate process — the relay, sometimes called the message relay or poller — reads unsent outbox rows and publishes them to the broker, marking each row as sent once the broker acknowledges it.

```
   ┌──────────────────── one DB transaction ───────────────────┐
   │                                                            │
   │   UPDATE accounts SET balance = balance - 100 ...          │
   │   INSERT INTO outbox (id, type, payload, sent_at=NULL)     │
   │                                                            │
   └──────────────────────────┬─────────────────────────────────┘
                              │ COMMIT (atomic)
                              ▼
                   ┌────────────────────┐
                   │   outbox table     │  rows where sent_at IS NULL
                   └─────────┬──────────┘
                             │  poll / tail
                             ▼
                   ┌────────────────────┐
                   │   relay / poller   │  publish, then mark sent_at
                   └─────────┬──────────┘
                             ▼
                   ┌────────────────────┐
                   │   message broker   │
                   └─────────┬──────────┘
                             ▼
                   ┌────────────────────┐
                   │  consumer (ledger, │  MUST be idempotent
                   │  notify, fraud...) │
                   └────────────────────┘
```

> **▸ [Open the interactive diagram](/blog/handbook-diagrams/outbox-reconciliation.html)** — pan, zoom, and trace every step (light/dark, self-contained).

Notice what this buys you and what it does not. It guarantees the event is *durable* the moment the business transaction commits — you can no longer lose it. But the relay can crash after publishing and before it updates `sent_at`, in which case it will publish the same row again on restart. So the outbox is an **at-least-once** delivery mechanism. It trades "might lose events" for "might send duplicates," which is the correct trade, because duplicates are a problem you can engineer around and lost money is not.

The consequence lands on the consumer: **every consumer must be idempotent.** Give each outbox event a stable ID and have consumers record processed IDs (a dedup table, or a unique constraint on the effect they produce). Processing `payment.initiated` with ID `evt_abc` twice must move the money exactly once. If you take one thing from this section: the outbox is only half a pattern; idempotent consumers are the other half.

A minimal relay loop is unglamorous, which is the point:

```
rows = SELECT * FROM outbox WHERE sent_at IS NULL ORDER BY id LIMIT 500
for row in rows:
    broker.publish(row.type, row.payload, key=row.id)   # dedup key travels with it
    UPDATE outbox SET sent_at = now() WHERE id = row.id
```

Run it every second, or trigger it on commit. Keep the batches bounded, index on `(sent_at)` so the poll stays cheap as the table grows, and archive sent rows so the hot set stays small.

## CDC: the same idea, without the table

There is a second way to get events out of your database reliably, and it comes from a nice observation: your database already has a perfect, ordered, durable log of every change — the write-ahead log. Change Data Capture (CDC) tails that log and turns committed row changes into a stream of events. No outbox table, no relay polling, no second write in your application code at all. You debit the account, the WAL records it, and a CDC connector reads the WAL and publishes the change.

The appeal is that it is nearly invisible to application developers and it captures *everything* by construction — you can never forget to write the outbox row because there is no outbox row. The cost is that your events are now shaped like database rows, not like domain events. A `payment.initiated` domain event carries intent; a raw row change carries "column `status` went from `pending` to `sent`." Rebuilding meaning from column diffs downstream is doable but leaky, and it couples every consumer to your table schema.

My rule of thumb: reach for the **outbox when you want to publish deliberate, well-shaped domain events** and you are willing to write them; reach for **CDC when you want low-touch replication** of state to a warehouse, cache, or search index. Plenty of mature systems run both. Neither one, though, saves you from the last problem.

## Reconciliation: because two systems will drift anyway

Here is the uncomfortable truth the outbox does not fix. Even with perfect delivery of your own events, your internal ledger and an external party's statement *will* disagree. A processor charges a fee you did not model. A settlement lands a day later than expected. A webhook you were counting on never arrives, or arrives twice. Delivery guarantees are about *your* events; they say nothing about the other side's books. Reconciliation is how you find and fix the divergence.

A reconciliation loop compares two records of the same reality, classifies every discrepancy — a **break** — and resolves what it can:

```
   internal ledger              external statement
        │                              │
        └──────────────┬───────────────┘
                       ▼
                ┌─────────────┐
                │   MATCH     │  by (external_id, amount, date)
                └──────┬──────┘
                       ▼
                classify breaks
        ┌──────────────┼───────────────┬───────────────┐
        ▼              ▼                ▼               ▼
   missing on     missing on      amount           duplicate
   external       internal        mismatch         on one side
        │              │                │               │
        └──── auto-resolve known cases ─┘               │
   (timing lag, modeled fee)          │                 │
                                      ▼                 ▼
                              escalate to human    dedup / reverse
                              (ops queue + alert)
```

Match first — typically on an external reference ID, amount, and date window. Everything that matches cleanly is done. Everything that does not is a break, and breaks fall into a small set of types: present on one side but not the other, amounts that disagree, or the same transaction counted twice. A good reconciliation engine auto-resolves the breaks it understands — a two-day settlement lag, a fee that matches a known schedule — and escalates the rest to a human with enough context to act. The escalation path matters as much as the matching; a break no one sees is just a slow-motion loss. This is also where clean, consistent status semantics pay off, the same discipline behind [orchestrating error codes across a payments platform](/blog/posts/globe-error-code-orchestration.html) — if "failed" means five different things across your systems, you cannot even define a match.

Run reconciliation on a schedule — hourly for high-value flows, at least daily for everything — and track the age and count of open breaks as a first-class metric. Rising, aging breaks are the earliest honest signal that something upstream is broken.

## Why it matters

The outbox stops you losing events. CDC gets state out with minimal ceremony. Idempotent consumers absorb the duplicates that at-least-once delivery guarantees you will produce. And reconciliation is the backstop that assumes all of it will still, occasionally, be wrong — because across a system boundary, it will be. In most domains a dropped event is an inconvenience. In fintech it is someone's rent. Reconciliation is not a feature you bolt on after launch; it is the only mechanism by which you can *say* your books are right instead of hoping they are.
