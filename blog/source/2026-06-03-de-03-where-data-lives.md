# Where Data Lives: Warehouses, Lakes, and Lakehouses

*"Just put it in a database" stops working the moment you're dealing with analytics at scale — because the database that runs your application is optimized for exactly the wrong thing. Analytical data needs different storage: systems built to scan and aggregate huge volumes, not to serve fast individual transactions. The landscape of analytical storage — data warehouses, data lakes, and the newer lakehouses — is where data engineering decisions about where data lives get made, and understanding the differences (starting with OLTP vs OLAP) is essential.*

Where data is stored shapes what you can do with it. This post covers the analytical storage landscape: the crucial **OLTP vs OLAP** distinction (why analytical storage differs from application databases), **data warehouses**, **data lakes**, and the **lakehouse** that combines them. It builds on the pipelines post (pipelines load data into these stores) and sets up modeling (how data is organized within them). Choosing where data lives is a core data-engineering decision.

## OLTP vs OLAP: two kinds of workload

The foundational distinction is between **OLTP** (transactional) and **OLAP** (analytical) workloads — they have opposite needs, requiring different storage:

- **OLTP: transactional (application databases).** *OLTP* (Online Transaction Processing) is the workload of *applications* — many small, fast operations reading/writing individual records (place an order, update a profile). Application databases (the operational databases behind apps) are optimized for OLTP: fast individual transactions, many concurrent users, quick reads/writes of specific rows. This is what "database" usually means in app development.
- **OLAP: analytical (data warehouses).** *OLAP* (Online Analytical Processing) is the workload of *analytics* — large, complex queries that *scan and aggregate huge amounts of data* (total sales by region over years, trends across millions of rows). Analytical storage is optimized for OLAP: scanning and aggregating large volumes fast, complex queries over lots of data — not fast individual-record transactions.
- **Why they need different storage.** These workloads are *opposite*: OLTP wants fast small transactions on individual records; OLAP wants fast scans/aggregations over massive data. Storage optimized for one is bad at the other — you can't efficiently do big analytics on an application database (it's built for transactions, not scans), and you wouldn't run an app on an analytical warehouse. So analytics needs *separate, analytical* storage (warehouses/lakes), not the application database. This OLTP/OLAP split is *why* data engineering moves data into dedicated analytical stores.

The OLTP (transactional, application databases, fast small operations) vs OLAP (analytical, warehouses, big scans/aggregations) distinction is foundational: the two workloads have opposite needs, so analytics requires dedicated analytical storage, not the application database. This is the reason data engineering exists to move data into warehouses/lakes. Those analytical stores come in a few forms.

## Data warehouses

A **data warehouse** is a storage system *optimized for analytics* (OLAP) — structured, organized data designed for fast analytical queries. It's the classic analytical store:

- **Structured, optimized for analytical queries.** A warehouse stores *structured* data (organized into tables with defined schemas) and is *optimized* for OLAP — scanning and aggregating large volumes efficiently (often using columnar storage, from the database-internals series, which is great for analytics). It's built to answer complex analytical queries over lots of data fast. Warehouses are the workhorse of analytics/BI.
- **Schema-on-write: structure first.** Traditionally, warehouses use *schema-on-write* — data is *structured and modeled* (fit to a defined schema) *before* being loaded (or during load). You define the structure, then load data into it. This gives clean, organized, query-ready data, but requires defining structure upfront (and handles unstructured/varied data poorly). It fits well-defined, structured analytical data.
- **Modern cloud warehouses.** Modern *cloud data warehouses* made warehouses cheap, scalable, and powerful — separating storage and compute, scaling elastically, and providing huge query power. These cloud warehouses are central to the modern data stack (and enabled the ELT shift from the previous post — cheap powerful warehouses to load raw data into and transform in place). The cloud warehouse is the hub of modern analytical data.

Data warehouses are analytical (OLAP) stores of structured, modeled data optimized for fast analytical queries (schema-on-write — structure defined first), with modern cloud warehouses being cheap, scalable, and central to the modern stack. Warehouses excel at structured analytical data but handle varied/unstructured data poorly — which is where data lakes come in.

## Data lakes

A **data lake** is a store for *large amounts of raw data in any format* — flexible, scalable, and schema-on-read. It complements the warehouse's structure with flexibility:

