# Understanding Customers & Driving AI Adoption

*A forward-deployed engineer's first job isn't to build — it's to understand. Before a line of code, you have to see how the customer actually works, whether they're ready for AI, and what it will take for them to adopt it rather than admire it. This opens a field guide to forward-deployed engineering, organized into six themes, and starts where every engagement starts: with the customer.*

This is the first post in **The Forward Deployed Field Guide** — a map of the whole forward-deployed-engineering (FDE) discipline, organized into six themes:

1. **Understanding customers & driving AI adoption** — workflows, readiness, adoption (this post)
2. **Building agents & AI systems** — agents, MCP, context, connectors, data, cost, latency
3. **Finding the right problem & proving value** — discovery, scope, prototypes, acceptance, value
4. **Shipping AI: production, security & reliability** — deployment, evals, security, sovereignty, reliability, handover
5. **The FDE craft: people, practice & influence** — stakeholders, roles, careers, hiring, mentoring, community
6. **From field lessons to better products** — lessons, reuse, patterns, product feedback

Each post maps a theme's topics and the current AI developments reshaping it, and points to the deeper series where the craft is worked out in full. This series is the index; the others are the chapters. Start with the whole-picture view in [The Forward Deployment Stack](/blog/series/the-forward-deployment-stack/) and the role itself in [Forward Deployed Engineering](/blog/series/forward-deployed-engineering/).

## Why "understanding the customer" comes first

Forward deployment exists because the hard part of AI isn't the model — it's fitting it to a specific customer's reality. That reality is invisible from the outside. So the engagement begins with learning: how work actually gets done here (not the official process, the real one), where the pain is, who the people are, and what they're afraid of. Build before you understand and you build the wrong thing beautifully.

This is the human foundation under everything else in the field guide. The best technical decision made in ignorance of the customer's workflow is still the wrong decision.

## The topics in this theme

- **Workflow mapping.** The real sequence of steps, hand-offs, exceptions, and the one spreadsheet everyone secretly depends on. AI value lives in a specific workflow, not in the abstract — you're looking for where it's slow, error-prone, or expensive.
- **AI readiness.** Is this organization ready? Readiness spans data (is it accessible, clean enough, governed?), skills (can the team operate and maintain an AI system?), process (will the workflow actually change?), and leadership appetite for the risk. Honest readiness assessment prevents doomed engagements.
- **Adoption, not deployment.** A deployed system that nobody uses is a failure that looks like a success. Adoption is a people problem: trust, habit, incentives, and change management. Driving adoption — training, champions, designing the system into the workflow rather than beside it — is as much the FDE's job as the build.
- **Measuring adoption.** Usage, not applause. Track whether the thing is actually used, by whom, for what — and feed that back into the build.

## The new AI topics reshaping it

AI changes the adoption problem in specific ways worth naming:

- **Trust is the gating factor.** Because AI is probabilistic and occasionally confidently wrong, adoption hinges on *calibrated* trust — users need to know when to rely on it and when not to. Designing for appropriate reliance (showing confidence, enabling easy verification, human-in-the-loop on the risky path) is now core to adoption.
- **Workflow-native agents.** Agentic AI shifts the question from "will they open the tool?" to "can the agent act inside the workflow they already use?" — which raises connectors, permissions, and change management, covered in [Building Agents & AI Systems](/blog/posts/fdfg-02-building-agents-and-ai-systems.html).
- **Organizational AI maturity.** Readiness is becoming a measurable discipline — AI maturity models, data readiness, governance posture. Enterprises increasingly need help assessing it before they can adopt, which is itself a forward-deployed engagement (see [the AI FDE playbook](/blog/series/the-ai-forward-deployed-engineer/)).

## Where this fits

Understanding the customer is the soil; the rest of the field guide grows from it. It feeds directly into [finding the right problem and proving value](/blog/posts/fdfg-03-finding-the-right-problem-and-proving-value.html), and the trust you build here is what later makes [shipping to production](/blog/posts/fdfg-04-shipping-ai-production-security-reliability.html) and [handover](/blog/posts/fdfg-06-from-field-lessons-to-better-products.html) land. For the deeper human craft of working with these stakeholders, see [The Forward Deployed Consultant](/blog/series/the-forward-deployed-consultant/).

## Key takeaways

- A forward-deployed engineer's **first job is to understand, not build** — how the customer really works, whether they're ready, and what adoption will take — because the hard part of AI is fitting it to a specific customer's reality, which is invisible from outside.
- This series, **The Forward Deployed Field Guide**, maps the FDE discipline into **six themes** (customers/adoption, building, problem/value, shipping, craft, field-to-product) and points to the deeper series for each.
- The topics in this theme: **workflow mapping** (the real process, not the official one), **AI readiness** (data, skills, process, leadership appetite), **adoption not deployment** (a deployed-but-unused system is a disguised failure; adoption is a people problem of trust, habit, incentives, change management), and **measuring adoption** (usage, not applause).
- **New AI dynamics:** trust is the **gating factor** (calibrated reliance, verification, human-in-the-loop), **workflow-native agents** change adoption from "open the tool" to "act inside the existing workflow", and **organizational AI maturity/readiness** is becoming a measurable discipline enterprises need help assessing.
- Understanding the customer is the **foundation** for the rest of the field guide — it feeds problem-finding, and the trust built here is what makes production and handover land.

## Further reading

- [Technology adoption life cycle — how new technology actually spreads through an organization](https://en.wikipedia.org/wiki/Technology_adoption_life_cycle)
- [Change management — the discipline of making adoption stick](https://en.wikipedia.org/wiki/Change_management)
