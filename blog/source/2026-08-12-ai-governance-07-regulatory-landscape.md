# The AI Regulatory Landscape

*How an engineer should read AI regulation without a law degree — what the EU AI Act, ISO/IEC 42001, the NIST AI RMF, and sector rules actually ask for, and how each obligation maps to a control or artifact your pipeline can already produce.*

---

If you build or ship AI systems, "the regulation" can feel like a wall of statutes written for someone else. It is not. Most of what regulators ask for translates into engineering work you either already do or should be doing: classify the risk, manage it, document the system, log what it does, keep a human in the loop where the stakes are high, and be able to *show* all of that on request. This post is an orientation map — not legal advice — for turning the regulatory landscape into a control set.

One framing to carry through the whole post: **regulation is satisfied with evidence.** A regulator or auditor rarely wants to read your code. They want proof that you identified the risks, put controls in place, and kept records. The risk register, model and system cards, evaluation results, monitors, and audit logs from earlier posts in this series *are* your compliance deliverables. The engineering job is to generate that evidence as a byproduct of building the system, not to reconstruct it under deadline.

**A hard boundary before we start:** this is not legal advice. Engineers produce evidence; counsel interprets obligations. Where I mention a specific mechanism, treat it as "the kind of thing the law asks for" and confirm the exact wording, thresholds, and article numbers against the primary text with your legal team. The landscape also moves fast — dates, delegated acts, and guidance shift — so anchor decisions on current official sources.

---

## Determine your risk tier first — it sets the burden

The single most important early decision is *how risky your use case is*, because that determines how much you have to do. The EU AI Act is the clearest example of this pattern: it is **risk-tiered**, applying heavier obligations to higher-risk uses rather than a flat rule for all AI. At a high level the tiers run:

- **Unacceptable risk (prohibited).** A small set of uses the law bans outright — the kind of practices considered incompatible with fundamental rights. If your use case is here, no amount of documentation makes it compliant; the answer is don't build it.
- **High risk.** Uses in sensitive domains (think safety components, and systems affecting access to things like employment, education, essential services, or law-enforcement contexts) carry the bulk of the obligations. This is where risk management, data governance, documentation, logging, human oversight, and robustness requirements concentrate.
- **Limited risk (transparency).** Systems that interact with people or generate content carry transparency duties — for example, letting people know they are dealing with an AI system or that content was AI-generated.
- **Minimal risk.** The large remainder, where the law imposes little to nothing beyond good practice.

On top of the tiers, the Act sets separate obligations for **general-purpose AI models** — the large foundation models used across many applications — with additional duties for the most capable ones. If you fine-tune, host, or deploy such a model, some of those obligations may reach you.

**The gotcha:** your risk tier sets everything downstream, so misclassifying a high-risk use case as low-risk is the expensive mistake. It is tempting to argue your way into a lighter tier, but a wrong classification means you skip controls you were required to have, and that surfaces at the worst possible time — an incident, an audit, or a procurement review. Do the tiering deliberately, write down the reasoning, and have counsel sanity-check the boundary cases.

---

## What the EU AI Act's obligations mean in engineering terms

For high-risk systems especially, the Act's requirements read like a checklist of things you can build controls around. Here is the translation from legal-speak to engineering work, with pointers to where earlier posts in this series covered the mechanics:

- **Risk management** → a living risk register that identifies foreseeable harms, their likelihood and severity, and the mitigations in place. Not a one-time document — something reviewed as the system changes.
- **Data governance** → provenance, representativeness, and quality controls on training and evaluation data; documented handling of gaps and bias. This is dataset documentation plus a data-quality process.
- **Technical documentation** → a description of the system complete enough that a reviewer understands what it is, how it was built, and its known limits. This maps directly to the **model and system cards** from post 3.
- **Record-keeping / logging** → automatic logging of the system's operation so events can be traced after the fact. This is the **audit logging** from post 6 — logs designed to answer "what did the system do, when, and on what input."
- **Human oversight** → design that lets a person understand, monitor, intervene in, or override the system's output, sized to the risk of the decision.
- **Accuracy, robustness, and cybersecurity** → the system performs consistently, resists manipulation and adversarial inputs, and is secured against tampering. This is the territory of the security series — evaluation results plus hardening controls.

