# Model Providers

*The model drives a Strands agent, so which model you use is the single biggest determinant of how well it works — and Strands keeps that a swappable choice across providers rather than locking you to one. Model-agnosticism isn't a convenience here; in a model-driven framework it's foundational.*

Strands is model-driven, so the model is the most important component — and this post covers **model providers**: how Strands stays model-agnostic across providers (Bedrock, Anthropic, and others), why that matters more in a model-driven framework than elsewhere, and how model choice interacts with the model-driven approach. If the model drives, the model *is* the agent, and keeping it swappable is essential.

## Model-agnostic by design

Although Strands comes from AWS, it is **model-agnostic** — it supports multiple model providers (including Amazon Bedrock, Anthropic, and others), not just AWS's own. You choose the model provider when defining the agent, and swapping it is a configuration change, not a rewrite:

```python
# Illustrative shape — see the Strands docs for exact API.
agent = Agent(model=bedrock_model, system_prompt=..., tools=[...])
# swap the provider without changing the agent's logic:
agent = Agent(model=anthropic_model, system_prompt=..., tools=[...])
```

This reflects the keep-the-model-swappable principle from the [AI Architecture Decisions](/blog/posts/ai-decisions-01-how-to-choose.html) series, and it's notable that an AWS framework is deliberately provider-agnostic rather than Bedrock-only — it works well in AWS environments (natural Bedrock integration) but doesn't lock you there. The agent's definition (prompt, tools, loop) is independent of the provider, so the model is a pluggable choice.

## Why model choice matters more here

Model-agnosticism is valuable in any framework, but in a *model-driven* framework it's foundational, for a specific reason: **the model drives the agent, so the model's capability directly determines the agent's capability.** In a heavily workflow-first framework, a weaker model can still perform because the developer's orchestration carries much of the intelligence; in Strands, there's no orchestration to compensate — the model does the planning, deciding, and adapting. So:

- **A more capable model makes a Strands agent meaningfully better** — better planning, better tool selection, better adaptation — because the model *is* where the intelligence lives (the model-driven bet). The model choice isn't one factor among many; it's *the* factor.
- **The model-driven approach assumes a sufficiently capable model** (the limits from the philosophy post) — so choosing a model capable enough to drive the loop for your task is a first-order decision, not a detail.
- **Model choice interacts with cost per task** — the cost-playbook lesson applies: a more capable model that drives the loop in fewer steps can cost *less per completed task* despite a higher per-token price (the model-selection post), and in a model-driven agent this effect is pronounced because the model controls how many steps the loop takes.

So in Strands, "which model" is among the most consequential decisions you make — more so than in frameworks where orchestration carries the load. Model-agnosticism gives you the freedom to make that choice well and revisit it, which matters precisely because the choice matters so much.

## Model choice as a cost and reliability lever

Because the model is swappable and central, it becomes a lever for cost, reliability, and capability — the same production levers as the Pydantic AI and cost series, sharpened by the model-driven design:

- **Cost** — route to the model that minimizes cost per completed task for your workload (measure it — the cost playbook's discipline), and consider that a capable model driving efficiently may beat a cheap one that flails through many loop steps. Model-agnosticism makes this routing cheap to implement.
- **Reliability** — the ability to swap providers enables fallback (route to an alternative if one is down or rate-limited) — the resilience benefit of provider-agnosticism.
- **Capability evolution** — as better models arrive, a model-agnostic agent adopts them by configuration, so your agent improves as models improve *without a rewrite* — which compounds the model-driven bet (the approach ages with model capability, and agnosticism lets you ride that curve).

That last point is worth emphasizing: the model-driven approach bets on models getting better (the philosophy post), and model-agnosticism is what lets a Strands agent *capture* that improvement — swap in the better model and the agent gets better, no code change. The two design choices (model-driven + model-agnostic) reinforce each other: the model drives, so improvements in the model directly improve the agent, and agnosticism lets you adopt those improvements freely.

## Choosing and using models in Strands

Practical guidance, tying it together:

- **Choose a model capable enough to drive your task's loop** — since the model does the planning, its capability is the agent's capability; the model-driven approach needs a sufficiently strong model.
- **Measure cost per completed task, not per token** — a capable model driving in fewer steps can be cheaper per task (the cost-playbook lesson), and the model controls the step count in a model-driven agent.
- **Keep the model swappable and revisit the choice** — use model-agnosticism to route by cost/capability, enable fallback for reliability, and adopt better models as they arrive by configuration.
- **Match model to environment where convenient** — Bedrock integrates naturally in AWS environments, but you're free to use any supported provider; let requirements, not the framework's origin, drive the choice.

The model is the beating heart of a Strands agent — it drives everything — and Strands keeping it a swappable, provider-agnostic choice is what lets you put the *right* heart in and upgrade it over time. The next post covers building systems of multiple agents when one isn't enough.

## Key takeaways

- Strands is model-agnostic despite its AWS origin — supporting Bedrock, Anthropic, and other providers as a swappable configuration choice — reflecting the keep-the-model-swappable principle, with natural Bedrock integration in AWS environments but no lock-in.
- Model choice matters more in a model-driven framework because the model drives the agent: there's no orchestration to compensate for a weaker model, so the model's capability directly determines the agent's capability — "which model" is *the* first-order decision.
- The model-driven approach assumes a sufficiently capable model, and model choice interacts strongly with cost per completed task (a capable model driving in fewer loop steps can cost less per task despite higher per-token price — and the model controls the step count).
- Swappability makes the model a cost lever (route to cheapest-per-task, measured), a reliability lever (fallback across providers), and a capability lever (adopt better models by configuration as they arrive).
- Model-driven and model-agnostic reinforce each other: the model drives so its improvements directly improve the agent, and agnosticism lets you capture those improvements freely — choose a model capable enough to drive your task, measure cost per task, and keep it swappable.

## Further reading

- [Tools (previous post)](/blog/posts/strands-04-tools.html)
- [The AI Cost Optimization Playbook: model selection](/blog/posts/aicostplay-04-model-selection-and-audits.html)
- [Strands Agents documentation](https://strandsagents.com/)
