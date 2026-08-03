# LCR and NSFR: Engineering Liquidity Regulatory Reporting

*How the two Basel liquidity ratios are computed from raw positions, and why the hard part is a data pipeline, not a formula.*

Every internationally active bank files two liquidity ratios that a regulator can read in a single line each. The **Liquidity Coverage Ratio (LCR)** asks whether the bank holds enough cash-like assets to survive a thirty-day funding panic. The **Net Stable Funding Ratio (NSFR)** asks whether the bank's longer-term assets are matched by funding that will still be there in a year. Both are simple fractions. Producing them correctly, on time, and defensibly is where the engineering lives.

## The two formulas, plainly

LCR is high-quality liquid assets divided by net cash outflows over a thirty-day stress window:

```
LCR = HQLA / net cash outflows (30-day stress)   >= 100%
```

HQLA is not "cash on the balance sheet." It is a tiered stock of assets that stay liquid under stress, each tier discounted by a **haircut**:

- **Level 1** (central bank reserves, high-grade sovereign bonds): 0% haircut, no cap.
- **Level 2A** (certain agency and covered bonds): 15% haircut.
- **Level 2B** (some corporate bonds, qualifying equities): 25%-50% haircut, and the whole Level 2 stock is capped at 40% of HQLA.

Net cash outflows are gross expected outflows minus capped inflows over the same window. Outflows come from applying **run-off factors** to liabilities: a stable retail deposit might run off at 5%, a less stable one at 10%, and unsecured wholesale funding at 100%. Inflows (from performing loans maturing inside the window) are recognized but capped at 75% of outflows, so the bank can never look liquid purely on paper receivables.

NSFR is a one-year structural ratio:

```
NSFR = available stable funding (ASF) / required stable funding (RSF)   >= 100%
```

ASF weights each funding source by how "sticky" it is: capital and long-term debt count at 100%, stable retail deposits around 90-95%, short-term wholesale funding much less. RSF weights each asset by how much stable funding it needs: cash needs ~0%, a mortgage a large fraction, an illiquid or encumbered asset close to 100%.

The pattern is identical for both ratios: **classify each position into a regulatory bucket, multiply by a factor, and sum.** That symmetry is what lets one pipeline produce both returns.

## It is a data pipeline, not a spreadsheet

The instinct is to write two formulas. The reality is that a bank has millions of positions across dozens of source systems, each needing to be mapped to exactly one Basel bucket, weighted by a factor that changes as regulation changes, and reconciled back to the general ledger before anyone signs the return.

```
   Sources          Classify         Aggregate          Return         Sign-off
 +-----------+
 | Position  |\
 | Ledger    | \                   +------------+     +-----------+
 | (GL bal.) |  \                  | LCR Agg    |---->| LCR       |\
 +-----------+   \   +----------+  | apply      |     | Return    | \
                  -->| Classifier|->| haircuts  |     | HQLA/     |  \  +-----------+
 +-----------+   /   | bucket + |  +------------+     | outflows  |   ->|  Recon +  |
 | Factor    |  /    | weight   |  +------------+     +-----------+     |  Sign-off |
 | Tables    | /     +----------+->| NSFR Agg   |---->| NSFR      |   ->|  tie to   |
 | (config)  |/          |         | apply      |     | Return    |  /  |  balance  |
 +-----------+           |         | factors    |     | ASF/RSF   | /   |  sheet    |
                         |         +------------+     +-----------+/    +-----------+
                    versioned                                          blocks unbalanced
                    factor set                                              filings
```

> **▸ [Open the interactive diagram](/blog/diagrams/fintech-lcr-nsfr-liquidity-reporting.html)** — Positions and versioned factor tables flow through a shared classifier into two weighted-aggregation lanes, producing the LCR and NSFR returns that reconcile against the balance sheet.

Reading left to right: raw positions and the factor tables both feed a **classifier**, which tags every position with its regulatory bucket and applicable weight. The tagged stream fans into two aggregation lanes, one per ratio. Each lane applies its haircuts or factors and sums the results into a return. Both returns then converge on a reconciliation and sign-off gate.

## Classification is the real work

A position does not arrive labelled "Level 2A" or "available stable funding." Classification is a rules engine that reads dozens of attributes — instrument type, issuer, credit rating, currency, encumbrance status, counterparty type, residual maturity, deposit insurance flag — and resolves each to a single bucket.

Two engineering rules keep this sane. First, **every position must classify to exactly one bucket**; an unclassified position is a bug, not a rounding error, and the pipeline should fail loudly rather than silently drop it. Second, **classification must be explainable**: for any position the system should emit which rule fired and why. When a regulator questions a number, "the engine decided" is not an answer; "instrument X matched rule 47 because rating >= AA- and residual maturity < 30 days" is.

Encumbrance deserves special care. An asset pledged as collateral cannot count toward HQLA and carries a heavier RSF weight. That status lives in a different system from the position itself, so classification is inherently a join across sources, and a stale join quietly overstates liquidity.

## Factors and haircuts are versioned configuration

The single most important design decision is to treat the factor and haircut tables as **versioned data, not code**. Run-off rates, haircuts, ASF and RSF weights, and inflow caps are all set by regulation and are revised over time and across jurisdictions. Hard-coding `0.85` for a Level 2A haircut buries a regulatory parameter inside a program where no reviewer will ever find it.

Instead, keep every factor in a table with an effective date and a version tag. A reporting run pins one version; the version identifier is stamped onto the output return. This buys three things: you can reproduce any historical filing exactly by replaying its factor version; you can diff two versions to see precisely what a regulatory change moved; and a jurisdiction-specific override is a data change, not a release. When the classifier and both aggregators read from the same versioned table, one release re-prices LCR and NSFR together and cannot drift apart.

## Reconciliation is the gate, not an afterthought

A liquidity return that does not reconcile to the balance sheet is worthless, because the regulator will tie it out and the discrepancy becomes your problem. So the pipeline's final stage sums classified exposures back up and compares the total against the general ledger. If HQLA-eligible securities in the return do not equal the corresponding GL balances net of known adjustments, the run **fails** and no one signs it.

Reconciliation is where the abstract pipeline meets accounting reality: intraday timing, in-flight trades, and positions that legitimately net differently for liquidity than for accounting all create explainable breaks. The engineering goal is not zero breaks but **zero unexplained breaks** — each difference carries a documented reason, and anything else halts the filing.

## What good looks like

A liquidity reporting system that survives audit tends to share the same properties. Classification is deterministic and explainable, with every position resolving to one bucket. Factors live in versioned tables, and the version is recorded on the output. The same classified dataset drives both ratios, so LCR and NSFR can never silently disagree about what a position is. And reconciliation to the balance sheet is a hard gate rather than a report someone reads later. Get those four right and the ratios themselves are almost an afterthought — two divisions at the very end of a long, careful pipeline.