- **Raw data, any format.** A data lake stores *vast* amounts of data in its *raw, native format* — structured, semi-structured, and unstructured (tables, logs, JSON, images, text, anything) — cheaply and at massive scale (typically on cheap cloud object storage). It doesn't require structuring data upfront; you dump raw data in. This flexibility handles the variety (and volume) of modern data that warehouses struggle with.
- **Schema-on-read: structure later.** Lakes use *schema-on-read* — data is stored raw, and *structure is applied when you read/query it* (not when you write it). This is the opposite of the warehouse's schema-on-write. Schema-on-read gives *flexibility* (store anything now, figure out structure later, use it different ways) at the cost of *query-readiness* (raw data isn't organized/optimized for queries until you process it). Lakes trade structure for flexibility.
- **Flexibility vs the "data swamp" risk.** Lakes' flexibility (store everything raw, cheaply) is powerful — great for varied data, ML (which often needs raw data), and keeping all data. But without governance, a lake can become a *"data swamp"* — a dumping ground of disorganized, poorly-documented, hard-to-use data. Lakes need governance and organization to stay useful (the data-quality/governance post). Flexibility without discipline becomes chaos. The lake's strength (dump anything) is also its risk.

Data lakes store vast raw data in any format, cheaply and flexibly (schema-on-read — structure applied at query time), complementing warehouses' structure — great for varied data and ML but risking becoming a disorganized "data swamp" without governance. Warehouses (structured, query-ready) and lakes (flexible, raw) each have strengths and weaknesses — which the lakehouse tries to unite.

## The lakehouse: combining both

The **lakehouse** is a newer architecture that combines the *flexibility of a lake* with the *structure and query performance of a warehouse* — aiming to get the best of both:

- **Warehouse capabilities on lake storage.** A lakehouse adds *warehouse-like structure, management, and query performance* (schemas, transactions, fast analytical queries, reliability) *on top of* cheap, flexible lake storage (raw data in open formats on object storage). It brings warehouse features to the lake — so you get flexibility *and* structure/performance in one system. It's an attempt to unify the two.
- **Why combine them.** Historically, organizations used *both* a lake (for raw/varied data and ML) and a warehouse (for structured analytics/BI) — a complex, two-system setup with data copied between them. The lakehouse aims to *combine* these into *one* system — avoiding the duplication and complexity of separate lake and warehouse, while serving both analytical (BI) and ML needs. One system for both, rather than two. Simplicity and unification are the motivation.
- **The modern direction.** The lakehouse (enabled by open table formats and modern cloud data platforms) is a significant modern trend — unifying analytical storage. Whether via lakehouse or separate systems, the *landscape* is the point: warehouses (structured, query-optimized), lakes (raw, flexible), and lakehouses (combining both). Knowing these options and their tradeoffs is the core "where data lives" knowledge. The trend is toward unified, flexible-yet-structured analytical storage.

Where data lives — driven by the OLTP/OLAP split that separates analytical from application storage — comes down to data warehouses (structured, query-optimized, schema-on-write), data lakes (raw, flexible, schema-on-read, but swamp-prone), and lakehouses (combining lake flexibility with warehouse structure/performance). Choosing the right analytical storage is a core data-engineering decision. Next: data modeling — how data is organized *within* these stores for analytics.

## Key takeaways

- The foundational distinction is OLTP (transactional — application databases, many fast small operations on individual records) vs OLAP (analytical — large complex queries scanning/aggregating huge data): these opposite workloads need different storage, which is *why* analytics requires dedicated analytical stores (warehouses/lakes) rather than the application database.
- A data warehouse is an analytical (OLAP) store of structured, modeled data optimized for fast analytical queries (often columnar), using schema-on-write (structure defined before loading) — modern cloud warehouses are cheap, scalable, and central to the modern stack (and enabled the ELT shift); warehouses excel at structured data but handle varied/unstructured data poorly.
- A data lake stores vast raw data in any format (structured to unstructured) cheaply and at scale, using schema-on-read (structure applied at query time) — flexible and great for varied data and ML, but risks becoming a disorganized "data swamp" without governance (flexibility needs discipline).
- The lakehouse combines the flexibility of a lake (cheap raw storage in open formats) with the structure and query performance of a warehouse (schemas, transactions, fast queries) — aiming to unify the historically-separate lake + warehouse into one system serving both analytics/BI and ML, avoiding duplication.
- Choosing where data lives — warehouse (structured/query-optimized), lake (raw/flexible), or lakehouse (both) — is a core data-engineering decision, and the modern trend is toward unified, flexible-yet-structured analytical storage (the lakehouse).

## Further reading

- [Data warehouse (Wikipedia)](https://en.wikipedia.org/wiki/Data_warehouse)
- [Data lake (Wikipedia)](https://en.wikipedia.org/wiki/Data_lake)
- [Data lakehouse (Wikipedia)](https://en.wikipedia.org/wiki/Data_lakehouse)
