# AML and Transaction Monitoring

*Knowing your customer is the front door; watching what they do is the rest of the house. AML transaction monitoring is the always-on system that scans activity for signs of money laundering — and it's a fascinating engineering problem precisely because the signal is rare, the cost of missing it is severe, and the cost of over-flagging drowns your investigators.*

KYC establishes who your customers are. **AML (Anti-Money Laundering)** monitoring watches what they *do* — scanning transactions and behavior for patterns that suggest money laundering or other financial crime, and flagging suspicious activity for investigation and reporting. This post covers AML monitoring as an engineering system: what it's looking for, the rules-versus-ML approaches, the false-positive problem that dominates it, and the investigation workflow it feeds. It's where compliance meets real-time data engineering and detection.

## What AML monitoring is for

Money laundering is making illegally-obtained money appear legitimate, and financial institutions are legally required to detect and report activity that suggests it. **Transaction monitoring** is the system that does this: it analyzes transactions (and related behavior) to identify **suspicious activity** — patterns inconsistent with legitimate use or matching known laundering techniques — so it can be investigated and, where warranted, reported to authorities.

The engineering shape: transaction data flows through a monitoring system that applies detection logic and generates **alerts** on suspicious patterns; alerts go to human investigators who decide whether to file a report (the reporting post). It's a detection-and-triage pipeline, running continuously over the transaction stream, and it must be both effective (catch real laundering) and efficient (not bury investigators in noise) — a tension that defines the whole domain.

## What it looks for

AML monitoring hunts for patterns that suggest laundering rather than legitimate activity. Without cataloguing every technique, the recurring shapes include:

- **Structuring** — breaking a large amount into many smaller transactions to stay under reporting thresholds. A classic pattern monitoring specifically targets.
- **Unusual activity for the customer** — transactions inconsistent with the customer's established profile and history (the KYC profile matters here): sudden large volumes, activity that doesn't fit their stated purpose, or a dormant account springing to life.
- **Rapid movement / layering** — money moving quickly through many accounts or products to obscure its origin.
- **High-risk connections** — transactions involving high-risk jurisdictions, entities, or counterparties.
- **Velocity and volume anomalies** — spikes in frequency or amount that deviate from normal.

The key idea for engineers: much of AML detection is **anomaly and pattern detection over customer behavior**, which is why the customer profile from KYC and the *baseline* of normal behavior are so central — "suspicious" is largely defined relative to what's normal for *this* customer and expected for this product. Monitoring both against fixed known-bad patterns *and* against each customer's own baseline is the substance of the system.

## Rules vs. machine learning

There are two broad approaches to detection, and mature systems combine them — a decision that echoes the rules-vs-ML theme across this blog:

- **Rules-based monitoring** — explicit rules encoding known suspicious patterns ("flag structuring: multiple transactions just under a threshold in a short window"). Strengths: **explainable** (you can state exactly why an alert fired — crucial for regulators and investigators), predictable, and directly encoding known typologies. Weaknesses: rigid (misses novel patterns not encoded), and prone to generating many false positives because rules are coarse.
- **Machine-learning monitoring** — models that learn to detect suspicious patterns, including subtle or novel ones rules miss, and that can reduce false positives by scoring risk more nuancedly. Strengths: catches what rules don't, adapts, can prioritize better. Weaknesses: **explainability** — a model flagging a transaction must still be explainable to regulators and investigators (you can't tell an auditor "the model said so"), which is a hard requirement, connecting straight to the [AI Governance](/blog/series/ai-governance-for-engineers/) concerns.

The practical reality is that most serious AML systems use **both**: rules for the well-understood, must-catch patterns (with clear explainability) and ML to catch subtler patterns and to *prioritize* alerts. And crucially, in this regulated context, **explainability is non-negotiable** — however you detect, you must be able to justify why something was (or wasn't) flagged. This constrains how ML is used: favor explainable models or pair models with explanations, because "unexplainable" fails a core compliance requirement.

## The false-positive problem

The single most important operational reality of AML: **the vast majority of alerts are false positives.** Genuine laundering is rare relative to total transactions, so any detection sensitive enough to catch it inevitably flags large numbers of legitimate transactions too. This dominates the engineering, because both directions are costly:

- **False positives** — legitimate transactions flagged as suspicious. Each one consumes scarce investigator time, and the sheer volume can overwhelm compliance teams, causing backlogs where real issues wait behind noise. Excessive false positives are the chronic pain of AML operations.
- **False negatives** — real laundering *missed*. These are the truly dangerous failures — the ones regulators penalize and that let crime through — so you can't simply tighten everything to reduce false positives, because that raises false negatives.

This is the balance principle at its sharpest: you cannot minimize both, so AML is a constant tuning exercise — sensitive enough to catch real crime (few false negatives) without generating so much noise that investigators can't function (too many false positives). The key engineering levers: **tune detection carefully**, use **risk-based prioritization** (score and rank alerts so investigators work the highest-risk first rather than a flat queue), and use ML to reduce false positives *without* sacrificing recall on real cases. Reducing false positives while holding detection is one of the highest-value problems in RegTech, precisely because investigator time is the binding constraint.

## The investigation workflow

Monitoring generates alerts, but a person decides what they mean — so AML is also a **case-management workflow** system:

- **Alert generation** — the monitoring system produces alerts with the supporting evidence (which transactions, which pattern, the customer context).
- **Triage and prioritization** — alerts are ranked by risk so the most serious get attention first (essential given the false-positive volume).
- **Investigation** — a trained investigator reviews the alert, the customer, and the activity, gathering context to decide: is this genuinely suspicious?
- **Disposition** — the investigator either clears the alert (false positive, documented) or escalates it, potentially leading to filing a **Suspicious Activity Report (SAR)** to authorities (the reporting post).
- **Everything recorded** — every alert, investigation, and decision is logged immutably, because you must prove to regulators that you monitored, investigated, and acted appropriately (auditability again).

Good AML engineering therefore builds not just the detection but the *investigator experience*: alerts rich with context, efficient case management, and complete audit trails. The system's effectiveness is limited by how efficiently investigators can work the alerts, so the tooling around the human matters as much as the detection itself. With monitoring watching behavior, the next post covers a related but distinct check — screening *who* the customer is against sanctions and watchlists.

## Key takeaways

- AML transaction monitoring continuously scans transactions and behavior for patterns suggesting money laundering, generating alerts for human investigation and potential reporting — a detection-and-triage pipeline over the transaction stream.
- It hunts for patterns like structuring, activity inconsistent with the customer's profile, rapid layering, and high-risk connections — much of it anomaly detection relative to each customer's normal baseline (which is why KYC profiles matter).
- Detection uses rules (explainable, encode known patterns, but rigid and noisy) and machine learning (catches subtle/novel patterns, better prioritization, but must be made explainable) — mature systems combine both, and explainability is non-negotiable for regulators.
- False positives dominate: real laundering is rare, so sensitive detection flags many legitimate transactions, overwhelming investigators — but false negatives (missed crime) are the dangerous, penalized failures, so AML is constant tuning of a balance you can't fully win.
- AML is also a case-management workflow (alert → triage/prioritize → investigate → disposition → immutable record), so the investigator experience and audit trail matter as much as the detection, since investigator time is the binding constraint.

## Further reading

- [KYC and identity verification (previous post)](/blog/posts/regtech-02-kyc-identity-verification.html)
- [Financial fraud detection with ML (Financial AI series)](/blog/series/the-fintech-engineering-handbook/)
- [AI Governance for Engineers — explainability of automated decisions](/blog/series/ai-governance-for-engineers/)
