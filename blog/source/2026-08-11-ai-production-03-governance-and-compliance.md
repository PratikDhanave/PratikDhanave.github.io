# Governance, Risk, and Compliance Before Real Users

*Governance is the one phase whose ordering is non-negotiable: every major framework treats it as a lifecycle function established up front, and retrofitting it after an incident is how you end up with unexplainable models and regulatory exposure.*

Most phases of this roadmap iterate freely. This one has a hard rule: **governance must be established before the system touches real users or regulated data.** Retrofitting it after an incident produces undocumented data, unexplainable decisions, and legal exposure that is far more expensive than doing it first. This post is Phase 1 — standing up the governance, risk, and compliance scaffolding so every later phase is built inside guardrails rather than having them bolted on.

## Adopt a risk framework as the spine

Start by adopting a recognized risk-management framework as your operating spine rather than inventing one. The **NIST AI Risk Management Framework** is a strong, freely available choice. Its core has four functions that map cleanly onto this roadmap: **GOVERN** (culture, policies, roles, accountability — this phase and platformization), **MAP** (establish context and frame risks — strategy and this phase), **MEASURE** (analyze and monitor risk quantitatively — evaluation and observability), and **MANAGE** (prioritize, respond, recover — security and incident response). The framework pairs with seven characteristics of trustworthy AI: valid and reliable, safe, secure and resilient, accountable and transparent, explainable and interpretable, privacy-enhanced, and fair with harmful bias managed.

For generative systems specifically, NIST's Generative AI Profile enumerates GenAI-specific risk categories — confabulation (hallucination), data privacy, harmful bias, information integrity and security, intellectual property, and value-chain risks among them. Use that list as the starting taxonomy for your risk register rather than a blank page.

## Classify regulatory exposure

Even outside the EU, the **EU AI Act's risk-based tiering** is a useful universal triage, and if you operate in or serve the EU it is binding. Classify each system into a tier:

- **Unacceptable risk** — prohibited practices such as social scoring and manipulative or exploitative systems. Do not build.
- **High risk** — systems affecting safety or fundamental rights (for example hiring, credit, education, biometric identification). These carry the heaviest obligations: a risk-management system, data governance, technical documentation, logging, human oversight by design, accuracy and robustness and cybersecurity, and conformity assessment.
- **Limited / transparency risk** — disclosure duties: people must be told they are interacting with AI, and AI-generated content must be labeled.
- **Minimal risk** — largely unregulated.

Regulatory timelines shift and vary by jurisdiction — verify the current obligations and dates against the primary source at authoring time rather than trusting any secondary summary. The durable point is to *classify early*: the tier determines how heavy your obligations are, and discovering the classification after launch is a classic, expensive mistake.

## Establish an auditable management system

Where the organization needs auditable, certifiable governance, **ISO/IEC 42001** is the first certifiable AI management-system standard. It follows the familiar ISO plan-do-check-act structure (like ISO/IEC 27001), so an organization can be third-party audited on how it establishes, maintains, and improves its AI governance. It gives you the management-system backbone; a companion risk-guidance standard supplies the risk-process detail. You do not need certification to benefit — the structure itself is a useful checklist for turning policy into enforced practice.

## The artifacts to produce now

Governance that lives only in a policy PDF is theater. Produce concrete, enforced artifacts:

1. **An AI system inventory** — every AI system, its owner, risk tier, data sensitivity, and lifecycle stage. If you cannot answer "how many AI systems do we run and who owns each?", start here.
2. **A risk register** — seeded from the NIST GenAI categories and the OWASP LLM Top 10 (the security phase), with likelihood, impact, and mitigations.
3. **A responsible-AI policy** — the principles you commit to (fairness, transparency, accountability, privacy, safety, human oversight), synthesized from the OECD principles and NIST's trustworthy characteristics.
4. **An impact-assessment template** for high-risk systems — privacy (DPIA-style), fundamental-rights, and broader socio-technical harm.
5. **Human-oversight design** — for each consequential decision, the defined human review point and the accountable owner named back in the strategy phase.
6. **A documentation standard** — mandate **model cards** and **datasheets for datasets**, and a **system card** for whole deployed systems, so models and data are documented by default.

## Records and incidents are legal duties

Some governance obligations are not runbooks but legal duties with hard deadlines. Depending on jurisdiction and risk tier, you may face serious-incident notification requirements to regulators and, for personal-data breaches under GDPR, notification to the data-protection authority within 72 hours. There are also record-keeping duties — event logging by design and log retention over defined periods — that ordinary telemetry may not satisfy because they require tamper-evidence and retention guarantees. The artifact here is an immutable audit-log and records-retention policy plus a *rehearsed* notification procedure, wired to the kill-switch you will build in the observability phase. Verify the specific deadlines and retention periods against primary sources for your jurisdiction.

## Cloud tooling implements, it does not replace

Each major cloud now ships responsible-AI and governance tooling — content-safety services, responsible-AI dashboards, model-card generators, AI service cards. These are useful tools *inside* your governance program, not a substitute for it. A content filter does not classify your regulatory risk or name your accountable owner.

## The gate and the anti-patterns

Phase 1 is done when a risk framework is formally adopted, every in-scope system has a regulatory classification and a named owner, a risk register exists seeded from the GenAI and OWASP taxonomies, the responsible-AI policy and impact-assessment and documentation standards are published, and human-oversight points are defined for all consequential decisions. Avoid the classic failures: governance theater (a policy no pipeline enforces), governance last (finding your classification after launch), and no inventory (unable to say what you run and who owns it).

## Key takeaways

- Governance ordering is non-negotiable: establish it before the system touches real users or regulated data; retrofitting after an incident is far more expensive.
- Adopt a recognized risk framework (NIST AI RMF) as the spine — GOVERN/MAP/MEASURE/MANAGE map onto the roadmap — and seed your risk register from NIST's GenAI risk categories.
- Classify regulatory exposure early using the EU AI Act's risk tiers (universal triage even outside the EU); verify current obligations and dates against primary sources.
- Produce enforced artifacts — system inventory, risk register, responsible-AI policy, impact-assessment template, human-oversight design, and a documentation standard (model cards, datasheets, system cards).
- Treat incident-notification and record-keeping as legal duties with deadlines; cloud responsible-AI tooling implements parts of governance but never replaces the program.

## Further reading

- [NIST AI Risk Management Framework](https://www.nist.gov/itl/ai-risk-management-framework)
- [ISO/IEC 42001:2023 — AI management systems](https://www.iso.org/standard/81230.html)
- [Model Cards for Model Reporting — Mitchell et al., 2018](https://arxiv.org/abs/1810.03993)
