# Indexes

*An index is a data structure that lets a database find rows without reading the whole table — the difference between flipping to a book's index and reading every page. It's the highest-leverage performance tool a database gives you, and also the most misused: every index you add speeds up reads and slows down writes, so the skill is knowing exactly which ones earn their cost.*

The storage half of this series covered how rows live on disk. Now we move to *finding* them efficiently. Without an index, answering `WHERE email = 'x'` means scanning every row in the table — a **full table scan**. An **index** is a secondary structure that maps column values to the rows that contain them, turning that scan into a direct lookup. This post covers how indexes work, the main kinds, and — most importantly — when they help and when they hurt.

## The problem indexes solve

Consider a table of ten million users and the query `SELECT * FROM users WHERE email = 'a@b.com'`. With no index, the database must examine every row to find the match — ten million page-touches worth of work for one row. That's O(n): cost grows linearly with table size, and it's ruinous at scale.

An index on `email` changes the complexity. Because the index keeps email values *sorted* (in a B-tree, from the earlier posts), the database can navigate to the matching entry in a few page reads — O(log n) instead of O(n). For ten million rows that's roughly a handful of reads versus ten million. Indexes are how a database stays fast as data grows; without them, every query degrades linearly with table size.

## How an index points to rows

An index stores **(indexed value → row location)** entries, sorted by value. The "row location" detail differs by database and matters:

- In a **clustered** design (InnoDB's primary key, for example), the table's rows are *physically stored in the primary-key B-tree itself* — the index leaves *are* the rows. Secondary indexes then store the primary key as the pointer, so a secondary-index lookup finds the PK, then walks the primary tree to get the row.
- In a **heap** design (PostgreSQL), rows live in an unordered heap and every index (including the primary key) points to a physical row location. All indexes are "secondary" in the sense that they point into the heap.

The practical upshot: a secondary-index lookup often costs *two* traversals — find the entry in the index, then fetch the actual row from the table (a "heap fetch" or primary-key lookup). That extra fetch is why some indexes help less than expected — and why *covering indexes* (below) are so valuable.

## Kinds of indexes

Not all indexes are the same structure or serve the same query:

- **B-tree index** — the default, from the [B-tree post](/blog/posts/dbint-02-btrees-vs-lsm-trees.html). Great for equality (`=`), ranges (`<`, `>`, `BETWEEN`), sorting (`ORDER BY`), and prefix matches, because it keeps values sorted. This is the workhorse; most indexes you create are B-trees.
- **Hash index** — maps values through a hash for O(1) *equality* lookups, but useless for ranges or ordering (hashing destroys order). Rarely the right default since B-trees handle equality nearly as well *and* do ranges.
- **Composite (multi-column) index** — indexes several columns together, e.g. `(last_name, first_name)`. The **column order is critical**: such an index supports queries filtering on `last_name`, or `last_name` + `first_name`, but *not* `first_name` alone — this is the "leftmost prefix" rule. A composite index is sorted by the first column, then the second within that, so you can only use it left-to-right.
- **Covering index** — an index that contains *all* the columns a query needs, so the database answers entirely from the index without fetching the row (an "index-only scan"). This eliminates the second traversal above and is one of the most effective optimizations for hot queries.
- **Specialized indexes** — for cases B-trees can't serve: **GIN/inverted** indexes for full-text and array/JSON containment, **GiST** for geometric/spatial data, and (relevant to AI systems) **vector indexes** like HNSW for similarity search — the subject of its own series entry elsewhere.

## The cost of an index

Here is the discipline that separates good schema design from cargo-culting "add an index." **Indexes are not free** — every index is a second data structure that must be kept in sync:

- **Writes slow down.** Every `INSERT`, `UPDATE` (of an indexed column), and `DELETE` must update *every* affected index, not just the table. A table with eight indexes pays roughly eight times the index-maintenance cost per write. Over-indexing quietly throttles write throughput.
- **Storage grows.** Indexes consume disk (and buffer-pool memory that competes with the data pages). A heavily indexed table can have indexes larger than the table itself.
- **The optimizer has more to consider,** and an unused index is pure overhead — cost with no benefit.

So the goal is not "index everything" but "index exactly what your read patterns need, and nothing more." The trade is explicit: **you buy faster reads with slower writes and more space.** For read-heavy workloads that's a great deal; for write-heavy tables, each index must justify itself.

## When indexes don't help (or hurt)

Indexes have failure modes worth knowing, because they explain a lot of "I added an index and nothing got faster":

- **Low selectivity.** An index on a column with few distinct values (e.g. a boolean, or `status` with three values) barely helps — if a value matches 40% of rows, reading the index *and* fetching all those scattered rows is often *slower* than a sequential scan. Indexes shine on **high-selectivity** predicates that match a small fraction of rows.
- **The optimizer chooses a scan anyway.** If a query will return a large portion of the table, the planner (next post) may correctly ignore the index — a sequential read of many pages beats scattered index-driven fetches. That's the optimizer being smart, not broken.
- **Functions and type mismatches defeat indexes.** `WHERE lower(email) = 'x'` can't use a plain index on `email` (it'd need an index on `lower(email)`), and comparing a column to the wrong type can force a scan. The predicate must match the indexed expression.
- **Leftmost-prefix violations.** Filtering on the second column of a composite index without the first can't use it.
- **Write-heavy penalty.** On a table dominated by writes, an index that speeds a rare read may cost more in write overhead than it saves.

The recurring theme: an index is a *bet* that a given read pattern is frequent and selective enough to be worth the write and space cost. Confirm the bet with `EXPLAIN` (next post) rather than adding indexes on faith.

## Practical guidance

- **Index your access paths, not your columns.** Look at the `WHERE`, `JOIN`, and `ORDER BY` clauses your app actually runs, and index to serve those — especially foreign keys used in joins.
- **Prefer composite indexes ordered by selectivity and query shape,** respecting the leftmost-prefix rule; one well-ordered composite often replaces several single-column indexes.
- **Consider covering indexes for hot read paths** to get index-only scans.
- **Audit and drop unused indexes** — they cost writes and space for nothing (databases expose index-usage stats).
- **Verify with `EXPLAIN`** that the index is actually used and improves the plan; don't assume.

Indexes are the bridge between the storage layer and the query layer. Having them isn't enough — the database has to *decide* to use them, and weigh index access against scans and joins. That decision is the job of the query planner, the next post.

## Key takeaways

- An index maps column values to row locations, sorted, turning a full table scan (O(n)) into a direct lookup (O(log n)) — the primary reason a database stays fast as data grows.
- Secondary-index lookups often cost two traversals (index → then fetch the row), which is why covering indexes (that contain every column a query needs, enabling index-only scans) are so effective.
- Know the kinds: B-tree (the versatile default: equality, ranges, sorting), hash (equality only), composite (multi-column, governed by the leftmost-prefix rule), covering, and specialized (GIN/GiST/vector) for what B-trees can't do.
- Indexes are not free: every index slows writes (each insert/update/delete maintains it) and consumes storage/memory — so index exactly what read patterns need, buying faster reads with slower writes.
- Indexes fail to help on low-selectivity predicates, large result sets (the optimizer rightly scans), function/type mismatches, and leftmost-prefix violations — an index is a bet on a frequent, selective read pattern; verify it with EXPLAIN.

## Further reading

- [PostgreSQL documentation — Indexes](https://www.postgresql.org/docs/current/indexes.html)
- [Use The Index, Luke! — a guide to SQL indexing](https://use-the-index-luke.com/)
- [The write-ahead log (previous post)](/blog/posts/dbint-04-write-ahead-log-and-durability.html)
