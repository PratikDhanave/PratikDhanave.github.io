# Data Modeling for Analytics

*The same data can be organized in ways that make analytical queries fast, intuitive, and cheap — or slow, confusing, and expensive. Data modeling is the craft of that organization, and it's where a counterintuitive truth lives: the careful normalization that's correct for application databases is often exactly wrong for analytics. Analytical data wants to be shaped differently, around how questions are asked rather than how data is written, and understanding dimensional modeling is understanding how to make a warehouse actually usable.*

**Data modeling** is how data is *organized and structured* for its use — and modeling for *analytics* differs from modeling for applications. This post covers what data modeling is, the normalization-vs-denormalization tradeoff (and why analytics leans denormalized), dimensional modeling and the **star schema**, and why modeling matters. It builds on the storage post (modeling organizes data within warehouses) and is where raw data becomes *usefully structured* data for analytics.

## What data modeling is

**Data modeling** is designing *how data is organized and structured* — what tables/entities exist, their fields, and how they relate — for the intended use. It shapes how usable, performant, and understandable the data is:

- **It's the structure of the data.** Modeling defines the *schema* — the tables, columns, relationships, and organization of the data. Good modeling makes data *usable* (intuitive to query, correctly structured for its purpose); poor modeling makes it confusing, slow, or wrong. It's the blueprint for how data is arranged. The same underlying data, modeled differently, yields very different usability.
- **Modeling depends on the use.** Crucially, the *right* model depends on *how the data will be used*. Modeling for *transactional applications* (OLTP) and modeling for *analytics* (OLAP) have *different* goals and best practices — because the workloads differ (from the OLTP/OLAP distinction in the previous post). Data engineering mostly cares about modeling for *analytics*, which differs from the application-database modeling many engineers know. Same data, different optimal model for different uses.
- **It determines query performance and clarity.** How data is modeled directly affects *query performance* (a good analytical model makes queries fast and simple; a bad one makes them slow and complex) and *clarity* (a good model is intuitive for analysts to understand and query). Modeling is where usability and performance for analytics are largely determined. Getting it right makes the warehouse pleasant and fast; getting it wrong makes it painful.

Data modeling is designing how data is organized and structured for its intended use, determining usability, performance, and clarity — and modeling for analytics (OLAP) differs from modeling for applications (OLTP). The key analytical-modeling tradeoff is normalization vs denormalization.

## Normalization vs denormalization

A central modeling tradeoff is **normalization** vs **denormalization** — and analytics leans the opposite way from application databases, which surprises many engineers:

- **Normalization: minimize redundancy (good for OLTP).** *Normalization* organizes data to *minimize redundancy* — each piece of data stored once, split across many related tables, connected by relationships. It's the standard for *application databases* (OLTP): it keeps data consistent (no duplication to get out of sync) and efficient for transactional writes/updates (change data in one place). Normalized models are correct and efficient for transactions. Most engineers learn normalization as "good database design."
- **Denormalization: reduce joins (good for OLAP).** *Denormalization* deliberately *duplicates* data / combines it into fewer, wider tables — the *opposite* of normalization. For *analytics* (OLAP), this is often *better*: analytical queries scan and aggregate lots of data, and normalized data requires many *joins* (combining the split tables) which are expensive at analytical scale. Denormalizing (fewer, wider tables, some duplication) *reduces joins*, making analytical queries *faster and simpler*. So analytics leans *denormalized*.
- **The tradeoff and why analytics flips it.** Normalization optimizes for *consistency and write efficiency* (OLTP's needs); denormalization optimizes for *read/query performance and simplicity* (OLAP's needs) at the cost of some redundancy. Analytics *flips* the usual "normalize" wisdom because its priorities differ: analytical data is *read* heavily (queries) and *written* in controlled bulk (pipelines), so query performance matters more than write efficiency, and controlled duplication is acceptable. This is why analytical modeling denormalizes — a key insight for engineers used to OLTP normalization. Different workload, opposite optimal choice.

The normalization (minimize redundancy — good for OLTP consistency and writes) vs denormalization (duplicate/combine to reduce joins — good for OLAP query performance) tradeoff flips for analytics: analytics leans *denormalized* because it prioritizes read/query performance over write efficiency, and controlled duplication is acceptable. This surprises engineers trained on normalization, and it underlies dimensional modeling.

## Dimensional modeling and the star schema

The dominant analytical modeling approach is **dimensional modeling**, whose signature is the **star schema** — a denormalized structure designed for analytical queries:

