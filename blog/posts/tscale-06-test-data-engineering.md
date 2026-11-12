<!-- Markdown version for AI agents and readers. Canonical: https://pratikdhanave.com/blog/posts/tscale-06-test-data-engineering.html -->

# Test Data Engineering — Fixtures, Factories, and the Anonymization Trap

*Every test runs against data, and at scale the data becomes its own engineering discipline: fixtures that encode last year's schema, factories that drift from what production actually produces, "anonymized" snapshots that are neither anonymous nor current, and demo environments whose data convinces no one. Test data rots faster than tests do — because nobody owns it — and the fix is the same as everywhere else in this series: make it declared, generated, versioned, and owned.*

Post [4](/blog/posts/tscale-04-test-environments.html) seeded environments "from versioned specs" and deferred the hard part; this post is the hard part — where the data in those specs comes from and how it stays true.

## The source spectrum, and where each belongs

- **Hand-written fixtures** — explicit records for explicit scenarios. Right for golden cases (the bill-07 invoices, apiver-03's gate fixtures) where *exact* values are the point. Wrong as the general mechanism: fixtures are frozen the day they're written, multiply per scenario, and fail silently to represent anything but themselves.
- **Factories** — code that generates valid entities on demand (`customer(overrides)`), with randomized-but-valid defaults and scenario-relevant fields pinned. The workhorse for unit and service tests: schema changes propagate through one factory instead of ten thousand fixtures, and tests state only what they care about — the rest is explicitly arbitrary. The discipline that keeps factories honest: they create through the **real creation paths** (application services, not raw inserts) wherever feasible, so an entity a factory makes is an entity the system could have made — raw-insert factories drift into producing states production can't reach, and tests pass against impossible data.
- **Synthetic generation at scale** — statistically-shaped data for volume: load tests, query-plan realism, pagination and cardinality behavior. Generators parameterized by production's *statistics* (distributions, cardinalities, null rates, skew — measurable without copying any record) produce data that behaves like production without containing it.
- **Production-derived data** — the tempting default and the trap, next.

## The anonymization trap

"Just use an anonymized prod snapshot" carries two compounding problems. **Anonymization is harder than it looks**: masking names and emails leaves quasi-identifiers (dates, locations, amounts, rare categories) whose combinations re-identify; linked tables leak through foreign keys; free-text fields hide PII in unstructured corners; and the copy now lives in lower-security environments with wider access — which is why privacy regimes treat pseudonymized data as still-personal (agmem-08's GDPR obligations follow the snapshot into staging). **And it rots anyway**: the snapshot ages from the moment it's taken, refreshing it re-runs the entire risk ceremony, and teams end up testing against a two-year-old frozen world with yesterday's edge cases and none of today's. The honest hierarchy: prefer **synthetic-from-statistics** (production's shape, nobody's records) for realism at scale; where production-derived data is genuinely irreplaceable (rare pathological records that resist synthesis), treat extraction as a **governed pipeline** — field-level allowlists, strong transformation, documented ownership, scheduled refresh, audit trail — not a DBA favor; and let the generators *learn from* production continuously (statistics re-sampled on schedule) so realism tracks reality without copying it.

## Data as versioned seed artifacts

Post 4's environments consume what this post produces: **seed specs** — named, versioned, composable data states ("empty org", "org with 50 active subscriptions mid-cycle", "fraud-ring graph", "tenant at quota") built from factories and generators, checked into version control beside the code they serve. The practices that keep the seed library alive: **scenario seeds are owned like fixtures** (each has a maintaining team; schema migrations must update seeds in the same change — zdm-02's expand/contract applies to seed specs too, and a migration PR that breaks seeding is caught in CI, not discovered in the next demo); **seeds compose** (big states assemble from small named ones, so "enterprise org under audit" is a composition, not a fork); **determinism is a dial** — seeded randomness reproduces a run exactly when debugging, varies when exploring (property-based testing's lesson applied to data); and **demo data is a first-class seed consumer** — the sales-demo environment is just another seeded state, which ends the tradition of demo databases lovingly hand-maintained and one `DELETE` away from catastrophe. The through-line matches the whole series: data stops being something environments *have* and becomes something they're *given* — declared, generated, versioned, owned.

The takeaway: test data is engineered along a spectrum — **exact fixtures for golden cases, real-path factories as the workhorse, statistics-driven synthesis for scale** — with production-derived snapshots treated as the governed exception, because anonymization under-delivers (quasi-identifiers, linked leakage, regulatory residue) and rots regardless. Package it all as **versioned, composable, owned seed specs** that migrations must update and environments consume, with determinism as a debugging dial and demos as just another seed. Rot is the default; ownership is the cure.

## Key takeaways

- The spectrum: **fixtures** (golden exactness only), **factories** (through real creation paths — raw-insert factories breed impossible states), **synthetic-from-statistics** (production's shape without its records), governed extraction as last resort.
- The **anonymization trap**: quasi-identifiers and linked tables re-identify, free text hides PII, regulation follows the copy — and the snapshot rots anyway. Statistics travel; records shouldn't.
- **Seed specs are code**: named, versioned, composable states owned by teams, updated in the same PR as schema changes (CI-enforced), consumed by post 4's environments.
- **Determinism is a dial** (reproduce when debugging, vary when exploring) and **demo data is a seed consumer** — ending the hand-tended demo database.

## Further reading

- [Test data — the asset this post gives an owner](https://en.wikipedia.org/wiki/Test_data)
- [Data anonymization — the technique whose limits define the trap](https://en.wikipedia.org/wiki/Data_anonymization)

---

Author: Pratik Dhanave (https://pratikdhanave.com) | Published: 2026-11-07
Canonical: https://pratikdhanave.com/blog/posts/tscale-06-test-data-engineering.html
Attribution: please link the canonical URL when citing or quoting this post.
