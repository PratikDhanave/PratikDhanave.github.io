# Query Planning and Execution

*SQL is a language where you say what you want, not how to get it — and the component that invents the "how" is the query planner, the closest thing a database has to a brain. When a query is mysteriously slow, the answer is almost always in the plan, which is why reading `EXPLAIN` is the single most valuable database skill you can learn.*

This final post ties the whole series together. You've seen how data is stored (pages, B-trees/LSM, buffer pool, WAL), found (indexes), and kept correct under concurrency (transactions, isolation, MVCC). But between your SQL and all that machinery sits the **query planner** — the component that decides *how* to execute a declarative query using the storage and indexes available. Understanding it is how you turn all the prior knowledge into faster queries.

## Declarative SQL needs a planner

SQL is **declarative**: `SELECT name FROM users WHERE age > 30 ORDER BY name` states the desired result, not the procedure. But there are many *procedures* that could produce it — scan the whole table and filter, or use an index on `age`, or use an index on `name` to get the ordering for free, then filter. Each has wildly different cost depending on the data. The database must *choose*, and that choice is the job of the **query planner** (optimizer).

This is why the same query can be fast on Monday and slow on Friday, or fast on a small table and catastrophic on a large one: the *plan* changed, or a plan that was fine for 1,000 rows is terrible for 10 million. The SQL didn't change; the planner's decision did.

## The stages of query processing

A query flows through several stages before returning rows:

```text
SQL text
   │  Parser        →  syntax check, build a parse tree
   ▼
Parse tree
   │  Analyzer/binder → resolve tables/columns, types, permissions
   ▼
Logical query
   │  Optimizer      →  explore plans, estimate costs, pick the cheapest
   ▼
Execution plan
   │  Executor       →  run the plan operators, produce rows
   ▼
Result
```

- **Parser** — checks syntax and builds a tree from the SQL text.
- **Analyzer/binder** — resolves names (which table is `users`?), checks types and permissions, producing a validated logical representation.
- **Optimizer** — the interesting stage: it considers alternative execution strategies and picks one. This is where indexes are chosen or ignored, join orders are decided, and scan types are selected.
- **Executor** — runs the chosen plan, invoking the storage layer, buffer pool, and indexes to actually produce rows.

Most performance mysteries live in the optimizer's output — the **execution plan** — which is exactly what `EXPLAIN` shows you.

## The plan is a tree of operators

An execution plan is a **tree of physical operators**, each consuming rows from its children and producing rows for its parent. Knowing the common operators lets you read any plan:

- **Sequential scan (table scan)** — read the whole table. Best when you need most of the rows, or there's no useful index. Not inherently bad — for large result fractions it beats index access.
- **Index scan** — use an index to find matching rows, then fetch each from the table. Best for high-selectivity predicates returning few rows.
- **Index-only scan** — answer entirely from a covering index without touching the table (from the indexes post). Fastest when applicable.
- **Join operators** — the big ones:
  - **Nested loop join** — for each row of one input, look up matches in the other. Great when one side is small (often via an index); quadratic and slow when both are large.
  - **Hash join** — build a hash table on one input, probe it with the other. Excellent for large, unsorted inputs joined on equality.
  - **Merge join** — merge two *sorted* inputs in one pass. Great when both are already sorted (e.g. on indexed columns).
- **Sort, aggregate, limit** — for `ORDER BY`, `GROUP BY`, and `LIMIT`; a sort that spills to disk because it exceeds working memory is a common hidden cost.

The optimizer's job is to pick operators *and their arrangement* — which join algorithm, in what order to join tables, whether to scan or use an index — to minimize total cost.

## Cost-based optimization and statistics

How does the optimizer choose? Modern databases are **cost-based**: they estimate the cost (in terms of page reads, CPU, rows processed) of candidate plans and pick the cheapest. Those estimates depend entirely on **statistics** the database keeps about your data:

- **Row counts** and **table sizes.**
- **Cardinality / selectivity** — how many distinct values a column has, and how many rows a predicate is estimated to match. This drives the scan-vs-index decision (few matches → index; many → scan).
- **Value distributions (histograms)** — so the optimizer knows `WHERE country = 'US'` might match half the table while `country = 'FJ'` matches a handful.

