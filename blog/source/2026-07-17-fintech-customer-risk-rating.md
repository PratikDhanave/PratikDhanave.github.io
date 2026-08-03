# Customer Risk Rating: Scoring AML Risk
*Turning geography, product, channel, and behavior into a single defensible number — and a due-diligence tier a regulator can follow.*

Every regulated financial institution has to answer one question about every customer it onboards: how much money-laundering risk does this relationship carry? The answer drives everything downstream — how much identity evidence you collect, how closely you watch the account, how often you refresh the file. Get it too low and you miss the launderer; get it too high and you drown your analysts in false diligence and annoy good customers. The instrument that answers the question is the **customer risk rating** (CRR), and its job is to be *right enough, and explainable*.

The engineering trap is to treat CRR as a machine-learning problem. It is not, or at least not first. A CRR is a **policy expressed as arithmetic**. An examiner will ask why a specific customer scored what they scored, and "the gradient-boosted model decided" is not an acceptable answer. What follows is how to build a scoring pipeline that produces a number, maps it to a diligence tier, and — crucially — can reconstruct exactly why, for any customer, on any date, under any version of the policy.

## The risk factors

CRR aggregates a fixed set of risk dimensions. The specific list is a policy decision, but the common ones are:

- **Geography** — the customer's country of residence, nationality, and the jurisdictions they transact with. Sanctioned, high-corruption, or weak-AML-regime countries score high. This is usually driven off a maintained country-risk table, not free-form judgment.
- **Product / service** — a basic savings account is low risk; correspondent banking, private wealth, trade finance, and anything enabling rapid cross-border movement of value is high.
- **Channel** — how the relationship was established and is operated. Face-to-face onboarding scores lower than fully remote or third-party-introduced; anonymity-friendly channels score higher.
- **Customer type** — individual vs. legal entity, and within entities the opacity of the ownership structure. Complex multi-layer structures, bearer shares, and trusts raise the score.
- **Expected vs. actual activity** — at onboarding the customer declares expected turnover and behavior. The rating watches the *gap* between that declaration and observed activity. A stated $5k/month that runs $500k is a factor, not a footnote.
- **PEP and adverse media** — is the customer (or a beneficial owner) a politically exposed person, and does screening surface negative news or watchlist hits? These are typically the heaviest single factors.

Each of these is scored **on its own first**. That is the non-negotiable design rule: you compute a per-factor sub-score before anything is combined, because the per-factor scores are what you show an auditor and what a customer's relationship manager reasons about.

## Weighting and aggregation

Once each factor has a sub-score — say normalized to 0–100 — you combine them into a composite. The dumbest defensible method is a weighted sum:

```
composite = Σ (factor_score[i] × weight[i]) / Σ weight[i]
```

The weights encode policy: if PEP status matters three times as much as channel, that is `weight[pep] = 3 × weight[channel]`, written down, reviewed, and approved. Two engineering rules make this auditable:

1. **Weights are versioned configuration, never constants in code.** A weight change is a policy change. It gets a version number, an effective date, an approver, and a changelog entry. The score record stores *which* weight version produced it. This is what lets you re-run history: "under policy v7, this customer was medium; under v8 they became high because we re-weighted geography."

2. **Some factors are overrides, not addends.** A confirmed sanctions match or certain PEP categories should not be *averaged* — they should force the ceiling. Model this explicitly as a rule that pins the composite to the top band regardless of the weighted sum, and log that the ceiling rule fired. Averaging a sanctions hit down to "medium" because the other factors were clean is exactly the failure examiners look for.

The output is a single composite score, then **banded** into discrete tiers. Banding is deliberate: a continuous score invites false precision ("62.4 vs 61.9"), whereas tiers map cleanly to operational policy.

## Mapping to due-diligence tiers

The composite lands in one of three tiers, each with a defined diligence posture:

- **SDD — Simplified Due Diligence.** Low-risk, well-understood customers. Reduced evidence, light monitoring. Only permitted where regulation allows it.
- **CDD — Customer Due Diligence.** The standard baseline: verified identity, understood purpose, ongoing monitoring.
- **EDD — Enhanced Due Diligence.** High-risk. Source-of-funds and source-of-wealth evidence, senior sign-off, tighter transaction thresholds, and more frequent review. PEPs and high-risk geographies typically land here by policy.

The tier is the *actionable* output. The score exists to produce the tier; the tier drives real work — document requests, monitoring rules, review cadence. Routing customers into the right queue by tier is where the rating stops being a number and starts being control.

```
   RISK FACTORS            SCORING              AGGREGATE            ROUTE
 ┌───────────────┐
 │ geography     │─┐
 │ product       │ │      ┌──────────┐       ┌───────────┐
 │ channel       │ ├────▶ │  factor  │─────▶ │ weighted  │──score──┐
 │ customer type │ │      │ scoring  │       │ aggregate │         ▼
 │ expected/act. │─┘      └──────────┘       └───────────┘     ┌────────┐    ┌─────────┐
 │ PEP / adverse │            ▲                    ▲           │  risk  │───▶│  SDD /  │
 └───────────────┘            │                    │           │  tier  │    │ CDD/EDD │
                        versioned weights ─────────┘           └────────┘    └─────────┘
                                                                    ▲             │
                                              analyst override ─────┘             ▼
                                                (with reason)                 audit log
```

> **▸ [Open the interactive diagram](/blog/diagrams/fintech-customer-risk-rating.html)** — Risk factors are scored per-factor, weighted into a composite, banded to a tier, and routed to SDD/CDD/EDD, with overrides captured and every decision logged.

## Overrides, with reasons

No scoring model is complete. An analyst will sometimes know something the factors don't — a benign explanation for a suspicious pattern, or the reverse. So the pipeline must accept a **manual override**, but under strict discipline: an override requires a documented reason, an identified approver, and it never silently replaces the model score. You store *both* — the computed score and the overridden tier, side by side, with the justification. An unexplained override is indistinguishable from tampering; a reasoned one is a legitimate control that examiners expect to see used sparingly and recorded fully.

## Periodic vs. event-driven recalculation

A risk rating is not a fact you compute at onboarding and forget. Two triggers refresh it:

- **Periodic review** runs on a cadence set by the current tier — EDD customers might be re-rated annually, CDD less often, SDD least. This is the safety net that catches slow drift.
- **Event-driven recalculation** fires immediately on a material change: a new adverse-media hit, a PEP status change, activity breaching expected thresholds, a change in beneficial ownership, or a move to a higher-risk jurisdiction. These cannot wait for the periodic clock — the whole point is that a customer can become high-risk on a Tuesday.

Event-driven recalculation is where the versioning discipline pays off. Every recompute writes a new immutable score record: inputs, factor sub-scores, weight version, composite, tier, and any override. You never mutate the previous rating; you append a new one. The result is a full lineage — for any customer, at any point in time, you can answer *what was their rating, what drove it, and under which policy* — which is precisely the question an audit, a regulator, or your own investigations team will eventually ask.

## The engineering takeaway

A customer risk rating is a small amount of arithmetic wrapped in a large amount of discipline. The arithmetic — score each factor, weight, aggregate, band — is the easy part. The value is in the properties around it: documented and versioned weights, explicit override records with reasons, ceiling rules that can't be averaged away, and an append-only history that makes every past decision reconstructable. Build those in from the start and the model is defensible. Bolt them on later and you have a number nobody can explain — which, in AML, is worse than no number at all.
