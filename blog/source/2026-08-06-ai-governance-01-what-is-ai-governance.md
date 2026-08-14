# What AI Governance Is

*A working definition of AI governance for engineers — what it means, how it differs from security and compliance, why you already own a slice of it, and the frameworks and lifecycle map that anchor the rest of this series.*

---

If you ship models, you have already done AI governance — you just may not have called it that. Every time you wrote down which dataset trained a model, gated a deploy behind an eval threshold, or added an alert for prediction drift, you produced a governance artifact. **AI governance** is the set of policies, roles, and controls an organization uses to make sure its AI systems are built and operated responsibly: that risks are identified, accountability is assigned, decisions are documented, and the whole thing can be inspected later. The word "governance" makes it sound like a boardroom activity, and part of it is. But a large part of it is engineering, because governance is only as real as the evidence behind it — and engineers produce most of that evidence.

This post opens an eight-part series aimed at engineers who want to do governance well without turning into policy writers. The theme throughout: **governance is the artifacts and controls you can show, not paperwork theater.** If a claim about your AI system can't be backed by something concrete — a model card, an eval report, a monitoring dashboard, an audit log — it isn't governance, it's a promise.

---

## Governance vs. security vs. compliance

These three words get used interchangeably, and conflating them leads to bad prioritization. They overlap, but they answer different questions.

