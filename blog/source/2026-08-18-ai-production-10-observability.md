# Observability, Reliability, and Incident Response

*You cannot operate what you cannot see, and AI systems fail in ways ordinary monitoring misses — quality silently degrades, cost silently climbs, and inputs silently drift — so observability has to watch the things that don't throw exceptions.*

A system can be up, fast, and error-free by every traditional metric and still be quietly getting worse: answers degrading, costs climbing, inputs drifting away from what it was built for. AI observability has to see those failures — the ones that don't raise a 500 — and the operation has to detect, diagnose, and recover from them. The control you cannot skip here is **traces plus quality and drift alerts plus runbooks.** This post is Phase 8 of the roadmap.

## Trace the whole request

Start with end-to-end tracing. A single AI request often fans out into retrieval calls, tool calls, and one or more model calls, and when something goes wrong you need to see the whole trajectory: what was retrieved, what the model was actually sent, what tools it called with what arguments, and what came back at each step. Structured traces of the full request are the difference between diagnosing a failure in minutes and guessing for hours. Emerging OpenTelemetry conventions for GenAI give you a standard vocabulary for these traces (spans for model calls, token counts, tool invocations) so your AI telemetry lives in the same system as the rest of your infrastructure rather than a bespoke silo.

## Watch the signals that don't throw

Beyond ordinary latency, availability, and error rates, AI systems need telemetry on failures that are silent by nature:

- **Quality.** Sample production interactions and score them (with the same LLM-as-judge and checks from the evaluation phase) so you can see quality trending down before users complain. This is continuous evaluation pointed at live traffic.
- **Cost.** Track token consumption and spend per request, per feature, and per user — cost is a first-class reliability signal because a runaway agent loop or a prompt regression shows up as a spend spike, and unit economics is what tells you the system is sustainable (the cost phase makes this its whole subject).
- **Drift.** Monitor input distributions and, where you can, output distributions. A shift in the kind of questions users ask, or in the data being retrieved, can silently move the system outside where it was evaluated. Silent data drift with no monitoring is the failure the data phase warned about; this is where you catch it.
- **Safety.** The adversarial and content-safety signals from the security and evaluation phases run continuously here too — a spike in blocked injections or flagged outputs is an attack indicator.

The unifying idea: instrument the things that degrade without erroring, because those are exactly the AI failures traditional monitoring lets through.

## Alerts, runbooks, and the kill-switch

Telemetry without response is just dashboards. Turn signals into action:

- **Alerts** on the metrics that matter — quality below a threshold, cost above budget, drift beyond a bound, safety events — routed to the accountable owner named in strategy, not into a channel no one reads.
- **Runbooks** for the predictable failure modes: a provider outage (fail over to a fallback model or degrade gracefully), a quality regression (roll back to the last registered artifact), a cost spike (rate-limit or disable the offending feature), a safety incident (invoke the notification procedure from governance).
- **A kill-switch.** For consequential systems, a tested way to rapidly disable or roll back the AI — wired to the governance phase's incident procedure. A kill-switch you have never rehearsed is a kill-switch you don't have.

## Reliability patterns carry over

Much of classical reliability engineering applies directly, with AI-specific twists. Set SLOs and track error budgets (the serving phase defined them; here you watch them). Use timeouts, retries with backoff, and circuit breakers around model and tool calls, because a hung provider should fail fast to a fallback rather than stall every request. Design graceful degradation — a smaller model, a cached answer, a "try again shortly" — so a dependency failure is a degraded experience, not an outage. These patterns are ordinary; the discipline is remembering to apply them to the probabilistic, expensive, externally-dependent components that AI adds.

## Close the loop back to development

Observability is not a terminal phase; it is a feedback source for every earlier one. Production failures become new test cases in the evaluation golden set. Drift surfaces data issues that route back to the data phase. Cost signals inform the cost and FinOps phase. Safety events feed the security threat model and red-team. A production incident that does not produce a new test, a fix, and a lesson is a wasted incident. This is the MEASURE-and-MANAGE loop of a risk framework, running continuously.

## The gate and anti-patterns

Phase 8 is done when the full request is traced end to end; quality, cost, drift, and safety are monitored (not just latency and errors); alerts route to the accountable owner; runbooks exist for the predictable failures; and a tested kill-switch and rollback are in place. Avoid the recurring failures: monitoring only infrastructure metrics while quality silently rots; no drift detection on inputs; alerts no one owns; and an un-rehearsed kill-switch discovered to be broken during the first real incident.

## Key takeaways

- AI systems fail silently — quality degrades, cost climbs, inputs drift — so observability must watch signals that never throw an exception.
- Trace the whole request end to end (retrieval, tool, and model calls), ideally with OpenTelemetry GenAI conventions so AI telemetry lives with the rest of your infrastructure.
- Monitor quality (sampled continuous eval on live traffic), cost (per request/feature/user), drift (input/output distributions), and safety — alongside ordinary latency, availability, and errors.
- Turn signals into action: owned alerts, runbooks for predictable failures, and a *rehearsed* kill-switch/rollback wired to the governance incident procedure.
- Apply classical reliability patterns (SLOs, timeouts, retries, circuit breakers, graceful degradation) to AI's probabilistic, expensive, external components, and feed every incident back into evaluation, data, cost, and security.

## Further reading

- [AI Cost Optimization series](/blog/series/ai-cost-optimization/)
- [NIST AI Risk Management Framework](https://www.nist.gov/itl/ai-risk-management-framework)
- [OWASP Top 10 for LLM Applications](https://genai.owasp.org/)
