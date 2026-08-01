# From AML Alert to Filed SAR: Engineering the Case Management Pipeline

*Turn AML alerts into investigated cases and filed SAR/STR reports, complementing rule-based monitoring.*

---

Rule-based transaction monitoring is the part of anti-money-laundering (AML) engineering that gets the attention: thresholds, velocity rules, peer-group models, typology detectors. But a firing rule is not the deliverable. The regulator does not care how clever your structuring detector is; it cares whether suspicious activity was investigated and, where warranted, reported through a Suspicious Activity Report (SAR) or Suspicious Transaction Report (STR). The system that carries an alert from "a rule fired" to "a report was filed and the decision is defensible" is the case management pipeline. It is a workflow engine wearing a compliance costume, and it fails in the same ways any workflow engine fails: lost state, missing audit trail, and unbounded queues.

This post is about that pipeline as an engineering artifact — the states, the data model, and the invariants that keep it audit-ready.

## Why an alert is not a case

An alert is a cheap, high-volume signal. A case is an expensive, durable investigation record. Conflating them is the first design mistake, because they have different cardinalities and lifetimes.

A single customer can generate dozens of alerts across different rules in a week. If each alert became its own case, an investigator would open the same customer twenty times and re-derive the same context. So the pipeline needs a **correlation step**: alerts are grouped into a case by subject (customer, account, or a cluster of related parties) and a time window. One case aggregates many alerts; a case outlives the alert that opened it.

That correlation decision is load-bearing. Group too aggressively and you bundle unrelated behavior, diluting the narrative you will eventually have to write for the regulator. Group too loosely and you flood the queue with duplicates and risk *tipping-off* inconsistencies where two investigators reach different conclusions about the same person.

## Triage: cutting the false-positive flood

Rule-based monitoring is deliberately over-sensitive; false-positive rates of 90–95% are normal. If every alert went straight to a human, the investigation team would drown. Triage is the pressure-relief valve.

Triage is a scoring and routing layer that sits between raw alerts and case creation. It enriches each alert with context the rule engine never had — KYC risk rating, prior case history, sanctions and PEP status, expected activity profile — and produces a disposition: auto-close with a reason code, hold for more signal, or promote to a case with a priority.

```text
   Monitoring rules            Triage layer                 Case queue
 ┌──────────────────┐    ┌──────────────────────┐    ┌──────────────────┐
 │ velocity rule ───┼──▶ │ correlate by subject │    │   HIGH  ▓▓▓      │
 │ structuring  ───┼──▶ │ enrich (KYC/PEP/hist) │──▶ │   MED   ▓▓       │
 │ peer-group   ───┼──▶ │ score + dedupe        │    │   LOW   ▓        │
 └──────────────────┘    └──────────┬───────────┘    └──────────────────┘
        (high volume)               │ auto-close (reason-coded)
                                     ▼
                              audit log (append-only)
```

> **▸ [Open the interactive diagram](/blog/diagrams/fintech-sar-str-case-management.html)** — pan, zoom, and trace every step (light/dark, self-contained).

The critical engineering rule here: **an auto-close is still a decision, and every decision is logged.** Regulators examine your false-positive handling as closely as your filings. A silently dropped alert is indistinguishable from a bug, and in an exam it will be treated as one. Auto-closure needs a reason code, a model version, and a timestamp, written to the same append-only log that records human decisions.

## The case as a state machine

Once an alert is promoted, it becomes a case with an explicit lifecycle. Modeling it as a state machine — rather than a bag of boolean flags — is what makes the pipeline auditable and testable. Each transition has an actor, a timestamp, and a reason; the current state is always derivable by folding the transition log.

A minimal but honest lifecycle looks like this:

```text
  NEW ──▶ TRIAGE ──▶ OPEN ──▶ UNDER_REVIEW ──┬──▶ FILE_SAR ──▶ FILED
   │         │                     │          │
   │         └──▶ AUTO_CLOSED      │          └──▶ NO_ACTION ──▶ CLOSED
   │             (reason-coded)    │
   └──────────────────────────────┴──▶ ESCALATED ──▶ (MLRO review)
```

The invariants matter more than the boxes:

- **No terminal state without a documented rationale.** `CLOSED` and `FILED` both require a written narrative. You cannot close a case by clicking a button; the button demands text.
- **Transitions are append-only.** You never mutate a case's state field in place. You append a transition event and recompute. This is what lets you reconstruct exactly what an investigator knew at each step during an exam years later.
- **Separation of duties.** The person who investigates may not be the person who approves a filing. The Money Laundering Reporting Officer (MLRO) or a designated approver signs off. The state machine enforces this by making `FILE_SAR` reachable only through an approval transition performed by a different authenticated actor.

## The investigation workspace

`UNDER_REVIEW` is where the human work happens, and it is mostly a data-aggregation problem. The investigator needs one screen that pulls together transaction history, counterparties, device and session signals, prior alerts and cases, and any adverse-media or sanctions hits. The engineering challenge is assembling this **as of the case's timeline**, not as of now — balances and risk ratings change, and the record must reflect what was true when the activity occurred.

Two patterns keep this defensible:

1. **Snapshot on promotion.** When a case is created, snapshot the enrichment data (KYC state, risk score, related-party graph) into the case record. Live links to the customer master are fine for convenience, but the frozen snapshot is the evidence.
2. **Immutable evidence attachments.** Documents, screenshots, and exported statements are content-addressed and write-once. If an investigator adds a note, it is a new event, never an edit of an old one.

The narrative the investigator writes is the actual product of this stage. Everything else — the graph views, the enrichment — exists to make that narrative accurate and fast to produce.

## Filing, the regulatory clock, and confidentiality

When a case reaches `FILE_SAR`, two hard constraints kick in.

First, **the clock.** Most regimes impose a filing deadline measured from the moment of determination — commonly around 30 days. Your system must track the determination timestamp and surface aging prominently, because a late filing is itself a violation. This is a queue-latency SLO with legal teeth, and it deserves the same monitoring you would give any latency SLO: dashboards, alerting on cases approaching the deadline, and a hard-to-ignore escalation when one breaches.

Second, **confidentiality.** SAR/STR filings are subject to strict anti-tipping-off rules — the subject must never learn they were reported. This shapes access control: filing records are compartmentalized, visible only to the compliance function, and never surfaced in customer-facing systems or support tooling. A join that accidentally exposes "this customer has a SAR" to a call-center agent is not a minor bug; it is a reportable failure.

The actual submission goes to the relevant Financial Intelligence Unit (FIU) over its prescribed channel — a structured file format or API. Treat it like any external integration with a compliance twist: validate against the schema before submission, capture the acknowledgment and reference number, and store both in the immutable case record.

## The audit trail is the product

The theme running through every stage is that the append-only audit log is not a side effect — it is the deliverable. Auth decisions, triage scores, state transitions, evidence attachments, and the final filing acknowledgment all land in the same tamper-evident event stream, each carrying actor, timestamp, and reason.

Build the pipeline log-first and the compliance properties fall out for free: you can replay any case, prove separation of duties, demonstrate that no alert was silently dropped, and reconstruct exactly what was known when a decision was made. Build it state-field-first and you will spend the next exam explaining why you cannot answer those questions. The case management pipeline is where AML stops being a detection problem and becomes a systems-of-record problem — and systems of record live or die by their logs.
