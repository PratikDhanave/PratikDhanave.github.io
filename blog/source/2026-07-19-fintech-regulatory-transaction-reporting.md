# Regulatory Transaction Reporting: MiFID II, EMIR, and Beyond

*How a trade turns into a regulator-ready report — eligibility, enrichment, validation, submission, and the break management loop that keeps you compliant.*

Every derivative, equity, and bond trade a regulated firm executes is potentially a reportable event. Under MiFID II, EMIR, Dodd-Frank, ASIC, MAS, and the growing family of rewrites (EMIR REFIT, the CFTC rewrite, JFSA), the obligation is deceptively simple to state and brutally hard to satisfy: report the right trades, with the right fields, to the right venue, within the right deadline — and be able to prove all of it years later. This post walks through the reporting pipeline as an engineering system, not a legal checklist.

## The obligation, in three words

Regulators evaluate transaction reporting against three axes, and every design decision traces back to one of them.

- **Completeness** — did you report every reportable trade, and only reportable trades? Under- and over-reporting are both findings.
- **Accuracy** — do the field values match the economic reality of the trade and the reference data behind it?
- **Timeliness** — did the report land inside the window? MiFID II is T+1; EMIR is T+1; some regimes demand near-real-time. Miss the window and the report is late even if perfect.

Hold these three in mind. The rest of the pipeline exists to make them measurable and defensible.

## Stage 1: Eligibility — which trades count

Not every fill is reportable, and the rules are jurisdiction-specific. A trade booked in one entity may be in scope for EMIR (as an OTC derivative) but out of scope for MiFIR (instrument not admitted to trading). Eligibility is a decision engine, not a filter: for each trade event it answers *which regimes apply* and *what report type* each requires (new, modify, cancel, error, position component).

The engineering trap here is treating eligibility as a boolean. Model it as a **matrix**: trade × regime × action. A single lifecycle event — say, a partial termination — can produce a MiFIR cancel and an EMIR modify simultaneously. Encode the ruleset as versioned, testable data (decision tables) rather than branching code, because the rules change on regulatory timelines you do not control, and every past decision must be reproducible for an audit.

## Stage 2: Enrichment — the identifier problem

A raw trade knows almost nothing the regulator cares about. Enrichment is where you attach the alphabet soup of standardized identifiers, and each one is a distributed-systems problem:

- **LEI** (Legal Entity Identifier) — the 20-character code for each counterparty. LEIs lapse; a lapsed LEI on a report is a rejection. You need a cache with freshness checks against GLEIF.
- **UPI** (Unique Product Identifier) — introduced by the DSB to classify OTC products. Under EMIR REFIT and the CFTC rewrite, UPI replaced a swathe of taxonomy fields.
- **UTI** (Unique Trade Identifier) — the shared key that lets both sides of a trade report the same transaction. Someone must *generate* it and someone must *consume* it; the tie-breaker logic (who mints the UTI) is itself defined by the regulator.
- **ISIN** — for the instrument, sourced from ANNA or the trading venue.

Enrichment is I/O-bound and failure-prone: every lookup can miss, time out, or return stale data. Design it as an idempotent, retryable step that records the *provenance* of every value it attaches — which reference source, which version, at what time. That provenance is not optional metadata; it is future audit evidence.

## Stage 3: Validation — passing the schema before you send

Each Trade Repository (TR) and Approved Reporting Mechanism (ARM) publishes a schema — increasingly ISO 20022 XML under the REFIT rewrites — plus a thick book of business validation rules. Validating locally, *before* submission, is the single highest-leverage thing you can build, because a rejection at the venue costs you a full round-trip against a hard deadline.

Run validation in two tiers. **Schema validation** checks structure and datatypes cheaply. **Business validation** replicates the regulator's own rules — conditional mandatory fields, enumerations, cross-field consistency (notional currency must match the leg, maturity must be after execution). Keep this ruleset versioned and diffable so you can prove which rule set was in force on any given reporting date.

```text
 SOURCES            ELIGIBILITY        ENRICHMENT          VALIDATION         SUBMIT
 ┌──────────┐       ┌──────────┐       ┌──────────┐        ┌──────────┐       ┌──────────┐
 │  Trade   │──────▶│ Scope &  │──────▶│ LEI/UPI  │───────▶│  Schema  │──────▶│  ARM /   │
 │  Events  │       │ action   │       │ UTI/ISIN │        │ + rules  │       │   TR     │
 └──────────┘       │ matrix   │       └──────────┘        └────┬─────┘       └────┬─────┘
 ┌──────────┐       └────┬─────┘                                │ fail            │ ACK/NACK
 │ Reference│            │                                      ▼                 ▼
 │   Data   │────────────┘                              ┌──────────────┐   ┌──────────────┐
 │ (GLEIF/  │                                           │    Break     │◀──│  Reconcile   │
 │  ANNA)   │                                           │  Management  │──▶│  & Resubmit  │
 └──────────┘                                           └──────────────┘   └──────────────┘
```

> **▸ [Open the interactive diagram](/blog/diagrams/fintech-regulatory-transaction-reporting.html)** — the reporting pipeline from trade capture through eligibility, enrichment, and validation to ARM/TR submission, with the break management resubmission loop.

## Stage 4: Submission — the ARM and the Trade Repository

The submission target depends on the regime. MiFIR transaction reports typically flow through an **ARM**, which forwards to the National Competent Authority. Derivative reports under EMIR and Dodd-Frank flow to a **Trade Repository**. Either way, submission is asynchronous: you send a batch, receive an initial technical acknowledgement, and later a per-record accept/reject.

Treat submission as an outbox with delivery guarantees. Persist the exact bytes you sent, correlate every response by your message and record identifiers, and never assume a missing NACK means success — poll or subscribe for status. The gap between "sent" and "acknowledged accepted" is exactly where timeliness breaches hide.

## Stage 5: Break management and resubmission

A **break** is any divergence between what you reported and what should have been reported — a venue rejection, a field the regulator flagged, or a mismatch surfaced by **reconciliation**. Under EMIR, both counterparties report and the TR performs pairing and matching; unmatched fields become breaks you must investigate and correct.

Break management is a workflow engine with SLAs. Each break needs an owner, a root cause (bad reference data? wrong eligibility decision? a mapping bug?), a remediation, and a resubmission that carries the correct action type — a *correction* or *cancel-and-rebook*, not a naive resend that creates a duplicate. Close the loop by feeding root causes back upstream: a recurring LEI break means your enrichment cache is stale, not that an analyst needs to work harder.

## The audit trail is the product

Here is the mindset shift that separates a reporting system that survives an inspection from one that does not: **the report is a side effect; the audit trail is the deliverable.** A regulator can ask, two years later, why a specific trade was reported the way it was — or why it was not reported at all. You must reconstruct the full lineage: the source event, the eligibility decision and the rule version that made it, every enriched value and its provenance, the exact submitted payload, the venue's response, and any subsequent correction.

Build this as an append-only, immutable event log keyed by trade and reporting identifiers. Version the rulesets. Timestamp everything to a trusted clock. Make reconciliation a first-class scheduled job, not a quarterly fire drill. Do that, and completeness, accuracy, and timeliness stop being aspirations you hope to hit and become properties you can measure, alert on, and prove.
