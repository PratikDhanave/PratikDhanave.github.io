# Building a Credit Decisioning Engine

*How to assemble features from bureau, bank, and alt data, serve a scorecard or model, apply policy cutoffs, and emit adverse-action reason codes with a full audit trail.*

A credit decisioning engine is the service that turns an application into an approve, decline, or refer verdict. It is deceptively simple to prototype and genuinely hard to run in production, because two forces pull against each other. The business wants flexible policies that change weekly. The regulator wants every declined applicant to receive an accurate, reproducible explanation of why. An engine that cannot reconstruct the exact inputs and rules behind a decision it made six months ago is a liability, not an asset.

The design that survives audit treats decisioning as a deterministic pipeline over versioned inputs. Each stage has a narrow contract, emits an immutable record, and can be replayed. This post walks that pipeline stage by stage.

```text
 application ──▶ feature ──▶ scoring ──▶ policy ──▶ decision
   + PII        assembly    scorecard    hard       approve/
                (bureau,     or model    rules +    refer/
                 bank,       → PD        cutoff     decline
                 alt data)                            │
                                                      ▼
                                              adverse-action
                                               reason codes
```

> **▸ [Open the interactive diagram](/blog/diagrams/fintech-credit-decisioning-engine.html)** — pan, zoom, and trace every step (light/dark, self-contained).

## Feature assembly is the part that decides everything

The scoring model gets the headlines, but feature assembly is where correctness is won or lost. This stage takes the raw application plus enrichment pulls — a credit bureau file, bank transaction or income data, and alternative signals like device and thin-file indicators — and produces a single typed feature vector.

Two properties matter more than any modelling choice.

First, **point-in-time correctness**. Every feature must be computed as of the decision timestamp, using only data that existed then. If your training pipeline joins a bureau attribute that was actually backfilled a week after the application, your offline metrics are inflated and your live model underperforms in ways that are almost impossible to debug. The assembly layer should carry an `as_of` timestamp and refuse any source record with a later ingestion time.

Second, **an explicit contract**. A feature is not just a number; it is a name, a type, a source, a version, and a null-handling rule. Represent it that way:

```python
@dataclass(frozen=True)
class Feature:
    name: str          # "bureau.utilization_ratio"
    value: float | None
    source: str        # "bureau:v3", "bank:plaid", "derived"
    as_of: datetime
    missing: bool      # true when source returned no data

def assemble(application, pulls) -> dict[str, Feature]:
    # deterministic ordering, one Feature per contract entry
    ...
```

The `missing` flag is not a detail. Enrichment sources time out, return partial files, or have no record for a thin-file applicant. The engine must distinguish "utilization is zero" from "we never learned utilization," because those drive different policy branches and different reason codes. Silently coercing a missing value to zero is the most common and most expensive bug in this domain.

## Scorecards and models are interchangeable behind one interface

The scoring stage consumes the feature vector and returns a probability of default (PD) or an equivalent score band. The important architectural decision is to hide *what kind* of scorer runs behind a stable interface, so you can move from a hand-built scorecard to a gradient-boosted model — or run both — without touching anything upstream or downstream.

```python
class Scorer(Protocol):
    version: str
    def score(self, features: dict[str, Feature]) -> ScoreResult: ...
```

A traditional scorecard is a sum of weight-of-evidence bins; it is transparent and trivially explainable. A machine-learned model is more accurate but needs an explanation layer (per-feature attributions) bolted alongside its prediction. Both should return the same `ScoreResult`: a score, a PD, the scorer version, and the ranked feature contributions. Downstream stages never learn which one produced the number.

Pin the scorer version into the decision record. When a regulator asks why two similar applicants got different outcomes months apart, "they were scored by different model versions" must be an answer you can prove, not a guess.

## Policy is a separate layer from the model, on purpose

New engineers often want to fold cutoffs into the model — just threshold the PD. Resist this. Policy and scoring change at different rates, are owned by different teams, and carry different risk. The model is retrained quarterly by data science. Policy rules change weekly in response to fraud trends, funding constraints, or a new regulatory line, and are owned by risk and compliance.

Keep policy as an ordered, versioned ruleset evaluated *after* scoring:

- **Hard knockouts** run first and are independent of the score: applicant below minimum age, on an exclusion list, in an unsupported region, or failing identity verification. These decline regardless of how good the PD looks.
- **Score cutoffs** map the PD to an outcome band — approve above one threshold, decline below another, refer in between for manual review.
- **Affordability and exposure rules** can override an otherwise-approvable score when requested amount exceeds a debt-to-income ceiling.

Each rule that fires is recorded with its rule ID and version. The final verdict is a function of the ordered rule evaluation, not a single opaque threshold, and that ordering is what makes the outcome reproducible.

## Adverse-action reason codes are a first-class output

In many jurisdictions a declined or downgraded applicant is entitled to the principal reasons for that decision. Reason codes are not a UI afterthought; they must be derived from the same features and rules that drove the decision, at decision time, and stored with it.

The mechanism differs by scorer type but the output is uniform. For a scorecard, rank the features by how far each pushed the applicant below the approval baseline and map the top few to human-readable codes. For a model, use the per-feature attributions the scorer already returned. A hard knockout maps directly to its own reason. The rule is that every code must trace to a concrete input:

```text
decline
├─ R-04  high credit utilization        (bureau.utilization_ratio)
├─ R-11  limited credit history length  (bureau.age_of_file)
└─ R-27  income below required minimum   (bank.verified_income)
```

Generating these post hoc — asking a model "why did you decline this?" weeks later — produces explanations that may not match the original decision. Compute them inline and freeze them.

## Make the whole pipeline replayable

Tie the stages together with one invariant: given the same application ID and the same pinned versions, the engine reproduces the identical decision. That requires persisting, per decision, the full feature vector, every source pull with its `as_of`, the scorer version and output, the ordered list of rules evaluated, the verdict, and the reason codes.

This record is what auditors, dispute handlers, and your own debugging depend on. It also enables the champion/challenger and backtesting work that keeps the engine honest: you can re-run a new policy or model against historical decisions and measure the delta before shipping. An engine you can replay is an engine you can improve safely. One you cannot replay is one you are afraid to touch — and in credit, fear is how good models quietly rot behind stale policy.
