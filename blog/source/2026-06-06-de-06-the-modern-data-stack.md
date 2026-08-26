# The Modern Data Stack

*A decade ago, building a data platform meant heavy, monolithic, on-premises systems and long projects. Today it's assembled from specialized cloud tools that snap together around a central cloud data warehouse — ingest here, transform there, visualize over there — each best-in-class at one job. This "modern data stack" is less a specific set of products than an architecture and a philosophy, and understanding its shape (and what drove it) is understanding how data platforms are actually built now.*

The **modern data stack** is the contemporary, cloud-based, modular approach to building data platforms — a set of specialized tools organized around a cloud data warehouse, connected by the ELT pattern. This post covers what the modern data stack is, its architecture and components, the key idea of transformation-in-the-warehouse (dbt-style), and what drove its rise. It ties together the previous posts (pipelines, storage, modeling) into the overall architecture of a modern data platform.

## What the modern data stack is

The **modern data stack** is a *cloud-based, modular* approach to data infrastructure — assembling *specialized, best-in-class tools* around a central *cloud data warehouse*, rather than one monolithic system. Its defining traits:

- **Cloud-based and managed.** The modern data stack runs on *cloud* services — managed, scalable, pay-as-you-go tools — rather than self-managed on-premises systems. This makes powerful data infrastructure accessible without heavy ops (the cloud handles scaling, management), lowering the barrier to building a data platform. Cloud is foundational to the modern stack.
- **Modular: specialized tools that connect.** Rather than one big system doing everything, the modern stack *composes specialized tools* — each best at one job (ingestion, storage, transformation, visualization) — that *connect* into a pipeline. You assemble best-in-class components rather than buying a monolith. This modularity (mix and match specialized tools) is a defining characteristic. It's an architecture of composed specialists.
- **Centered on the cloud data warehouse.** The *cloud data warehouse* (from the storage post) is the *hub* — the central store around which the stack is organized. Data is ingested *into* the warehouse, transformed *in* it, and served *from* it. The powerful, cheap cloud warehouse being the center is what makes the modern stack's architecture (especially ELT) work. The warehouse is the gravitational center.

The modern data stack is a cloud-based, modular approach — specialized best-in-class tools composed around a central cloud data warehouse — replacing monolithic on-premises systems. It's an architecture and philosophy (compose cloud specialists around the warehouse) more than a fixed product set. Its components form a recognizable pipeline.

## The architecture and components

The modern data stack has a recognizable architecture — a pipeline of component types from source to consumption:

```text
   Sources → Ingestion → Cloud Data Warehouse → Transformation → BI/Serving
             (extract &   (central hub —          (transform IN     (dashboards,
              load raw)    store raw + transformed) the warehouse)    analytics, ML)
             [ELT: load raw first, then transform in the warehouse]
```

- **Ingestion (extract & load).** Tools that *extract* data from sources and *load* it (raw) into the warehouse — the "EL" of ELT. Managed ingestion tools connect to many sources and land raw data in the warehouse with minimal effort. This is the entry point, loading raw data first (ELT). Ingestion tools handle the connectors so you don't build them all.
- **The cloud data warehouse (the hub).** The central store (from the storage post) — holding raw loaded data *and* transformed data, providing the compute for transformation and queries. Everything flows through it. It's the heart of the stack. (Or a lakehouse serving the same central role.)
- **Transformation (in the warehouse).** Tools that *transform* the raw loaded data *inside* the warehouse — the "T" of ELT, done *after* loading, *in* the warehouse (the key modern idea, below). Transformation tools (dbt being the prominent example) let you define transformations (often in SQL) that run in the warehouse, turning raw data into modeled, usable data. This is where modeling (the previous post) is applied.
- **BI / serving / consumption.** Tools that *serve* the transformed data to consumers — BI/dashboard tools for analysts, and interfaces for ML and applications. This is the output, making the processed data useful. BI tools let analysts explore and visualize the warehouse's modeled data.
- **Plus orchestration, quality, governance.** Around these, *orchestration* (coordinating the pipeline — from the pipelines post), *data quality/observability* (ensuring reliability — a later post), and *governance* (managing the data — a later post) tools complete the stack. These support the core flow. The full stack includes these operational concerns.

The modern data stack's architecture is a pipeline of specialized components — ingestion (extract & load) → cloud warehouse (the hub) → transformation (in the warehouse) → BI/serving — plus orchestration, quality, and governance. This modular pipeline around the central warehouse is the shape of modern data platforms. Its most distinctive idea is transformation happening *in* the warehouse.

## Transformation in the warehouse (the dbt idea)

The signature idea of the modern data stack is **transformation in the warehouse** — doing the "T" of ELT *inside* the cloud warehouse, exemplified by tools like **dbt** (data build tool):

