# Metering — Counting Billions of Events Without Losing One

*Usage-based pricing has a humble prerequisite: you must count correctly. Not approximately — correctly, at whatever volume success brings, across retries, duplicates, late arrivals, and clock skew, because every counted unit is money and every miscounted one is a dispute. Metering is stream processing where the aggregation result appears on an invoice, and that destination changes every engineering trade-off.*

Post [2](/blog/posts/bill-02-pricing-models-in-code.html) modeled prices over usage; this post builds the system that measures the usage. It leans on ideas from [Stream Processing from First Principles](/blog/series/stream-processing-from-first-principles/) — but where analytics tolerates approximation, metering's output is billable, and the differences all flow from that.

## The metering pipeline

Every metering system is the same four stages, each with a correctness obligation:

- **Emit** — the product records a usage event: who, what metric, how much, when. The design rule that prevents years of pain: every event carries a **unique, deterministic idempotency key** (derived from the action, not randomly generated), because everything upstream retries, and at-least-once delivery is the only delivery you'll get.
- **Ingest** — events land in a durable log. Deduplication by idempotency key happens here, at the door (the same write-side discipline as [agent memory](/blog/posts/agmem-04-retrieval-memory.html), for the same reason: the store you can trust is the one you were disciplined about filling).
- **Aggregate** — raw events roll up into per-customer, per-metric, per-period totals. This is where billing's time-dominance (post 1) bites: the aggregation window is the *billing period*, and a unit must land in exactly one period.
- **Rate** — aggregated quantities meet post 2's price versions to produce amounts. Keeping rating separate from aggregation is the classic telecom lesson: quantities are facts; prices are policy; entangling them means re-metering whenever pricing changes.

## The hard problems are all about time and truth

- **Late events.** A usage event generated at 23:59:58 on the period's last day may arrive after midnight — or after the invoice draft. The system needs a declared **grace window** (aggregate finalizes N hours after period close) and a policy for stragglers beyond it (bill next period, or drop and log). What it cannot do is silently re-open finalized totals an invoice already used.
- **Event time vs arrival time.** Billing must aggregate on *when usage happened*, not when the event arrived — which means tolerating out-of-order arrival within the grace window, the watermark discipline of stream processing applied with an accountant watching.
- **Duplicates vs legitimate repeats.** Two identical-looking events may be a retry (count once) or two real actions (count twice). Only the deterministic idempotency key distinguishes them — which is why it's derived from the business action (request ID, job ID) and minted at the *source*, never downstream.
- **Mutations.** Usage sometimes un-happens: a job is cancelled, a customer is credited. Never decrement silently — append compensating events, keeping the log append-only and every total explainable as a sum of visible facts.

## Two meters, one truth

A pattern most teams converge on: **real-time approximate, batch exact**. A streaming path maintains running totals for product surfaces — dashboards, "80% of quota" alerts, spend caps — where seconds matter and small transient error is tolerable. A batch path recomputes period totals from the raw log at finalization — where correctness matters and latency doesn't. The invoice always bills from the batch truth; the streaming view reconciles against it continuously, and divergence beyond tolerance is an alert, not a shrug. This buys the product immediacy without ever billing from an approximation — and the raw event log underneath both is the system of record that makes any total re-derivable, auditable, and (post 8) reconcilable.

Two operational notes earn their place early: **meter at the value boundary, not the cost boundary** — for AI products, bill the thing customers understand (documents processed, minutes transcribed) even while you track tokens internally for margin ([AI Cost Optimization](/blog/series/ai-cost-optimization/) manages that side); and **cardinality is a design budget** — per-customer × per-metric × per-period totals are cheap, but per-request line-item storage at billions of events is a database bill of its own; keep raw events in cheap append storage and aggregates in the fast path.

The takeaway: metering is the emit → ingest → aggregate → rate pipeline with invoice-grade obligations at each stage — deterministic idempotency keys minted at the source, dedup at the door, event-time aggregation into exactly one billing period with a declared grace window, compensating events instead of silent mutation, and rating kept separate from counting. Run two meters — streaming for product immediacy, batch from the raw log for the invoice — reconciled continuously, and meter the unit customers understand while tracking cost units internally. Counting sounds trivial; counting *billably* is a discipline.

## Key takeaways

- The pipeline is **emit → ingest → aggregate → rate**, with quantities (facts) strictly separated from prices (policy) — the old telecom lesson that survives every pricing change.
- **Idempotency keys are deterministic and source-minted**: derived from the business action, because at-least-once delivery is guaranteed and only the key distinguishes a retry from a repeat.
- Time is the hard part: aggregate on **event time**, declare a **grace window**, give stragglers a policy, and never silently reopen finalized totals; usage un-happens via **compensating events**, not decrements.
- **Real-time approximate, batch exact**: stream for dashboards, alerts, and caps; recompute from the raw log for the invoice; reconcile the two continuously.
- Meter the **value unit** customers understand; track cost units internally; budget aggregate cardinality and keep raw events in cheap append-only storage.

## Further reading

- [Stream processing — the computation model metering specializes](https://en.wikipedia.org/wiki/Stream_processing)
- [Idempotence — the property that makes retries billable-safe](https://en.wikipedia.org/wiki/Idempotence)