This yields the most important practical truth about planners: **the optimizer is only as good as its statistics.** When statistics are **stale** — after a bulk load, a big delete, or rapid growth — the optimizer's estimates diverge from reality and it picks bad plans (choosing a nested loop expecting 10 rows when there are 10 million). The fix is usually to update statistics (`ANALYZE` in PostgreSQL; databases also do it automatically, but not always in time). A huge fraction of "the database suddenly got slow" incidents trace to stale statistics leading to a plan flip.

## EXPLAIN: reading the planner's mind

The planner exposes its decision through **`EXPLAIN`** (and `EXPLAIN ANALYZE`, which actually runs the query and reports real timings and row counts). This is the master skill of database performance, because it turns guesswork into diagnosis:

- **`EXPLAIN`** shows the chosen plan tree with *estimated* costs and row counts.
- **`EXPLAIN ANALYZE`** shows the plan plus *actual* execution times and *actual* rows per operator.

The most powerful diagnostic move is comparing **estimated vs. actual rows**. A large gap — the planner expected 5 rows and got 500,000 — is the tell-tale sign of a bad estimate (usually stale or missing statistics), and it explains most bad plans: the optimizer chose a strategy that's only good for the row count it *wrongly expected*. Things to look for:

- A **sequential scan** on a large table where you expected an index — is the index missing, unusable (function/type mismatch, leftmost-prefix violation from the indexes post), or did the planner estimate too many matching rows?
- A **nested loop** over large inputs — often a cardinality misestimate; a hash join might be far better.
- A **sort spilling to disk** — may need more working memory or an index that provides the order.
- **Estimated ≪ actual rows** — run `ANALYZE`, add or fix statistics, or reconsider indexing.

Reading a plan connects every earlier post: whether an index is used (indexes), how many pages a scan touches (pages/buffer pool), whether the working set is cached, and how join strategy interacts with data size. `EXPLAIN` is where the theory becomes actionable.

## Bringing the series together

A database, seen whole, is a pipeline: the **planner** turns your declarative SQL into a physical plan using **statistics**; the **executor** runs that plan against **indexes** and the **storage engine**; the storage engine works in **pages** cached by the **buffer pool** and made durable by the **WAL**; and the **transaction/MVCC** layer keeps it all correct while many clients do this at once. Every layer trades something — memory for disk, read speed for write speed, isolation for concurrency, plan quality for statistics freshness — and performance work is really the work of understanding which trade is biting. With this series, when a query is slow you now have the vocabulary to ask the right question: is it the plan, the index, the cache, the lock, or the statistics? — and `EXPLAIN` to find out.

## Key takeaways

- SQL is declarative (what, not how), so the query planner/optimizer must choose an execution strategy — which is why identical SQL can be fast or catastrophically slow depending on the plan and data size.
- A query flows parser → analyzer → optimizer → executor; the plan is a tree of physical operators (sequential/index/index-only scans; nested-loop/hash/merge joins; sort/aggregate/limit), and the optimizer picks operators and join order to minimize estimated cost.
- Optimization is cost-based and depends entirely on statistics (row counts, cardinality/selectivity, histograms) — the optimizer is only as good as its stats, and stale statistics after bulk loads or growth are a leading cause of sudden slowdowns (fix with ANALYZE).
- EXPLAIN (and EXPLAIN ANALYZE) reveal the chosen plan and estimated-vs-actual rows; a large estimate/actual gap is the classic signature of a bad plan from stale/missing statistics.
- The whole database is a pipeline of trade-offs — planner+statistics → executor → indexes → storage engine → pages+buffer pool → WAL, with transactions/MVCC keeping it correct — and performance work is diagnosing which trade (plan, index, cache, lock, or statistics) is biting.

## Further reading

- [PostgreSQL documentation — Using EXPLAIN](https://www.postgresql.org/docs/current/using-explain.html)
- [MVCC and concurrency control (previous post)](/blog/posts/dbint-07-mvcc-and-concurrency-control.html)
- [How a database stores data — start of the series](/blog/posts/dbint-01-how-a-database-stores-data.html)
