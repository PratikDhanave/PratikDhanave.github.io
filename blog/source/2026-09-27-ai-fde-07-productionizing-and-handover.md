# Productionizing and Handing Over AI

*A pilot that works is not a system the customer can run. Productionizing AI means making it reliable, affordable, fast, and observable enough to be real infrastructure — and then handing it over so the customer operates it without you. The forward deployed engineer's goal, in the end, is to make themselves unnecessary: a deployment that only works while you're standing next to it hasn't actually been delivered.*

The system is grounded (post 4), measured (post 5), and integrated (post 6). Now it has to become production infrastructure and then leave your hands. Productionizing AI shares much with productionizing any software, but adds AI-specific concerns — cost, latency, drift, and the peculiar operational needs of probabilistic systems. And handover, the true end of an FDE engagement, has an AI twist: you're handing over a system that changes behavior over time, which needs a different kind of operating discipline.

## What productionizing AI adds

Beyond ordinary production hardening (reliability, security, monitoring), deployed AI has concerns that don't exist for deterministic software:
- **Cost is a first-class design constraint.** Model calls cost money per token, and at production volume a careless design produces alarming bills. Productionizing means controlling cost deliberately: caching repeated/similar queries, choosing the right-sized model per task (not the biggest for everything), trimming context, and budgeting. Total cost of ownership — not just accuracy — determines whether a deployment survives, so the AI FDE designs for it.
- **Latency shapes usability.** Models are slow relative to normal software. A response that takes many seconds breaks the workflow it's embedded in. Streaming output, caching, model choice, and parallelizing retrieval and generation are the levers. The latency budget is a real constraint the integration (post 6) depends on.
- **Quality drifts.** Unlike a deterministic function, a deployed AI system's real-world quality degrades over time — the customer's data changes, usage patterns shift, and providers update models underneath you. [Concept drift](https://en.wikipedia.org/wiki/Concept_drift) means "it worked at launch" is not "it works now." Continuous evaluation (post 5) in production is how you catch this.
- **The model can change under you.** If you depend on a provider's model, they may deprecate or silently update it, changing your system's behavior. This is a core reason to route through an [AI gateway](/blog/series/ai-gateways-and-llm-infrastructure/) — provider-independence, plus the caching, rate limiting, cost metering, and logging that production AI needs in one control point.

## Observability for probabilistic systems

You can't operate what you can't see, and AI systems are unusually hard to see into. Production AI observability goes beyond standard metrics (latency, errors, throughput) to AI-specific signals:
- **Quality monitoring** — continuous evaluation on live traffic and sampled outputs, so a drop in answer quality is detected, not discovered via an angry user. This is the production arm of post 5's eval discipline.
- **Cost and usage tracking** — per-feature, per-team token spend and volume, so cost is visible and controllable (and chargeable back), not a month-end surprise.
- **Logging and traceability** — what was asked, what was retrieved, what the model returned, and why — enough to debug a bad answer after the fact. For grounded systems, logging the *retrieved context* is essential, because most bad answers are retrieval failures (post 4).
- **Feedback capture** — user acceptance, edits, overrides, and thumbs (post 6) flowing back as both a live quality signal and eval-set growth.

The gateway is the natural place for much of this, because every model call flows through it — making it the single point where cost, latency, quality, and usage become visible.

## Handover: making yourself unnecessary

The defining goal of an FDE engagement is that the customer ends up able to run the system without you. A deployment you must personally babysit is not delivered — it's a dependency. For AI specifically, handover means transferring the ability to operate a system that *changes over time*, which is more than handing over a codebase:
- **Documentation that fits the operators.** How the system works, how to run and monitor it, how to interpret the eval and cost dashboards, and — crucially — the known limitations and failure modes. For AI, "what it's bad at and how it fails" is as important as "how it works."
- **The operational runbook.** How to re-run ingestion when data changes, how to update the eval set, what to do when quality drops, when to retrain or swap models, and how to respond to incidents. The AI-specific operations (re-grounding, re-evaluating) are the parts a customer won't know to do unless you teach them.
- **The eval set and its discipline.** The customer's eval set (post 5) is the crown jewel — hand it over along with the *practice* of maintaining it and gating changes on it. A customer who keeps evaluating can safely evolve the system; one who stops is flying blind the moment anything changes.
- **Skills transfer, not just artifacts.** The people who will run it need to understand grounded AI enough to operate it — that retrieval drives quality, that quality drifts, that the eval set is the source of truth. Teaching that mindset is part of the handover, and it's what lets the customer own the system rather than merely possess it.

Handover is also gradual: you move from building, to co-operating, to advising, to gone — transferring responsibility in stages as the customer's confidence and capability grow, rather than dropping it all at once. Done well, the system keeps working and improving after you leave, which is the real measure of a successful deployment.

## When a human must stay in the loop

One honest caveat specific to AI: some deployments should *never* become fully autonomous, and part of productionizing is deciding that deliberately. Where errors are costly and the model's reliability doesn't clear the bar, the human-in-the-loop design (post 6) is permanent, not a training-wheels phase. Being clear-eyed about this — designing a durable human+AI system rather than promising an eventual full automation that shouldn't happen — is part of responsible delivery. The goal is the customer's outcome (post 1), and sometimes the best outcome is a reliable human-in-the-loop system, handed over and running, not a risky automation.

The takeaway: productionizing AI adds concerns deterministic software doesn't have — cost as a first-class constraint, latency shaping usability, quality that drifts, and models that change under you — met with deliberate cost/latency design, an AI gateway as the control point, and observability into quality, cost, and retrieval. Then comes the true end of the engagement: handover that makes you unnecessary, transferring not just the codebase but the operational runbook, the eval set and its discipline, and the grounded-AI mindset needed to run a system that changes over time. The measure of success is that the system keeps working and improving after you leave — and, where the stakes demand it, that a human stays in the loop by design.

## Key takeaways

- Productionizing AI adds concerns deterministic software lacks: **cost as a first-class constraint** (per-token bills → caching, right-sized models, budgets, TCO), **latency** shaping usability (streaming, caching, model choice), **quality drift** (it worked at launch ≠ works now), and **models changing under you** (route through an **AI gateway** for provider-independence + caching/limits/metering/logging).
- **Observability** must cover AI-specific signals beyond latency/errors: **quality monitoring** on live traffic, **cost/usage** tracking, **logging with the retrieved context** (most bad answers are retrieval failures), and **feedback capture** — the gateway is the natural single point for it.
- The FDE's defining goal is to **make yourself unnecessary**: a system you must babysit isn't delivered — **handover** transfers the ability to operate a system that *changes over time*, not just a codebase.
- Handover includes **operator-fit documentation** (especially known limitations/failure modes), an **operational runbook** (re-ingest, re-evaluate, when to retrain/swap models, incident response), the **eval set plus the discipline** of maintaining and gating on it, and **skills/mindset transfer** — done **gradually** (build → co-operate → advise → gone).
- Some AI deployments should **never be fully autonomous**: where errors are costly and reliability doesn't clear the bar, **human-in-the-loop is permanent by design** — a reliable handed-over human+AI system can be the best outcome, and saying so is responsible delivery.

## Further reading

- [MLOps — operating machine-learning systems in production](https://en.wikipedia.org/wiki/MLOps)
- [Total cost of ownership — why cost, not just accuracy, decides survival](https://en.wikipedia.org/wiki/Total_cost_of_ownership)
