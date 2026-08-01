# Rules and ML in One Fraud Decision Path

*How to combine a deterministic rules engine with an ML risk model in a single decision: rule precedence, score bands, shadow mode, and champion/challenger evaluation with feedback labels.*

---

Fraud teams rarely get to choose between rules and machine learning. They run both, and the hard part is engineering. A rules engine is auditable, instantly changeable, and trusted by risk officers who need to explain a decline to a regulator. An ML model catches the fuzzy, drifting patterns that no analyst can hand-write. The failure mode is running them as two disconnected systems that occasionally disagree in production with no defined winner. This post describes a single decision path where rules and a model each have a well-defined job, the arbitration between them is explicit, and every outcome feeds the next model.

## One path, two kinds of judgment

The core design decision is ordering. Rules run first, but not all rules do the same thing. Split them into two tiers with different authority.

**Hard rules** are non-negotiable blocks: a card on the internal fraud list, a sanctioned counterparty, a velocity ceiling that no legitimate customer reaches. These short-circuit the path. If a hard rule fires, the model never runs, because no model score should be able to approve a transaction that policy forbids.

**Soft signals** are everything else a rule can assert cheaply: this device is new, this amount is unusual for the account, this IP geolocates far from the billing address. Soft signals do not decide anything on their own. They become features the model consumes, and they become tie-breakers when the model score lands in an ambiguous band.

```
  transaction
       │
       ▼
 ┌───────────┐   fires    ┌──────────────┐
 │ hard rules├──────────► │ DECLINE/BLOCK│
 └─────┬─────┘            └──────────────┘
       │ pass
       ▼
 ┌───────────┐   soft signals as features
 │ ML scoring│◄─────────────────────┐
 └─────┬─────┘                       │
       │ risk score + band           │
       ▼                             │
 ┌───────────┐                 ┌─────┴─────┐
 │  policy   │                 │  feature  │
 │ approve / │                 │  assembly │
 │ step-up / │                 └───────────┘
 │ decline   │
 └─────┬─────┘
       │ outcome + reason codes
       ▼
 ┌───────────┐   labels    ┌──────────────┐
 │  outcome  ├──────────►  │  champion /  │
 │   log     │  (fraud?)   │  challenger  │
 └───────────┘             └──────────────┘
```

> **▸ [Open the interactive diagram](/blog/diagrams/fintech-rules-vs-ml-fraud-scoring.html)** — pan, zoom, and trace every step (light/dark, self-contained).

The path is linear on the happy route and has exactly one early exit. That constraint keeps the system explainable: for any decision you can replay, you know whether a rule blocked it or the model scored it, and you never have to reconcile two systems that both claim authority.

## Precedence and the override contract

The word "combine" hides the real work, which is precedence. Define it as a strict, testable contract rather than an emergent property of code order.

The rule that has served well: **hard rules can only make a decision more conservative, never less.** A hard rule may downgrade an approve to a decline or a step-up. It may never upgrade a model decline into an approve. This one-directional authority means a risk officer can add an emergency block rule at 2 a.m. during an attack and be certain it cannot be silently overridden by a model that was trained before the attack existed.

Overrides run the other direction and need their own guardrails. An allowlist entry — a known-good corporate card, a manually reviewed merchant — can override a model decline, but only through a separate, logged override rule with an owner and an expiry. Model output and override output are stored as distinct fields so an audit can always answer "would the model alone have declined this?"

```python
def decide(txn, features, model):
    for rule in HARD_RULES:              # tier 1: blocks only
        if rule.matches(txn):
            return Decision("decline", reason=rule.code, source="rule")

    signals = [s for s in SOFT_SIGNALS if s.matches(txn)]
    score = model.score(features + encode(signals))
    band = to_band(score)                # low / review / high

    decision = policy_for(band, signals) # tier 2: model + tie-breakers

    for ov in ACTIVE_OVERRIDES:          # logged, owned, expiring
        if ov.applies(txn) and ov.relaxes(decision):
            return decision.override(ov, source="override")
    return decision
```

## Score bands, not a magic threshold

A single cutoff — approve below 0.8, decline above — throws away the model's most useful output, which is its uncertainty. Map the continuous score into bands, and give the middle band somewhere to go that is neither approve nor decline.

- **Low risk:** approve straight through.
- **Review band:** the model is unsure. Do not decline. Route to a step-up challenge — a one-time passcode, a 3-D Secure prompt, a hold for manual review — depending on channel. The soft signals decide *which* step-up: a new device leans toward device verification, an unusual amount leans toward a customer confirmation.
- **High risk:** decline, with the top contributing features surfaced as adverse-action reason codes.

Band boundaries are policy, not model artifacts. They live in configuration with their own change control, because moving the review boundary a few points is how you trade false positives against fraud losses without retraining anything. The step-up band is where most of the business value sits: it converts a hard binary into a recoverable friction event, so a legitimate customer the model doubted still completes the payment.

## Shadow mode before anything decides

No new model or rule version reaches a live decision without running in shadow first. In shadow mode the candidate scores every real transaction, its decision is computed and logged, but the incumbent — the champion — is what actually executes. You compare the two decision streams offline.

Shadow mode answers the questions that offline test sets cannot: How often would the candidate disagree with production? What is the decline-rate delta on real traffic? Are the disagreements concentrated in one segment, one merchant, one country? A model that looks better on a held-out set but would decline 4% more of a major partner's volume is a business incident waiting to happen, and shadow mode surfaces it before a single customer is affected.

Keep the shadow path strictly side-effect-free. It writes to the outcome log and nothing else — no charges, no holds, no customer messaging. The moment a shadow evaluation can touch state, it stops being a safe test.

## Labels close the loop

The scoring path is only half the system. The other half is the feedback that makes the next model. Every decision writes an outcome record: the features as they were at decision time, the score, the band, the final action, the reason codes, and the deciding source. That snapshot is critical — reconstructing features later invites training-serving skew, where the model learns on data it never actually saw in production.

Labels arrive later and from several sources with different latencies. A chargeback confirms fraud weeks after the fact. A customer confirmation during step-up is a same-session good-label. A manual review analyst's disposition lands in hours. Each label carries its own delay and reliability, and the training pipeline has to respect that a transaction is "unlabeled" until enough time has passed for a chargeback to be possible.

Champion/challenger is how those labels become progress without risk. The challenger is trained on accumulated labeled outcomes, validated offline, promoted to shadow, and only after it beats the champion on real disagreement analysis does it take over as the executing model. The former champion is retained for rollback. This turns model updates into a routine, reversible operation instead of a high-stakes swap — which is exactly what a system that touches every payment needs.

## What the architecture buys you

The value is not in the rules or the model individually; both are commodities. It is in the contract between them: hard rules that only ever tighten, a model that owns the fuzzy middle through bands, a step-up path that recovers false positives, shadow mode as the gate to production, and an immutable outcome log that feeds champion/challenger. Each piece is independently auditable, independently changeable, and — most importantly — has one unambiguous answer to the question every fraud system eventually gets asked: why was this transaction declined?