- **Facts and dimensions.** Dimensional modeling organizes data into *facts* and *dimensions*. **Fact tables** hold the *measurements/events* you analyze — the numeric, quantitative data (sales amounts, quantities, event counts), typically many rows. **Dimension tables** hold the *descriptive context* — the "who, what, where, when" attributes you analyze *by* (customer, product, location, date). You analyze *facts* (measures) *by* *dimensions* (attributes) — e.g. sales (fact) by product and region and month (dimensions). This facts-and-dimensions split matches how analytical questions are naturally asked.
- **The star schema.** A **star schema** arranges a central *fact table* connected to surrounding *dimension tables* — forming a star shape (fact in the middle, dimensions around it). It's *denormalized* (dimensions are wide, some redundancy) precisely to make analytical queries *fast and simple*: analysts join the fact to the relevant dimensions and aggregate. The star schema is the classic, widely-used analytical model because it's *performant* (few joins, denormalized) and *intuitive* (facts and dimensions map to how people think about analysis).

```text
   Star schema:
                 [Dim: Date]
                     |
   [Dim: Product]—[FACT: Sales]—[Dim: Customer]
                     |
                 [Dim: Store]
   central fact table (measures) surrounded by dimension tables (context)
```

- **Why it works for analytics.** The star schema fits analytics because it's structured around *how analytical questions are asked* (measures by dimensions), it's *denormalized* for query performance (fewer joins than a normalized model), and it's *understandable* (facts and dimensions are intuitive). It's the archetypal analytical model — knowing it is knowing how analytical data is typically structured. (Variations like the snowflake schema normalize dimensions somewhat; the star is the core idea.)

Dimensional modeling — organizing data into facts (measures/events) and dimensions (descriptive context), arranged as a star schema (central fact table surrounded by dimension tables) — is the dominant analytical modeling approach, denormalized for query performance and structured around how analytical questions are asked. It's how analytical data is typically modeled. This modeling matters a great deal.

## Why modeling matters

Data modeling is often underappreciated but critically important — worth making explicit:

- **It determines whether analytics is usable.** Good modeling makes data *usable* — analysts can query it intuitively, queries are fast, and the data correctly represents the business. Poor modeling makes analytics *painful* — confusing structure, slow queries, wrong results. Modeling largely determines whether the warehouse is a pleasure or a pain to use. It's the difference between usable and unusable analytical data.
- **It affects performance and cost.** How data is modeled directly affects *query performance* (good analytical models make queries fast) and thus *cost* (in cloud warehouses, faster queries scan less data and cost less). A well-modeled warehouse is faster and cheaper to query; a poorly-modeled one is slow and expensive. Modeling has real performance and cost consequences at scale.
- **It's a durable, high-leverage design decision.** The data model is *foundational* — everything (queries, dashboards, reports, downstream use) is built on it, and changing it later is disruptive (lots depends on it). So getting modeling right is *high-leverage* and worth care upfront. Like software architecture, the data model is a foundational decision with long-lasting impact. Invest in it.
- **It requires understanding the business and the questions.** Good analytical modeling requires understanding *what questions* the data must answer (what facts to measure, what dimensions to analyze by) — so it connects data engineering to the business and the analysts' needs. Modeling well means modeling around real analytical needs, not just technical structure. It's a business-aware design activity.

Data modeling — organizing data for its use, denormalized and dimensional (facts/dimensions, star schema) for analytics — is how raw data becomes usefully structured, and it critically determines whether analytics is usable, performant, and cost-effective. It's a high-leverage, foundational, business-aware design decision that surprises engineers by flipping OLTP normalization. Next: batch vs streaming — the two paradigms for processing data.

## Key takeaways

- Data modeling designs how data is organized and structured (tables, columns, relationships) for its intended use — determining usability, query performance, and clarity — and the *right* model depends on the use: modeling for analytics (OLAP) differs from modeling for applications (OLTP).
- The normalization vs denormalization tradeoff flips for analytics: normalization (minimize redundancy, split across related tables) is good for OLTP (consistency, write efficiency), but analytics leans *denormalized* (duplicate/combine into fewer wider tables to reduce expensive joins) because it prioritizes read/query performance over write efficiency — surprising engineers trained on normalization.
- Dimensional modeling organizes data into facts (numeric measures/events you analyze — e.g. sales amounts) and dimensions (descriptive context you analyze *by* — customer, product, date), matching how analytical questions are naturally asked (measures by dimensions).
- The star schema (a central fact table surrounded by dimension tables) is the classic analytical model — denormalized for fast, simple queries (few joins) and intuitive (facts/dimensions map to how people think about analysis) — the archetype of how analytical data is structured.
- Modeling matters greatly: it determines whether analytics is usable (vs painful), affects query performance and cost (faster models scan less and cost less in cloud warehouses), is a durable high-leverage foundational decision (everything builds on it, hard to change later), and requires understanding the business and the questions the data must answer.

## Further reading

- [Data modeling (Wikipedia)](https://en.wikipedia.org/wiki/Data_modeling)
- [Star schema (Wikipedia)](https://en.wikipedia.org/wiki/Star_schema)
- [Where data lives: warehouses, lakes, and lakehouses (previous post)](/blog/posts/de-03-where-data-lives.html)
