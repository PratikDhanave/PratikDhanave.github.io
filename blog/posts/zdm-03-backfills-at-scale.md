<!-- Markdown version for AI agents and readers. Canonical: https://pratikdhanave.com/blog/posts/zdm-03-backfills-at-scale.html -->

# Backfills at Scale — Rewriting a Billion Rows Under Live Traffic

*The expand phase created an empty column; something has to fill it for a billion existing rows while production traffic continues oblivious. Backfills are the manual labor of migrations — conceptually trivial, operationally where migrations actually spend their calendar time and take their production risks. The craft is entirely in the adverbs: incrementally, throttled, resumably, idempotently.*

Post [2](/blog/posts/zdm-02-expand-contract.html) placed the backfill inside expand/contract's migrate phase; this post is the backfill itself — the difference between the version that quietly finishes over a week and the version that pages the on-call twice and gets abandoned at 60%.

## Batching: the shape of safe bulk work

The cardinal sin is the single statement — `UPDATE big_table SET new_col = f(old_col)` — which is post 1's taxonomy in one line: a data-proportional lock, a giant transaction holding back housekeeping, an I/O saturation event, and an all-or-nothing rollback. The pattern is **small batches over a stable order**:

- **Walk the primary key**, not OFFSET. Range predicates (`WHERE id > last AND id <= last + N`) stay fast forever; OFFSET re-scans skipped rows and degrades quadratically. For non-sequential keys, walk the index order with keyset pagination — same property, same reason.
- **Size batches by time, not count.** The target is a batch duration (tens to hundreds of milliseconds) that keeps each transaction — and thus each lock — beneath anyone's noticing. Row counts that achieve it vary wildly across a table (hot pages, wide rows, index fan-out), so good backfill harnesses *adapt*: measure each batch, resize toward the target.
- **Commit per batch.** Each batch is its own transaction: locks release, housekeeping advances, failure loses one batch, not the run.

## Throttling: production goes first

A backfill that never locks can still take the site down by competing (post 1's starvation) — so pacing is a control loop, not a constant. **Sleep between batches** as the baseline dial; **watch the signals that matter** — replication lag above all (replicas apply your writes too; lag breaks read-your-writes for actual users), plus p99 latency and I/O saturation; **back off automatically** when signals degrade and resume when they recover — the backfill is the lowest-priority tenant and should behave like it. The practical corollary: backfills at this politeness level take days, and that's correct — post 2's write-both phase keeps new rows consistent during the entire span, so backfill duration costs calendar, not correctness. Teams that panic at "ten days" and crank the throttle are trading invisible risk for visible speed; the lag spike finds them eventually.

## Resumability and idempotency: built for interruption

A multi-day job *will* be interrupted — deploys, failovers, the backfill's own bugs, an operator pausing it for a sale day. Two properties make interruption boring. **Checkpointing**: persist the cursor (last completed key) transactionally with each batch; resume reads the checkpoint and continues — no "start over," no guessing. **Idempotent application**: re-running any batch must be harmless, because at-least-once execution is the only kind that exists (the crash between apply and checkpoint guarantees occasional re-runs). The backfill write is therefore shaped like post 3 of the webhook series shaped its handlers: absolute, not relative — `SET new_col = f(old_col)` recomputed is naturally idempotent; anything accumulative needs explicit guards. Add **observability as a first-class feature** — progress (keys done / total), rate, ETA, error and skip counts, current throttle state — because a job you can't see is a job you'll kill out of uncertainty at hour 40.

Two sharp edges complete the craft. **The moving table**: rows written *during* the backfill are already correct (write-both covers them) — the backfill must tolerate meeting them (idempotency again) and must bound itself to the key range that existed at start, or a busy insert pattern makes the job chase its own tail. And **the transform is code**: `f(old_col)` carries all the semantic-drift risk of post 1 — review it like production logic, run it first in verify-only mode (compute, compare, don't write) on a sample, and let post 4's verification judge the result before reads ever switch.

The takeaway: backfills are bulk rewrites made production-safe by four adverbs — **incrementally** (keyset-walked, time-sized, per-batch-committed), **throttled** (a control loop yielding to replication lag and latency, content to take days because write-both guards correctness meanwhile), **resumably** (transactional checkpoints), and **idempotently** (absolute writes, safe re-runs, tolerant of the moving table). Treat the transform as reviewed production code with a verify-only mode, make progress observable, and the week-long rewrite becomes what it should be: boring.

## Key takeaways

- Never the single UPDATE: **keyset-paginated batches, sized by target duration (ms) not row count, committed individually** — locks stay invisible, housekeeping advances, failures cost one batch.
- Throttling is a **control loop**: baseline inter-batch sleep, automatic backoff on replication lag / p99 / I/O — the backfill is the lowest-priority tenant, and days-long is the correct speed.
- Built for interruption: **transactional checkpoints** + **idempotent (absolute) writes** — at-least-once execution is assumed, resume is exact, re-runs are harmless.
- Bound the run to the starting key range (write-both owns the new rows), treat the **transform as reviewed code** with a verify-only sample mode, and expose progress/rate/ETA — invisible jobs get killed at hour 40.

## Further reading

- [Batch processing — bounded units of bulk work](https://en.wikipedia.org/wiki/Batch_processing)
- [Data migration — the broader practice backfills serve](https://en.wikipedia.org/wiki/Data_migration)

---

Author: Pratik Dhanave (https://pratikdhanave.com) | Published: 2026-10-31
Canonical: https://pratikdhanave.com/blog/posts/zdm-03-backfills-at-scale.html
Attribution: please link the canonical URL when citing or quoting this post.
