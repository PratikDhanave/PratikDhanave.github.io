# Engineering DORA Operational Resilience

*Turn ICT asset and third-party risk, incident classification, and reporting into a system you can actually run — with a resilience-testing loop that keeps it honest.*

---

Digital operational resilience regulation reframes a familiar engineering problem. It is not asking you to write a policy PDF; it is asking you to prove, continuously, that your critical systems keep working under stress and that when they break you can classify, report, and recover on a clock. For an engineering team that means five moving parts have to become one connected pipeline: an inventory of ICT assets, a risk register, live monitoring, an incident classification engine, and structured regulator reporting — closed by a resilience-testing loop that feeds findings back into the register.

Most teams already have fragments of this. They have a CMDB, a monitoring stack, an incident tool, and a compliance spreadsheet. The gap is that these live in separate silos with no shared identity for an asset, no automatic path from a page to a classification, and no discipline that forces test results back into the risk view. This post walks the pipeline as a system and shows where the wiring usually rots.

## The ICT asset and third-party inventory

Everything anchors to a stable asset identity. An asset is not just a server; it is any ICT resource whose failure could interrupt a business function — a service, a database, a message bus, and critically a third-party provider such as a cloud region, a payment processor, or a KYC vendor. The inventory has to carry the dependency edges, because resilience is a graph property, not a per-node one.

```
[ICT + third-party inventory]
        |
   (each asset carries: owner, criticality, dependencies)
        v
   business function  ── supported by ──▶  asset ── depends on ──▶ third party
```

> **▸ [Open the interactive diagram](/blog/diagrams/fintech-dora-operational-resilience.html)** — pan, zoom, and trace every step (light/dark, self-contained).

The engineering trap here is drift. An inventory maintained by hand is wrong within a quarter. The durable pattern is to derive it: tag infrastructure-as-code resources and service manifests with an owner and a criticality tier, then reconcile that emitted graph against a registry nightly. A third-party provider gets the same treatment — it is a node with a contract reference, a concentration flag (are three critical functions all sitting on one region?), and an exit-plan pointer. If you cannot answer "which business functions break if this vendor goes dark" from a query, the inventory is decorative.

## The risk register as a live index

The risk register is where each asset gets a residual-risk score, not a static rating buried in a document. Treat it as a materialized view over the inventory: for every critical asset, join its known vulnerabilities, its control coverage, its recovery objectives (RTO/RPO), and its last test result. The output is a ranked list that answers "where is our thinnest ice right now."

The important design decision is that the register is downstream of evidence, never a source of it. Controls are asserted by scanners and config checks; recovery objectives are proven by tests; concentration is computed from the dependency graph. When an engineer edits the register directly, you have lost the audit chain. Keep it read-mostly, and make every field trace back to a producing system.

## Monitoring: from telemetry to a candidate incident

Monitoring is the sensor layer, and its job is narrower than most dashboards suggest. It must detect deviation from expected behavior on the assets the register says are critical, and it must emit a candidate incident with enough context to classify. That context is the whole game: which business function is affected, when the degradation started, how many clients or transactions are impacted, and whether data integrity is in question.

```
metrics/logs/traces ─▶ detectors ─▶ candidate incident
                                     { function, start_ts,
                                       clients_hit, txn_hit,
                                       data_integrity? }
```

A page that says "latency high on service-x" is not a candidate incident. A signal that says "the payments function has been degraded for 12 minutes, affecting an estimated 4,000 clients, no data-integrity concern" is — because those are exactly the fields the classifier needs. Instrument for the classification you will have to do, not just for the graph you like to watch.

## Incident classification against thresholds

This is the piece that pure ops tooling usually lacks. Classification is a deterministic function from incident facts to a severity that decides whether a regulatory clock starts. The inputs are the standard resilience dimensions — number of clients affected, duration, geographic spread, data losses, economic impact, and criticality of the affected service — evaluated against thresholds.

```
                 ┌──────────────────────────┐
candidate  ─────▶│  classification engine    │
incident         │  clients ≥ T1 ?           │
                 │  duration ≥ T2 ?          │──▶ major     ─▶ start clock
                 │  data loss ?              │──▶ significant ─▶ track
                 │  economic impact ≥ T3 ?   │──▶ minor      ─▶ log only
                 └──────────────────────────┘
```

Build this as versioned rules, not code buried in a handler, because the thresholds change and every past decision must be reproducible. Store the classifier version alongside each incident record. When an auditor asks why a January incident was "significant" and not "major," you replay the exact rule set that ran, against the exact facts captured. A classification you cannot reproduce is a finding waiting to happen.

## Regulator reporting on a clock

A major classification starts a reporting obligation with distinct phases: an initial notification shortly after detection, an intermediate update as understanding improves, and a final report with root cause once resolved. Engineering-wise this is a small state machine bolted to the incident, with deadlines derived from the detection timestamp.

```
detect ─▶ initial ──(hrs)──▶ intermediate ──(days)──▶ final
   │         │                    │                     │
   └─────────┴──── same incident id, growing evidence ──┘
```

The reports are documents, but the mechanism is data: assemble each report from the captured incident facts plus the investigation timeline, render to the required schema, and submit through the reporting channel. Never retype what monitoring already knows — every hand-copied field is a chance to contradict your own audit trail. Keep the submission receipts; the proof that you reported on time is itself evidence you will be asked for.

## Closing the loop with resilience testing

The pipeline described so far is reactive. What makes it a resilience system rather than an incident-reporting one is the feedback loop from testing. Scenario tests, failover drills, and advanced threat-led penetration testing all produce the same output: findings about where recovery objectives were not met or a dependency failed unexpectedly.

Those findings must land back in the risk register as new or revised entries, which re-ranks the thinnest ice, which redirects monitoring and remediation. Without that write-back, testing becomes a compliance ritual whose results evaporate. With it, each test measurably moves the register, and the register measurably drives the next quarter's engineering work. That closed loop — inventory to register to monitoring to classification to reporting, and testing feeding the register — is the whole architecture, and it is the part a regulator is genuinely checking for.

The lesson from building this is that resilience is not a document you produce; it is a property you can query. If every arrow in that loop is a real integration rather than a manual copy, you can answer any resilience question from your own systems — and that is precisely what the regulation is trying to force.
