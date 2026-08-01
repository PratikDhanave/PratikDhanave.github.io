# Building an AML Transaction Monitoring Rules Engine

*Typology rules, sliding-window aggregation, alert scoring, and case management that feeds STR/SAR filing — treated as a streaming systems problem, not a compliance checkbox.*

Anti-money-laundering transaction monitoring is usually described in policy language: "detect structuring," "flag rapid movement of funds," "escalate suspicious activity." Underneath that language is a fairly ordinary stream-processing system with unusually strict requirements around auditability and reproducibility. If you build it as a pile of ad-hoc SQL jobs, it becomes impossible to explain why an alert fired eight months ago when a regulator asks. If you build it deliberately, it looks like any other feature-aggregation-plus-rules pipeline, with a few domain-specific twists.

This post walks the pipeline end to end: raw transactions in, suspicious-activity report decisions out.

## The shape of the problem

At the top you have a transaction stream. Each event is a normalized posting — debit or credit, amount in minor units, an entity key, a counterparty, a channel, a timestamp, and a geography. The monitoring system does not care about the payment rail; it cares about behavior over time. That is the first design decision: monitoring operates on an aggregated view of an entity, not on individual transactions in isolation.

The pipeline has five logical stages, and keeping them separate is what makes the system explainable.

```
 transaction        windowed          typology         alert scoring      case queue
   stream    ──▶   aggregation  ──▶    ruleset    ──▶    + dedup     ──▶   + STR/SAR
 (postings)      (sliding sums)   (structuring,      (severity, group    (analyst
                                   velocity, geo)      by entity)          disposition)
                                        │
                                        └── low score ──▶ auto-clear (logged)
```

> **▸ [Open the interactive diagram](/blog/diagrams/fintech-transaction-monitoring-rules.html)** — pan, zoom, and trace every step (light/dark, self-contained).

Each stage produces an immutable, timestamped artifact. The aggregation stage produces feature snapshots. The rule stage produces rule-hit records. The scoring stage produces alerts. This lineage is not optional bookkeeping — it is the evidence trail. When someone asks "why did this alert fire," you replay the answer from stored features rather than reconstructing it from live data that has since changed.

## Sliding-window aggregation is the hard part

The interesting engineering is in the aggregation stage. Typologies are almost always expressed over windows: "more than nine cash deposits under the reporting threshold within a rolling seven days," "aggregate inbound and outbound within 24 hours exceeds a multiple of expected activity." So you need windowed counters and sums keyed by entity, and you need them to be correct under replay.

Two properties matter more than raw throughput. First, windows must be **deterministic**: the same input stream must produce the same aggregate regardless of when the job runs or how events are batched. That rules out naive wall-clock windows and pushes you toward event-time windows with a defined watermark and late-arrival policy. Second, aggregates must be **queryable at decision time**, so an online feature store or a compacted state store sits between aggregation and rule evaluation.

A minimal sliding-window aggregate keyed by entity looks like this:

```python
def update_window(state, event, now, window_secs):
    key = (event.entity_id, event.metric)          # e.g. ("acct-42", "cash_in")
    dq = state.setdefault(key, deque())
    dq.append((event.ts, event.amount))
    cutoff = now - window_secs
    while dq and dq[0][0] < cutoff:                 # evict aged events
        dq.popleft()
    return {
        "count": len(dq),
        "sum":   sum(a for _, a in dq),
        "max":   max((a for _, a in dq), default=0),
    }
```

In production the `deque` becomes a state store with checkpointing, and eviction is driven by event-time watermarks rather than `now`, but the semantics are exactly this. The rule engine never touches raw postings; it reads these rolled-up features. That separation is what lets you re-tune a threshold and replay six months of history in an afternoon.

## Encoding typologies as rules

A typology is a named pattern of suspicious behavior. Structuring, rapid movement, layering, unusual geography, and dormant-then-active are the common ones. Each becomes a rule that reads features and emits a hit with a severity and — critically — the exact feature values that triggered it.

```python
def structuring_rule(features, cfg):
    if (features["cash_in.count_7d"] >= cfg.min_deposits and
            features["cash_in.max"] < cfg.report_threshold and
            features["cash_in.sum_7d"] >= cfg.aggregate_floor):
        return Hit(
            typology="structuring",
            severity="high",
            evidence={
                "deposits_7d": features["cash_in.count_7d"],
                "largest":     features["cash_in.max"],
                "total_7d":    features["cash_in.sum_7d"],
            },
        )
    return None
```

Three engineering rules keep this maintainable. Keep rule logic **pure** — a function of features and config, no I/O — so it is unit-testable and replayable. Externalize every **threshold** into versioned config so tuning is a data change, not a deploy, and so an alert can record which config version produced it. And always attach **evidence**, because an alert without the numbers that caused it is useless to an analyst and indefensible to a regulator.

New typologies are added as new pure functions; they never modify the aggregation contract. This is the extension point that gets exercised most, so it must be cheap.

## Scoring, deduplication, and alert fatigue

Raw rule hits are not alerts. A busy account can trip several typologies in one window, and the same behavior can re-trigger every time the pipeline runs. Dumping all of that into an analyst queue is how monitoring programs drown.

The scoring stage collapses hits into alerts. It groups hits by entity and time bucket, combines severities into a single score, and **deduplicates** against recent open alerts so the same ongoing behavior does not generate a fresh case every hour. A common approach is a stable alert key — entity plus typology plus window bucket — with a suppression window: if an open alert with the same key exists, attach the new evidence to it rather than creating a duplicate.

Scoring is also where the economics live. Below a configured score, an alert is **auto-cleared** and logged rather than routed to a human. That auto-clear path is not a shortcut to hide work — it is a recorded disposition, reviewable and reversible, that keeps analyst attention on the cases most likely to be genuinely suspicious. Getting this threshold right is the difference between a program that reviews signal and one that reviews noise.

## From alert to case to STR

Alerts that survive scoring become cases. A case aggregates all the alerts for an entity, the underlying transactions, the entity's KYC profile, and any prior filings. An analyst dispositions it: close as not suspicious, request more information, or escalate.

Escalation produces a suspicious-activity report — an STR or SAR depending on jurisdiction — filed with the financial intelligence unit. From an engineering standpoint the important properties are that every disposition is **attributable** (who decided, when, on what evidence) and **immutable** (dispositions append, never overwrite), and that filing is **idempotent** so a retried submission does not double-file. The case record becomes the durable audit object that outlives the transient alert.

## Replay, tuning, and false-positive economics

The recurring theme is reproducibility. Because features, hits, and alerts are all stored artifacts, you can answer three questions that regulators and your own risk team will ask: why did this fire, what would a proposed threshold change do to historical volume, and did we miss anything a new typology would have caught. All three are replay operations over stored state, not forensic reconstructions.

That is the payoff for treating AML monitoring as a disciplined streaming pipeline rather than a bag of alerts. The compliance requirements — explainability, auditability, defensibility — turn out to be the same properties good stream engineering gives you anyway: deterministic windows, pure rules, versioned config, immutable lineage, and idempotent side effects. Build those in from the first stage and the compliance story writes itself.
