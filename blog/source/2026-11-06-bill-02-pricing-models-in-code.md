# Pricing Models in Code — The Catalog Is Data, Not Constants

*Every pricing page looks simple: three tiers, a slider, maybe "contact us." The code behind a pricing page that can evolve is anything but — because pricing changes faster than software, old customers keep old deals, and the moment a price lives as a constant in application code, every experiment becomes a deploy and every grandfathered customer becomes an if-statement. The foundational move of billing engineering is modeling the catalog as versioned data.*

Post [1](/blog/posts/bill-01-why-billing-is-an-engineering-problem.html) framed billing as a system; this post builds its first subsystem — the pricing catalog — and the modeling discipline that keeps five years of pricing history coexisting without a single hardcoded price.

## The model zoo, and what each demands of the system

Pricing models form a small taxonomy, and each adds a requirement to the machinery downstream:

- **Flat rate** — one price for the product. Demands almost nothing; survives nowhere, because customers vary by orders of magnitude in the value they take.
- **Per-seat** — price × quantity of users. Adds *quantity tracking* and mid-period change handling (post 4's proration).
- **Tiered** — price depends on which bracket the quantity falls in, with the critical distinction between *graduated* tiers (each bracket priced like tax brackets: first 100 at X, next 900 at Y) and *volume* tiers (the final bracket's rate applies to everything). Teams confuse these constantly, and the difference is real money at every boundary.
- **Usage-based** — price × measured consumption. Adds the entire metering subsystem (post 3), plus period aggregation and estimation UX ("what will my bill be?").
- **Hybrids** — the practical norm: a platform fee plus usage, seats plus overage, committed-use minimums with drawdown, credits that expire. Hybrids are where naive models die, because they compose two models' edge cases.

The engineering insight: these aren't seven features — they're one abstraction. A **price** is a function from (quantity or usage, over a period) to an amount, described by data: a model type, brackets, unit amounts, a billing period, a currency. Get that abstraction right and tiered-usage-with-platform-fee is configuration; get it wrong and every sales experiment is a sprint.

## Versioning: the rule that makes everything else possible

Prices change; agreements persist. The customer who signed at $49 keeps $49 after the list price moves to $59 — perhaps forever, perhaps until renewal. This forces the catalog's cardinal rule: **price versions are immutable; changes create new versions**. A subscription references the *specific version* it was sold under, not "the current price of plan X." The payoffs compound: grandfathering becomes the default behavior instead of special-case code; an invoice can always be re-derived because the version it referenced still exists, unchanged; finance can answer "who is on what terms?" with a query; and pricing experiments (post 1's drift problem) become version rollouts with measurable cohorts rather than constant-edits with archaeology.

The corollary rule: **application code never contains an amount**. Code asks the catalog; the catalog answers from versioned data. The moment a `PRICE_PRO = 4900` constant appears, a second source of truth exists, and drift begins.

## The edges that find you

A few catalog realities arrive later and hurt more if unmodeled from the start. **Currency is not presentation** — multi-currency pricing is per-currency price points (a € price set deliberately, not a $ price converted daily), which means the catalog's key includes currency. **Custom deals are catalog entries too** — enterprise negotiations produce bespoke terms; resist the side-letter spreadsheet and model them as (possibly single-customer) price versions, or post 8's reconciliation becomes fiction. **Credits and minimums are first-class objects** — committed-use contracts, promotional credits, and free allowances interact with every model above and deserve explicit modeling, not invoice-time adjustments. And **the catalog needs an audit trail** — who changed what price when is a question finance, sales, and occasionally lawyers will ask; immutable versions give it for free.

The takeaway: pricing is a small taxonomy — flat, per-seat, tiered (graduated vs volume — not the same thing), usage-based, and the hybrid norm — unified by one abstraction: a price is versioned *data* mapping quantity-over-a-period to an amount. The cardinal rules: versions are immutable and subscriptions pin the version they were sold under (grandfathering, re-derivable invoices, and experiments fall out for free), and application code never holds an amount. Model currency, custom deals, and credits as catalog citizens from the start — they're cheaper as design than as archaeology.

## Key takeaways

- The model taxonomy — flat, per-seat, **graduated vs volume tiers** (chronically confused, materially different), usage, hybrids — is one abstraction: price = data describing (quantity/usage, period) → amount.
- **Immutable price versions** are the load-bearing rule: subscriptions pin their version, making grandfathering default behavior, invoices re-derivable, and pricing changes measurable rollouts.
- **No amounts in application code** — the first hardcoded price creates the second source of truth, and drift follows.
- Model the inevitable edges early: per-currency price points (not conversion), custom enterprise deals as catalog entries, credits/minimums as first-class objects, and an audit trail (immutability provides it).

## Further reading

- [Pricing — the commercial discipline being encoded](https://en.wikipedia.org/wiki/Pricing)
- [Price discrimination — why one product carries many prices](https://en.wikipedia.org/wiki/Price_discrimination)
