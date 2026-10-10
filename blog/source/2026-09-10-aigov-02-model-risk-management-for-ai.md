# Model Risk Management for AI — Borrowing a Discipline That Works

*Banks have managed the risk of models being wrong for decades, under a formal discipline called model risk management. AI didn't invent the problem of a model that's confidently incorrect — it industrialized it. The good news is that a mature, battle-tested framework already exists, and adapting it to machine-learning and LLM systems is one of the highest-leverage moves in AI governance. This post is about treating "the model might be wrong" as a managed risk, not a hope.*

Post 1 built the operating model and named the registry as its foundational control. This post is about what you *do* with each registered system: manage its risk systematically. The frame comes from finance's **model risk management (MRM)** — the practice developed because a wrong trading or credit model can sink a bank — and it transfers remarkably well to AI, where a wrong model can deny a loan, misdiagnose, or hallucinate a fact a user acts on.

## What model risk is

**Model risk** is the risk of adverse outcomes from decisions based on a model that is incorrect or misused. It has two classic sources, both sharply present in AI:
- **The model is fundamentally wrong** — built on bad assumptions, trained on unrepresentative data, or simply not capturing reality. An LLM that hallucinates and a credit model trained on biased history are both this.
- **The model is used wrong** — applied outside the conditions it was validated for, trusted beyond its reliability, or fed inputs unlike its training distribution. A model that was fine for one population deployed on another is this.

Finance formalized managing this risk (the US regulatory touchstone is the Federal Reserve/OCC guidance **SR 11-7**), and its core principles are exactly what AI governance needs: *every model is an imperfect approximation, so its risk must be identified, measured, controlled, and independently validated across its whole life.* The insight AI teams often miss is that this is a solved organizational problem — you don't have to invent the discipline, you have to adapt it.

## The MRM lifecycle, adapted for AI

Model risk management runs a model through a governed lifecycle, and each stage maps cleanly onto an AI/ML system:

- **Development with documented assumptions.** The model is built with its purpose, data, assumptions, and limitations written down — this is what **model cards** (the conceptual series' topic) formalize for ML. The deliverable is a model whose intended use and known weaknesses are explicit, so misuse is detectable.
- **Independent validation.** Someone *other than the builder* checks the model before it's used: is it conceptually sound, does it perform on representative and edge-case data, is it robust, is it fair? Independence is the point — self-validation misses what the builder couldn't see. For AI this is rigorous evaluation (post 5) plus bias and robustness testing, done by the second line (post 1).
- **Approval tied to risk tier.** High-risk models clear a formal gate before deployment; low-risk ones follow a lighter path (post 1's tiering). Approval is a decision with an owner, recorded.
- **Ongoing monitoring.** A validated model degrades as the world shifts (drift, post 7), so risk is re-assessed continuously, not just at launch — the single biggest difference from one-time software QA.
- **Periodic revalidation and retirement.** Models are re-reviewed on a schedule proportional to risk, and *retired* when they're no longer sound — a lifecycle stage AI teams almost always forget, leaving stale models running unmanaged.

The reframe this buys: an AI model is not a feature you ship and forget, but a *risk position you hold and must continuously manage*. That mindset, imported from finance, is what turns ad-hoc "we tested it once" into governed assurance.

## What AI adds to classic model risk

Adapting MRM to AI isn't copy-paste — modern AI stresses the framework in specific ways that the operating model has to account for:

- **Opacity.** Deep models and LLMs are far less interpretable than a regression, so "validate the model's logic" becomes "validate its *behavior* empirically" — heavy reliance on evaluation, testing, and explainability techniques rather than reading the equations. Validation shifts from inspecting the model to interrogating its outputs.
- **Foundation models you didn't build.** When you use a third-party LLM, you can't validate its internals or training data, and the provider can change it under you. Model risk extends to *vendor/third-party risk*: what you can and can't know, contractual assurances, your own wrapping evaluation, and a plan for when the model changes.
- **Generative, open-ended output.** A classifier's errors are bounded; an LLM's output space is effectively infinite, so "is it wrong?" is fuzzier and the failure modes (hallucination, unsafe content, prompt injection) are new. Validation must include adversarial and safety testing, not just accuracy.
- **Scale and speed.** Organizations deploy many AI systems fast, so MRM has to be *proportionate and partly automated* (posts 4–5) or it becomes the bottleneck that teams route around — the same tiering discipline from post 1, applied so validation effort tracks risk.

The throughline: the problem of a model being confidently wrong is old and solved-ish, and AI governance should stand on that shoulder. **Model risk management** gives AI a proven lifecycle — documented development, *independent* validation, risk-tiered approval, ongoing monitoring, and revalidation/retirement — that reframes each AI system as a managed risk position rather than a shipped feature. AI then stresses the framework with opacity, un-inspectable foundation models, open-ended generation, and scale — which the operating model absorbs by validating *behavior* empirically, extending risk to vendors, adding safety/adversarial testing, and keeping effort proportionate to tier. Borrowing MRM is one of the highest-leverage moves available because it replaces invented process with a discipline that already works.

## Key takeaways

- **Model risk** is the risk of bad outcomes from a model that is **wrong** (bad assumptions/data, doesn't capture reality — e.g. hallucination, biased training) or **used wrong** (outside validated conditions, over-trusted, off-distribution inputs) — both acute in AI.
- Finance solved this as **model risk management (MRM)** (touchstone: **SR 11-7**): every model is an imperfect approximation, so its risk is **identified, measured, controlled, and independently validated** across its life — a *solved organizational problem* AI teams can adapt rather than reinvent.
- The MRM lifecycle maps onto AI: **documented development** (model cards), **independent validation** (someone other than the builder — rigorous eval + bias/robustness testing), **risk-tiered approval gates**, **ongoing monitoring** (models degrade — drift, post 7), and **periodic revalidation/retirement** (the stage AI teams forget, leaving stale models running).
- The reframe: an AI model is a **risk position you continuously manage**, not a feature you ship and forget — turning "we tested it once" into governed assurance.
- AI stresses the framework via **opacity** (validate *behavior* empirically, not the equations), **third-party foundation models** (extend to vendor risk — can't inspect internals, provider changes it), **open-ended generation** (add safety/adversarial testing), and **scale/speed** (keep validation proportionate and partly automated — posts 4–5 — or it becomes the bottleneck).

## Further reading

- [Model risk — the risk of decisions from an incorrect model](https://en.wikipedia.org/wiki/Model_risk)
- [Algorithmic accountability — responsibility for algorithmic decisions](https://en.wikipedia.org/wiki/Algorithmic_accountability)
