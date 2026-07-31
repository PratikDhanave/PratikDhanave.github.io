# Representing Money
*The first decision in any financial system, and the one people get wrong most often: never store money in a floating-point number.*

Every payments system I have worked on has, at some point, shipped a bug that traces back to how it represented money. A total that is off by a paisa. A refund that doesn't reconcile. A currency conversion nobody can reproduce three months later during an audit. These are not exotic failures. They come from a handful of early decisions that feel trivial when you make them and become expensive once real balances flow through the system.

This post is about those decisions: the data type, the rounding, the currency, and the exchange rate. Get them right on day one and most of the hard problems downstream simply do not happen.

## Floats lie, and they lie quietly

Start with the classic. Open any language with IEEE-754 floating point and evaluate `0.1 + 0.2`. You get `0.30000000000000004`, not `0.3`. This is not a bug in the language. It is a consequence of storing base-10 fractions in base-2. Values like `0.1` have no exact binary representation, so the hardware stores the nearest approximation and the error surfaces the moment you do arithmetic.

For a physics simulation, a rounding error in the fifteenth decimal place is noise. For money, it is a discrepancy that accumulates across millions of transactions and eventually fails a reconciliation report. The danger is that floats are *usually* right. Your tests pass, the demo works, and then six weeks into production a ledger is off by a cent and you cannot explain why.

The rule is simple and absolute: money is never a float. Not for storage, not for arithmetic, not for the intermediate variable you swore you would fix later.

## Store integer minor units with an explicit scale

The reliable representation is an integer count of the smallest unit the currency deals in — paise for rupees, cents for dollars — together with the currency and the scale that tells you where the decimal point sits.

```
Money value object
+-------------------+-----------+-------+
| minor_units (int) | currency  | scale |
+-------------------+-----------+-------+
| 129950            | INR       | 2     |
+-------------------+-----------+-------+
        |               |          |
        |               |          +-- 10^-2 : two decimal places
        |               +------------- ISO 4217 code
        +----------------------------- exact integer, no rounding

  display amount  =  minor_units / 10^scale
  1299.50 INR    <-  129950 / 10^2

  stored:   129950   (an exact integer, safe to add and compare)
  shown:    "1,299.50"  (formatted only at the edge, for humans)
```

The integer is the source of truth. Formatting to `1,299.50` happens at the very edge of the system, when you render a screen or a statement — never in between. Everything internal — sums, comparisons, ledger entries — operates on integers, which are exact by definition.

Keep the scale explicit rather than assuming "two decimals everywhere." It is not true. Dinar-denominated currencies use three minor digits; some accounting contexts need four for unit prices. A `Money` that carries its own scale refuses to guess.

```go
type Money struct {
    Minor    int64  // amount in the smallest unit, e.g. paise
    Currency string // ISO 4217, e.g. "INR"
    Scale    int32  // decimal places, e.g. 2
}

// Add refuses to combine mismatched money; there is no meaningful
// answer to "100 INR + 5 USD" without an explicit conversion.
func (a Money) Add(b Money) (Money, error) {
    if a.Currency != b.Currency || a.Scale != b.Scale {
        return Money{}, fmt.Errorf("cannot add %s and %s", a.Currency, b.Currency)
    }
    return Money{a.Minor + b.Minor, a.Currency, a.Scale}, nil
}
```

If integers feel too low-level for your domain — heavy tax math, per-unit pricing — reach for a fixed-scale decimal type (`BigDecimal`, Python's `Decimal`, a decimal library in Go) instead. The principle is identical: an exact base-10 representation with a scale you control. What you must never do is fall back to `float64` because it was convenient.

## Rounding is a policy, not an afterthought

The moment you divide — interest, tax, splitting a bill — you produce fractions of a minor unit and must round. The default most languages give you is round-half-up, which is biased: over many operations it nudges totals systematically upward.

Financial systems prefer **round-half-even**, also called banker's rounding. Halfway cases round to the nearest even digit, so `2.5` becomes `2` and `3.5` becomes `4`. Across a large population of values the up-rounds and down-rounds cancel, and the aggregate stays unbiased. Pick your rounding mode deliberately and apply it consistently; a system that rounds half-up in one service and half-even in another will never reconcile cleanly.

## Splitting money without losing a cent

Rounding each part independently creates a subtler problem. Split `10.00` three ways and naive rounding gives you `3.33 + 3.33 + 3.33 = 9.99`. A cent has vanished. Do this on a payout run and the sum of the parts no longer equals the whole, which is exactly the kind of thing a ledger check will reject.

The fix is **allocation** using the largest-remainder method. Divide to get the base share and the remainder, hand everyone the floor, then distribute the leftover minor units one at a time to the parts with the largest fractional remainders until nothing is left.

```
Split 1000 paise (10.00) across 3 parts
  base share = 1000 / 3 = 333, remainder = 1

  part A: 333  +1 leftover  -> 334
  part B: 333               -> 333
  part C: 333               -> 333
                               ----
  sum                          1000   (exact, nothing lost)
```

The parts differ by at most one minor unit, and critically, they sum to the original amount. Every serious money library ships an allocate function for this reason. If yours does not, write one and test that the parts always re-sum to the input.

## Currency is part of the value, not a label

An amount without a currency is meaningless. `500` is not money; `500 INR` is. This is why `Currency` sits inside the `Money` type above and why `Add` returns an error on a mismatch. Adding `100 INR` to `5 USD` has no answer — the operation is a category error, and the type system should make it impossible rather than silently producing `105` of nothing.

Treat currency as a first-class field that travels with the amount everywhere: in memory, in the database, across the wire. A column of bare integers with the currency implied by "we only do rupees" is a landmine waiting for your first multi-currency feature.

## Exchange rates must be reproducible

When you do convert, the output is not just a number — it is a decision you must be able to defend later. A rate has a **direction** (INR per USD is not USD per INR), a **timestamp** (rates move by the second), and a **source** (which provider or desk quoted it). Store all three alongside the converted amount and the original.

The failure mode is storing only the result: a wallet shows `8,300 INR` and nobody can say how a `100 USD` deposit became that figure. Was the rate `83.00`? When? From whom? Persist the rate you actually applied and the resulting `Money`, so any conversion can be replayed and reconciled months later.

```
Deposit 100.00 USD, converted to INR
  original : 10000  USD  scale 2
  rate     : 83.15  (INR per USD)  @ 2026-07-25T09:12:04Z  src=fx-desk-a
  result   : 831500 INR  scale 2
  -> store original, rate, direction, timestamp, source, AND result
```

## Why it matters

None of this is advanced. It is a value object, a rounding mode, an allocation loop, and a habit of recording the rate you used. But money is the one domain where "close enough" is a defect, not a tolerance. The systems that stay auditable and reconcilable for years are the ones that made these four choices correctly in the first commit — because every layer above them inherits the exactness, or inherits the bug.
