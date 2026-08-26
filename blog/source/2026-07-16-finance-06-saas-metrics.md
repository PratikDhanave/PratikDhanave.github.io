# SaaS and Recurring-Revenue Metrics

*Subscription businesses changed what "revenue" means. When customers pay every month instead of once, a whole new vocabulary appears — MRR, ARR, churn, net revenue retention, the Rule of 40 — and these metrics, not the raw P&L, are how SaaS companies are actually judged. For any engineer working at or evaluating a subscription business (which is most software today), these are the numbers that matter, and the logic behind them explains why SaaS companies behave the way they do.*

Most modern software is sold by subscription (SaaS — software as a service), and recurring revenue has its own set of metrics that extend the unit-economics ideas. This post covers the **recurring-revenue model** and why it's valuable, the core metrics — **MRR/ARR**, **churn and retention**, **net revenue retention** — and the **Rule of 40**. These are the numbers SaaS companies live by, and understanding them explains a huge amount of how subscription businesses operate and are valued.

## Why recurring revenue is special

The subscription model — customers paying *repeatedly* (monthly/annually) rather than *once* — fundamentally changes a business's economics, which is why it gets its own metrics:

- **Predictable, compounding revenue.** Recurring revenue is *predictable*: existing subscribers keep paying, so you start each period with a base of known revenue and build on it. This predictability is enormously valuable — it makes planning, forecasting, and valuation more reliable than one-off sales, where you start each period at zero. It also *compounds*: new customers add to the retained base, so revenue can stack upward over time.
- **The value is in the relationship, not the sale.** In a one-off model, the sale is the end; in subscription, it's the *beginning* of a relationship that generates revenue as long as the customer stays. This shifts the whole business toward *keeping* customers (retention) rather than just *acquiring* them — because a customer's value (LTV, from the unit-economics post) depends on how long they stay. Retention becomes central.
- **It's why SaaS is valued highly.** Predictable, recurring, growing revenue with good retention is a valuable, durable business — which is why subscription businesses are often valued richly (on revenue multiples) compared to one-off-sale businesses. The model's economics justify the distinct metrics and the premium.

The recurring model reframes the business around a *retained, compounding base of revenue* and the *ongoing relationship* with customers — which is why it needs metrics that capture recurring revenue, retention, and their growth. Those metrics start with measuring the recurring revenue itself.

## MRR and ARR

The foundational SaaS metrics measure the *recurring* revenue itself:

- **MRR (Monthly Recurring Revenue)** — the total predictable revenue the company earns *per month* from subscriptions. It's the heartbeat metric of a SaaS business: the recurring monthly revenue base, tracked closely as it grows (or shrinks). **ARR (Annual Recurring Revenue)** is the annual equivalent (roughly MRR × 12) — the yearly recurring revenue run-rate. Companies use MRR (often for smaller/monthly) or ARR (often for larger/annual contracts) depending on their model.
- **It's about *recurring* revenue specifically.** MRR/ARR count the *predictable, recurring* subscription revenue — not one-off fees or variable usage that isn't recurring. This focus on the recurring base is the point: it's the reliable, compounding revenue that defines the business.
- **MRR changes tell a story.** MRR moves through several forces: *new* MRR (from new customers), *expansion* MRR (existing customers upgrading/paying more), *contraction* MRR (existing customers downgrading), and *churned* MRR (customers leaving). Decomposing MRR growth into these components reveals the health of the business — healthy growth from new + expansion, drained by contraction + churn. This decomposition is more informative than the net number alone, because it shows *where* growth comes from and leaks.

MRR/ARR is the base SaaS metric — the recurring revenue run-rate — and understanding its components (new, expansion, contraction, churn) is how you read the dynamics of a subscription business. But the single most important dynamic, the one that makes or breaks a SaaS business, is *retention* — whether customers stay.

## Churn and retention

**Churn** is the rate at which customers (or revenue) *leave* over a period; **retention** is the inverse (how many stay). Retention is arguably the most important thing in a subscription business:

- **Churn erodes the base.** Since SaaS depends on a retained, compounding base, churn is a leak in the bucket: every churned customer is lost recurring revenue *and* lost future LTV. High churn means you're constantly refilling a leaking bucket — acquiring new customers just to replace lost ones — which caps growth and wrecks unit economics (short customer lifetimes mean low LTV, from the unit-economics post). Low churn means customers accumulate, and growth compounds.
- **Retention drives LTV and thus the whole model.** A customer's lifetime value depends directly on how long they stay — so retention *is* LTV, and LTV vs CAC is the core of unit economics. Improving retention is often the highest-leverage thing a SaaS business can do: it raises LTV, improves unit economics, and lets growth compound. This is why subscription businesses obsess over reducing churn and keeping customers successful (connecting to the customer-success idea and, via the EQ/GTM series, to actually serving customers well).
- **Churn compounds against you.** Because it applies every period, even a "small" monthly churn rate compounds into large annual customer loss — so churn that sounds minor can be quietly fatal to growth. This compounding is why SaaS companies treat churn so seriously.

