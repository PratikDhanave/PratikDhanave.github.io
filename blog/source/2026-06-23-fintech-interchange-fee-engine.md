# Building a Deterministic Interchange Fee Engine

*Turn card transaction attributes into interchange, scheme, and markup lines that reconcile to the cent.*

Every card transaction a merchant runs carries a cost of acceptance, and most of that cost is interchange: the fee the acquirer pays the issuer, set by the card network in a published rate table. On top of interchange sit scheme assessments (the network's own cut) and the acquirer's markup. If you operate an acquiring or payment-facilitator platform, you have to reproduce these numbers exactly, per transaction, for thousands of merchants, and then defend them when a merchant's finance team asks why a coffee sale cost 12 cents more than they expected.

The naive version — a percentage times the amount — is wrong on day one. Real interchange depends on the merchant category, the card product, the region, whether the transaction qualified for a lower rate, and which version of the network's rate schedule was in effect on the transaction date. This post is about building a fee engine that treats all of that as data, computes deterministically, and stores enough detail that any line item can be explained months later.

## What actually drives a fee

Before writing any code, get precise about the inputs. An interchange rate is selected by a tuple of attributes, not a single field:

- **Merchant category code (MCC)** — a supermarket, a utility, and a jeweller sit in different interchange programs.
- **Card product** — regulated debit, unregulated debit, standard credit, and rewards/commercial credit each price differently.
- **Region pair** — domestic, intra-region, and inter-region rates diverge sharply.
- **Authorization characteristics** — was the card present, was the full magnetic-equivalent data captured, was the transaction cleared within the network's timing window? These decide whether the transaction *qualifies* for the best rate or *downgrades* to a more expensive one.

Qualification is the part teams underestimate. Networks define a preferred rate and a set of conditions to earn it; miss a condition and the transaction falls to a downgrade tier. Modeling that as an explicit rule set — rather than burying it in an `if` chain — is what makes the engine auditable.

```
 attributes           classify            price              record            bill
┌──────────┐  MCC   ┌──────────┐  tier  ┌──────────┐ lines ┌──────────┐ roll ┌──────────┐
│ txn:     │  BIN   │ qualify  │ ─────▶ │  price   │ ────▶ │ fee      │ ───▶ │ merchant │
│ MCC/BIN  │ ─────▶ │ downgrade│        │ IC+scheme│       │ record   │      │ statement│
│ region   │        │  rules   │        │ +markup  │       │ (per txn)│      │  rollup  │
│ auth data│        └──────────┘        └────┬─────┘       └──────────┘      └──────────┘
└──────────┘                                 ▲
                                        ┌────┴─────┐
                                        │ rate     │  effective-dated
                                        │ tables   │  by txn date
                                        └──────────┘
```

> **▸ [Open the interactive diagram](/blog/diagrams/fintech-interchange-fee-engine.html)** — pan, zoom, and trace every step (light/dark, self-contained).

## Rate tables are versioned data, not constants

The single most important design decision is that rates live in effective-dated tables, keyed by network, program, card product, region, and a validity window. Networks publish rate changes several times a year; a transaction from March must price against March's schedule even if you compute the fee in June after a mandate update.

That means every lookup takes the **transaction date**, never "today":

```python
def lookup_rate(rate_store, network, program, product, region, txn_date):
    row = rate_store.find(
        network=network, program=program, product=product, region=region,
        valid_from__lte=txn_date, valid_to__gte=txn_date,
    )
    if row is None:
        raise UnpricedTransaction(network, program, product, region, txn_date)
    return row  # e.g. Rate(pct=Decimal("0.0080"), fixed=Cents(10))
```

Two rules keep this honest. First, never delete a rate row — supersede it with a new version and a fresh validity window, so historical statements stay reproducible. Second, treat a missing rate as a hard error, not a fallback to zero. An unpriced transaction is an operational alert, because silently charging nothing erodes margin invisibly.

## The compute step: money math you can defend

The pricing function takes the qualified category plus the resolved rates and produces separate components. Keep them separate all the way through — merchants dispute the *breakdown*, so a single blended number is useless.

```python
def price(txn, category, ic_rate, scheme_rate, markup):
    ic     = ic_rate.pct * txn.amount + ic_rate.fixed
    scheme = scheme_rate.pct * txn.amount + scheme_rate.fixed
    mkup   = markup.pct * txn.amount + markup.fixed
    return FeeBreakdown(
        interchange=round_half_up(ic),
        scheme=round_half_up(scheme),
        markup=round_half_up(mkup),
        category=category,
        rate_version=ic_rate.version,
    )
```

Three engineering disciplines matter here. Use fixed-point decimals in the transaction currency's minor unit, never floats — a rounding drift of a hundredth of a cent, multiplied across millions of transactions, becomes a reconciliation break. Define one rounding convention (typically half-up on each component independently) and apply it identically everywhere. And stamp the `rate_version` onto the output, so when someone asks "why this number," the exact rate row that produced it is one join away.

## Make it a pure function, then wrap it

The core engine should be a pure function: given transaction attributes and a snapshot of rate tables, it returns a fee breakdown with no I/O, no clock, no randomness. Purity buys you two things — trivial unit testing against known network examples, and safe re-execution. Re-running the engine over last month's transactions with the same rate version must produce byte-identical results.

Wrap that pure core in a thin service layer that handles the messy parts:

- **Idempotency** — key each computed fee by transaction ID plus rate version, so replays and retries never double-post. If the same transaction arrives twice, you overwrite the same record rather than appending a second fee.
- **Late adjustments** — a chargeback reversal or a clearing correction produces a new fee event that references the original, rather than mutating the stored breakdown. The record is append-only; corrections are deltas.
- **Backfills** — when a network issues a retroactive rate correction, you re-run affected transactions against the new version and emit adjustment records for the difference, keeping the original intact for audit.

## From per-transaction records to a statement

The record stage writes one immutable fee document per transaction: the component amounts, the category, the rate version, and the input attributes that drove classification. That immutability is what lets you regenerate a statement identically a year later.

The billing rollup then aggregates these records over the merchant's statement period. Because every fee is already decomposed, the rollup is straightforward summation grouped by component and by interchange category — which is exactly the breakdown a merchant wants to see:

```
Statement — Merchant #4471 — August
  Interchange                     $ 3,812.40
  Scheme assessments              $   214.06
  Acquirer markup                 $   906.55
  ─────────────────────────────────────────
  by category
    Regulated debit  (1,204 txns) $   241.80
    Rewards credit   (  318 txns) $ 1,988.10
    Standard credit  (  902 txns) $ 1,582.50
```

Two properties make this trustworthy. The statement total must equal the sum of stored per-transaction fees to the cent — reconcile it as a build-time invariant, not a hope. And every displayed category rolls up from records that each name their rate version, so a merchant challenge resolves to a specific transaction, a specific rule, and a specific published rate.

## Testing and reconciliation

Interchange is one of the rare domains where authoritative test vectors exist: networks publish worked examples. Encode those as golden tests so a rate-table edit that breaks a known case fails immediately. Beyond that, run a daily reconciliation that re-prices a sample of settled transactions and compares against what the network actually billed the acquirer; a systematic gap points to a stale rate version or a qualification rule that drifted from the current mandate.

Build it this way and the fee engine stops being a black box. It becomes a deterministic function over versioned data, every output traceable to the inputs and the rule that produced it — which is exactly what you need the first time a merchant, an auditor, or a network dispute asks you to prove a number.
