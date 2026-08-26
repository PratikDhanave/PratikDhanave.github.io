# Data Pipelines and ETL/ELT

*The core artifact of data engineering is the pipeline: an automated flow that pulls data from somewhere, reshapes it, and lands it somewhere useful. And the single most consequential shift in modern data engineering is captured in three reordered letters — ETL became ELT — a change driven by cheap, powerful cloud data warehouses that flipped when and where transformation happens. Understanding pipelines, and the ETL-to-ELT shift, is understanding how data actually moves and gets made usable.*

**Data pipelines** are the automated flows that move and transform data — the core building block of data engineering. This post covers what pipelines are, the classic **ETL** (Extract, Transform, Load) pattern, the modern shift to **ELT** (Extract, Load, Transform) and why it happened, and pipeline **orchestration**. It builds on the data lifecycle from the previous post: pipelines are how data flows through ingestion, transformation, and loading. Getting pipelines right is much of what data engineering is.

## What a data pipeline is

A **data pipeline** is an automated process that moves data from source(s) to destination(s), transforming it along the way — the fundamental unit of data engineering work. Its essence:

- **It moves and transforms data automatically.** A pipeline *extracts* data from sources, *processes/transforms* it (cleaning, reshaping, combining), and *loads* it to a destination (a warehouse, another system) — automatically and repeatedly. It's the automated flow that gets data from where it's produced to where it's used, made usable in transit. Pipelines are what actually implement the data lifecycle.
- **It's repeatable and scheduled.** Pipelines *run repeatedly* — on a schedule (e.g. nightly) or triggered by events/new data — keeping the destination data up to date as new source data arrives. This automation and repetition is key: data engineering isn't a one-time move but an ongoing flow that must run reliably again and again. Pipelines are automated, recurring processes.
- **It's the core data-engineering artifact.** Building, running, and maintaining pipelines is much of what data engineers *do*. A data platform is largely a collection of pipelines moving and transforming data. So understanding pipelines — how they extract, transform, and load, and how they're orchestrated — is central to understanding data engineering. Pipelines are the discipline's core artifact.

A data pipeline is an automated, repeatable process that extracts data from sources, transforms it, and loads it to a destination — the fundamental building block of data engineering, implementing the data lifecycle as an ongoing reliable flow. The classic structure of a pipeline is ETL.

## ETL: the classic pattern

**ETL** (Extract, Transform, Load) is the classic data-pipeline pattern, defining three stages:

- **Extract: get data from sources.** *Extract* pulls data out of source systems (databases, APIs, files, logs) — collecting the raw data to be processed. This is the ingestion step, gathering data from where it lives.
- **Transform: clean and reshape.** *Transform* processes the extracted data — cleaning it (fixing errors, handling missing values), standardizing formats, joining sources, aggregating, and reshaping it into the desired structure. This is where raw data becomes usable data, and it's often the most complex stage. In classic ETL, transformation happens *before* loading — the data is transformed *on the way* to its destination.
- **Load: store it in the destination.** *Load* writes the transformed data into the destination (traditionally a data warehouse) where it'll be used. The data arrives already transformed and ready to use.

```text
   ETL:  Extract → Transform → Load
         (get)     (clean/reshape   (store the
                    BEFORE loading)   ready data)
```

Classic ETL — transform *before* load — made sense historically because storage and compute were *expensive*: you transformed data (often on a separate processing system) to a compact, ready form *before* loading it into the costly warehouse, so the warehouse only held clean, needed data. ETL was the standard for decades, and it's still used. But the economics changed, driving a shift in the order.

## ELT: the modern shift

The major modern shift is from ETL to **ELT** (Extract, Load, Transform) — *loading raw data first, then transforming it in the destination*. The reordering is consequential:

- **ELT: load raw, then transform in place.** In ELT, you *Extract* data, *Load* it (raw or lightly-processed) directly into the destination (a modern cloud data warehouse), and *Transform* it *there* (inside the warehouse, using its compute). Transformation happens *after* loading, *in* the destination — the reverse order from ETL.

```text
   ELT:  Extract → Load → Transform
         (get)     (store RAW    (clean/reshape
                    first)        IN the warehouse)
```

