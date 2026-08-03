# Real-Time Velocity Checks and the Fraud Feature Store

*Building low-latency sliding-window counters, entity-keyed aggregates, and an online feature store that stays consistent with its batch-computed twin.*

---

A velocity check answers a deceptively simple question at authorization time: *how many times has this thing happened recently?* Five card-not-present attempts on one PAN in ninety seconds, forty distinct cards from one device in an hour, a burst of small-dollar authorizations across one IP range — each is a count over a window, evaluated inline while a cardholder waits for approval. The hard part is not the arithmetic. It is producing that count in single-digit milliseconds, for millions of entities, without letting the numbers quietly drift away from reality.

This post walks through the engineering of that path: the counter primitive, the entity keys that drive fan-out, the online store that serves reads, and the batch pipeline that has to agree with it.

## The latency budget shapes every other decision

Velocity checks live on the authorization critical path. The whole auth round trip typically has a budget in the tens of milliseconds, and fraud scoring is one stage among several — tokenization, balance checks, network round trips. Realistically the feature layer gets a few milliseconds of that budget to return a vector of counts. That single constraint forces most of the architecture.

You cannot compute `COUNT(*) WHERE entity = ? AND ts > now - window` against a transactional database inline. Even with a good index, the tail latency under load is unacceptable, and you would be putting fraud reads in contention with the writes that book money. So the counts are **pre-aggregated and pushed** to a store optimized for point reads, and the auth path only ever does a keyed lookup — never a scan, never a join.

```
                 write path (async)                 read path (inline, few ms)
  auth event ─▶ stream ─▶ window aggregator ─▶ online feature store ◀── decisioning
  (card/device/IP)          (sliding counters)     (keyed point reads)     (rules + model)
                                   │
                                   └────▶ batch backfill ◀── event lake (source of truth)
                                          (recompute + reconcile)
```

> **▸ [Open the interactive diagram](/blog/diagrams/fintech-velocity-fraud-feature-store.html)** — pan, zoom, and trace every step (light/dark, self-contained).

The read side is dumb and fast on purpose. All the interesting work is on the write side, where a stream processor maintains the windowed aggregates, and in the reconciliation loop that keeps the fast store honest.

## Sliding-window counters as the core primitive

The naive "store every event timestamp and count on read" approach is correct but too slow and too heavy — an entity with a burst holds thousands of timestamps and every read re-scans them. The standard trick is a **bucketed sliding window**: divide the window into fixed sub-intervals, keep one counter per bucket, and sum the buckets that overlap the window. A one-hour window with one-minute buckets is sixty small integers per entity; incrementing is O(1) and reading is a fixed 60-add.

```python
# Fixed-granularity bucketed window. Increment is O(1); read sums a fixed
# number of buckets. Buckets are addressed by (entity_key, bucket_index)
# so old buckets expire naturally instead of being deleted.

def bucket_index(ts_ms: int, bucket_ms: int) -> int:
    return ts_ms // bucket_ms

def on_event(store, entity_key: str, ts_ms: int, bucket_ms: int, ttl_s: int):
    idx = bucket_index(ts_ms, bucket_ms)
    field = f"{entity_key}:{idx}"
    store.incr(field)                 # atomic add
    store.expire(field, ttl_s)        # bucket self-expires past the window

def velocity(store, entity_key: str, now_ms: int,
             bucket_ms: int, num_buckets: int) -> int:
    end = bucket_index(now_ms, bucket_ms)
    fields = [f"{entity_key}:{i}" for i in range(end - num_buckets + 1, end + 1)]
    return sum(int(v or 0) for v in store.mget(fields))
```

Two properties make this production-safe. First, buckets **expire on their own** via TTL, so there is no delete job and no unbounded growth — an entity that goes quiet simply ages out. Second, the counts are approximate at the edges (you get bucket-granular boundaries, not exact per-second precision), which is fine: a fraud rule that fires at "≥ 20 in 10 minutes" does not care whether the true figure is 20 or 21. Choose bucket size by how much boundary error a rule tolerates. When exactness genuinely matters — distinct-count features like "unique cards per device" — reach for a probabilistic structure such as HyperLogLog rather than a growing set.

## Entity keys and the fan-out problem

A single authorization is not one velocity feature; it is many. The same event updates counters keyed by PAN, by device fingerprint, by IP, by email, by merchant, and by composite keys like `device × merchant`. Each key answers a different fraud question — a compromised card, a bot farm, a proxy pool, a testing spree against one merchant. So one inbound event fans out into a dozen or more counter increments.

This fan-out is the real throughput driver. Model it explicitly: a declarative table of `(feature_name, entity_key_expr, window, bucket_size)` that the aggregator reads, rather than hand-written increments scattered through code. That table becomes the contract between the real-time job and the batch job — both must derive features from the *same* definitions, or they will disagree. Keep the key extraction pure and side-effect free so it can run identically in a stream operator and a batch mapper.

Guard the key space, too. Fraudsters deliberately generate high-cardinality garbage — fresh device IDs, rotating IPs — to blow up your key count and evict useful hot keys. Cap per-entity memory, prefer bounded structures, and treat "never seen before" as its own signal rather than something to store forever.

## Keeping online and offline features consistent

Here is the failure that quietly poisons fraud models. Your model is trained offline on historical features computed by a batch job over the event lake. It is served online with features from the streaming store. If the two compute even slightly differently — a different window boundary, a timezone, an event the stream dropped — the model sees inputs at inference that never appeared in training. This **train/serve skew** degrades the model with no error, no alert, just a slow rise in missed fraud.

The defenses are structural:

- **One definition, two runtimes.** Both paths read the same feature registry. If a window is "10 minutes, 30-second buckets," neither job gets to reinterpret it.
- **Batch is the source of truth; stream is the fast approximation.** A periodic backfill recomputes windowed aggregates from the immutable event lake and overwrites the online store's older, already-closed buckets. The stream owns only the *live* edge of the window; everything behind the current bucket boundary is reconciled to the batch figure.
- **Log served features, not just recompute them.** Persist the exact feature vector used for each decision. Training on *logged* values — what the model actually saw — sidesteps skew entirely and gives you ground truth for debugging.

The batch/stream split also handles late and out-of-order events. The stream, optimized for latency, may miss a straggler that arrives after its bucket closed; the backfill, optimized for completeness, folds it back in. Real-time is allowed to be slightly wrong on old buckets precisely because a slower, correct process is coming behind it.

## Failure modes and safe defaults

Decide up front what a velocity check returns when the store is unreachable or slow. The two options — fail-open (approve, assume zero velocity) and fail-closed (decline or step up) — are a fraud-loss-versus-false-decline tradeoff, and the right answer is segment-specific: fail-closed on a high-risk corridor, fail-open on a trusted low-value flow. Bound every lookup with a hard timeout well inside the auth budget, and treat a timeout as a first-class outcome the rules can branch on, not an exception that bubbles up.

Finally, remember counts are a **feature, not a verdict**. Velocity feeds the rules and the model; it does not decide alone. Emit the raw counts and let the decisioning layer combine them with everything else — which is exactly where the next boundary in the fraud stack begins.
