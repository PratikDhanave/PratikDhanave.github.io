# Features and Feature Stores — Where Fraud ML Is Actually Won

*Ask practitioners where fraud detection quality comes from and the answer is uniform: not the model — the features. Velocities, histories, graph signals, and their freshness carry the signal; the model just reads it. And ask where production fraud ML fails and the answer is equally uniform: the gap between how features were computed in training and how they're computed at serving time. This post covers both — the feature families that catch fraud, and the feature-store discipline that keeps them honest.*

Post [2](/blog/posts/fraud-02-rules-and-models.html) chose the engines; this post builds their fuel system — the infrastructure layer that is, in practice, most of a fraud platform's engineering.

## The feature families that carry the signal

- **Velocity features** — counts and sums over sliding windows, per entity: transactions per card per hour, distinct cards per device per day, amount per account per week. The workhorses of fraud signal, because attacks are fundamentally *bursts* — monetizing stolen credentials quickly before they die. Engineering weight: every velocity is a windowed streaming aggregate that must be **fresh to the second** (an hour-stale velocity misses the burst entirely) — this is the metering machinery of bill-03 repurposed, same event-time and idempotency disciplines, tighter latency.
- **History and profile features** — the entity's past as context: account age, prior chargebacks, typical amounts and merchants, device-account associations over time. Fraud is deviation; these features define the "from" that deviation is from. Slower-moving, batch-computable, cheap to serve from a profile record (the entity-centric pattern of agmem-05, wearing a risk hat).
- **Graph features** — the connective tissue: how many accounts share this device, this card's distance from known-fraud clusters, ring structures of mutually-linked entities. Fraud is organizationally networked — stolen cards are monetized through shared infrastructure — and graph features see what per-entity features can't. Served, in the latency budget, as *precomputed* neighborhood aggregates refreshed asynchronously, not as online graph traversals.
- **Derived risk signals** — upstream model outputs as features: email-address risk scores, device-fingerprint reputation, BIN-level statistics, the rules-as-features of post 2. The stack composes vertically, which is why post 2 preferred signals over verdicts.

## Point-in-time correctness: the silent killer

Training features have a property serving can't violate: each training row must contain **the feature values as they were at that transaction's moment** — not as they are now. Compute "cards per device, last 24h" from today's data for a six-month-old training transaction and the feature *includes the future* — often including the fraud outcome itself laundered through a velocity count. The model trains brilliantly, validates brilliantly, and collapses in production, because in production the future is unavailable. This is **label leakage via feature time-travel**, and it is the most common serious failure in applied fraud ML. The defense is architectural, not vigilant: features are defined once with explicit **event-time semantics**, training sets are built by **point-in-time joins** (as-of lookups against feature history, never against current state), and the same definition drives both paths — which is precisely the job description of a feature store.

## The feature store: one definition, two speeds

The feature store pattern — the infrastructure fraud teams built before the industry named it — solves training/serving skew by construction: **declare each feature once** (entity, aggregation, window, event-time source); the platform **materializes it twice** — an *offline* path (batch, over history, supporting as-of joins for training) and an *online* path (streaming, serving current values in single-digit milliseconds from a hot key-value tier) — from the **same definition**, so skew becomes a platform bug rather than a per-feature recurring accident. The remaining engineering is honesty between the paths: **parity checks** continuously compare online values against offline recomputation (the shadow-read discipline of zdm-04, applied to features); **freshness SLOs** per feature make staleness visible (a velocity feature's value *is* its freshness); and **feature lifecycle** — versioned definitions, owners, usage tracking, deprecation — because feature sprawl has the same sediment dynamics as rule sprawl, with the added cost that every serving-path feature spends milliseconds of post 1's budget. Features are the asset; the store is what keeps the asset from quietly becoming fiction.

The takeaway: fraud signal lives in **features** — second-fresh velocities (streaming aggregates with metering-grade discipline), entity histories, precomputed graph neighborhoods, and composed upstream scores — and fraud ML's characteristic failure lives in **training/serving skew**, above all *feature time-travel* leaking the future into training rows. The cure is the feature store pattern: single event-time definitions materialized offline (as-of joins) and online (millisecond serving) from the same source, held honest by parity checks, freshness SLOs, and lifecycle discipline. Win the features and the model is easy; lose point-in-time correctness and no model can save you.

## Key takeaways

- Signal hierarchy: **velocities** (burst detection; second-fresh streaming aggregates), **histories/profiles** (the baseline deviation is measured from), **graph features** (fraud is networked; precompute neighborhoods), **derived scores** (the stack composes vertically).
- **Point-in-time correctness is non-negotiable**: training rows carry features *as of* the transaction; current-state joins leak the future (often the label itself) — brilliant validation, production collapse.
- The **feature store** solves skew by construction: one event-time definition → offline (as-of joins) + online (ms serving) materializations.
- Keep the two paths honest: **parity checks** (shadow-recompute), **freshness SLOs** (a stale velocity is a different feature), **lifecycle** (versions, owners, deprecation — sprawl costs latency budget).

## Further reading

- [Feature engineering — crafting the signal the model reads](https://en.wikipedia.org/wiki/Feature_engineering)
- [Feature (machine learning) — the unit the store manages](https://en.wikipedia.org/wiki/Feature_(machine_learning))