- **Transform where the data and compute are.** Because the modern stack loads raw data *into* the powerful cloud warehouse first (ELT), transformation happens *there* — using the warehouse's scalable compute, operating on the data in place. Rather than a separate transformation system (as in classic ETL), you transform *in* the warehouse. This leverages the warehouse's power and keeps data in one place. It's ELT's "transform in place" realized.
- **Transformation as code (dbt).** Tools like *dbt* let data teams define transformations *as code* — typically SQL models with dependencies, version control, testing, and documentation — that run *in* the warehouse. This brought *software-engineering practices* (version control, testing, modularity, CI) to data transformation, a major improvement. dbt-style transformation-as-code in the warehouse is central to the modern stack and a big reason for its productivity. Transformation became a disciplined, engineered activity.
- **Why it matters.** Transformation-in-the-warehouse (ELT with dbt-style tools) is *why* the modern stack is powerful and productive: it's simpler (no separate transformation infrastructure), leverages the warehouse's scalable compute, keeps all data (raw and transformed) in one place, and applies software-engineering rigor (testing, version control) to transformation. This approach — the "T" done in the warehouse as code — is the modern stack's defining, most impactful characteristic. It's the heart of how modern data platforms transform data.

Transformation in the warehouse — doing ELT's "T" inside the cloud warehouse as code (dbt-style, with version control, testing, and modularity) — is the modern data stack's signature idea, leveraging the warehouse's compute, keeping data in one place, and bringing software-engineering rigor to transformation. It's the defining modern practice. This whole approach arose from specific drivers.

## What drove the modern data stack

Understanding *why* the modern data stack emerged clarifies its logic — a few drivers converged:

- **Cheap, powerful cloud warehouses.** The foundational driver: *cloud data warehouses* that were cheap, scalable, and powerful (separating storage/compute, elastic scaling) — which made ELT feasible (load raw, transform in the warehouse) and gave the stack its central hub. The cloud warehouse's economics enabled the whole architecture (as the pipelines post noted for ELT). Cheap powerful warehouses are the root enabler.
- **Managed cloud tools lowered the barrier.** *Managed, specialized cloud tools* for each stage (ingestion, transformation, BI) meant teams could *assemble* a data platform from best-in-class services without building or heavily managing infrastructure. This modular, managed approach made powerful data platforms accessible to far more organizations. Accessibility via managed tools drove adoption.
- **ELT and transformation-as-code.** The *ELT shift* (from the pipelines post) and *transformation-as-code* (dbt) made the stack simpler and more productive — load raw, transform in the warehouse with engineering rigor. This is the methodological core that the tools enabled. ELT + dbt-style transformation is the modern way.
- **The result: accessible, powerful, modular data platforms.** Together, these drivers produced the modern data stack — an accessible, powerful, modular way to build data platforms, dramatically lowering the barrier to good data infrastructure compared to the monolithic, on-premises past. This is *why* it matters: it democratized and improved how data platforms are built. Building a solid data platform got far easier and better.

The modern data stack — cloud-based, modular, specialized tools around a central cloud warehouse, using ELT and transformation-in-the-warehouse (dbt-style, as code) — is how modern data platforms are built, driven by cheap powerful cloud warehouses, managed tools, and the ELT/transformation-as-code approach. It ties together pipelines, storage, and modeling into an accessible, powerful architecture. Next: data quality and governance — keeping the data reliable and well-managed.

## Key takeaways

- The modern data stack is a cloud-based, modular approach to data platforms — assembling specialized best-in-class tools (ingestion, transformation, BI) around a central cloud data warehouse — replacing monolithic on-premises systems; it's an architecture and philosophy more than a fixed product set.
- Its architecture is a pipeline of components: ingestion (extract & load raw — the "EL") → cloud data warehouse (the central hub holding raw and transformed data) → transformation (the "T", done *in* the warehouse) → BI/serving (dashboards, analytics, ML), plus orchestration, quality, and governance around the core flow.
- Its signature idea is transformation in the warehouse (ELT's "T" done inside the cloud warehouse using its compute), exemplified by dbt-style transformation-as-code — bringing software-engineering practices (version control, testing, modularity, CI) to data transformation, a major productivity improvement.
- It arose from converging drivers: cheap, powerful cloud data warehouses (the root enabler — making ELT feasible and providing the central hub), managed specialized cloud tools (lowering the barrier by letting teams assemble rather than build/manage infrastructure), and the ELT + transformation-as-code approach.
- The result is accessible, powerful, modular data platforms that dramatically lowered the barrier to good data infrastructure versus the monolithic on-premises past — tying together pipelines (ELT), storage (cloud warehouse/lakehouse), and modeling (applied in warehouse transformation) into how data platforms are built today.

## Further reading

- [Data warehouse — the central hub of the modern stack (Wikipedia)](https://en.wikipedia.org/wiki/Data_warehouse)
- [Extract, transform, load — ELT and the modern stack (Wikipedia)](https://en.wikipedia.org/wiki/Extract,_transform,_load)
- [Batch vs streaming (previous post)](/blog/posts/de-05-batch-vs-streaming.html)
