# Evaluation Gates and Evidence — Proving Governance Happened

*Two questions separate real AI governance from theater: can you stop a model that fails its checks from reaching production, and can you prove, after the fact, that the checks were done? The first is an evaluation gate; the second is evidence. Together they turn governance from a set of good intentions into something enforceable and auditable. This post is about the mechanics of gating AI systems on quality and automatically capturing the proof that it happened.*

Post 4 made policy executable; this post makes it *provable*. The two ideas are joined: a gate is where a policy blocks a bad deployment, and evidence is the durable record that the gate ran and what it decided. The driving insight is that governance you can't enforce is a suggestion, and governance you can't prove is unauditable — and regulators, auditors, and incident reviews all eventually ask for the proof.

## The evaluation gate: governance that can say no

An **evaluation gate** is a checkpoint in the AI lifecycle where a system must pass defined quality and safety criteria before it can proceed — to deployment, or to use at a given risk tier. It's the concrete form of post 1's "lifecycle gates" and post 4's "deployment gates," and it's where governance gets the power to *stop* something:

- **It's tied to real decision points.** The gate sits at deploy time (and at promotion from one environment to the next), so review happens *before* harm, not after. For high-risk systems (post 6) there may be gates to even begin development or to go live.
- **It checks defined, measurable criteria** — passing evaluation on the governed eval set (the LLMOps series' core asset), bias/fairness thresholds met, required documentation (model card) complete, security and privacy checks passed, approvals obtained for the risk tier. The criteria are explicit so "pass" is objective, not a vibe.
- **It can block.** The defining property: a system that fails a required criterion does not proceed — the gate fails closed (post 4). A gate that can only *warn* is not a gate; it's a notification that gets ignored. The authority to say "no, this doesn't ship" is what makes governance real.
- **It scales by tier.** A low-risk system passes a light gate automatically; a high-risk one triggers heavier checks and human sign-off (post 1's proportionality), so the gate is strict where it matters and frictionless where it doesn't.

The cultural point is that the gate must have *teeth* and *legitimacy*: teams have to know a failing gate genuinely blocks, and the criteria have to be reasonable enough that gating is respected rather than resented and routed around. A gate that's always overridden is worse than none, because it manufactures false assurance.

## Evidence: proving the gate ran

Passing a gate is worthless to an auditor if you can't *show* it happened. **Evidence** (the audit trail of governance) is the durable, tamper-resistant record of what was checked, when, by what/whom, and with what result — generated automatically as a byproduct of the gates and controls running. This is the part teams most often neglect and most regret neglecting:

- **Why it matters.** Regulators increasingly *require* demonstrable governance (post 6's EU AI Act mandates documentation and record-keeping for high-risk systems); auditors (post 1's third line) need to verify controls were followed; and when an incident happens, the evidence is how you reconstruct what the governance process did and didn't catch. "We're confident we tested it" is not evidence; the recorded eval run, with its inputs, version, and results, is.
- **What to capture.** For each governed system and each gate: which model/prompt version (tie to the registry and version control), what evaluations and bias checks ran and their results, which policies were evaluated and their allow/deny outcomes (post 4), who approved and when, and the model card and risk assessment as of that decision. Link it all to the specific deployed version so the record answers "what governance applied to *this* thing in production?"
- **How to capture it — automatically.** Evidence generated as a manual afterthought is incomplete and gameable; evidence emitted *automatically* by the gates and pipelines as they run is complete and trustworthy. This is the governance-as-code payoff (post 4): because the checks are executable, their execution *is* the evidence — every gate run logs its decision and inputs to an immutable store. Governance that runs as code produces its own audit trail for free.

The reframe: evidence isn't bureaucratic overhead you bolt on for auditors — it's the automatic exhaust of a governance system that actually runs, and if you can't produce it, that's a sign the governance isn't really running.

## Gates + evidence in the lifecycle

Putting it together, gates and evidence instrument the whole AI lifecycle so governance is both enforced and provable at every stage:
- **At registration** (post 1): a new system gets an entry, an owner, and a risk tier — recorded.
- **At development/validation** (post 2): required evaluations, model card, and independent validation run — results captured as evidence.
- **At the deploy gate** (post 4): policies evaluated, criteria checked, tier-appropriate approvals obtained — the system proceeds only if it passes, and the decision is recorded.
- **In production** (post 7): ongoing monitoring results and incidents are logged, so the evidence record stays live, not frozen at launch.

The result is a system where, for any AI in production, you can answer both governance questions with confidence: *was it allowed to ship (and could it have been stopped)?* and *can we prove what was checked?* That combination — enforceable gates plus automatic evidence — is what separates governance that holds up under regulatory, audit, and incident scrutiny from governance that only looks good on a slide.

The takeaway: real governance requires two things — the power to **stop** a failing system and the ability to **prove** the checks happened. An **evaluation gate** is a lifecycle checkpoint (at deploy/promotion, tier-scaled) that tests **defined, measurable criteria** (passing eval on the governed set, bias thresholds, complete model card, security/privacy, tier approvals) and **fails closed** — a gate that can only warn isn't a gate — and it needs both *teeth* (it genuinely blocks) and *legitimacy* (reasonable enough to be respected, not routed around). **Evidence** is the automatic, durable audit trail of what was checked, when, by whom, and with what result, tied to the specific deployed version — required by regulators (post 6) and auditors (post 1), and essential for incident reconstruction. The key is that **governance-as-code produces evidence for free**: because checks execute, their execution *is* the record. Instrument the whole lifecycle (registration → validation → deploy gate → production monitoring) so that for any AI in production you can prove both that it was allowed to ship and what was checked.

## Key takeaways

- Two questions separate governance from theater: can you **stop** a model that fails its checks, and can you **prove** the checks were done? Gates answer the first, evidence the second.
- An **evaluation gate** is a lifecycle checkpoint (deploy/promotion time, scaled by risk tier) that tests **defined, measurable criteria** — passing eval on the governed set, bias/fairness thresholds, complete model card, security/privacy, tier-appropriate approvals — and its defining property is that it **fails closed** (a gate that only warns is just an ignored notification).
- Gates need **teeth** (genuinely block) *and* **legitimacy** (criteria reasonable enough to be respected) — an always-overridden gate is worse than none because it manufactures false assurance.
- **Evidence** is the durable, tamper-resistant audit trail — which model/prompt version, which evals/bias checks and results, which policy allow/deny outcomes, who approved when, the model card/risk assessment — linked to the specific deployed version; required by regulators (EU AI Act, post 6) and auditors (post 1), and the only way to reconstruct an incident.
- **Governance-as-code produces evidence automatically** (post 4): because checks execute, their execution *is* the record — so instrument the whole lifecycle (registration → validation → deploy gate → production monitoring) and you can always answer "was it allowed to ship?" and "can we prove what was checked?"

## Further reading

- [Audit trail — the durable record of what happened](https://en.wikipedia.org/wiki/Audit_trail)
- [Algorithmic accountability — demonstrating responsible algorithmic decisions](https://en.wikipedia.org/wiki/Algorithmic_accountability)
