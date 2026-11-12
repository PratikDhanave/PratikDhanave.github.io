# Dual-Writes and Shadow Reads — Proving Two Copies Agree

*Every serious migration passes through a phase where the same truth lives in two places — old column and new, old table and new, old store and new — and the entire migration's integrity rests on those copies agreeing. Hope is not a strategy and spot-checking is barely one; the disciplines that actually prove agreement are dual-writes done with eyes open, shadow reads that compare on every request, and diff sweeps that check everything else. This is the migration's measurement layer — post 1's third vow made operational.*

Posts [2](/blog/posts/zdm-02-expand-contract.html)–[3](/blog/posts/zdm-03-backfills-at-scale.html) created the two copies; this post keeps them honest — which matters because the write-both phase is where silent divergence is born, and reads switch (post 5) on the assumption it wasn't.

## Dual-writes with eyes open

Application-level dual-writing — the app writes old shape, then new — is the standard move and carries a known, frequently-ignored flaw: **two writes are not one transaction**. Within one database, you often *can* make them one transaction, and should — that's the happy case that makes same-store expand/contract gentle. Across stores (post 6's world), you usually can't, and the gap between writes is where divergence breeds: the crash after write-one, the partial failure, the two app instances racing the same row in opposite orders. Eyes-open dual-writing means naming the policy: old store remains **source of truth** throughout; a new-store write failure is logged-and-reconciled, never a user-facing error (the migration must not degrade production); ordering races are tolerated because verification-and-repair (below) converges them; and where the stakes demand better than "tolerated," the write is restructured around an **outbox/CDC feed** — publish the change once from the source of truth's own log and *derive* the new copy, trading the two-writers problem for one-writer-one-follower (the architecture post 6 builds fully).

## Shadow reads: verification on the request path

The backfill finished, dual-writes are flowing — are the copies equal *where it counts*? Shadow reads answer on live traffic: serve from the old path, **also** read the new path, compare, record. The design details that make it safe and useful: comparisons happen **off the response path** (async, sampled under load) so verification never adds user latency; mismatches emit **structured diffs** (key, fields differing, both values, timestamps) into a queue someone owns — a mismatch *rate* is a dashboard, but mismatch *examples* are the debugging; sampling is tiered (100% of a new tenant's traffic, 1% of the fleet) and ramped with confidence; and **expected noise is modeled** — replication delay and in-flight write-both races produce transient mismatches that re-check-after-delay filters out, leaving the persistent ones that matter. Shadow reads verify the *hot* truth: what traffic actually touches. Their blind spot is everything traffic doesn't touch — which is the diff sweep's job: a batch comparison walking both copies (checksums per range for cheap "probably equal," row-level diff on ranges that disagree — the same keyset/throttle machinery as post 3, pointed at reading), catching the cold-data divergence shadow reads never see.

## Repair, and the metric that gates cutover

Verification without repair is a very precise anxiety generator. Found divergence feeds a **repair loop**: re-copy from source of truth, idempotently (post 3's writes again), automatically for the known-benign classes, with human eyes on anything novel — because a *new class* of mismatch means a bug in dual-write logic or transform, and repairing the symptom without reading the cause is how you launder corruption into the new store. The output of this whole layer is one number with teeth: **sustained verified-agreement rate** — shadow-read match rate plus sweep cleanliness over a defined window. That number, at a defined threshold, for a defined duration, is the *precondition* post 5's cutover will demand. Not "the backfill finished," not "the team feels good" — measured agreement, because post 1's vow was prove it, don't believe it.

The takeaway: the two-copies phase is kept honest by three instruments — **dual-writes with the race named** (source of truth declared, new-write failures reconciled not surfaced, outbox/CDC when the stakes outgrow tolerate-and-repair), **shadow reads** (async, sampled, noise-filtered comparison on live traffic with structured diffs), and **diff sweeps** (checksum-then-drill batch comparison for the cold data traffic never touches) — all feeding an idempotent repair loop that fixes benign classes automatically and investigates novel ones. The deliverable is the agreement rate that gates cutover: proven, sustained, and numeric.

## Key takeaways

- **Dual-writes are not atomic across stores**: declare the source of truth, swallow-and-reconcile new-side failures, tolerate ordering races only because repair converges them — and upgrade to **outbox/CDC** (one writer, one follower) when tolerance isn't acceptable.
- **Shadow reads** compare on live traffic: off-path and sampled, structured diffs with an owner, transient-noise filtering via re-check — verifying the hot truth.
- **Diff sweeps** (range checksums, then row-level drill-down, throttled like any backfill) verify the cold truth shadow reads can't see.
- Verification feeds **idempotent repair** — automatic for known-benign classes, investigated for novel ones (new mismatch classes are bugs, not chores).
- The layer's output is the **sustained verified-agreement rate** — the numeric precondition cutover (post 5) requires.

## Further reading

- [Replication (computing) — maintaining agreeing copies, the general problem](https://en.wikipedia.org/wiki/Replication_(computing))
- [Data consistency — what "the copies agree" formally means](https://en.wikipedia.org/wiki/Data_consistency)