Notice that none of these are novel to compliance. They are engineering artifacts. The regulation's contribution is to make them *mandatory and evidenced* for high-risk uses.

```text
EU AI Act (risk-tiered)
├─ Unacceptable ──► prohibited (don't build)
├─ High risk    ──► risk mgmt · data governance · tech docs
│                   logging · human oversight · robustness/security
├─ Limited      ──► transparency duties (disclose AI / AI-generated)
└─ Minimal      ──► good practice
Plus: obligations for general-purpose AI models (extra for the most capable)
```

---

## Two frameworks that give the obligations a home: ISO/IEC 42001 and the NIST AI RMF

Regulations tell you *what* outcomes are required. Management-system standards and voluntary frameworks tell you *how to organize the work* so those outcomes are repeatable and provable.

**ISO/IEC 42001** is an AI **management system** standard — think of it as "ISO 27001, but for AI." Where ISO 27001 defines a certifiable information-security management system, 42001 defines a certifiable *AI* management system: policies, roles, risk processes, controls, and a continual-improvement loop specifically for how an organization develops and operates AI. It is certifiable, which matters commercially — an accredited certificate is portable evidence you can show customers and partners that your AI governance is more than a slide deck. If you already run an ISO-style management system, 42001 will feel structurally familiar.

**The NIST AI RMF** (AI Risk Management Framework) is the influential **voluntary** US framework introduced in post 2. It is not law and confers no certificate, but it gives you a common vocabulary and a lifecycle for managing AI risk, organized around a small set of functions — broadly, *govern, map, measure,* and *manage*. Many organizations use it as the backbone of their internal program even when no regulation compels them, precisely because it is practical and framework-agnostic.

The two complement each other: the NIST AI RMF is a strong way to *structure* your risk work; ISO/IEC 42001 is a way to get that work *certified*. Neither replaces reading the actual regulation that applies to you — they help you satisfy it.

---

## Sector and regional rules: assume the map is incomplete

The EU AI Act, ISO/IEC 42001, and the NIST AI RMF are the load-bearing landmarks, but they are not the whole landscape:

- **US state laws.** Several US states have passed or are advancing their own AI and automated-decision rules, especially around consumer protection, employment, and profiling. Coverage is uneven and changing, so which ones apply depends on where your users are.
- **Sectoral rules.** If you operate in a regulated industry, your existing sector regulator's expectations still apply to AI. Finance (model risk management, fair-lending and consumer-protection expectations) and healthcare (patient safety, medical-device and privacy regimes) are the clearest examples — AI does not get an exemption from the rules that already govern the domain.
- **It moves fast.** New laws, guidance, delegated acts, and enforcement priorities appear regularly. A control set that was complete last year may have gaps now.

The engineering posture that survives this churn is not "memorize every rule." It is "build a system that can *produce evidence on demand*," so that when a new obligation lands, you are mapping an existing artifact to it rather than building the artifact from scratch.

**The gotcha:** "the model vendor is compliant" does not make *your* system compliant. Obligations attach to the provider or deployer of the system — you — not only to whoever trained the underlying model. A vendor's certificate or documentation is useful input to your own evidence, but it does not discharge your duties for how *you* deploy, configure, monitor, and expose the system to users. Read your vendor contracts for what they actually warrant, and assume the accountability for the deployed system is yours.

---

## The crosswalk: obligations map to artifacts you already produce

Here is the payoff. If you have been following this series, you have been building the exact artifacts regulators ask for. The work now is to *map* obligations to artifacts, so each requirement points at a concrete deliverable and an owner. A crosswalk like this — kept in version control next to the system it describes — is itself compelling evidence of a governed process.

