# Building an FX Rate, Spread & Markup Engine

*How to ingest many rate feeds, derive a trustworthy mid, defend against stale prices, and quote a locked customer rate that survives a settlement failure.*

---

When a product surfaces "convert 500 USD to EUR at 0.9142," a lot of engineering hides behind that one number. The rate came from several upstream feeds, was reduced to a single mid, had a spread and a segment-specific markup applied, and was frozen behind a time-to-live so the customer sees the same number at confirmation that they saw at quote. Every one of those steps can leak money or ship a wrong price. This post walks the pipeline an FX pricing service actually runs, and the failure modes each stage exists to contain.

## The pipeline at a glance

The engine is a linear dataflow with one important guard rail in the middle. Raw feeds are noisy and occasionally wrong, so nothing downstream trusts a single source. Feeds are normalized to a canonical currency-pair convention, reduced to a mid, checked for staleness, then priced per customer segment.

```
  feeds        normalize        risk           pricing         output
 ┌──────┐     ┌─────────┐    ┌──────────┐   ┌──────────┐   ┌──────────┐
 │ Bank │────▶│ canon   │───▶│ staleness│──▶│ spread + │──▶│ quote    │
 │ ECN  │────▶│ pair +  │    │ circuit  │   │ markup   │   │ w/ lock  │
 │ Aggr │────▶│ mid calc│    │ breaker  │   │ (segment)│   │ TTL      │
 └──────┘     └─────────┘    └────┬─────┘   └──────────┘   └────┬─────┘
                                  │ trip                        │ accept
                                  ▼                             ▼
                             ┌──────────┐                  ┌──────────┐
                             │ fallback │                  │ booked   │
                             │ / reject │                  │ conversion│
                             └──────────┘                  └──────────┘
```

> **▸ [Open the interactive diagram](/blog/diagrams/fintech-fx-rate-markup-engine.html)** — pan, zoom, and trace every step (light/dark, self-contained).

The key architectural decision is that the *mid* and the *price* are separate concerns. Mid derivation is a market-data problem: it wants the freshest, most liquid, most agreed-upon number. Pricing is a commercial problem: it applies spread and margin that depend on who is asking and how much. Keeping them in different stages lets you change margin policy without touching the market-data path, and audit a bad quote by asking two independent questions: "was the mid right?" and "was the markup right?"

## Ingesting and normalizing feeds

Feeds disagree on almost everything except the price itself. One publishes `EURUSD`, another `EUR/USD`, another quotes the inverse. One sends bid/ask, another sends a single indicative rate. Timestamps arrive in different zones and precisions. Normalization collapses all of this to a canonical record before any math happens.

```
feed record ──▶ { pair: "EUR/USD" (base/quote, ISO 4217),
                  bid, ask, source, ts_utc, seq }
```

Two rules keep this stage honest. First, always store the pair in one canonical direction and derive the inverse on demand — never persist both, or they will drift. Second, carry the source and a monotonically increasing sequence number on every tick, because when you later debug a bad quote you will need to know exactly which tick from which feed produced it. Ingestion is also where you reject the obviously broken: a bid above the ask, a zero, a rate that moved 20% in one tick. These never reach mid calculation.

## Deriving a defensible mid

With several normalized feeds for the same pair, the mid is a reduction, not a copy. A naive `(bid + ask) / 2` from a single feed is fragile: that feed can lag, widen, or glitch. A more robust mid takes the median of the per-feed mids, which throws out a single outlier feed for free, and optionally weights by feed liquidity or recency.

```
feeds → per-feed mid = (bid+ask)/2
      → drop feeds older than max_age
      → mid = median(remaining mids)
      → spread_ref = tightest ask − tightest bid
```

Median over mean matters here. If three feeds say 0.9140, 0.9141, 0.9139 and a fourth glitches to 0.8800, the mean is dragged to 0.888 while the median stays at 0.9140. You still record the tightest observed bid/ask as a reference spread — it tells the pricing stage how liquid the pair is right now, which feeds directly into how wide a customer spread you can justify.

## Staleness and the circuit breaker

This is the guard rail. Markets gap, feeds go dark, and a weekend or a holiday can leave you pricing off a rate that is minutes or hours old. Quoting confidently off a dead feed is how you hand out free money. Every mid therefore carries the age of its youngest contributing tick, and the risk stage trips a circuit breaker when that age crosses a threshold or when too few feeds remain.

```
if fresh_feeds < min_sources        → TRIP
if youngest_tick_age > max_age      → TRIP
if mid deviates > k% from last good → TRIP

TRIP → serve last-known-good (flagged) OR reject quoting for pair
```

A tripped breaker has two honest responses, and you choose per product. A conversion flow that must stay up can serve the last-known-good mid but flag the quote as degraded and, usually, widen the spread to compensate for the uncertainty. A flow where a wrong price is worse than no price simply refuses to quote the pair until fresh ticks resume. What you must never do is silently serve the stale number as if it were live. Like any circuit breaker, it needs a half-open recovery: once fresh ticks return and agree with the last good mid within tolerance, it closes automatically rather than waiting for a human.

## Spread, markup, and the segment model

Only after a mid survives the risk gate does commercial pricing apply. Two adjustments stack on the mid: a **spread** that covers your own execution risk and market volatility, and a **markup** that is your margin. Both are policy, and both usually vary by customer segment, pair liquidity, and trade size.

```
mid = 0.91405
spread (bps by pair liquidity) = 8 bps  → 0.00073
markup (bps by segment/tier)   = 25 bps → 0.00229

customer sell rate = mid − spread − markup   (you buy their USD)
customer buy  rate = mid + spread + markup   (you sell them EUR)
```

Expressing spread and markup in basis points rather than absolute pips keeps the model sane across pairs with wildly different price magnitudes. A retail segment might carry 25 bps of markup while an enterprise tier negotiated 5 bps; a thin exotic pair carries a wider spread than a major. The engine resolves these from a rules table keyed by `(segment, pair, size_band)` and returns not just the final rate but the decomposition, so a statement or a support agent can explain exactly why the customer got 0.9142 and not the mid of 0.91405. Never collapse mid, spread, and markup into one opaque number before you have logged the parts.

## Rate locks: quoting a promise

A quote is a promise for a bounded window. The customer sees 0.9142, thinks, and clicks confirm eight seconds later — they must get 0.9142, not whatever the market did in the meantime. The engine mints a quote with a short TTL, typically seconds to a couple of minutes, and holds the exact decomposed rate against a quote ID.

```
POST /quote  → { quote_id, pair, rate, mid, spread, markup,
                 expires_at, source_seq }

POST /convert { quote_id }
   ts <= expires_at  → book at locked rate, mark quote consumed
   ts >  expires_at  → 409 expired, client re-quotes
```

Two properties make this safe. The quote is **immutable and single-use**: once consumed it cannot be replayed to book a second conversion, which closes an idempotency and abuse hole. And it captures the `source_seq` of the ticks it was priced from, so a disputed conversion can be reconstructed against the exact market state behind the promise. A booked conversion hands off to the ledger and the actual FX position, but everything the ledger records traces back to a quote whose every input was captured. The engine's job is done the moment that lock is honored or allowed to expire; it should never book against an expired quote to "be helpful."

## Wrapping up

An FX pricing service earns its keep by separating three concerns that are tempting to merge: deriving a trustworthy mid from disagreeing feeds, refusing to quote off stale data, and applying transparent, decomposable margin. Keep the mid and the markup independently auditable, make the circuit breaker a first-class state rather than an afterthought, and treat every quote as an immutable, expiring promise. Get those right and the single number the customer sees becomes something you can always explain — and always defend.
