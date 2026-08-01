# Payment SLOs That Actually Matter

*Instrument auth rate, settlement lag, and decline-reason breakdowns instead of raw uptime.*

---

## Why generic uptime lies about payments

Most service dashboards answer one question: is the process up and returning 200s? For a payment system that question is almost useless. A gateway can be at 100% uptime, p99 latency well inside budget, and zero 5xx responses while quietly losing money — because the acquirer silently started declining a card range, a 3-D Secure step-up began timing out, or a single PSP's issuer connection degraded. Every one of those failures returns a perfectly valid HTTP 200 carrying a decline. Your infrastructure is healthy; your revenue is not.

The fix is to stop treating a payment as an HTTP request and start treating it as a business event with a lifecycle. The signals that matter are the ones a finance team would recognize: what fraction of attempts got authorized, how long money took to actually settle, and *why* the declines happened. Those three — authorization rate, settlement lag, and decline-reason distribution — are the SLOs I instrument first on any payments platform. Everything else is supporting telemetry.

## The one event that anchors everything

The discipline that makes payment observability tractable is emitting a single, normalized event at each state transition of a payment, with a stable correlation ID that survives every hop. Retries, PSP failover, webhook callbacks, and settlement reconciliation all reference the same `payment_id`. If you get this right, every metric below is just a different aggregation over one event stream.

```
attempt ──► authorized ──► captured ──► settled
   │             │
   └─► declined  └─► failed (capture error)
```

> **▸ [Open the interactive diagram](/blog/diagrams/fintech-payments-observability-slos.html)** — pan, zoom, and trace every step (light/dark, self-contained).

A minimal event looks like this — flat, dimension-rich, and cheap to aggregate:

```json
{
  "payment_id": "p_8f3a...",
  "ts": "2026-08-24T10:14:22Z",
  "state": "declined",
  "psp": "psp_a",
  "method": "card",
  "scheme": "visa",
  "issuer_country": "GB",
  "amount_minor": 4200,
  "currency": "GBP",
  "decline_code": "insufficient_funds",
  "attempt": 1
}
```

The rule I enforce in review: no free-text status strings and no unbounded cardinality. `decline_code` comes from a fixed enumeration mapped from raw PSP responses; `issuer_bin` is bucketed, never raw. High-cardinality fields explode a time-series database and make the dashboards unqueryable at exactly the moment you need them.

## Authorization rate — the metric with a dozen denominators

Auth rate sounds trivial: authorized divided by attempts. The engineering difficulty is choosing the denominator, because the honest number depends entirely on what you exclude. Hard declines the customer caused (wrong CVV, expired card) are not the platform's fault. Soft declines the *issuer* returned that a retry could recover — `do_not_honor`, transient `issuer_unavailable` — absolutely are your problem, and blending the two hides the failures you can actually fix.

I compute auth rate as a set of sliced ratios rather than one headline number:

```
auth_rate(slice) = authorized(slice) / (attempts(slice) − customer_hard_declines(slice))
```

sliced by `psp`, `scheme`, `issuer_country`, and `method`. The slicing is the whole point. A 2-point drop in the blended number is invisible; the same drop isolated to `psp_a × visa × GB` is a page. When a PSP silently degrades, the blended average barely moves while one cell collapses — so you alert on per-slice deviation from that slice's own trailing baseline, not on a global threshold. A card range that normally authorizes at 94% dropping to 80% is an incident regardless of what the aggregate says.

## Settlement lag — the money-actually-moved metric

Authorization is a promise; settlement is the cash. The gap between them is where reconciliation breaks, where funding shortfalls hide, and where a stuck batch quietly ages. Settlement lag is the wall-clock time from `captured` to `settled`, and it is almost never normally distributed — it is multi-modal, clustered around PSP batch cut-off times and scheme settlement windows. Reporting a mean here is malpractice; the mean sits in an empty valley between the modes.

Track the distribution, not the average. What earns its place on the dashboard:

- **p50 / p95 / p99 lag per PSP** — the long tail is where funding risk lives.
- **Unsettled aging buckets** — count of captured-but-not-settled payments in 0–24h, 24–48h, 48h+ windows. Anything aging past the PSP's contractual window is a reconciliation break, not a slow batch.
- **Settled-amount vs captured-amount variance** — a running check that money in equals money promised, catching fee discrepancies and partial settlements.

The aging bucket is the one that saves you. A mean or even a p99 can look fine while a small, growing cohort of payments never settles at all — those are the ones that surface as an angry finance ticket three weeks later.

## Decline-reason breakdown — turning declines into a work queue

A raw decline rate tells you something is wrong; a decline-reason breakdown tells you what to *do*. The categories drive completely different responses, so the taxonomy is the deliverable:

- **Issuer soft declines** (`do_not_honor`, `issuer_unavailable`) → retry logic, PSP routing changes, retry-timing tuning.
- **Customer hard declines** (`insufficient_funds`, `expired_card`) → checkout UX, dunning, account-updater services.
- **Fraud / risk blocks** (`suspected_fraud`, 3DS failures) → risk-rule tuning; here a *rising* block rate can be the system working, so it is read against chargeback rate, never alone.
- **Technical failures** (timeouts, malformed requests, `processor_error`) → your bug, your page.

I render this as a stacked breakdown over time so a shifting *mix* is visible even when the total holds flat. A decline rate steady at 8% while the technical-error slice doubles is a silent integration regression that a single number would hide entirely. The pipeline that produces all of this is one aggregation job: consume the normalized event stream, roll up counts into the slices above, and emit both real-time aggregates for alerting and durable rollups for trend analysis and finance reconciliation.

```
events ─► aggregation ─► auth-rate / lag / decline-mix ─► dashboards ─► alerts ─► action
```

## Alert on symptoms customers feel

The final discipline is choosing *what* pages a human. Do not alert on infrastructure proxies like CPU or queue depth; alert on the business symptom directly, because that is what the customer experiences. My default alerting SLOs:

- Per-slice auth rate deviating below its trailing 7-day baseline by more than a set margin, sustained across a short window (not a single dip).
- Settlement aging past the PSP's contractual window — a hard threshold, because it is contractual.
- Technical-decline share crossing a ceiling, which almost always means an integration or config regression rather than customer behavior.

Route each alert to the owner implied by its category: soft-decline drops to the payments-routing team, aging breaks to reconciliation, technical spikes to on-call engineering. An SLO that pages the wrong team is only marginally better than no SLO at all. The whole system rests on one idea worth repeating: one normalized event per state transition, one correlation ID, and every metric that matters falls out as an aggregation you can trust when it is 3 a.m. and the money has stopped moving.
