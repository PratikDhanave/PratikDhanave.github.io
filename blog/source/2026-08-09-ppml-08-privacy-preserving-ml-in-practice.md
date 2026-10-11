# Privacy-Preserving ML in Practice — Choosing and Combining the Tools

*Four techniques, each protecting against a different threat, each with real costs — how do you actually decide what to use? Privacy-preserving machine learning in practice isn't about picking one silver bullet; it's about understanding your threat model and composing the right techniques to meet it. This closing post is the decision framework the series was building toward: match the tool to the threat, pay the trade-offs honestly, and combine for defense in depth.*

Posts 1–7 built the toolkit: differential privacy, federated learning, secure computation, and synthetic/anonymized data. This post assembles them into practical judgment — when to reach for which, how they combine, and how to think about the privacy-utility trade-off that runs through all of them. It's where the series becomes something you can apply.

## Start with the threat model, not the technique

The first and most important move is to stop asking "which privacy technique should I use?" and start asking "**what exactly am I protecting, from whom, at what stage?**" Each technique in this series answers a *different* threat, and using the wrong one is wasted effort:

- **Threat: the released model leaks its training data** (membership inference, extraction — post 2). → **Differential privacy** (DP-SGD, posts 3–4) bounds what the model can reveal about any individual.
- **Threat: centralizing the data is itself the risk** (a breach honeypot, a regulation against pooling, data that can't leave a device/organization). → **Federated learning** (post 5) keeps data where it lives.
- **Threat: the party doing the computation shouldn't see the data** (an untrusted cloud, mutually-distrusting organizations). → **Secure computation / homomorphic encryption** (post 6) computes on data that stays encrypted/hidden.
- **Threat: you need to share a dataset** with a less-trusted party. → **Synthetic data / anonymization** (post 7), ideally with a differential-privacy guarantee.

Naming the threat precisely tells you the technique. Most privacy mistakes come from protecting the wrong stage — e.g. carefully securing the data pipeline (encryption at rest) while shipping a model that leaks the data (needed DP), or "anonymizing" a dataset that's re-identifiable (needed DP-synthetic). The threat model is the map; the techniques are just the routes.

## Combine for defense in depth

The techniques are **complementary, not competing**, and serious systems layer them — each closing a gap the others leave (the recurring lesson of the series):

- **Federated learning + differential privacy** — don't centralize the data (FL) *and* bound what the shared model/updates reveal about individuals (DP). This is the canonical combination for learning across decentralized sensitive data (phones, hospitals), because FL alone leaks through updates (post 5) and DP alone doesn't address centralization.
- **Federated learning + secure aggregation (SMPC)** — the server sees only aggregated updates, never individual ones (post 6), closing FL's adversarial-server gap; widely deployed in cross-device settings.
- **The full stack** — federated learning (architecture) + secure aggregation (cryptographic) + differential privacy (formal) composes all three, protecting data in transit, in use, and in the output simultaneously. This is roughly what the most privacy-serious large-scale systems run.
- **Synthetic data + differential privacy** — a shareable artifact (post 7) with a provable guarantee (posts 3–4), rather than fragile bare anonymization.

The principle is **defense in depth**: because every single technique leaves *some* gap (post 7's unifying lesson — none is "automatically private"), real privacy comes from composing techniques so that each threat is covered and no single failure exposes the data. And one technique has a special anchoring role: **differential privacy is the only one offering a formal, provable, future-proof guarantee**, so where it's feasible it should be the backbone, with the others (federated learning, secure computation, synthetic data) addressing threats DP doesn't — centralization, in-use exposure, shareability. Build around the provable guarantee, not around what feels safe.

## The trade-offs are real — budget for them

Privacy is never free, and honest practice means pricing the costs rather than pretending they don't exist:

- **Accuracy** — differential privacy's noise reduces model accuracy (post 4), most on small datasets and under-represented groups (a privacy-fairness tension to watch and measure, not ignore).
- **Performance** — homomorphic encryption and SMPC are orders of magnitude slower / communication-heavy (post 6); DP-SGD adds per-example overhead; federated learning adds coordination and communication cost (post 5). These shape what's feasible at your scale and latency.
- **Complexity** — all of these are harder to build and operate than plain centralized training; federated and cryptographic systems especially demand real distributed-systems and security expertise.
- **The persistent privacy-utility trade-off** — the through-line of the series: more privacy generally means less utility (accuracy, speed, or simplicity), and you *choose where to sit* on that curve for your context. The goal isn't maximum privacy or maximum utility but the *right, deliberate, defensible point* — and with differential privacy, a *provable* one (a stated ε).

The practical discipline: decide how much privacy you *need* (driven by the sensitivity of the data, the threat model, and regulation), how much utility you can *spare*, and buy exactly that — explicitly, measured, and documented. Over-engineering privacy can kill a model's usefulness; under-engineering it can leak real people's data. Both are failures.

## The series in one frame

Privacy-preserving ML resolves the dilemma of post 1 — learn from sensitive data without exposing it — and the series reduces to a few durable ideas:
- **The naive protections fail** (anonymization → re-identification; aggregation/synthetic → memorization; securing data ≠ securing the model). Privacy ≠ security ≠ anonymity.
- **Models leak** (post 2): a model trained on sensitive data *is* sensitive data, attackable through normal access — so privacy must be engineered, not hoped.
- **Four complementary techniques**, each for a different threat: differential privacy (output), federated learning (centralization), secure computation (in-use), synthetic/anonymization (sharing).
- **Differential privacy is the anchor** — the only formal, provable, composable, future-proof guarantee — and the others cover what it doesn't.
- **Compose for defense in depth, match to the threat model, and pay the privacy-utility trade-off deliberately.**

The deepest takeaway is a mindset: privacy is an *engineered property with guarantees and costs*, matched to a *specific threat model*, composed for *defense in depth* — not a checkbox, not a promise, and never a single technique assumed to be "automatically private." Hold that, and you can build systems that learn from the world's most sensitive data while genuinely protecting the people in it — which is, increasingly, the only acceptable way to build with data at all.

The throughline: effective privacy-preserving ML starts not with a technique but with the **threat model** — *what are you protecting, from whom, at what stage?* — which maps directly to a tool: **differential privacy** (released model leaks training data), **federated learning** (centralization is the risk), **secure computation/HE** (the computing party mustn't see the data), **synthetic/anonymized data** (sharing a dataset). The techniques are **complementary**, so real systems **compose** them for **defense in depth** (canonically **federated learning + DP**, or the full FL + secure-aggregation + DP stack), anchored by **differential privacy** as the only **formal, provable** guarantee with the others covering what it doesn't. The **trade-offs are real** (accuracy — worst for minorities; performance; complexity; the persistent **privacy-utility** curve), so decide how much privacy you *need* and utility you can *spare*, and buy exactly that — explicitly and measurably. The mindset: privacy as an **engineered, guaranteed, costed property matched to a threat model and composed in depth** — never a single technique assumed automatically private.

## Key takeaways

- **Start with the threat model**, not the technique: *what are you protecting, from whom, at what stage?* — which maps to the tool. **Model leaks training data** → **differential privacy**; **centralization is the risk** → **federated learning**; **computing party mustn't see data** → **secure computation/HE**; **need to share a dataset** → **synthetic/anonymized data (+ DP)**. Most mistakes protect the *wrong stage*.
- The techniques are **complementary, not competing** — **compose** them for **defense in depth**: **federated learning + DP** (don't centralize *and* bound leakage — the canonical pairing), **FL + secure aggregation** (hide individual updates), the full **FL + secure aggregation + DP** stack (protect data in transit, in use, and in output), **synthetic data + DP** (shareable *and* provable).
- **Differential privacy is the anchor** — the only **formal, provable, composable, future-proof** guarantee — so build around it where feasible, with federated learning, secure computation, and synthetic data covering the threats (centralization, in-use exposure, sharing) it doesn't.
- **The trade-offs are real and must be budgeted**: accuracy loss (worst on small data and **under-represented groups** — a privacy-fairness tension to measure), performance (HE/SMPC orders slower; FL/DP-SGD overhead), and complexity — the persistent **privacy-utility trade-off** where you choose a *deliberate, defensible* point (with DP, a *provable* ε).
- The series' mindset: privacy is an **engineered property with guarantees and costs, matched to a specific threat model and composed for defense in depth** — never a checkbox, a promise, or a single technique assumed "automatically private" — which is how you learn from the most sensitive data while genuinely protecting the people in it.

## Further reading

- [Differential privacy — the anchoring formal guarantee](https://en.wikipedia.org/wiki/Differential_privacy)
- [Federated learning — the decentralized-training technique in the stack](https://en.wikipedia.org/wiki/Federated_learning)
