# Engineering a Basel RWA Calculation Engine

*How to turn a book of exposures into risk-weighted assets and a capital ratio with a deterministic, auditable pipeline*

A bank's regulatory capital requirement is not a single number someone types into a spreadsheet. It is the output of a computation that starts from every loan, guarantee, and undrawn commitment on the books and ends with a ratio that a supervisor will inspect line by line. That computation is the risk-weighted asset (RWA) engine, and under the Basel standardized approach it is far more of a data-engineering problem than a quantitative-finance one. The pipeline below is the shape most implementations converge on.

```
  Exposures ──▶ Classify ──▶ Weight ──▶ Aggregate ──▶ Capital Ratio
     │                          ▲
     └──▶ CCF Convert ──────────┘
          (off-balance EAD)
```

> **▸ [Open the interactive diagram](/blog/diagrams/fintech-basel-rwa-engine.html)** — pan, zoom, and trace every step (light/dark, self-contained).

The core identity is simple:

```
capital ratio = eligible capital / total RWA

total RWA = sum over exposures of ( EAD * risk_weight )

where  EAD = on-balance amount
            + off-balance amount * credit_conversion_factor
```

Everything hard about the engine lives in getting `EAD` and `risk_weight` right for millions of heterogeneous positions, and in being able to prove, months later, exactly how a given number was produced.

## Start with an exposure, not a loan

The first modeling mistake is to run the engine over your product tables directly. A term loan, a revolving credit line, a letter of guarantee, and a repo all live in different systems with different schemas, but the RWA engine only cares about a normalized *exposure* record. Introduce that boundary explicitly.

An exposure needs, at minimum: a counterparty identifier and its type, the on-balance carrying amount, any off-balance (undrawn or contingent) amount, currency, residual maturity, collateral references, and an external rating where one applies. Producing this record from source systems is an ETL concern you want isolated, because it is where most reconciliation breaks originate. If your engine consumes a clean exposure feed, the calculation stages downstream become pure functions of that feed — which is exactly what makes the whole thing testable and replayable.

Keep the exposure immutable for a given reporting date. The engine should never mutate an exposure in place; it snapshots the book as of the cutoff and treats that snapshot as the sole input. This is what lets you re-run last quarter's numbers bit-for-bit when an auditor asks.

## Classification decides everything downstream

Classification maps each exposure into a regulatory asset class — sovereign, bank, corporate, retail, residential mortgage, commercial real estate, past-due, and so on. The asset class, combined with attributes like rating and loan-to-value, is what selects the risk weight. Get classification wrong and every downstream number is wrong in a way that is expensive to unwind.

Model classification as an ordered ruleset, not a giant switch statement. Rules are evaluated in priority order, and the first match wins. This mirrors how the regulation itself reads (specific carve-outs override general categories) and it gives you a natural place to attach an audit trail: record *which* rule fired for each exposure.

```python
def classify(exposure, rules):
    for rule in rules:  # ordered, most-specific first
        if rule.matches(exposure):
            return Classification(
                asset_class=rule.asset_class,
                rule_id=rule.id,          # audit hook
                bucket=rule.bucket,       # e.g. LTV band
            )
    raise Unclassified(exposure.id)       # never silently default
```

The `raise` on the last line matters. An unclassifiable exposure is a data-quality incident, not a zero-weight freebie. Silent defaulting to a low weight is the kind of bug that understates capital and ends careers.

## Off-balance items and the credit conversion factor

On-balance exposures already sit at their exposure-at-default: the money is out the door. Off-balance items — undrawn commitments, guarantees, trade finance — represent potential future exposure, so you cannot weight the notional directly. The credit conversion factor (CCF) scales the off-balance amount into an EAD-equivalent before weighting.

A revocable commitment might carry a 10% CCF, an unconditionally cancellable line a 0% CCF, a direct credit substitute 100%. The CCF depends on the instrument type and its terms, so this is its own classification-and-lookup step running in parallel to the on-balance path. The two paths converge at the weighting stage, both delivering a clean EAD number.

Separating the CCF path in the pipeline is not just diagram tidiness. It means the off-balance logic — which has its own regulatory nuances and its own reconciliation against commitment systems — can be tested and versioned independently from the on-balance flow.

## Risk-weight lookup must be a versioned table

Under the standardized approach, the risk weight is a lookup: given asset class, rating band, and any modifiers, return a percentage. Do not bury these percentages in code. They change with regulation, they differ by jurisdiction, and you must be able to state which version of the table produced a historical number.

Model the table as data with an effective-date and a version identifier:

```
asset_class   rating_band   modifier      risk_weight   version
corporate     AAA..AA-      —             20%           2026Q1
corporate     A+..A-        —             50%           2026Q1
corporate     unrated       —             100%          2026Q1
mortgage      —             LTV<=60%      35%           2026Q1
past_due      —             —             150%          2026Q1
```

Every RWA figure the engine emits should carry the table version it used. When a supervisor asks why the corporate weight was 50% and not 100% for a given date, the answer is a row lookup, not an archaeology project.

The weighting stage then becomes trivial and side-effect-free: `rwa_contribution = ead * weight_lookup(classification, version)`. Purity here is the whole point — it is what makes per-exposure results reproducible and unit-testable against known regulatory examples.

## Aggregation, capital, and reproducibility

Aggregation sums the per-exposure contributions into total RWA, usually with intermediate rollups by asset class and business line because supervisors want the breakdown, not just the grand total. Aggregation should be associative and order-independent so you can shard the calculation across workers and still get an identical answer — floating-point drift in a regulatory number is not acceptable, so many engines carry amounts as integer minor units and only present as decimals.

Divide eligible capital by total RWA and you have the CET1 and Tier 1 ratios that headline the regulatory report. But the ratio is the easy part; the value of the engine is everything that lets you *defend* it:

- **Replayability.** Same exposure snapshot plus same rule and table versions must yield byte-identical output. Pin all three and store them together.
- **Lineage.** Each RWA contribution should trace back to its exposure, the classification rule that fired, the CCF applied, and the weight-table row used.
- **No silent defaults.** Unclassified exposures, missing ratings, and stale data must surface as explicit exceptions that block sign-off, never as convenient low weights.
- **Attribution deltas.** When the ratio moves quarter over quarter, you need to decompose the change into new exposures, reclassifications, and rule or table updates.

Build the RWA engine as a chain of pure stages over an immutable exposure snapshot, keep the regulatory parameters in versioned tables rather than code, and make every number trace back to the rule and row that produced it. Do that and the quarterly capital calculation stops being a fire drill and becomes what it should be: a deterministic function you can run, audit, and trust.
