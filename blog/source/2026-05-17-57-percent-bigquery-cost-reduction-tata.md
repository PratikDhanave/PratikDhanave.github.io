# How I Cut a Fortune 500 BigQuery Bill by 57%

*Architecture decisions that delivered multi-million dollar savings at petabyte scale.*

---

I helped redesign a large BigQuery-based enterprise data warehouse and cut spend by 57%. The biggest savings didn't come from dashboards or one-off query tuning. They came from architecture decisions — partitioning, clustering, incremental MERGE patterns, and a better capacity model.

Here's how I approach cost as an architectural problem in large systems.

## The Problem

I joined as the Solution Architect for a Fortune 500 financial company running BigQuery at scale — hundreds of analysts, dozens of automated pipelines, 4+ TB of daily ingestion across finance, risk, and regulatory reporting workloads.

The platform had grown organically. Datasets were added without architectural standards. Queries ran without cost awareness. The pricing model was never revisited as workloads matured. Leadership was asking "how much are we spending?" We needed to answer a different question: "why does our architecture force us to spend this much?"

In BigQuery, cost scales with data scanned — so table design and query patterns directly determine spend. One unoptimized query scanning 10 TB hourly — without caching or partition pruning — burns through a massive annual budget. We had dozens of patterns like this across hundreds of queries.

The cost drivers fell into four areas: compute (unoptimized queries and MERGE operations), storage (no partitioning, clustering, or lifecycle policies), governance (no cost attribution or alerting), and capacity (on-demand pricing for predictable workloads).

## What We Found

The first four weeks were pure analysis. No changes. Using BigQuery's INFORMATION_SCHEMA and Jobs logs — no third-party tools — we profiled every query by cost, frequency, and scan volume, mapped every dataset by partitioning state and access patterns, traced pipelines end-to-end to understand what would break, and modeled 90 days of workload behavior for capacity planning.

Across hundreds of pipelines, a small number of recurring architectural patterns dominated total spend.

The single largest: what we internally called the **MERGE anti-pattern** — MERGE operations doing full-table read + write on every execution, even when only a fraction of rows had changed. This one pattern accounted for more waste than any other issue we found.

We explicitly avoided query-level tuning as a primary strategy. At this scale, tuning individual queries reduces cost — but redesigning the architecture that generates those queries changes the cost curve. That decision shaped everything that followed.

## Five Architecture Decisions

Every decision was constrained by zero-downtime requirements — hundreds of downstream pipelines, regulatory reporting jobs, and cross-team dependencies all depended on these tables. Nothing could break.

Zero-downtime wasn't a constraint — it was the primary design input.

**Partitioning:** Ingestion-date partitioning on high-traffic tables, over business-key partitioning. We traded optimal query performance for migration safety — accepting slightly higher scan costs on edge-case query patterns to avoid breaking production pipelines.

**Clustering:** High-cardinality filter columns, over composite clustering. 80% of the benefit for 20% of the complexity. We accepted the remaining gap for operational simplicity.

**The MERGE anti-pattern — the biggest win.** The underlying pattern: treating BigQuery like a traditional RDBMS. Every MERGE operation was reading and rewriting the entire target table on every run. We shifted from full-table DML to idempotent, partition-scoped operations — joining only against affected shards using staging tables with predicate filters. Write amplification dropped ~90%. One architectural pattern change eliminated the platform's largest cost driver.

**Capacity model:** Hybrid — 70/30 split between committed slots for predictable workloads and on-demand burst for peaks. We traded slightly higher peak cost for 40% lower total cost and predictable billing. Finance could finally forecast cloud spend annually — that alone changed the stakeholder conversation from reactive to strategic.

**Monitoring:** Real-time cost attribution with automated multi-tier alerting, replacing the monthly bill-review cycle. It required instrumentation effort upfront, but it shifted governance from reactive to proactive — and gave every team visibility into their own cost footprint for the first time.

## Results

These were structural changes, not temporary fixes. The savings persist because the architecture prevents regression.

- **57% reduction** in data warehouse spend
- Significant realised annual savings at multi-petabyte scale with thousands of daily queries
- **3–5x performance improvement** on the highest-cost query patterns
- Top pipelines reduced from ~10 TB scans per run to under 500 GB — a **95% reduction** through partition pruning and clustering

The engagement evolved from a tactical intervention into a strategic FinOps roadmap. The client established a permanent Architecture Review Board to vet all future high-scale pipelines.

The approach was repeatable: diagnostic → cost driver isolation → architecture intervention → governance. We've since applied the same model across multiple enterprise environments.

## What I'd Do Differently: The Trust Gap

I underestimated how long it takes to get stakeholder buy-in without real-time proof. For nine weeks, leadership was trusting my word that the architecture changes were working — I couldn't show them live cost-attribution data until the monitoring layer went live in Phase 3. That was a risk I shouldn't have taken.

If I reran this, I'd deploy cost instrumentation in Week 1, alongside the first architecture changes. Not because dashboards solve cost problems — they don't. But because architects need to show their work in real-time, or the next budget review becomes a trust exercise instead of a data conversation. I'd also implement Cost-as-Code — CI/CD gates that reject queries exceeding a scan threshold — so cost governance becomes automated rather than advisory.

## The Takeaway

At scale, cloud cost is an architectural outcome — not a reporting problem. Monitoring explains spend. Architecture determines it.
