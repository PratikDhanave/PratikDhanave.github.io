# Humans in the Loop — Review Queues, Friction Ladders, and the Third Answer

*The best fraud decision is often neither yes nor no but "prove it" — a verification step that fraudsters abandon and legitimate customers clear in seconds. And for the genuinely ambiguous rest, trained human reviewers remain the highest-precision classifier available, at a unit cost that makes their deployment an optimization problem. This post builds the human layer: friction as a decision outcome, review queues as both safety valve and labeling engine, and the operations that keep both honest.*

Post [4](/blog/posts/fraud-04-scoring-thresholds-and-the-cost-of-errors.html) put friction and review on the decision ladder between approve and decline; this post fills in those rungs — the layer where fraud systems stop being classifiers and become workflows.

## Friction: the self-selecting filter

Step-up friction — 3-D Secure authentication, one-time codes, document checks — has a property pure classification lacks: it **separates by behavior rather than by prediction**. A stolen-card fraudster usually can't complete the cardholder's bank challenge; a legitimate customer usually can. The decision outsources its own resolution to the one party who knows the truth. The engineering economics: friction costs *abandonment* — some legitimate customers quit rather than complete the challenge — so it slots into post 4's expected-cost frame as a middle outcome whose cost (abandonment rate × order value, per segment) sits between approve's risk and decline's certainty. Design consequences follow: friction is a **band, not a point** (scores too risky to approve clean, not risky enough to decline — challenge them); the band's edges move with the same cost logic as every threshold; and **liability shift** (3DS moving chargeback liability to the issuer) changes the FN cost side of the equation, which is why 3DS-where-available bends the whole ladder. One regulatory note: in some markets strong customer authentication is mandated with exemption regimes, turning friction placement partly into a compliance calculation — [RegTech](/blog/series/regtech-compliance-as-engineering/) territory meeting post 4's economics.

## Review queues: precision by the hour

Manual review deploys expensive, high-precision judgment against the cases models can't settle. Running it well is queue operations:

- **Queue economics drive everything.** Capacity is reviewers × cases/hour; post 4's precision-at-capacity metric exists precisely because sending more cases than capacity just converts review into delayed auto-decisions. The routing question is always: which cases *most reward* human attention — highest expected-cost ambiguity, not highest score.
- **Triage by value and risk.** High-amount ambiguity goes to senior reviewers with SLAs measured in minutes (the customer is waiting — post 8's latency story has a human chapter); low-value ambiguity often shouldn't be reviewed at all (the review cost exceeds the expected loss — approve it and let the label arrive).
- **Tooling is precision.** A reviewer's accuracy is a function of what they see: the case, the entity histories (post 3's profiles), the graph neighborhood, the model's top contributing signals (post 8's explainability serving its internal audience), similar past cases and their outcomes. Reviewer tooling is the feature store wearing a UI.
- **Measure reviewers like models.** Agreement rates, decision latency, outcome-confirmed precision per reviewer — with calibration sessions where reviewers decide pre-labeled cases. Not surveillance; quality control for a classifier that happens to be human, including its known failure modes (fatigue, anchoring on the model's score — which is why some fraction of cases should be reviewed score-blind).

## The dual mandate: decisions now, labels forever

Post 5 flagged it; here it becomes design: every review verdict is a **high-quality label** weeks ahead of chargeback truth, and the queue is the only place the system can *ask* for ground truth on cases it chooses. That choice is active learning in production: reserve a slice of capacity for **information-value sampling** — champion-challenger disagreements (post 6), drift-suspicious regions, the exploration borderlands of post 5 — alongside the expected-cost routing. The tension is real (capacity spent on learning is capacity not spent on the riskiest cases) and belongs in the open: a declared split (say, 80% decision-value, 20% label-value) reviewed like any budget. Teams that treat the queue purely as a decision backstop starve their own models; teams that design the dual mandate get a labeling engine the adversary can't poison cheaply.

The takeaway: the human layer adds the third answer and the truth supply — **friction** as behavior-based separation (a band in the cost ladder, priced by abandonment, bent by liability shift and SCA mandates), **review queues** run as operations (capacity-driven routing by expected-cost ambiguity, value-tiered SLAs, tooling that surfaces features and history, reviewers measured and calibrated like models), and the **dual mandate** made explicit — a declared capacity split between deciding today's hardest cases and labeling tomorrow's training data. Humans aren't the fallback for the model; they're components with distinct superpowers, deployed where those superpowers pay.

## Key takeaways

- **Friction separates by behavior**: fraudsters abandon challenges, customers clear them — a middle band priced by abandonment cost, with 3DS liability shift and SCA mandates bending the ladder's economics.
- **Queues are operations**: route by expected-cost ambiguity within capacity (excess volume = delayed auto-decisions), tier SLAs by value, skip review where its cost exceeds expected loss.
- **Tooling and measurement make precision**: profiles, graphs, contributing signals, similar cases in the UI; reviewers get agreement/latency/outcome metrics, calibration sessions, and score-blind samples against anchoring.
- **Design the dual mandate**: review verdicts are the system's freshest labels — reserve a declared capacity slice for information-value sampling (disagreements, drift regions, exploration) or starve the models.

## Further reading

- [3-D Secure — the step-up protocol that moves both behavior and liability](https://en.wikipedia.org/wiki/3-D_Secure)
- [Active learning (machine learning) — choosing which cases to pay for labels on](https://en.wikipedia.org/wiki/Active_learning_(machine_learning))
