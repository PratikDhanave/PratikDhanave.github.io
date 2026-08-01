# Three-Way Reconciliation That Closes the Long Tail

*Building a matching engine across the internal ledger, the processor report, and the bank statement — with tolerances, break classification, aging, and auto-resolution rules for the items nobody wants to touch.*

---

## Why two sources are never enough

Most teams start with two-way reconciliation: compare what the internal ledger says against what the bank statement says, flag the differences. It works until it doesn't. The moment a payment processor sits between your ledger and the settling bank, a two-way match hides where a break was born. A missing item could mean the processor never captured the transaction, or it captured it but the funds never settled to the bank. Those are different incidents with different owners and different fixes, and a two-way diff collapses them into one undifferentiated pile.

Three-way reconciliation keeps all three sources as first-class inputs: the **internal ledger** (what you believe happened), the **processor report** (what the intermediary claims it did), and the **bank statement** (what actually moved money, usually as a `camt.053` or a fixed-width export). The engine's job is to line up the same economic event across all three and tell you precisely which leg disagrees. That specificity is the whole point — it turns a daily spreadsheet triage into a routed queue where most breaks never reach a human.

## The matching pipeline

The core is a funnel. Every source record is normalized into a common shape, grouped by a matching key, and then compared within the group. Records that agree across all three legs fall out as matched; the rest get classified and routed.

```
 internal ledger ─┐
                  │
 processor report ─┼──▶ normalize ──▶ group by key ──▶ compare legs ──┬──▶ matched (auto-clear)
                  │                                                    │
 bank statement ──┘                                                    ├──▶ amount break
                                                                       ├──▶ timing break
                                                                       ├──▶ missing leg
                                                                       └──▶ unknown
                                                                            │
                                                       auto-resolve rules ──┴──▶ exception queue
```

> **▸ [Open the interactive diagram](/blog/diagrams/fintech-reconciliation-break-detection.html)** — pan, zoom, and trace every step (light/dark, self-contained).


The unglamorous work lives in **normalize**. The three sources rarely share an identifier. Your ledger keys on an internal transaction UUID; the processor keys on its own transaction reference plus a batch ID; the bank statement gives you an end-to-end reference if you are lucky and a free-text remittance line if you are not. Before anything can be compared, each record has to be projected onto a canonical tuple — normalized amount in minor units, a settlement date, a currency, and one or more candidate join keys extracted from whatever reference fields exist.

```python
def canonical(record, source):
    return CanonKey(
        amount_minor=to_minor_units(record.amount, record.currency),
        currency=record.currency,
        value_date=record.settlement_date,
        join_keys=extract_references(record, source),  # ordered, most-specific first
    )
```

`join_keys` is deliberately a list, ordered from most to least specific. The matcher tries the strong key first (an end-to-end ID present in all three sources), then falls back to progressively weaker composite keys (amount + date + last-four of an account). Every fallback you allow trades precision for recall, so each weaker key should be earned by a real, observed gap in the strong identifier — not added speculatively.

## Tolerances, or why exact-match is a trap

Insisting on exact equality guarantees a flood of false breaks. Real settlement introduces legitimate, bounded differences that are not errors:

- **Amount tolerance.** Interchange or scheme fees deducted at settlement mean the bank credit is a few basis points below the gross ledger amount. Rounding on currency conversion adds sub-unit noise. A tolerance band — absolute floor plus a small relative percentage — absorbs this without hiding a genuine shortfall.
- **Timing tolerance.** The ledger books at authorization time; the processor reports at capture; the bank settles a day or two later across a weekend or holiday. Two records describing the same event can carry value dates that differ by a bounded window.

The key discipline is that a tolerance is not the same as ignoring a difference. A match inside tolerance still records the residual — the exact fee or the exact day-lag — so those residuals can themselves be reconciled later against the fee schedule. Silent absorption is how a slowly widening fee error goes unnoticed for a quarter.

## Classifying the break

Once a group fails to cleanly match, classification decides everything downstream: who is paged, what timer starts, and whether a rule can close it without a human. A minimal, useful taxonomy:

| Class | Signal | Typical cause |
|---|---|---|
| **Amount break** | Same key, amounts differ beyond tolerance | Unexpected fee, partial settlement, FX slippage |
| **Timing break** | Same key and amount, value dates outside window | Weekend/holiday lag, cutoff crossing |
| **Missing leg** | Present in one or two sources, absent in another | Dropped capture, unsettled item, unbooked ledger entry |
| **Unknown** | No confident key match at all | Bad reference data, duplicate, misrouted item |

Classification should be *deterministic and explainable*. Each break carries the evidence that produced its class — the three raw records, the key that did (or did not) match, and the computed residual. When an analyst opens a break, they should not have to reverse-engineer why the engine thought it was a timing break; the engine already wrote down its reasoning.

## Aging and the auto-resolution long tail

The single most important behavioral property is that **breaks age**. A timing break at T+0 is not an incident — it is the expected state of a payment mid-flight. The same break still open at T+5 is a real problem. So every break gets a timer, and the queue is sorted by age against a per-class SLA rather than by creation time. This alone removes most of the noise: the engine holds young timing breaks quietly, expecting them to self-resolve on the next statement, and only surfaces them if they overstay.

That self-resolution is the long tail's economics. A large fraction of breaks close themselves on a subsequent run once the lagging leg arrives — the bank statement two days later carries the settlement that was missing on day one. An auto-resolution rule is just a guarded assertion: *if a timing break of this shape is now fully matched on a later cycle, close it and post nothing; if an amount break's residual exactly equals the published fee for this transaction class, reclassify it as a fee and post the fee entry instead of alerting.*

```python
def auto_resolve(break_, later_records, fee_schedule):
    if break_.klass == "timing" and now_matches(break_, later_records):
        return Resolution.CLOSE_NO_OP
    if break_.klass == "amount":
        expected = fee_schedule.lookup(break_.txn_class)
        if abs(break_.residual - expected) <= FEE_EPSILON:
            return Resolution.POST_FEE
    return Resolution.ESCALATE  # into the human exception queue
```

The rules should be conservative by construction: when in doubt, escalate. An auto-resolution engine that guesses wrong silently corrupts the books; one that escalates a resolvable item merely costs an analyst a few minutes. The asymmetry of those failures should be baked into every threshold.

## Idempotency and the audit trail

Reconciliation runs repeatedly over overlapping windows, so it must be safe to re-run. A break is identified by a stable content hash of its constituent records and class, not by a fresh row on every execution. Re-processing the same statement must converge on the same break set, update ages, and apply auto-resolutions — never duplicate them. Equally, every resolution, automatic or manual, appends an immutable record: what closed the break, which rule or user, and the exact residual posted. When an auditor asks why a fee entry appeared with no invoice, the reconciliation log is the answer.

Get these two properties right — deterministic classification and idempotent, audited resolution — and the engine stops being a daily fire drill. The vast majority of breaks route themselves; humans see only the genuinely ambiguous long tail, which is exactly where their judgment is worth paying for.
