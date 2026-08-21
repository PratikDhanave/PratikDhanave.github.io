# Regulatory Reporting

*Every compliance control eventually produces something you must tell a regulator: a suspicious activity report, a transaction report, a periodic filing. Regulatory reporting is where your internal compliance data becomes an external, deadline-bound, precisely-formatted obligation — and it's an unglamorous data-engineering problem where accuracy and timeliness are legal requirements, not quality goals.*

The monitoring and screening controls detect things; the audit trail records them; **regulatory reporting** is where required information is formally submitted to authorities. Regulated businesses must file various reports — suspicious activity, large transactions, periodic summaries — accurately, in the required format, by hard deadlines. This post covers reporting as an engineering problem: the kinds of reports, why accuracy and timeliness are non-negotiable, and how to build reporting as a reliable, auditable pipeline rather than a manual scramble.

## What regulatory reporting is

Regulators require businesses to *report* certain information — it's not enough to detect suspicious activity internally; you must formally *tell the authorities* about it, and you must file routine reports whether or not anything is wrong. Reporting is thus the outward-facing end of compliance: the point where your internal data and decisions become submissions to a regulator, in *their* required format, by *their* deadlines. Common report types include:

- **Suspicious Activity Reports (SARs)** — filed when your AML monitoring and investigation (from the AML post) conclude that activity is suspicious. This connects reporting directly to the monitoring pipeline: an investigation's disposition may be "file a SAR."
- **Transaction reports** — reports of transactions meeting defined criteria (e.g. large cash transactions over a threshold), filed as a matter of course.
- **Periodic / regulatory returns** — regular submissions summarizing activity, positions, or compliance metrics that regulators require on a schedule.

Each has its own required content, format, and timing. The engineering job is to reliably produce accurate reports in the mandated form and submit them on time — every time.

## Accuracy and timeliness are legal requirements

The defining characteristic of reporting is that **accuracy and timeliness are not quality targets — they're legal obligations**, and failing either is itself a violation:

- **Timeliness** — reports have **hard deadlines** (a SAR within a specified window of detection, periodic returns by a set date). Missing a deadline is a compliance failure *independent* of whether the underlying activity was handled correctly — you can do everything else right and still be penalized for filing late. Deadlines are firm, so the reporting pipeline must reliably meet them.
- **Accuracy** — reports must be *correct and complete*. Inaccurate or incomplete filings are violations, can mislead regulators, and undermine trust. A report with wrong figures or missing required fields is a problem even if made in good faith.

This changes how you engineer reporting versus ordinary data exports: it must be **reliable** (deadlines met consistently, not usually), **correct** (validated against the required schema and rules before submission), and **complete** (nothing required omitted). "Mostly works" is not acceptable when "works late" or "works with errors" is a legal violation. This is why reporting, though unglamorous, deserves the same engineering rigor as any critical system.

## Reporting as a data pipeline

Engineered well, reporting is a **data pipeline** from your internal compliance systems to the regulator's required output:

```text
1. Gather      → pull the required data from internal systems (transactions,
                 investigations, customer records)
2. Transform   → shape it into the regulator's required format/schema
3. Validate    → check completeness and correctness against the report's rules
                 BEFORE submission (catch errors early)
4. Submit      → file through the required channel by the deadline
5. Confirm     → capture proof of submission (when, what, acknowledgment)
6. Record      → log the whole thing immutably (auditability)
```

- **Gather and transform** — reports draw on data across your compliance systems, reshaped into the *specific* structured format the regulator mandates (formats are prescribed, often rigid). This is data engineering: extract, map, format.
- **Validate before submitting** — a critical step: check the report is complete and correct *before* filing, because errors caught pre-submission are cheap while errors filed are violations. Build validation against the report's rules into the pipeline.
- **Submit and confirm** — file through the required channel and *capture confirmation* — proof of what was submitted and when, which matters for demonstrating timeliness.
- **Record immutably** — like every compliance action, log the report, its contents, and its submission in the audit trail (you must prove you filed, what, and on time).

Two engineering values dominate: **automation** (manual report assembly is slow, error-prone, and hard to do reliably by deadline at scale, so automate the pipeline) and **validation** (catch errors before they become filed violations). Reporting is a place where investing in a solid automated, validated pipeline directly reduces legal risk.

## Reporting closes the compliance loop

It's worth seeing how reporting ties the whole series together, because it's the point where the internal controls become externally accountable:

- **AML monitoring** detects suspicious activity → investigation → **SAR** filed via reporting.
- **Transaction thresholds** trigger → **transaction reports** filed.
- **The audit trail** provides the evidence that supports and documents reports.
- **Data privacy** governs how the personal data in reports is handled.

Reporting is the outward expression of everything the other controls do internally — the mechanism by which regulators actually receive the information the compliance system produces. A gap here (late filings, inaccurate reports) undermines otherwise-good compliance, because from the regulator's view, what you *report* is much of what they see. Conversely, reliable, accurate, timely reporting demonstrates a functioning compliance program.

The practical guidance: treat reporting as a **first-class engineered pipeline** — automated, validated, deadline-reliable, and fully audited — not a periodic manual chore. The manual approach fails exactly when it matters (at scale, under deadline), while a well-built reporting pipeline turns a legal obligation into a routine, dependable process. With reporting covered, the series' final post assembles all these controls into a coherent compliance platform.

## Key takeaways

- Regulatory reporting is the outward-facing end of compliance: formally submitting required information (Suspicious Activity Reports, transaction reports, periodic returns) to authorities in *their* required format by *their* deadlines — detecting internally isn't enough, you must report.
- Accuracy and timeliness are legal obligations, not quality targets: missing a deadline is a violation independent of handling the underlying activity correctly, and inaccurate/incomplete filings are violations too — so "mostly works" is unacceptable.
- Engineer reporting as a reliable data pipeline: gather data from internal systems → transform into the mandated format → validate completeness/correctness *before* submission → submit by deadline → capture confirmation → record immutably.
- Two values dominate: automation (manual assembly can't reliably meet deadlines accurately at scale) and pre-submission validation (errors caught before filing are cheap; errors filed are violations).
- Reporting closes the compliance loop — AML investigations produce SARs, thresholds produce transaction reports, the audit trail evidences them — so it's a first-class engineered pipeline (automated, validated, deadline-reliable, audited), not a manual chore.

## Further reading

- [Data privacy and protection (previous post)](/blog/posts/regtech-06-data-privacy.html)
- [FinCEN — BSA reporting requirements (SARs, CTRs)](https://www.fincen.gov/)
- [Observability Engineering — building reliable, monitored pipelines](/blog/series/observability-engineering/)
