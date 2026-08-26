# Metrics and Data

*How do you know if your product is actually working? Not "did we ship the feature" but "did it make the difference we hoped?" Answering that requires metrics — and product management lives in a productive tension here: data is essential for knowing whether you're succeeding, yet the most metric-obsessed teams often build worse products by optimizing the measurable at the expense of the meaningful. Using data well means measuring what matters, letting it inform judgment, and resisting the traps that catch data-driven teams.*

**Metrics and data** are how product managers *measure whether the product is working* — moving from opinion to evidence about success. This post covers why metrics matter, what to measure (the north-star idea and good vs vanity metrics), experimentation (A/B testing), and the crucial balance between data and judgment. It connects to the measurement themes across the blog (GTM metrics, data engineering) and is how PMs know if they're building the right thing well. Data informs product decisions — but doesn't replace judgment.

## Why metrics matter

Metrics matter because they let you *know* whether the product is succeeding — replacing opinion and assumption with *evidence*:

- **They answer "is it working?"** The fundamental question — *is the product succeeding?* (are customers getting value, is the business benefiting?) — is answered by *metrics*, not opinion. Without measurement, you're guessing whether you're succeeding. Metrics turn "is it working?" from a matter of opinion into a matter of evidence. Metrics answer whether you're winning. Evidence, not opinion.
- **They enable learning and improvement.** Metrics let you *learn* — measuring the effect of what you build (did it help? by how much?) so you can *improve* (do more of what works, less of what doesn't). This measurement-and-learning loop (measure, learn, adjust) is how products get better over time. Metrics power the improvement loop. Measure to learn, learn to improve.
- **They ground decisions in reality.** Data grounds product decisions in *reality* (what's actually happening with the product) rather than assumptions or the loudest opinion. Data-informed decisions (grounded in evidence) generally beat opinion-driven ones. Metrics ground decisions in reality. Reality over opinion.

Metrics matter because they answer "is the product working?" with evidence (not opinion), enable the learning-and-improvement loop (measure the effect, adjust), and ground decisions in reality. Data is essential to good product management. But *which* data — what to measure — is where it gets subtle.

## What to measure

*What* you measure matters enormously — and the key distinction is between metrics that reflect real value and *vanity metrics* that just look good:

- **Measure what reflects real value/success.** The metrics that matter reflect *real product success* — genuine customer value and business outcomes (engagement that indicates value, retention, revenue, the outcomes you care about). Measure what actually indicates the product is succeeding, not just what's easy to count. Measure real success, not just activity. What indicates value?
- **Beware vanity metrics.** *Vanity metrics* look impressive but don't reflect real success — raw signups, page views, downloads, total users — numbers that can rise without the product actually succeeding (users who don't return, signups who never engage). Vanity metrics *mislead* (feeling like progress without being it — the theme from the GTM series). Focus on metrics that connect to *real* value, not vanity numbers. Beware metrics that look good but mean little. Activity isn't success.
- **The north-star metric.** A useful concept is a *north-star metric* — a single key metric that best captures the *core value* the product delivers to customers. It focuses the team on the *one thing* that most reflects delivering real value (aligning everyone on what matters most). A good north-star metric (reflecting genuine customer value) orients the whole team. Find the metric that captures core value. One number that matters most.
- **Retention is often the truest signal.** Across products, *retention* (do customers keep using it / coming back?) is often the *truest* signal of real value — because people return to things that genuinely provide value (and abandon things that don't). Retention (from the finance/GTM series) frequently reveals real product-market fit better than acquisition/vanity numbers. Retention often reveals real value best. Do they come back?

What to measure matters most: measure metrics reflecting *real value and success* (not vanity metrics that look good but don't indicate real success), ideally anchored by a *north-star metric* (capturing core customer value), with *retention* often the truest signal of real value. Measuring the right things is the crux. Beyond passive measurement, PMs actively test with experiments.

## Experimentation and A/B testing

Beyond measuring, PMs *experiment* — testing changes to *learn* what works, chiefly via **A/B testing**:

- **A/B testing: compare variants with data.** *A/B testing* compares two (or more) variants — e.g. show version A to half of users, version B to the other half, and *measure* which performs better on the target metric. It's a *controlled experiment* that gives *evidence* about which change actually works, rather than guessing. A/B testing measures the real effect of a change. Test, don't guess. Let users' behavior decide.
- **It replaces opinion with evidence.** A/B testing's value is turning *"which is better?"* from an *opinion debate* into a *measured answer* — the data shows which variant performs better on the metric. It grounds product decisions in evidence (what actually works) rather than argument (what someone thinks will work). Experiments settle debates with data. Evidence ends the argument.
- **It enables safe, iterative learning.** Experiments let you *test changes safely* (on some users first) and *learn* before full rollout — reducing the risk of a bad change and building understanding of what works. It fits the measure-learn-iterate loop (test a change, measure, learn, decide). Experiments enable safe iterative improvement. Learn before committing.
- **Not everything can (or should) be A/B tested.** A caveat: not every decision suits A/B testing (some changes are too big, too slow to measure, or better decided by judgment; small teams may lack traffic for statistical significance). A/B testing is powerful for *measurable, incremental* changes but isn't the answer to everything (big strategic bets need judgment, not just experiments). Use experiments where they fit. A tool, not a universal answer.

Experimentation, chiefly A/B testing (comparing variants by measuring which performs better on the target metric), turns "which is better?" from opinion into evidence, enabling safe iterative learning — though not everything can or should be A/B tested (big bets need judgment). Experiments are a powerful data tool. But data has limits, which is the crucial balance.

## Data and judgment: the balance

The most important lesson about metrics is the *balance* — data should *inform* judgment, not *replace* it — because pure data-worship produces worse products:

- **Data informs, doesn't replace, judgment.** Data is *essential* but *not sufficient* — it *informs* decisions (evidence about what's happening/working) but doesn't *make* them. Product decisions still require *judgment* (interpreting data, weighing what it doesn't capture, making calls under uncertainty). Data-*informed* (judgment guided by data) beats both data-*ignoring* (opinion-only) and data-*worshipping* (data as the sole decider). Let data inform judgment, not replace it. Data guides; you decide.
- **Not everything important is measurable.** A key limit: *not everything that matters is measurable* (and not everything measurable matters). Important things (long-term value, brand, some customer experience, big strategic bets) resist easy measurement — so relying *only* on metrics *misses* them. Judgment must cover what data can't. Measure what you can, judge what you can't. Some value evades metrics.
- **The over-optimization trap.** A real danger: *optimizing metrics* can *harm the product* — chasing a metric (especially the wrong or narrow one) can degrade real value (e.g. optimizing engagement in ways that hurt users, or gaming a metric that stops reflecting reality — "when a measure becomes a target, it ceases to be a good measure"). Metric obsession can build *worse* products. Beware optimizing metrics at the expense of real value. The metric is a proxy, not the goal.
- **Data as one input, not the master.** The healthy stance: treat data as *one important input* to product decisions (alongside customer understanding, strategy, judgment) — not the *master* that dictates everything. The best PMs are *data-informed* (using data well) without being *data-enslaved* (blindly following metrics). Data serves judgment; it doesn't rule. Use data; don't be used by it.

The crucial balance is that data *informs* judgment rather than replacing it — because not everything important is measurable, chasing metrics can harm the real product (the over-optimization trap), and data is one input, not the master. The best PMs are data-informed without being data-enslaved. Metrics — measuring real value (not vanity), experimenting to learn, and balancing data with judgment — are how PMs know if the product works. Next: shipping and iterating — getting the product into the world and improving it.

## Key takeaways

- Metrics matter because they answer "is the product working?" with evidence (not opinion), enable the measure-learn-improve loop (measure the effect of what you build, then adjust), and ground decisions in reality — data is essential to good product management.
- *What* you measure is crucial: measure metrics reflecting *real value and success* (genuine engagement, retention, business outcomes), not vanity metrics (signups, page views, total users) that look impressive but can rise without real success — ideally anchored by a north-star metric (capturing core customer value), with *retention* often the truest signal of real value.
- Experimentation, chiefly A/B testing (compare variants by measuring which performs better on the target metric), turns "which is better?" from opinion into measured evidence and enables safe iterative learning — though not everything can or should be A/B tested (big strategic bets need judgment, small teams lack traffic).
- The crucial balance: data *informs* judgment, it doesn't *replace* it — product decisions still require judgment (interpreting data, weighing what it misses, deciding under uncertainty) — so data-informed beats both opinion-only and data-worship.
- Beware the limits and traps: not everything important is measurable (long-term value, strategy, some experience — judgment must cover these), and optimizing metrics can *harm* the real product ("when a measure becomes a target, it ceases to be a good measure") — treat data as one important input, not the master, being data-informed without being data-enslaved.

## Further reading

- [A/B testing (Wikipedia)](https://en.wikipedia.org/wiki/A/B_testing)
- [Working with engineering and design (previous post)](/blog/posts/pm-05-working-with-engineering-and-design.html)
- [Business Finance: SaaS metrics — retention and real value](/blog/posts/finance-06-saas-metrics.html)
