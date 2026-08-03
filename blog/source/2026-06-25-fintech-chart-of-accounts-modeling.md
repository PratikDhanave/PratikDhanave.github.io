# Chart of Accounts and Sub-Ledger Modeling

*Designing an account hierarchy, dimensions, and posting rules that turn product events into balanced journal entries.*

---

Most engineers meet the general ledger late, usually when finance asks why the balance sheet does not tie out to the product database. The gap is almost never a bug in the code that moves money. It is a missing translation layer: no one decided, ahead of time, which accounts a "payout succeeded" event should debit and credit. A chart of accounts (CoA) and a sub-ledger model are that translation layer. Get them right and every product event lands as a balanced journal entry that rolls up cleanly into financial statements. Get them wrong and you spend quarter-end reverse-engineering journals from raw transaction logs.

This post is about the modeling decisions, not the accounting theory. I will assume you already know that assets and expenses carry debit balances, liabilities, equity, and revenue carry credit balances, and that every entry must balance.

## Two tiers: sub-ledgers feed a thin general ledger

The mistake I see most is treating the GL as the system of record for individual transactions. It is not. The GL should hold *summarized* balances per account per period. The detail lives in **sub-ledgers** — one per business domain (payments, lending, fees, FX) — where each economic event becomes a fully dimensioned journal entry. The GL is a rollup of those entries.

```
 Product event         Posting rule        Sub-ledger journal        General ledger        Statements
 ------------          -----------         ------------------        --------------        ----------
 payout.succeeded  ->  match rule set  ->  DR 2100 payable    -.
 fee.charged           by event type       CR 1010 cash bank    \                          Balance Sheet
 loan.disbursed        + dimensions        (dimensioned lines)   >- summarize per   ->     Income Stmt
 refund.issued         + currency          ...                  /   account+period         Cash Flow
                                           balanced batch      -'
```

> **▸ [Open the interactive diagram](/blog/diagrams/fintech-chart-of-accounts-modeling.html)** — pan, zoom, and trace every step (light/dark, self-contained).

Keeping the GL thin has three engineering payoffs. Summarization queries stay fast because the GL table has thousands of rows, not billions. The sub-ledger can carry rich dimensions the GL does not need. And you can rebuild GL balances by re-summarizing sub-ledger journals, which makes the GL a derived, reproducible artifact rather than a fragile source of truth.

## Model the account code as segments, not a string

The single highest-leverage decision is refusing to model an account as an opaque string like `"cash_usd_uk"`. Instead, model a **segmented account code**: a natural account plus a set of orthogonal dimensions.

```
segment          example        purpose
-------          -------        -------
natural account  1010           what kind of thing (cash, payable, revenue)
entity           UK-LTD         which legal entity
currency         USD            denomination
product          lending        business line
cost center      ops-emea       responsibility for P&L
counterparty     bank-xyz       optional sub-analysis
```

The natural account answers "what," and everything else answers "which slice." A journal line references one natural account and a tuple of dimension values. This lets finance ask for cash by entity, by currency, or by product without you creating a Cartesian explosion of hand-named accounts. The account *hierarchy* — 1000 Assets → 1010 Cash → 1011 Operating Cash — lives only on the natural-account segment, so a chart with a few hundred natural accounts and a handful of dimensions expresses millions of reportable balances.

Two rules keep this clean. Natural accounts are a controlled list owned by finance; engineers never invent them at runtime. Dimensions are validated against reference data at posting time, so a journal with `entity = TYPO` is rejected before it hits the ledger rather than surfacing as an unreconciled balance a month later.

## Posting rules map events to balanced entries

A **posting rule** is a pure function from a product event to a set of balanced journal lines. Centralizing these rules — rather than scattering `INSERT INTO ledger` calls across services — is what makes the ledger auditable. Every service emits domain events; one posting engine owns the translation.

```python
def post_payout_succeeded(evt) -> JournalEntry:
    dims = {"entity": evt.entity, "currency": evt.currency,
            "product": evt.product}
    lines = [
        Line(account="2100", side="DR", amount=evt.amount, dims=dims),  # settle payable
        Line(account="1010", side="CR", amount=evt.amount, dims=dims),  # cash out of bank
    ]
    assert sum_signed(lines) == 0, "entry must balance"
    return JournalEntry(event_id=evt.id, lines=lines,
                        effective_date=evt.value_date)
```

Three properties matter. The balance assertion is enforced in code, not hoped for. The `event_id` makes posting **idempotent** — replaying the same event must not double-post, so the engine upserts on `event_id`. And the `effective_date` (value date) is separate from wall-clock time, because a payout that settles on the 1st but is recorded on the 3rd belongs in the earlier period. Posting rules should be versioned: when finance changes how a fee books, you add a new rule version rather than mutating history.

## Contra accounts express reductions without losing gross

Finance frequently needs both a gross figure and its reduction visible side by side — gross revenue and the refunds netted against it, or a loan's principal and its loss-allowance. A **contra account** is a natural account that carries the opposite normal balance to its parent and rolls up beneath it. Refunds post to a contra-revenue account (a debit against a credit-balance revenue line) rather than reversing the original sale. On the income statement the two net to revenue-net-of-refunds, but both numbers survive for analysis. Model contras explicitly in the hierarchy — as children of their parent with an `is_contra` flag — so the rollup engine knows to subtract rather than add.

## Summarization and the statement rollup

Producing statements is a two-stage rollup. First, summarize sub-ledger journal lines into GL balances by `(natural_account, dimensions, period)` — a straightforward grouped sum of signed amounts, run incrementally as journals arrive or as a period-close batch. Second, walk the account hierarchy: sum leaf balances into their parents, applying contra signs, until you reach the statement lines (total assets, net revenue, operating expense).

```
1011 Operating Cash    +2,400,000  -.
1012 Reserve Cash         +600,000   >-> 1010 Cash  +3,000,000 -.
                                                                  >-> 1000 Assets ...
4010 Subscription Rev  -5,000,000  -.                            -'
4090 Refunds (contra)    +120,000    >-> 4000 Revenue -4,880,000  -> Income Statement
```

Because balances are derived from immutable, dimensioned journals, statements are reproducible: rerun the rollup for any past period and you get the same numbers. That reproducibility is the real prize. When finance asks why net revenue moved, you drill from the statement line down the hierarchy to the natural account, filter by dimension, and land on the exact journal entries and the events that produced them — no archaeology required.

Design the chart of accounts and the dimension model first, encode posting rules as versioned pure functions, keep the GL thin and derived, and the ledger stops being the thing that surprises you at close and becomes the thing you trust.