```yaml
# obligation → control/artifact crosswalk (illustrative; confirm scope with counsel)
crosswalk:
  - obligation: "Risk management process"
    artifact: "risk register (living, reviewed on change)"
    source_post: 5
    owner: "system owner"
  - obligation: "Data governance & quality"
    artifact: "dataset documentation + data-quality checks"
    source_post: 3
    owner: "data lead"
  - obligation: "Technical documentation"
    artifact: "model card + system card"
    source_post: 3
    owner: "ML engineer"
  - obligation: "Record-keeping / logging"
    artifact: "audit logs (input, output, decision, timestamp)"
    source_post: 6
    owner: "platform engineer"
  - obligation: "Human oversight"
    artifact: "human-in-the-loop design + override path + review UI"
    source_post: 4
    owner: "product + eng"
  - obligation: "Accuracy / robustness"
    artifact: "evaluation results + regression suite"
    source_post: "security series"
    owner: "ML engineer"
  - obligation: "Cybersecurity"
    artifact: "threat model + hardening controls + monitors"
    source_post: "security series"
    owner: "security"
  - obligation: "Transparency (limited-risk)"
    artifact: "AI-disclosure copy + AI-generated-content labeling"
    source_post: 4
    owner: "product"
  - obligation: "Program structure / continual improvement"
    artifact: "AI management system (ISO/IEC 42001-aligned)"
    framework: "ISO/IEC 42001 + NIST AI RMF"
    owner: "governance lead"
```

The same mapping as a quick-reference table:

| Regulatory obligation | Engineering control / artifact | Where it came from |
|---|---|---|
| Risk management | Risk register (living) | Post 5 |
| Data governance | Dataset docs + quality checks | Post 3 |
| Technical documentation | Model card + system card | Post 3 |
| Record-keeping / logging | Audit logs | Post 6 |
| Human oversight | Human-in-the-loop + override | Post 4 |
| Accuracy / robustness / security | Eval results + threat model + monitors | Security series |
| Transparency (limited-risk) | AI disclosure + content labeling | Post 4 |
| Program governance | AI management system | ISO/IEC 42001 + NIST AI RMF |

**The gotcha:** compliance is evidence, so retrofitting documentation after the fact is painful and unconvincing. Model cards written months after training, logs that were never captured, evaluation results reconstructed from memory — auditors can tell, and worse, the gaps are real. Generate the evidence *from the pipeline*: emit the model/system card as a build artifact (post 3), write structured audit logs at inference time (post 6), and store evaluation results as versioned outputs. Evidence produced by the system as it runs is both cheaper to maintain and far more credible than evidence assembled in a scramble.

---

## Human oversight is not optional for high-stakes decisions

One requirement deserves its own emphasis because engineers often under-scope it. For high-risk decisions, the law expects a human to be able to *understand, monitor, and override* the system — meaningfully, not as a rubber stamp. That has design consequences: the interface must surface enough context for the reviewer to make a real judgment, the override path must actually change the outcome, and the volume of decisions must be low enough that human review is possible rather than theatrical. A "human in the loop" who approves a thousand decisions an hour without looking is not oversight; it is a liability with a signature. Size the oversight to the risk, and log the interventions — those logs are evidence too.

---

## Key takeaways

- **Tier first.** Your risk classification sets the entire compliance burden. Do it deliberately, document the reasoning, and treat misclassification as the expensive mistake it is.
- **Obligations are engineering work.** Risk management, data governance, documentation, logging, oversight, and robustness are controls and artifacts — not paperwork bolted on at the end.
- **Compliance is evidence.** The artifacts from this series (risk register, model/system cards, eval results, monitors, audit logs) *are* your compliance deliverables. Generate them from the pipeline, not after the fact.
- **Frameworks organize the work.** ISO/IEC 42001 is a certifiable AI management system (ISO 27001 for AI); the NIST AI RMF is the voluntary US framework that structures risk work. Neither replaces the regulation that applies to you.
- **Accountability is yours.** A compliant model vendor does not make your deployed system compliant — obligations attach to the provider/deployer.
- **Keep humans in the loop** for high-risk decisions, and make the oversight real.
- **This is not legal advice.** Engineers produce evidence; counsel interprets obligations. Confirm specifics against the primary texts.

---

## Further reading

- [EU AI Act — regulatory framework (European Commission)](https://digital-strategy.ec.europa.eu/en/policies/regulatory-framework-ai) and the legal text on [EUR-Lex](https://eur-lex.europa.eu/legal-content/EN/TXT/?uri=CELEX:32024R1689)
- [ISO/IEC 42001 — Artificial intelligence management system](https://www.iso.org/standard/81230.html)
- [NIST AI Risk Management Framework (AI RMF)](https://www.nist.gov/itl/ai-risk-management-framework)
- [OECD AI Policy Observatory](https://oecd.ai/)
