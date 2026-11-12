# Why Migrations Break Things — The Downtime Taxonomy

*"Run the migration at 2 a.m." was a plan when users slept somewhere. For a system that's always on, every schema change, backfill, and datastore move must happen underneath live traffic — and the ways that goes wrong are surprisingly few and surprisingly repeatable: locks that queue the world, long transactions that starve it, mismatched assumptions between old code and new schema. This series is the discipline of changing data out from under a running system; this post is the map of how it breaks.*

The [Database Internals](/blog/series/database-internals/) series explains how databases work; this series is about *changing* them while they work. The craft matters doubly now: migration windows shrank to zero at the same time as data volumes made every operation hours long — the squeeze that forced this discipline into existence.

## The taxonomy of migration-induced downtime

Nearly every migration incident is one of five shapes:

- **Lock-induced stalls.** The classic: a DDL statement takes a lock that conflicts with reads or writes, and every query queues behind it. The cruel detail most teams learn in production: the damage isn't only the lock's *duration* but its *queueing* — an `ALTER` waiting politely for a long-running transaction to release its lock will itself block everything arriving after it. A one-second lock behind a ten-minute report is a ten-minute outage.
- **Resource starvation.** The migration competes with production for I/O, CPU, replication bandwidth. A backfill rewriting a terabyte at full speed doesn't lock anything and still takes the site down by saturating the disks — or by lagging the replicas until read-your-writes breaks (post 3's throttling discipline exists for this).
- **Long-transaction side effects.** A migration in one giant transaction holds back the database's housekeeping — vacuum/GC horizons, undo retention, replication positions — degrading everything slowly, then failing at hour three and rolling back at equal cost.
- **Code-schema mismatch.** The deploy and the migration are two events with a gap between them, in both orders: new code against old schema (reads a column that doesn't exist yet) or old code against new schema (violates a constraint it never knew about). During rolling deploys *both code versions run simultaneously* — so compatibility isn't a transition detail, it's the invariant: **every schema state must be compatible with every code version live against it** (post 2 turns this into the expand/contract method).
- **Semantic drift.** The subtlest: data migrated correctly by the letter and wrongly by the meaning — encodings normalized, timezones reinterpreted, implicit invariants ("this column is never null *in practice*") violated by the copy. Nothing errors; reports disagree weeks later. This is why verification (post 4) is a pillar, not a nicety.

## The three vows

The discipline that answers this taxonomy rests on three commitments the whole series elaborates:

- **Never hold a lock proportional to data size.** Operations must be either instant metadata changes or incremental work in small batches — anything that scales lock time with row count is forbidden by construction (posts 2–3).
- **Every step is reversible until the moment it provably isn't.** Migrations are sequences of states, each with a rollback story; the point of no return (dropping the old column, decommissioning the old store) is crossed deliberately, late, and after verification (posts 2, 5).
- **Prove it, don't believe it.** Dual-reads, checksums, diff sweeps — correctness during migration is measured continuously, not asserted at the end (post 4).

The series builds these into method: expand/contract for schema shape (post 2), batched throttled backfills (post 3), dual-write and shadow-read verification (post 4), cutover and rollback mechanics (post 5), cross-store moves via CDC (post 6), and the fleet view — migrations as a repeatable, increasingly automated capability rather than annual heroics (post 7).

The takeaway: migration incidents come in five repeatable shapes — lock queueing (duration × what's behind it), resource starvation, long-transaction side effects, code-schema mismatch across rolling deploys, and silent semantic drift. The discipline against them is three vows: no locks proportional to data size, reversibility until a deliberate and late point of no return, and continuous proof over belief — and the rest of the series is those vows turned into method.

## Key takeaways

- The five failure shapes: **lock queueing** (an ALTER behind a long transaction outages everything after it), **starvation** (I/O and replication lag without a single lock), **long transactions** (housekeeping held back, then a costly rollback), **code-schema mismatch** (both code versions run during rolling deploys — compatibility is the invariant), **semantic drift** (correct by the letter, wrong by the meaning).
- Zero-downtime is forced by two trends meeting: windows went to zero while data made every operation long.
- The three vows: **no data-proportional locks; reversible until a deliberate late point of no return; measured correctness** (verification as a pillar).
- Series map: expand/contract → batched backfills → dual-write/shadow-read verification → cutover and rollback → cross-store CDC moves → fleet-scale automation.

## Further reading

- [Schema migration — the practice this series makes survivable](https://en.wikipedia.org/wiki/Schema_migration)
- [Downtime — the thing being engineered to zero](https://en.wikipedia.org/wiki/Downtime)
