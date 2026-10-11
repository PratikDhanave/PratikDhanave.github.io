# Federated Learning — Training Without Centralizing the Data

*The most direct way to protect data is to never move it. Federated learning trains a shared model across many devices or organizations without their data ever leaving home — the model travels to the data, learns locally, and only the lessons (not the data) come back. It's how your phone's keyboard improves without uploading what you type, and how hospitals can build a shared model without sharing patient records. This post is about learning from data you're never allowed to see.*

Post 4 kept data centralized but made the *model* private. Federated learning takes the opposite tack from post 1's toolkit: **don't centralize the data at all.** It's an architectural privacy technique rather than a mathematical one, and it addresses a different threat — data movement and pooling — making it complementary to differential privacy. This post explains how it works and, honestly, what it does and doesn't protect.

## The inversion: move the model, not the data

Normal ML collects all data into one place and trains there. **Federated learning** inverts this: the data stays where it is — on users' phones, in separate hospitals, across different companies — and the training comes to it. The loop:

1. A central server sends the **current model** to each participant (device or organization).
2. Each participant **trains locally** on its own data, computing an update (improved parameters) — its data never leaves.
3. Participants send only their **model updates** back to the server (not their data).
4. The server **aggregates** the updates (e.g. averages them — "federated averaging") into an improved global model.
5. Repeat, so the global model learns from everyone's data without any of it being collected.

The result is a model trained on the *collective* data of all participants, while each participant's raw data never moved. Two flagship uses show the range:
- **Cross-device** — millions of phones collaboratively improving a keyboard, speech, or suggestion model. Your typing improves the shared model via on-device training; what you typed never uploads. This is federated learning's famous origin.
- **Cross-silo** — a handful of organizations (hospitals, banks) jointly training a model none could build alone, without pooling their regulated data. Each keeps its records; the shared model benefits from all of them. This is often the higher-value case, because it unlocks collaboration that regulation otherwise forbids.

The core value is unambiguous: **data minimization by architecture.** The data isn't protected by a promise or a policy; it's protected because it was never collected. That structural guarantee is federated learning's distinctive offer, and it directly satisfies regulations and user expectations that oppose data pooling.

## What federated learning doesn't solve

Here's the crucial, often-missed point: **federated learning alone is not full privacy.** It protects the raw data from being centralized, but the *model updates* participants send back can themselves leak information about the local data — because, as post 2 established, gradients and model updates carry information about the examples that produced them. An adversarial server (or anyone who sees the updates) can potentially infer things about a participant's data from its update, including membership and, in some cases, reconstructed examples. The data stayed home, but its *shadow* in the updates traveled.

So federated learning is necessary-but-not-sufficient for strong privacy, and it's almost always *combined* with the other techniques in this series:
- **+ Differential privacy** (posts 3–4) — add noise to the updates (or apply DP locally) so each participant's update provably reveals little about their data. This is the most important combination: **federated learning + DP** gives both "data never centralizes" *and* "the updates can't leak individuals," and it's the standard for serious deployments.
- **+ Secure aggregation** (a form of secure computation, post 6) — cryptographically combine updates so the server only ever sees the *aggregate*, never any individual participant's update. This closes the "adversarial server reads your update" hole directly, and it's widely used in cross-device federated learning.

The lesson that matters: *federated learning changes the threat model, it doesn't eliminate the threat.* It removes the risk of centralized data (a huge win — no honeypot to breach, no pooling to regulate) but introduces the risk of leaky updates, which the other techniques must then close. Treating federated learning as "automatically private" is a real and common mistake.

## The practical trade-offs

Federated learning is powerful but genuinely harder to operate than centralized training, and the costs shape where it fits:

- **Systems complexity.** Coordinating training across millions of unreliable devices (that drop off, have limited compute and battery, and vary wildly) or across organizations with different infrastructure is a hard distributed-systems problem. It's far more operationally complex than training on one cluster.
- **Non-IID data.** Each participant's data is *not* a random sample of the whole — your phone's data reflects *you*, each hospital's reflects its population. This "non-IID" (not independent and identically distributed) data makes training harder and the global model potentially unfair to under-represented participants, requiring careful aggregation.
- **Communication cost.** Repeatedly sending models and updates over networks (especially to constrained devices) is expensive, so federated learning works to minimize rounds and compress updates.
- **Weaker server-side guarantees and new attack surface.** A malicious participant can try to *poison* the global model with bad updates, so federated systems need robustness against adversarial participants — a threat centralized training doesn't have.

Given this, federated learning is the right tool when **data genuinely cannot or should not be centralized** — strict regulation, user-device data, cross-organization collaboration on sensitive data — and the architectural guarantee justifies the operational cost. When data *can* be centralized safely, centralized training with differential privacy is often simpler. And in the biggest deployments, the answer is the combination: federated learning for the architectural guarantee, differential privacy for the formal one, and secure aggregation for the server-trust one — three of this series' techniques composed into a system that learns from data no one is allowed to see.

The throughline: **federated learning** protects data by **never moving it** — the server sends the model to participants, each **trains locally** on data that never leaves, and only **model updates** come back to be **aggregated** into a shared model (cross-device: millions of phones; cross-silo: hospitals/banks collaborating on regulated data they can't pool). Its distinctive offer is **data minimization by architecture** — the data is safe because it was never collected. But it is **not full privacy alone**: the **updates themselves leak** information (gradients carry data, post 2), so it's combined with **differential privacy** (noise the updates — the key pairing) and **secure aggregation** (server sees only the aggregate). It changes the threat model (removes the centralized honeypot) rather than eliminating the threat, and carries real costs — **systems complexity**, **non-IID data** (fairness risk), **communication cost**, and **poisoning** by malicious participants — so use it when data genuinely can't be centralized, ideally composed with the series' other techniques.

## Key takeaways

- **Federated learning** inverts normal ML: the data stays put (on devices/in organizations) and the *model* travels — server sends the model → participants **train locally** (data never leaves) → send back only **updates** → server **aggregates** (federated averaging) → repeat — producing a model trained on everyone's data without collecting any of it.
- Its value is **data minimization by architecture**: data is protected because it was **never centralized**, not because of a policy — enabling **cross-device** (phone keyboards) and high-value **cross-silo** (hospitals/banks jointly training on regulated data they can't pool) use.
- **Federated learning alone is not full privacy**: the **model updates leak** information about local data (gradients carry it, post 2), so an adversarial server can infer membership or reconstruct examples — the data stayed home but its *shadow* in the updates traveled.
- It's therefore **combined** with other techniques: **+ differential privacy** (noise the updates so they provably reveal little — the key pairing, "data never centralizes" *and* "updates can't leak individuals") and **+ secure aggregation** (server sees only the aggregate, not individual updates).
- Real **costs**: **systems complexity** (coordinating unreliable/constrained devices or heterogeneous orgs), **non-IID data** (each participant unrepresentative → harder training, fairness risk), **communication cost**, and **poisoning** by malicious participants — so use it when data genuinely can't be centralized, ideally composing federated learning + DP + secure aggregation.

## Further reading

- [Federated learning — training across decentralized data](https://en.wikipedia.org/wiki/Federated_learning)
- [Differential privacy — the formal guarantee paired with federated learning](https://en.wikipedia.org/wiki/Differential_privacy)
