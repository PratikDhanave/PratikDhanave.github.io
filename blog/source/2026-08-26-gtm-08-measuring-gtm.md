# Measuring Go-to-Market

*Without measurement, GTM is guessing — you can't tell a channel that works from one that flatters you, a healthy business from one quietly bleeding, or whether your last change helped. But GTM measurement has a trap engineers fall into from the opposite side: drowning in dashboards of vanity metrics that feel rigorous while missing the two or three numbers that actually decide whether the business works. This closing post is about measuring what matters — and the unit economics that separate a real business from an expensive way to lose money.*

You've built a GTM strategy across market, positioning, motion, pricing, channels, and adoption. How do you know if it's *working*? This final post covers measuring GTM: the **funnel metrics** that show where you're winning and losing, the **unit economics** (especially CAC and LTV) that determine viability, key **retention/growth** metrics, and how to use metrics to iterate. Measurement is what turns GTM from guesswork into a system you can improve.

## Why measure, and the vanity-metric trap

Measurement serves two purposes: knowing whether GTM is working, and knowing *what to fix*. Without it, you can't distinguish a channel that produces customers from one that produces noise, or tell if a change helped. But there's a pervasive trap:

- **Vanity metrics feel good and mislead.** Metrics like total sign-ups, page views, social followers, or downloads *look* like progress but don't necessarily connect to a healthy business. A product can have huge sign-ups and no revenue, lots of traffic and no customers. Vanity metrics reward activity, not outcomes.
- **Measure what connects to the business.** The metrics that matter tie to actual customer acquisition, revenue, retention, and profitability. Ask of any metric: does moving this actually move the business? If a metric can go up while the business doesn't improve, it's probably vanity.
- **Few metrics, deeply understood, beat many.** The goal isn't a dashboard of hundreds of numbers but a handful of *decision-driving* metrics you genuinely understand. For GTM, the core few are funnel conversion, CAC, LTV, and retention — understood well and acted on.

The discipline is to measure the *few things that reflect real business health* and resist the comfort of vanity metrics. With that framing, the two most important families are funnel metrics (where you win and lose customers) and unit economics (whether each customer is profitable).

## Funnel metrics: where you win and lose

The funnel (awareness → interest → consideration → conversion, from the channels post) is measurable at each stage, and its metrics show *where* customers flow and drop off:

- **Conversion rates between stages.** What fraction move from one stage to the next — visitor→signup, signup→active, trial→paid, lead→customer. These reveal *where* the funnel leaks: a stage with a sharp drop-off is where you're losing people and where improvement has the most leverage. Funnel conversion turns "we're not getting enough customers" into "we lose people at *this specific* step."
- **Volume at each stage.** How many people are at each stage — showing whether the problem is too few entering the top (an awareness/demand problem) or too many dropping off lower down (a conversion problem). This tells you *what kind* of problem you have.
- **Where to focus.** The funnel shows the highest-leverage fix: if the top is narrow, focus on demand/channels; if a mid-stage leaks badly, focus on that step (messaging, product experience, sales process). Measuring the funnel directs effort to where it matters most, rather than improving everything blindly.

Funnel metrics diagnose the *health of the acquisition process* — where customers come from and where you lose them — making GTM debuggable. But acquiring customers isn't enough if it costs more than they're worth, which is where unit economics come in.

## Unit economics: CAC and LTV

The metrics that determine whether a GTM is *viable* — a real business versus an expensive way to lose money — are the **unit economics**, centered on two numbers:

- **CAC (Customer Acquisition Cost)** — the average cost to acquire one customer: total sales-and-marketing spend divided by customers acquired. It captures what your GTM *costs* per customer — ads, sales salaries, marketing, all of it.
- **LTV (Customer Lifetime Value)** — the total profit (or margin) a customer generates over their entire relationship with you, before they churn. It captures what a customer is *worth*.

The relationship between them is the heart of GTM viability:

