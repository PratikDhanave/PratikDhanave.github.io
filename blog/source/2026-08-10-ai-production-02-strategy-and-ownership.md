# Strategy, Use-Case Selection, and the Named Owner

*The most expensive AI failures are systems that work technically but solve the wrong problem, cannot show a return, or have no one accountable when they misbehave — and all three are decided before a single model is chosen.*

Strategy is the cheapest phase of the AI production roadmap to get right and the most expensive to skip. It answers four questions before any technical work: *should* we build this, *which* problem should it solve, *how much* is success worth, and *who* is accountable. Skipping it is how organizations end up with an impressive demo that has no path to value and no owner when it fails. This post is Phase 0 of the series — deciding what to build and who owns it.

## Problem before technology

The failure mode that starts everything wrong is "solution looking for a problem" — beginning from "we must use GenAI" instead of from a business problem worth solving. The antidote is to enumerate candidate use cases and score each on four axes: business value, technical feasibility, data availability, and risk or regulatory exposure. That produces a ranked shortlist grounded in value, not novelty.

There is a deeper fit question underneath. AI is probabilistic; it is a *feature* when the task tolerates and even benefits from that — ranking, summarization, drafting, extraction, routing, classification. It is a liability when the task demands deterministic correctness with zero tolerance for error, unless you can wrap it in a verification layer that bounds the risk. Prefer problems where the probabilistic nature is a fit, or where a check can make it safe.

## The value hypothesis

For each shortlisted use case, write an explicit value model before building: the metric you will move (revenue, cost, cycle time, deflection rate, quality), its current baseline, the target lift, and the full cost envelope — build *and* run *and* inference. Tie the AI metric to a business KPI so success is measurable in dollars, not demos.

The cost envelope is where teams deceive themselves. Inference is an operating expense paid on every request forever, not a one-time build cost. A use case that looks valuable at prototype scale can be deeply unprofitable at production volume once you price the tokens, the retries, and the agent steps. The value hypothesis has to survive contact with realistic run cost, which is why the cost phase later in this roadmap is not optional.

## Build vs. buy vs. compose

Every use case needs a recorded decision among a few options: consume a managed foundation-model API, retrieve-augment a base model with your data, adapt a model by fine-tuning, or build something bespoke. The sensible default now is **compose** — orchestrate managed models with your proprietary data and guardrails — reserving custom training for genuine, defensible differentiation. Owning model weights is worth the cost only when it is a real moat; for most systems it is not, and composition ships faster with less to operate. Record the decision and its rationale so it can be revisited as models and prices change.

## The named human

Here is the control you cannot skip in this phase: **for every AI system that affects a customer or a regulated decision, name a specific accountable human — not a team.** "The AI team owns it" is not accountability; it is diffusion of responsibility that evaporates the moment something goes wrong.

This is not a bureaucratic nicety. Human accountability and oversight are convergent requirements across every major governance framework — the NIST AI Risk Management Framework centers accountability structures in its GOVERN function, the EU AI Act requires human oversight by design for high-risk systems, and the OECD AI Principles make AI actors accountable. You will formalize and enforce this in the governance and responsible-AI phases, but it is *set here*, at strategy time, because a system that can harm someone needs a person who answers for it before it ships, not after.

## Operating model and team topology

Beyond the single accountable owner, define who owns the system across its whole lifecycle. A workable AI operating model names a product owner, an ML/AI engineering team, a platform or MLOps function, a security partner, and a governance/risk partner. Adopt a platform mindset early: data, evaluation, and deployment should be shared capabilities, not per-project reinvention — the seed of the platformization phase that closes this roadmap.

Secure two things from leadership before building: executive sponsorship, and a funding model that covers *run* cost, not just build. And plan the change management for the humans whose workflow the AI will alter — a system that technically works but that its intended users route around has still failed.

## Deliverables and the gate

Phase 0 is done when you can show a use-case portfolio matrix with a ranked shortlist, a one-page value hypothesis per shortlisted use case, a recorded build/buy/compose decision, an operating model and RACI naming the accountable human, and a funding model that separates build capex from inference opex. The gate to the next phase: at least one use case has a quantified value hypothesis and a named owner, the build/buy/compose call is recorded, risk exposure is at least coarsely classified (which seeds the governance phase), and funding covers ongoing operation.

## Anti-patterns

Watch for the recurring ways this phase goes wrong: demo-driven development that optimizes an impressive prototype with no path to a governed, cost-bounded system; treating inference as free and discovering unit economics only after launch; and "no named owner," where a system that can harm a customer has only a team to blame. Each is cheap to avoid now and expensive to fix later.

## Key takeaways

- Strategy is the cheapest phase to get right and the most expensive to skip; it decides whether you build, what problem it solves, what success is worth, and who owns it.
- Start from a business problem, not a technology; prefer tasks where AI's probabilistic nature is a fit, or where a verification layer bounds the risk.
- Write an explicit value hypothesis (metric, baseline, target, full cost envelope including recurring inference) and tie it to a business KPI in dollars.
- Default to *compose* (managed models + your data + guardrails); reserve fine-tuning or bespoke training for defensible differentiation, and record the decision.
- The non-skippable control is a specific named accountable human for any customer-affecting or regulated system — convergent with NIST, the EU AI Act, and OECD — plus an operating model that funds run cost, not just build.

## Further reading

- [NIST AI Risk Management Framework](https://www.nist.gov/itl/ai-risk-management-framework)
- [OECD AI Principles](https://www.oecd.org/en/topics/ai-principles.html)
- [EU AI Act — European Commission](https://digital-strategy.ec.europa.eu/en/policies/regulatory-framework-ai)
