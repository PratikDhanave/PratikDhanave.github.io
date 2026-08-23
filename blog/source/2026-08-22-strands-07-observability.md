# Observability and Production

*A model-driven agent decides its own path, which means you cannot know what it did without watching — so observability isn't a nice-to-have in Strands, it's a requirement. Built on OpenTelemetry and shaped by AWS's own production use, Strands treats seeing inside the agent as first-class, because a loop you can't see is a loop you can't trust.*

The model-driven approach trades authored control flow for the model's dynamic decisions — which makes **observability** essential, not optional, because you supervise the loop rather than script it. This post covers Strands's observability (built on OpenTelemetry) and the production concerns that come with running model-driven agents. It's where the model-driven philosophy meets the operational reality of the [observability](/blog/series/observability-engineering/) series.

## Why observability is essential in a model-driven framework

In a workflow-first framework, you know the flow because you wrote it — the observability question is "did each authored step run correctly?" In a *model-driven* framework, you *don't* know the flow in advance, because the model decides it at run time. This flips observability from helpful to *essential*:

- **You can't know what the agent did without observing it.** The model chose which tools to call, in what order, and when to stop — none of it scripted — so the *only* way to know what happened is to observe the loop. Without observability, a model-driven agent is a black box making unscripted decisions.
- **Debugging requires seeing the model's decisions.** When an agent misbehaves (wrong tool, wandering, wrong answer), you diagnose by *seeing* the model's reasoning and tool calls — there's no workflow definition to inspect, only the actual run. The trace *is* the program's behavior.
- **Supervision replaces scripting.** The model-driven developer's role (the philosophy post) is to observe and bound, not direct — and observation *is* observability. You steer a model-driven agent by watching it and adjusting the prompt/tools, which requires seeing what it does.

So observability is the natural complement to the model-driven approach: you gave up authored control flow, and observability is how you get *understanding* back. A model-driven framework without strong observability would be untenable — you'd have no way to know or trust what your agents do. That's why Strands treats it as first-class.

## OpenTelemetry-based observability

Strands builds observability on **OpenTelemetry** (the vendor-neutral standard from the [observability series](/blog/posts/observ-05-opentelemetry.html)), which is the right choice for the same reasons that series gives: it's standard, vendor-neutral, and lets you send telemetry to any compatible backend. For a Strands agent this means:

- **Traces of agent runs** — each run traced through its steps: the model's decisions, the tool calls with arguments, the results, and timings. This is distributed tracing (the traces post) applied to the agent's internal loop, turning the model's dynamic path into an inspectable waterfall — exactly what you need to understand an unscripted flow.
- **Metrics** — token usage, latency, tool-call counts, and errors, for monitoring cost and performance (the metrics post) — essential because a model-driven loop's cost and step count are determined by the model, so you must *measure* them rather than assume.
- **Vendor-neutral export** — because it's OpenTelemetry, you send the telemetry to whatever backend you use, no lock-in (the OTel post's core value).

The practical upshot: a Strands agent's behavior — the whole model-driven loop — is observable through standard tooling, so you can trace a run, see exactly what the model decided and why, monitor cost and latency, and diagnose issues. This is the observability discipline from that series, built into the framework because the model-driven approach *demands* it.

## Production concerns

Beyond observability, running model-driven agents in production brings the reliability concerns from across the blog, sharpened by the model driving:

- **Cost monitoring and control** — the model decides how many loop steps and tool calls happen, so cost is model-determined and *variable*; monitor token usage (via the observability above) and apply the cost-playbook levers — caching (agent loops resend growing context, so caching is huge here — the cost playbook's central point), bounded loops, right-sized models. A model-driven loop can be expensive if unwatched.
- **Bounded loops** — cap iterations so a model that doesn't converge fails fast rather than looping and burning budget (the agent-loop post) — critical when the model, not your code, decides when to stop.
- **Error handling** — model and tool calls are unreliable network calls (the networking/distributed-systems series): timeouts, retries, fallback (model-agnosticism enables provider fallback), and graceful degradation; feed tool errors back so the model can adapt.
- **Guardrails and safety** — a model driving autonomously with acting tools needs appropriate guardrails (scoped tools, spend limits as backstops, input/output checks) — the autonomy is powerful and needs boundaries, especially since you're trusting the model's decisions.
- **Deployment** — Strands is production-oriented (AWS uses it internally) and deployable in standard ways; the production disciplines (observability, cost control, resilience) are what make a deployment dependable, not the deployment mechanism itself.

The theme is consistent with the whole series: the model-driven approach's autonomy is its strength, and production readiness comes from *bounding and observing* that autonomy — the guardrails and telemetry that turn "the model drives" into "the model drives, and we can see, bound, and trust it."

## Observability as the model-driven complement

The deepest point: **observability is what makes the model-driven approach trustworthy in production.** You traded authored control flow for the model's dynamic planning (the philosophy), gaining simplicity and flexibility — and observability is the price and the enabler: it's how you get back the understanding you gave up. A model-driven agent you can fully observe (trace its decisions, monitor its cost, diagnose its failures) is one you can operate, improve, and trust; one you can't observe is a black box you're hoping works. Strands building observability in on OpenTelemetry, and its production orientation, reflect that the model-driven bet only pays off if you can *see* what the model does. Equip well, bound, and observe — that's operating a Strands agent. The final post covers when Strands is the right choice overall.

## Key takeaways

- Observability is essential (not optional) in a model-driven framework because the model decides the flow at run time — you can't know what the agent did without observing it, debugging requires seeing the model's decisions, and supervision (not scripting) is how you steer, so observation is the developer's core tool.
- Strands builds observability on OpenTelemetry (vendor-neutral, standard): traces of agent runs (the model's decisions, tool calls, results, timings — turning the unscripted flow into an inspectable waterfall), metrics (tokens, latency, tool calls, errors), and export to any backend.
- Production cost is model-determined and variable (the model decides loop steps and tool calls), so monitor token usage and apply cost-playbook levers — caching is especially large because agent loops resend growing context — plus bounded loops and right-sized models.
- Reliability brings the standard disciplines sharpened by model autonomy: bounded loops (fail fast, don't burn budget), error handling with retries/fallback (model-agnosticism enables provider fallback), and guardrails/safety (scoped tools, spend backstops) for an autonomously-driving model with acting tools.
- Observability is the complement that makes model-driven trustworthy: you traded authored control flow for the model's planning, and observability gives back the understanding — a fully-observable model-driven agent can be operated, improved, and trusted; an unobservable one is a black box you're hoping works.

## Further reading

- [Multi-agent systems (previous post)](/blog/posts/strands-06-multi-agent.html)
- [Observability Engineering series — OpenTelemetry and tracing](/blog/series/observability-engineering/)
- [The AI Cost Optimization Playbook — controlling agent cost](/blog/series/the-ai-cost-optimization-playbook/)