Churn/retention is the pivotal SaaS dynamic: it determines whether your revenue base leaks or compounds, drives LTV and unit economics, and is often the highest-leverage lever in the business. A SaaS company that can't retain customers can't build a durable base no matter how well it acquires — which leads to a metric that captures retention *and* expansion together.

## Net revenue retention and the Rule of 40

Two higher-level metrics capture SaaS health especially well:

- **Net Revenue Retention (NRR)** — measures how much revenue from *existing* customers grows or shrinks over a period, combining *expansion* (upgrades) against *contraction and churn*. NRR *above 100%* is a powerful signal: it means existing customers, as a group, are spending *more* over time (expansion outweighs churn) — so the company would grow *even with no new customers*. That's the hallmark of a strong SaaS business: the existing base compounds upward on its own. NRR *below 100%* means the base is shrinking (churn/contraction outweigh expansion) and must be refilled just to stay flat. NRR is one of the most-watched SaaS health metrics because it captures retention *and* expansion together.
- **The Rule of 40** — a rule of thumb for SaaS health balancing *growth* and *profitability*: a company's revenue *growth rate* plus its *profit margin* should be *at least 40%*. The idea is that growth and profitability trade off (you can grow fast while unprofitable, or grow slowly while profitable), and a healthy SaaS company should sum to ~40%+ across the two. It's a quick check that a company is either growing fast enough, profitable enough, or a healthy balance — capturing that early-stage SaaS can justify low/negative profit *if* growth is high, but the combination must clear the bar.

These metrics — NRR (does the existing base compound upward?) and the Rule of 40 (is the growth/profitability balance healthy?) — are how SaaS businesses are judged at a glance, extending the raw MRR/ARR and churn numbers into signals of durable health. NRR above 100% and clearing the Rule of 40 are the marks of a strong subscription business.

SaaS/recurring-revenue metrics extend unit economics for subscription businesses: the model is valuable because revenue is predictable and compounding, measured by MRR/ARR (the recurring base and its new/expansion/contraction/churn components); churn/retention is the pivotal dynamic (it drives LTV and whether the base leaks or compounds); and NRR (existing-base growth) and the Rule of 40 (growth + profitability ≥ 40%) capture overall health. These are the numbers modern software businesses live by. Next: budgeting and forecasting — planning the financial future.

## Key takeaways

- Recurring revenue (subscriptions) changes a business's economics: it's predictable and compounding (start each period with a retained base and build on it), shifts focus from the one-off sale to the ongoing customer *relationship* (retention), and is why SaaS is valued richly — justifying its own distinct metrics.
- MRR (Monthly Recurring Revenue) / ARR (annual, ≈ MRR × 12) measure the predictable recurring revenue base, and decomposing MRR change into new, expansion, contraction, and churned MRR reveals the business's health better than the net number — showing where growth comes from and leaks.
- Churn (customers/revenue leaving) vs retention is the pivotal SaaS dynamic: it erodes or compounds the base, directly drives LTV (retention *is* LTV) and unit economics, compounds against you every period (small churn → large annual loss), and is often the highest-leverage lever — a SaaS business that can't retain can't build a durable base.
- Net Revenue Retention (NRR) measures existing-customer revenue growth (expansion vs contraction/churn): above 100% means the existing base compounds upward on its own (would grow with zero new customers — the hallmark of a strong SaaS business), below 100% means it leaks and must be refilled to stay flat.
- The Rule of 40 (revenue growth rate + profit margin ≥ 40%) is a quick health check balancing growth and profitability — capturing that early SaaS can justify low/negative profit *if* growth is high, but the combination must clear the bar; NRR and the Rule of 40 are how SaaS health is judged at a glance.

## Further reading

- [Revenue (Wikipedia)](https://en.wikipedia.org/wiki/Revenue)
- [Customer lifetime value — retention drives LTV](https://en.wikipedia.org/wiki/Customer_lifetime_value)
- [Unit economics (previous post)](/blog/posts/finance-05-unit-economics.html)