- **LTV must exceed CAC — by a healthy margin.** If it costs more to acquire a customer than that customer is ever worth (CAC > LTV), you lose money on every customer and the business doesn't work, no matter how fast you grow (growing faster just loses money faster). A healthy business has LTV *comfortably* greater than CAC — a common rule of thumb is LTV several times CAC, to cover overhead and leave profit.
- **It bounds everything.** CAC/LTV is the constraint referenced throughout this series: how much you can spend on channels and demand gen, whether a sales-led motion's cost is justified, whether pricing supports your acquisition costs. All of it comes down to acquiring customers for meaningfully less than they're worth.
- **Payback period matters too.** How long it takes a customer's revenue to *recoup* their CAC (the payback period) affects cash flow — even a good LTV/CAC ratio strains cash if payback takes too long. Faster payback is healthier.

Unit economics are the ultimate GTM scorecard: a GTM strategy *works*, in the end, only if it acquires customers for less than they're worth (LTV > CAC, with a healthy ratio and reasonable payback). Everything else — clever positioning, great channels — is in service of this. If the unit economics don't work, the GTM doesn't, however good it looks.

## Retention, growth, and iterating

A few more metrics complete the picture, especially for recurring-revenue (subscription/SaaS) businesses, followed by how to use it all:

- **Retention and churn.** *Churn* is the rate at which customers leave; *retention* is the inverse. Retention is foundational because it drives LTV (customers who stay longer are worth more) and because acquiring customers who quickly churn is wasted spend. High churn quietly destroys a business — you fill the top of the funnel while the bottom leaks out. Retention is often where the highest-leverage improvement lies, because it compounds into LTV, word-of-mouth, and growth efficiency.
- **Recurring-revenue metrics.** For subscription businesses: MRR/ARR (monthly/annual recurring revenue) track revenue; net revenue retention (whether existing customers' spending grows or shrinks over time, via expansion vs churn) is a key health signal — customers *expanding* their spend is a sign of strong fit. (The business-finance series covers these metrics in depth.)
- **Use metrics to iterate.** The point of measurement is *action*: find the weakest link (a leaky funnel stage, a channel with bad CAC, high churn), improve it, measure again — GTM as a continuous improvement loop. Metrics turn GTM from a one-time plan into an empirical, iterated system.
- **Match metrics to stage.** Early on, the goal is finding product-market fit and learning (qualitative signal, early retention) more than optimizing CAC at scale; later, efficient, measured growth. Don't over-optimize metrics before you have fit, and don't scale un-measured after you do.

Measuring GTM means tracking the *few* metrics that reflect real business health — funnel conversion (where you win and lose customers), unit economics (CAC vs LTV, the viability test), and retention/churn (which drives LTV and durable growth) — while resisting vanity metrics, and using them to iterate toward a GTM that acquires customers for less than they're worth. That completes the series: from knowing your market, through positioning, motion, pricing, channels, and adoption, to measuring and improving the whole system. Go-to-market, done well, is what turns a good product into a real business.

## Key takeaways

- Measure the few metrics that reflect real business health and resist vanity metrics (sign-ups, page views, followers) that reward activity without connecting to revenue/retention/profitability — ask of any metric whether moving it actually moves the business; a handful of well-understood decision-driving metrics beats a huge dashboard.
- Funnel metrics — conversion rates between stages and volume at each stage — diagnose *where* you win and lose customers, revealing whether you have a top-of-funnel demand problem or a lower-funnel conversion problem, and directing effort to the highest-leverage leak.
- Unit economics are the viability test: CAC (cost to acquire a customer) must be comfortably less than LTV (lifetime value/profit of a customer) — if CAC > LTV you lose money on every customer and growth only loses money faster; LTV/CAC (often targeted at several-x) plus payback period bound everything you can spend on GTM.
- Retention/churn is foundational because it drives LTV (customers who stay are worth more) and because acquiring quick-churning customers is wasted spend — high churn quietly destroys a business, so retention is often the highest-leverage improvement; recurring-revenue metrics (MRR/ARR, net revenue retention) track subscription health.
- The purpose of measurement is iteration: find the weakest link (leaky funnel stage, bad-CAC channel, high churn), fix it, and remeasure — GTM as a continuous empirical loop — matching metric focus to stage (find product-market fit first, then scale measured growth), so the GTM ends up acquiring customers for less than they're worth.

## Further reading

- [Customer acquisition cost (Wikipedia)](https://en.wikipedia.org/wiki/Customer_acquisition_cost)
- [Customer lifetime value (Wikipedia)](https://en.wikipedia.org/wiki/Customer_lifetime_value)
- [Launch and adoption (previous post)](/blog/posts/gtm-07-launch-and-adoption.html)
