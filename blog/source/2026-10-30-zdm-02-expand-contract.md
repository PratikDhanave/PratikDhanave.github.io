# Expand/Contract — The Only Schema Change Pattern You Need

*Every zero-downtime schema change — rename a column, change a type, split a table, add a constraint — is the same move performed carefully: add the new shape alongside the old, migrate readers and writers in compatible steps, then remove the old shape long after anything needs it. Expand/contract (also traveling as "parallel change") is less a technique than the grammar all the techniques are written in. Learn it once and every migration becomes a sentence in it.*

Post [1](/blog/posts/zdm-01-why-migrations-break-things.html) established the invariant this pattern exists to satisfy: during rolling deploys, every live code version must work against the current schema state. Expand/contract is how you sequence change so that's always true.

## The grammar

The pattern has three phases, and the discipline is refusing to skip or reorder them:

- **Expand** — add the new structure without touching the old: new column, new table, new index. Additive changes are (with database-specific care) non-breaking and instant-or-online. Old code ignores new structure; nothing can break. Crucially, *expansion carries no meaning yet* — the new column exists, empty.
- **Migrate** — move reads and writes across in compatible increments, each its own deploy: (1) **write both** — new code writes old and new shapes (the application-level dual-write; post 4 handles its consistency obligations), old rows get backfilled (post 3) in parallel; (2) **read new** — once backfill completes and verification (post 4) agrees the shapes match, switch reads to the new shape, ideally behind a flag (post 5); (3) **write new only** — stop maintaining the old shape. Each step is a separate, rollback-able deploy, and at every intermediate state both the previous and next code versions are compatible with the schema — post 1's invariant, satisfied by construction.
- **Contract** — remove the old structure. Deliberately boring and deliberately *late*: days or weeks after step 3, when monitoring shows zero old-shape reads and the rollback window (post 5) has lapsed. Contraction is the point of no return, which is exactly why it's a separate, unhurried phase.

The worked example that teaches everything: **renaming a column** — the operation that looks trivial and, done as an actual `RENAME`, breaks every live query in the gap. In the grammar: expand (add `new_name`), write-both, backfill, read-new, write-new-only, contract (drop `old_name`). Six boring steps replace one exciting outage. Type changes, table splits, denormalizations — all the same sentence with different nouns.

## The database-specific fine print

Expand/contract assumes "additive is safe," and each engine attaches footnotes worth knowing cold. **Adding a column**: safe-and-instant when nullable or (on modern engines) with a non-volatile default — but historically, defaults meant full-table rewrites, and on older versions still do; know your engine's line. **Adding an index**: never plainly (full lock on many engines) — use the online/concurrent build variant, accept it's slower and can fail-and-retry, and remember it still competes for I/O (post 1's starvation). **Adding a constraint**: the two-step everywhere — declare it *unvalidated* (instant, enforces for new writes), then *validate* separately (scans without blocking writes). Foreign keys, NOT NULL, CHECK — same choreography. **The lock-timeout seatbelt**: per post 1, even "instant" DDL queues behind long transactions and outages everything behind *it* — so every migration sets an aggressive lock timeout (seconds) and retries, converting potential outages into visible, harmless failures. These four footnotes, plus a migration linter that enforces them mechanically (post 7), cover the large majority of real-world schema-change risk.

## The organizational halves

Two practices make the grammar stick. **Migrations ship separately from code** — each phase step is its own deploy/migration unit, sequenced over days; bundling expand-migrate-contract into one release recreates exactly the lockstep the pattern exists to avoid. And **contract debt is tracked debt** — the old columns and compatibility shims left after step 3 are safe but not free (confusing schemas, wasted writes, blocked future changes); every expand ticket spawns its contract ticket with a date, or the schema becomes an archaeology site of changes that were 90% finished.

The takeaway: expand/contract is the grammar of zero-downtime schema change — **add alongside (meaningless until migrated), migrate in compatible single-step deploys (write-both → read-new → write-new-only), contract late and deliberately** — satisfying by construction the invariant that every live code version works against every schema state. The fine print is per-engine: instant-adds have version caveats, indexes build online-or-not-at-all, constraints declare-then-validate, and lock timeouts are the universal seatbelt. Ship phases as separate deploys and track contraction as debt — the pattern's six boring steps are the price of deleting the one exciting outage.

## Key takeaways

- The grammar: **expand** (additive, instant, meaningless) → **migrate** (write-both + backfill → read-new behind a flag → write-new-only, each its own reversible deploy) → **contract** (late, deliberate, the point of no return).
- The column rename is the teaching case: one breaking `RENAME` becomes six compatible steps — and every other change is the same sentence with different nouns.
- Engine fine print to know cold: nullable/non-volatile-default adds, **concurrent index builds**, **declare-then-validate constraints**, and aggressive **lock timeouts with retry** so DDL fails visibly instead of queueing the world.
- Ship migration phases **separately from code releases**, and track **contraction as dated debt** — half-finished expand/contracts are how schemas rot.

## Further reading

- [Database schema — the structure being reshaped under load](https://en.wikipedia.org/wiki/Database_schema)
- [Backward compatibility — the property every intermediate state must hold](https://en.wikipedia.org/wiki/Backward_compatibility)
