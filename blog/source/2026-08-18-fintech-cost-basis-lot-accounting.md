# Cost-Basis and Lot Accounting: FIFO, LIFO, and Spec-ID
*Why tax lots, not positions, are the real unit of a brokerage ledger — and how to make disposal deterministic.*

A retail investor sees a single line: "500 shares of ACME, up 12%." The tax engine behind that line sees something else entirely — a stack of *tax lots*, each with its own quantity, cost basis, and acquisition date. When the investor sells 200 shares, the system has to answer a deceptively hard question: *which 200?* The answer changes the reported gain, the holding period, and ultimately the tax bill. Getting it wrong is not a rounding error; it is a filing error.

This post walks through the engineering of a lot ledger: how lots are created on buys, how they are selected on sells, how realized and unrealized gain are computed, and how the two ugly edge cases — wash sales and corporate actions — bend the rules.

## The lot is the atom

A *position* (net shares held) is a convenient display aggregate. It is the wrong primitive for accounting because it throws away the two facts the tax code cares about: **when** each share was acquired and **at what cost**. So the ledger's atom is the lot:

```
Lot { id, symbol, qty_open, basis_per_unit, acquired_at, method_hint?, status }
```

Every buy creates exactly one new lot. Basis is not just the trade price — it includes commissions and fees, allocated per unit. A buy of 100 shares at 40.00 with a 5.00 commission produces a lot with `basis_per_unit = 40.05`, not 40.00. Fold fees in at lot creation and the downstream gain math stays clean.

The single most important property of a lot store is that lots are **append-only and immutable**. You never mutate `qty_open` in place and forget the original; you record a disposal event that *references* the lot and decrements a derived open quantity. This is what makes the whole system auditable and, crucially, **replayable** — you can reconstruct the state of every lot as of any date by folding the event log up to that timestamp.

## Disposal: the four methods

When a sell arrives, the engine consumes open lots until the sold quantity is satisfied. The *disposal method* is the policy that orders the candidate lots. Four are common:

- **FIFO** (first-in, first-out): consume the oldest lots first. The default for most brokers and for equities under IRS rules absent other instruction.
- **LIFO** (last-in, first-out): consume the newest lots first. Often defers gains in a rising market.
- **HIFO** (highest-in, first-out): consume the highest-basis lots first, minimizing realized gain per sale. Popular for crypto, where per-unit specific identification is permitted.
- **Specific identification (Spec-ID)**: the client names the exact lots to sell. This is the most flexible and, from an engineering standpoint, the one that turns lot selection from a *policy* into an *input*.

The engineering rule that matters more than any single method: **lot selection must be deterministic.** Given the same lot ledger and the same sell, the selector must produce the same lot allocation every time. That means the sort key needs a tiebreaker. FIFO by `acquired_at` alone is ambiguous when two lots share a timestamp; append lot `id` as a secondary key so ordering is total. Without it, a report re-run can silently reassign basis and change the answer.

```
DISPOSAL SORT KEYS (ascending consume order)
  FIFO   -> (acquired_at, lot_id)
  LIFO   -> (-acquired_at, lot_id)
  HIFO   -> (-basis_per_unit, acquired_at, lot_id)
  SpecID -> caller-supplied [lot_id, ...]  (validated against open lots)
```

A sell for 250 shares against lots of 100, 100, and 100 consumes the first two whole and *splits* the third: 50 shares disposed, 50 left open. The split is where partial-lot bookkeeping lives — the disposed slice carries its share of basis, the remainder keeps the original `basis_per_unit`.

## Realized versus unrealized

Two numbers, one subtraction, but they answer different questions.

**Realized gain/loss** is booked at disposal: `proceeds − matched_basis`, computed per consumed lot slice and summed. Proceeds are net of sale-side fees. Because each slice carries its own `acquired_at`, the engine also stamps the holding period — short-term (≤ 1 year) or long-term — which drives the tax rate. A single sell can produce both, if it consumes an old lot and a new one together.

**Unrealized gain/loss** is not an event at all; it is a *read* over the currently open lots at a market mark: `Σ (mark − basis_per_unit) × qty_open`. It moves every time the price moves and is never written to the ledger. Keep it out of the event log entirely — deriving it on demand avoids a whole class of staleness bugs.

## The workflow

The happy path is a straight line from acquisition to report; the wash-sale rule is the one branch that reaches back and rewrites basis.

```
 Trade Events   Buy Trade ─────────────────────▶ Sell Trade
                    │  (qty+price+fees)               │  (qty to close)
                    ▼                                 ▼
 Lot Ledger      Open Lot ══════════════════▶  Select Lots
                 (immutable basis)          (FIFO/LIFO/HIFO/Spec-ID)
                                                      │
                                                      ▼
 Tax Engine                             Realized G/L ─────▶ Tax Report
                                        (proceeds−basis)   (Form 8949)
                                                │  ▲
                                    loss+rebuy  ▼  │ deferred loss
 Wash-Sale Adj.                        [ Wash-Sale: disallow, 30-day ]
```

> **▸ [Open the interactive diagram](/blog/diagrams/fintech-cost-basis-lot-accounting.html)** — buy opens a lot, a sell selects lots by method and realizes gain, and a disallowed loss defers into replacement-lot basis before the report.

## Wash sales: the rule that rewrites history

The wash-sale rule (a U.S. equities rule; crypto is currently outside it, though that is a moving target) says: if you sell at a loss and buy a "substantially identical" security within **30 days before or after** the sale, the loss is **disallowed**. It does not vanish — it is *deferred* by adding the disallowed amount to the basis of the replacement lot, and the replacement lot's holding period absorbs the original's.

Engineering this correctly means the loss disposal cannot be treated as final at the moment of sale. You need a ±30-day window scan against buys of the same symbol, matched share-for-share. When a match is found:

1. Disallow the loss on the sold slice (it does not reduce realized gain).
2. Add the disallowed loss to the replacement lot's `basis_per_unit`.
3. Carry the original acquisition date forward onto that replacement basis.

Because the window extends *forward* 30 days, a report can be provisional: a buy next week can retroactively disallow a loss you booked today. Systems handle this by keeping realized events amendable until the window closes, and by re-running the wash-sale pass before finalizing a tax year. This is exactly why immutability plus replay matters — you re-fold the log with the wash-sale adjustment applied, rather than trying to patch a mutated position in place.

## Corporate actions and transfers

Lots do not only change through trades. A **stock split** multiplies `qty_open` and divides `basis_per_unit` by the same ratio, preserving total basis and the original acquisition date. A **spinoff** allocates a fraction of the parent lot's basis to newly issued lots. A **transfer in** from another custodian should arrive with basis and acquisition date intact; when it does not (a "non-covered" transfer), the lot is flagged and its gain may have to be reported as basis-unknown. Model each of these as an event that produces new lots or restates existing ones — never as a silent field edit — so the audit trail survives.

## Producing the report

The realized-gains report (Form 8949 in the U.S.) is a projection over disposal events: one row per consumed lot slice, with acquired date, sold date, proceeds, basis, wash-sale adjustment, and gain, grouped into short- and long-term buckets. Because everything upstream is deterministic and replayable, the report is reproducible — the same ledger and the same method always yield the same rows. That reproducibility, not the arithmetic, is the hard part worth engineering for.