**Governance** asks: *Should we build this, is it working as intended, and who is answerable for it?* It covers policy (what's allowed), accountability (who owns outcomes), risk management (what could go wrong and how bad), transparency (can we explain what the system does), and lifecycle oversight (are we watching the system from data to retirement). Governance is the umbrella.

**Security** asks: *Is the system protected from adversaries and misuse?* This is model theft, prompt injection, data poisoning, membership-inference attacks, jailbreaks, and the usual application-security surface around your inference stack. Security is a critical *input* to governance — you cannot claim a system is responsible if it's trivially exploitable — but it is its own discipline with its own techniques. This series treats security as a dependency and cross-references the separate AI Security series rather than re-deriving it.

**Compliance** asks: *Does the system meet a specific external requirement?* A regulation (the EU AI Act), a standard you've certified against (ISO/IEC 42001), a contractual clause, an internal policy. Compliance is narrower than governance: it's about satisfying named obligations and being able to prove it. Good governance usually produces compliance as a byproduct, because the same artifacts — documentation, risk assessments, evaluation records — are what an auditor or regulator asks to see.

Here's the relationship in one line: **governance is the practice, compliance is meeting specific rules within that practice, and security is one of the risk domains governance must cover.**

| Question it answers | Discipline | Typical engineering artifact |
|---|---|---|
| Should we build it, and is it working as intended? | Governance | Model card, risk register, eval report, monitoring dashboard |
| Is it protected from adversaries and misuse? | Security | Threat model, red-team results, access controls |
| Does it satisfy a named external rule? | Compliance | Conformity assessment, audit evidence pack, DPIA |

**The gotcha:** teams often buy a compliance checklist, tick the boxes, and believe they've "done governance." Compliance without governance is fragile — you pass the audit and still ship a biased model, because the checklist only covered what one regulation happened to name. Governance without compliance is incomplete — you're careful but can't prove it to a regulator. You want both, and they're built from the same underlying evidence.

---

## Why engineers own part of governance

There is a persistent myth that governance is a legal-and-policy function that happens somewhere else, and that engineers just receive requirements from it. That's backwards. Policy teams can write the rules, but they cannot produce the evidence that the rules are being followed. Only the people who build and run the system can do that. Concretely, engineers own:

- **Model and data documentation** — what data trained the model, what it's for, what it shouldn't be used for, known limitations. (Post 3 in this series.)
- **Evaluations and quality gates** — the tests a model must pass before and after deployment, wired into CI so they actually block bad releases. (Post 4.)
- **Fairness, bias, and explainability measurements** — the numbers that show whether the system treats groups equitably and whether its decisions can be explained. (Post 5.)
- **Monitoring and drift detection** — the runtime evidence that the model still behaves in production the way it did in evaluation. (Post 6.)
- **Audit trails** — the logs and versioned records that let someone reconstruct, months later, which model version made which decision on which input.

None of that is legal work. It's engineering work that *happens to be* the substance of governance. When a regulator, auditor, or incident review asks "how do you know this model is fair / accurate / safe?", the answer is a set of files and dashboards that engineers built. The policy team frames the question; engineering supplies the answer.

A useful mental model: treat governance evidence like you treat tests and observability. You don't write tests because a policy told you to — you write them because untested code is unsafe to ship. Governance artifacts are the same idea extended to model behavior, fairness, and provenance. If you already believe in CI and dashboards, you already believe in governance; you just need to point the same instincts at a wider set of risks.

---

## The frameworks this series uses

Four bodies of work anchor the field. You don't need to memorize them, but you should know what each is *for*, because the rest of the series maps onto them. Where a specific article or clause number matters for your situation, go read the primary text — these are high-level descriptions, not legal advice.

### NIST AI Risk Management Framework (AI RMF)

A voluntary framework published by the U.S. National Institute of Standards and Technology. It's not a law and it certifies nothing; it's a structured way to think about and reduce AI risk. Its core organizes work into four functions:

```text
GOVERN   — culture, roles, policies, accountability (cuts across the other three)
MAP      — establish context; identify where and how the system can cause harm
MEASURE  — analyze, assess, and track the identified risks (metrics, evals)
MANAGE   — prioritize and act on risks; allocate resources; respond and recover
```

The reason engineers like the AI RMF is that MEASURE and MANAGE are inherently technical — they're where your evals, fairness metrics, and monitoring live — while GOVERN and MAP give you the vocabulary to explain *why* those measurements exist. Post 2 uses this structure as the backbone for building a risk-management practice.

### EU AI Act

A regulation of the European Union — this one *is* law, and it applies based on whether your system touches the EU market, not on where your company sits. Its defining idea is a **risk tier**: obligations scale with how much harm a system can do.

- Some uses are **prohibited** outright.
- **High-risk** systems (think safety components, and uses in areas like employment, credit, or essential services) carry the heaviest obligations: risk management, data governance, technical documentation, logging, human oversight, and accuracy/robustness requirements.
- **Limited-risk** systems mainly carry transparency duties (e.g., telling people they're interacting with AI or that content is AI-generated).
- **Minimal-risk** systems are largely unconstrained.

The precise categories, thresholds, and timelines are detailed and phased in over time — treat the tiering above as the shape, and consult the official text and your legal team for whether a given system is "high-risk" and what exactly that entails. The engineering takeaway is that the Act's high-risk obligations map almost one-to-one onto the artifacts this series teaches: documentation, logging, evaluation, human oversight.

### ISO/IEC 42001

An international standard specifying an **AI management system (AIMS)** — a management-system standard in the same family as ISO/IEC 27001 for information security. Rather than dictating specific model techniques, it describes how an organization should establish, run, and continually improve a system for managing AI responsibly: leadership commitment, policies, roles, risk and impact assessment, operational controls, and improvement cycles. Because it's a certifiable standard, it's often how a company demonstrates governance maturity to customers and partners. Post 7 (building a governance program) leans on this framing.

### Responsible-AI principles

Beneath the frameworks sit a set of widely shared principles that keep recurring — expressed, for example, in the OECD AI Principles and echoed across many national and corporate guidelines. The common threads:

- **Fairness** — the system doesn't produce unjustified disparate outcomes across groups.
- **Transparency** — its purpose, data, and limitations are documented and, where relevant, its decisions are explainable.
- **Accountability** — a named human or team is answerable for outcomes.
- **Safety and robustness** — it performs reliably and fails gracefully, including under stress and misuse.
- **Privacy** — it respects data-protection obligations and minimizes exposure of personal data.

Principles alone don't ship anything — they're the *why*. The frameworks turn them into structure; your artifacts turn them into evidence.

---

## The AI lifecycle and where governance attaches

Governance isn't a phase you do at the end. It attaches at every stage of the lifecycle, and the artifact you owe changes as the system moves along it.

```text
DATA  →  MODEL / SELECTION  →  EVALUATION  →  DEPLOY  →  MONITOR  →  RETIRE
 │             │                   │            │          │           │
 └─ provenance └─ documented       └─ quality   └─ human   └─ drift    └─ decommission
    & consent     choice &            gates &      oversight  detection   record &
    (datasheet)   limitations         thresholds   & logging  & alerts    data disposal
```

- **Data** — Where did it come from, do you have the right to use it, what's in it, what's missing? The artifact is a dataset datasheet and a provenance/consent record.
- **Model / selection** — Whether you train or pick a foundation model, record what you chose and why, its intended use, and its known limitations. The artifact is a model card.
- **Evaluation** — Define what "good enough" means with concrete metrics — accuracy, fairness, robustness, safety — and record the results. The artifact is an eval report tied to a specific model version.
- **Deploy** — Gate the release on those eval results, and put humans in the loop where the risk tier demands it. The artifact is a passing quality gate plus an approval/oversight record.
- **Monitor** — Watch production for drift, degraded accuracy, and emerging harms. The artifact is a monitoring dashboard and alert history.
- **Retire** — When a model is decommissioned, record why, what replaced it, and how its data was handled. The artifact is a retirement record.

The unifying idea: **every lifecycle stage produces a durable artifact, and the collection of those artifacts *is* your governance posture.** A regulator's request, an incident post-mortem, and an internal audit all reduce to "show me the artifacts for this system across its lifecycle."

Here's a minimal, framework-agnostic way to represent that posture as a machine-readable inventory entry — the kind of record a governance program keeps for each system. It uses only plain YAML fields you define yourself; there's no special library or API here.

```yaml
# governance-inventory/credit-scoring-v3.yaml
system:
  name: credit-scoring
  version: "3.2.0"
  owner: risk-ml-team            # accountable team (accountability principle)
  risk_tier: high                # your mapping to EU AI Act-style tiers
lifecycle:
  data:
    datasheet: docs/datasheets/credit-2026Q2.md
    provenance_verified: true
  model:
    card: docs/model-cards/credit-scoring-v3.md
    intended_use: "Rank applicants by repayment likelihood"
    out_of_scope: ["employment screening", "insurance pricing"]
  evaluation:
    report: reports/eval/credit-scoring-v3.2.0.json
    passed_gate: true
    fairness_checked: true
  deployment:
    human_oversight: true        # required for high-risk decisions
    deployed_at: "2026-08-05T00:00:00Z"
  monitoring:
    dashboard: "https://dashboards.internal/credit-scoring"
    drift_alerts: enabled
  retirement:
    status: active               # active | scheduled | retired
```

You can lint a file like this in CI to enforce that no system reaches production without an owner, a risk tier, a model card, and a passing eval gate — turning governance policy into a check that fails the build. That's the whole ethos of this series: encode the policy as something executable.

**The gotcha:** the most common governance failure isn't a missing policy — it's artifacts that drift out of sync with reality. A model card that describes version 2 while version 3 is in production is worse than no model card, because it manufactures false confidence. Tie every artifact to a specific model version, regenerate it in the same pipeline that ships the model, and treat a stale artifact as a failing check, not a documentation nicety.

---

## The series map

Eight posts, each turning one slice of governance into engineering practice:

1. **What AI governance is** (this post) — definitions, distinctions, frameworks, lifecycle.
2. **Risk management with the NIST AI RMF** — turning Govern/Map/Measure/Manage into a working risk register.
3. **Model cards and documentation** — what to record about a model and how to generate it automatically.
4. **Evaluation and quality gates** — defining "good enough" and wiring it into CI so it blocks releases.
5. **Bias, fairness, and explainability** — measuring disparate impact and making decisions inspectable.
6. **Monitoring and drift** — proving in production that the model still behaves as evaluated.
7. **The regulatory landscape** — reading the EU AI Act, ISO/IEC 42001, and friends as an engineer, not a lawyer.
8. **Building a governance program** — assembling the artifacts, roles, and controls into a coherent, auditable system.

---

## Key takeaways

- **Governance is evidence, not paperwork.** A claim about your AI system counts only if you can show the artifact behind it — model card, eval report, dashboard, audit log.
- **Governance, security, and compliance are different questions.** Governance asks whether you should build it and whether it works; security protects it from adversaries; compliance meets named external rules. You need all three, and they share the same evidence.
- **Engineers own a real slice of governance.** Documentation, evals, fairness metrics, monitoring, and audit trails are engineering deliverables that happen to be the substance of governance.
- **The frameworks are complementary.** NIST AI RMF gives you a risk process, the EU AI Act sets legal obligations by risk tier, ISO/IEC 42001 structures the management system, and responsible-AI principles supply the *why*.
- **Governance attaches at every lifecycle stage.** Data, model, eval, deploy, monitor, retire — each owes a durable, version-tied artifact, and the collection is your governance posture.

Treat the rest of this series as a way to make governance executable: policy you can lint, thresholds that fail the build, documentation the pipeline regenerates. Governance done this way isn't overhead on top of engineering — it's engineering pointed at a wider definition of "working."

---

## Further reading

- [NIST AI Risk Management Framework (AI RMF 1.0)](https://www.nist.gov/itl/ai-risk-management-framework) — the Govern/Map/Measure/Manage framework and its companion playbook.
- [EU AI Act — regulatory framework (European Commission)](https://digital-strategy.ec.europa.eu/en/policies/regulatory-framework-ai) — the risk-tiered regulation; see also the [EUR-Lex legal text](https://eur-lex.europa.eu/eli/reg/2024/1689/oj) for the authoritative wording.
- [ISO/IEC 42001 — AI management system standard](https://www.iso.org/standard/81230.html) — the certifiable AIMS standard.
- [OECD AI Principles](https://oecd.ai/en/ai-principles) — the widely referenced responsible-AI principles.
- [Model Cards for Model Reporting (Mitchell et al., 2019)](https://arxiv.org/abs/1810.03993) — the original model-card proposal.
- [Datasheets for Datasets (Gebru et al., 2018)](https://arxiv.org/abs/1803.09010) — the dataset-documentation proposal referenced throughout this series.
