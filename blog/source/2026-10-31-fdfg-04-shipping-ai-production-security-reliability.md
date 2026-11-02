# Shipping AI: Production, Security & Reliability

*Proving value on a prototype is the halfway point. The other half — and the harder one — is making it survive production: evaluated, secured, compliant, reliable, and owned by the customer's team. This post maps the shipping theme of the field guide, where most AI initiatives actually stall.*

Fourth in [The Forward Deployed Field Guide](/blog/posts/fdfg-01-understanding-customers-and-driving-ai-adoption.html). The gap between a proven prototype and a dependable production system is wide, and crossing it is the defining forward-deployed skill. This theme is where demos go to become products — or to die.

## The topics in this theme

- **Deployment.** Getting the system running in the customer's real environment — their cloud, their security boundary, their data — not a sandbox. Integration with existing systems is usually where the time goes.
- **Evaluation.** Ongoing measurement against the agreed bar, with an eval set and guardrails — pass/fail evidence, not vibes. Evals are what let you change the system later without fear, and what prove it's still good enough in production.
- **Security.** AI-specific threats on top of normal application security: prompt injection, data exposure through the model, tool/agent permissions, and sandboxing. For agents that can act, containment (least privilege, approval gates, a kill switch) is a precondition, not a feature.
- **Sovereignty and compliance.** For regulated and government customers, where data lives and how it's governed is often the real gate — data residency, auditability, and the compliance posture the AI system must satisfy.
- **Reliability.** Observability, monitoring for quality drift, cost and latency SLOs, graceful degradation. A probabilistic system needs to be watched differently than deterministic software.
- **Handover.** The engagement's measure of success: the customer's team owns and can run the system — code, architecture, the eval discipline, and the understanding behind it. A deployment that only works while you're standing next to it hasn't been delivered.

## The new AI topics reshaping it

- **Agent security as its own field.** As agents gain the ability to act, prompt injection and over-broad permissions become serious, not theoretical — a fast-growing area of practice.
- **AI governance, operationalized.** Governance is moving from policy documents to runtime controls — policy-as-code, audit logs as the system of record, and the toolkits that enforce them.
- **Sovereign AI.** Data sovereignty and on-/in-country model deployment are rising fast as regulated and government buyers adopt AI — often the deciding constraint on an architecture.
- **Evals as infrastructure.** Continuous evaluation and monitoring for drift are becoming standing infrastructure, not a one-time gate.

## Where to go deep

This theme maps to [AI Security Engineering](/blog/series/ai-security-engineering/), [AI Governance for Engineers](/blog/series/ai-governance-for-engineers/), and [AI Governance in Practice](/blog/series/ai-governance-in-practice/), with the end-to-end path in [The AI Production Roadmap](/blog/series/the-ai-production-roadmap/) and the deployment/handover craft in [The AI Forward Deployed Engineer](/blog/series/the-ai-forward-deployed-engineer/). Reliability and cost/latency SLOs connect back to [Building Agents & AI Systems](/blog/posts/fdfg-02-building-agents-and-ai-systems.html).

## Why handover is the real finish line

It's tempting to call "it's live" the finish line. For a forward-deployed engineer it isn't — the finish line is the customer's team confidently running what you built without you. Handover done well is the whole point of the engagement: it's what turns a dependency into a capability, and (not coincidentally) what earns the trust that leads to the next engagement. Shipping that isn't owned is shipping that will quietly decay.

## Key takeaways

- **Shipping is the harder half** — making a proven prototype survive production (evaluated, secured, compliant, reliable, owned) is the defining forward-deployed skill, and where most AI initiatives stall.
- The topics: **deployment** (real environment, not a sandbox; integration eats the time), **evaluation** (ongoing pass/fail evidence + guardrails), **security** (prompt injection, data exposure, agent permissions, containment as a precondition), **sovereignty & compliance** (data residency and governance — often the real gate), **reliability** (observability, drift monitoring, SLOs, graceful degradation), and **handover** (the customer's team owns and can run it).
- **New AI dynamics:** **agent security** as its own field, **AI governance operationalized** (policy-as-code, audit logs, enforcement toolkits), **sovereign AI** (rising fast as the deciding constraint), and **evals as standing infrastructure** (continuous, not one-time).
- Go deep via AI Security Engineering, AI Governance for Engineers / in Practice, The AI Production Roadmap, and The AI Forward Deployed Engineer.
- **Handover is the real finish line** — not "it's live" but "the team runs it without me"; handover turns a dependency into a capability and earns the trust that leads to the next engagement. Shipping that isn't owned will quietly decay.

## Further reading

- [MLOps — the operational discipline of running models in production](https://en.wikipedia.org/wiki/MLOps)
- [Prompt injection — the signature security threat for AI systems and agents](https://en.wikipedia.org/wiki/Prompt_injection)