- **Why the shift happened: cheap cloud warehouses.** ELT became dominant because *modern cloud data warehouses* (and lakehouses) made storage and compute *cheap and scalable*. When storage is cheap, you can afford to load *all* the raw data first (no need to pre-transform to save space); when the warehouse has powerful, scalable compute, you can transform *there* efficiently. The old reason for ETL (expensive storage/compute forcing pre-transformation) went away, so it became simpler and better to load raw and transform in the powerful warehouse. Cheap cloud data infrastructure drove the ETL→ELT shift.
- **ELT's advantages.** ELT is *simpler* (load raw first, no complex pre-load transformation infrastructure), *more flexible* (you have all the raw data in the warehouse, so you can transform it different ways for different needs, and re-transform as needs change — the raw data is preserved), and *leverages the warehouse's power* (transformation uses the warehouse's scalable compute, often via SQL). This flexibility and simplicity made ELT the modern default, especially with tools (like dbt) that do transformation *in* the warehouse. ELT fits the modern cloud data stack (the modern-data-stack post).

The ETL→ELT shift — from transform-before-load to load-raw-then-transform-in-the-warehouse — is the defining modern data-pipeline change, driven by cheap, powerful cloud warehouses (removing ETL's storage/compute-saving rationale) and offering simplicity, flexibility (all raw data preserved, transform any way), and use of the warehouse's compute. ELT is the modern default. Both patterns are pipelines that need orchestration.

## Orchestration: running pipelines reliably

Pipelines don't run themselves — **orchestration** coordinates *when* and *how* pipeline steps run, and it's essential for reliable data engineering:

- **Orchestration coordinates the workflow.** Real data pipelines have *many steps* with *dependencies* (step B needs step A's output; task C runs after B and D) and *schedules* (run nightly, or when new data arrives). *Orchestration* manages this — running steps in the right order, respecting dependencies, on schedule, handling the overall workflow. It's the coordination layer that makes complex, multi-step pipelines run correctly. (Orchestration tools model pipelines as dependency graphs — DAGs — of tasks.)
- **It handles failures and retries.** Pipelines fail (a source is down, data is bad, a step errors) — orchestration handles *failures*: retrying failed steps, alerting on problems, managing partial failures, and ensuring the pipeline recovers or fails safely. Since reliability is essential (the previous post), robust failure handling is a key orchestration job. Pipelines *will* fail, and orchestration is how they fail gracefully and recover.
- **It provides visibility and reliability.** Orchestration gives *visibility* into pipeline runs (what ran, when, succeeded/failed) and enables *reliable, monitored* operation — essential because everything downstream depends on pipelines running correctly and on time. Orchestration turns a collection of pipeline steps into a reliably-operated, observable system. It's central to running data engineering in production, not just building it.

Data pipelines — automated, repeatable flows that extract, transform, and load data — are data engineering's core artifact, structured classically as ETL (transform before load) and now dominantly as ELT (load raw, transform in the powerful cloud warehouse — driven by cheap cloud infrastructure, offering simplicity and flexibility), and run reliably via orchestration (coordinating steps, dependencies, schedules, and failures). Next: where data lives — warehouses, lakes, and lakehouses.

## Key takeaways

- A data pipeline is an automated, repeatable process that extracts data from sources, transforms it, and loads it to a destination — running on schedules or triggers to keep destination data current; pipelines are data engineering's core artifact (a data platform is largely a collection of pipelines).
- ETL (Extract, Transform, Load) is the classic pattern — transform data *before* loading it into the destination — which made sense when storage/compute were expensive (pre-transform to a compact, ready form before the costly warehouse).
- ELT (Extract, Load, Transform) is the modern shift — load raw data first, then transform it *in* the destination warehouse — driven by cheap, powerful cloud data warehouses (removing ETL's storage/compute-saving rationale), and offering simplicity (no complex pre-load transformation), flexibility (all raw data preserved, transform any way and re-transform as needs change), and use of the warehouse's scalable compute (often via SQL/dbt).
- The ETL→ELT reordering is the defining modern data-pipeline change and fits the modern cloud data stack — ELT is now the default.
- Orchestration coordinates when and how pipeline steps run — managing dependencies (as DAGs of tasks), schedules, failures/retries, and visibility — turning multi-step pipelines into reliably-operated, observable systems, which is essential because everything downstream depends on pipelines running correctly (and pipelines *will* fail, so graceful failure handling matters).

## Further reading

- [Extract, transform, load (Wikipedia)](https://en.wikipedia.org/wiki/Extract,_transform,_load)
- [Data pipeline (Wikipedia)](https://en.wikipedia.org/wiki/Data_pipeline)
- [What data engineering is (previous post)](/blog/posts/de-01-what-data-engineering-is.html)
