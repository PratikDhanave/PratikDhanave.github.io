# The Label Problem — Delay, Noise, and the Data Your Own Decisions Hide

*Supervised learning assumes someone hands you the truth. In fraud, the truth arrives 30 to 90 days late, labeled by processes with their own agendas, for only the transactions you approved — and silence means nothing, because unreported fraud and un-disputed legitimate purchases are indistinguishable until they aren't. Label engineering is the least glamorous layer of a fraud system and the one that decides whether everything upstream learns reality or a convenient fiction.*

Post [1](/blog/posts/fraud-01-the-fraud-problem.html) named the three pathologies — delay, noise, censoring; this post is the engineering that handles each honestly, because post 6's retraining loop is only as good as the labels this layer feeds it.

## Delay: training on a moving horizon

The primary fraud label is the chargeback, and its timeline is contractual, not technical: cardholders dispute on statement cycles, issuers process on their own clocks, and the window stretches months. Three disciplines handle it:

- **Maturity-aware training sets.** A transaction can only be labeled "legitimate" once enough time has passed for a dispute to have arrived — so training data has a *maturity horizon*: recent transactions are excluded or handled as unlabeled, not presumed good. Teams that train on last week's "clean" data are training on fraud-not-yet-reported and teaching the model that fresh fraud patterns are legitimate.
- **Label versioning over time.** A label isn't an event; it's a *state that updates* — approved → presumed-good → disputed → resolved-fraud (or resolved-friendly). The label store keeps the trajectory with timestamps (the same event-time discipline as the feature store in post 3 — as-of label joins matter for honest backtesting too).
- **Early proxies, weighted honestly.** Waiting 90 days for every label concedes months to the adversary (post 6's problem), so systems use early signals — issuer fraud alerts (days, not months), customer reports, manual-review verdicts (post 7's queue is also a labeling machine, and that dual role should be designed, not incidental) — as provisional labels with lower weight, later reconciled against the mature truth.

## Noise: labels that lie a little

Chargebacks are imperfect truth in both directions. **Friendly fraud** — a genuine cardholder disputing a purchase they made (regret, confusion, family members) — stamps "fraud" on transactions whose features are entirely legitimate, teaching the model to find fraud signal in ordinary behavior. **Unreported fraud** — small amounts unnoticed, victims who never check — leaves true fraud labeled good. The engineering responses: model the *label source* (a dispute coded "fraudulent" vs "product not received" vs "unrecognized" carries different reliability; review-queue verdicts differ from automated alerts — keep the provenance, weight accordingly); let **dispute outcomes** refine labels (a merchant-won dispute reverses the fraud label — another state transition for the label store); and accept that some noise floor is irreducible, which is an argument for robust training practices and against chasing the last decimal of offline metrics that the labels can't support anyway (post 4's metrics inherit this noise).

## Censoring: the data your declines destroyed

The selective-labels problem is the deepest: declined transactions get no outcome, so observed data is filtered *by the current system's own judgment*. The consequences compound — models evaluated on approved-only traffic look better than they are (the hardest cases were removed by the incumbent); new models trained on it inherit the incumbent's blind spots; and regions of feature space the system declines hardest become permanently unlearnable without intervention. The honest mitigations all spend money to buy sight, which is why they need the business sponsorship post 4's cost framework provides: **exploration traffic** — approve a small, randomized, bounded slice of would-be declines (with amount caps) to observe true outcomes; this is the only ground-truth window into the declined region, and its fraud losses are correctly booked as *data acquisition cost*; **counterfactual weighting** — use the exploration slice (or historical policy variation) to reweight training and evaluation toward the full-traffic distribution rather than the approved-only one; and **decline-region monitoring** — at minimum, track how much of the declined population the current model has never observed outcomes for, so the blindness is measured even where it isn't yet paid for. Teams that skip this entirely aren't avoiding the cost — they're paying it invisibly, in blocked legitimate customers no metric ever counts.

The takeaway: labels are an engineered pipeline, not a given — **maturity horizons** (never presume recent silence is legitimacy) with labels as versioned state trajectories and early proxies weighted then reconciled; **noise handled by provenance** (friendly fraud and dispute codes weighted by source, outcomes refining labels, an irreducible floor accepted); and **censoring confronted with bought data** — bounded exploration of would-be declines booked as data acquisition, counterfactual reweighting, and measured blindness. Everything the system learns passes through this layer; its honesty is the model's ceiling.

## Key takeaways

- **Maturity horizons**: a transaction is only "legitimate" after the dispute window; labels are **state trajectories with timestamps** (as-of joins for honest backtests); early proxies (issuer alerts, review verdicts) carry weight, not certainty.
- **Label noise is structured**: friendly fraud poisons the positive class, unreported fraud the negative; keep **provenance** and weight by source; dispute outcomes update labels; accept the floor instead of chasing decimals it can't support.
- **Selective labels**: declines produce no outcomes — approved-only data flatters evaluation and inherits the incumbent's blind spots.
- Buy sight deliberately: **bounded exploration approvals** as explicit data-acquisition cost, counterfactual reweighting, and measured never-observed regions — the invisible alternative is paying in blocked good customers forever.
- The review queue (post 7) is also a **labeling machine** — design its dual role.

## Further reading

- [Chargeback — the delayed, imperfect primary label](https://en.wikipedia.org/wiki/Chargeback)
- [Selection bias — the statistical trap your own decisions create](https://en.wikipedia.org/wiki/Selection_bias)
