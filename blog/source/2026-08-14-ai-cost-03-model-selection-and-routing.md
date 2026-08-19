# Model Selection and Routing

*The single biggest cost lever in most AI systems is not clever prompting — it is not using an expensive model for work a cheap one would do just as well.*

Prices vary enormously across models: the most capable frontier models can cost many times more per token than smaller, faster ones. That spread makes model choice the highest-leverage cost decision in most systems, because it applies a multiplier to every single call. Using a frontier model for a task a small model handles perfectly is overpaying on every request, forever. This third post in the AI cost optimization series is about right-sizing the model to the task, and routing requests to the cheapest model that can actually do the job.

## Match the model to the task, not the ambition

The instinct to reach for the most capable model "to be safe" is expensive and usually unnecessary. Many tasks in a real system are not hard: classifying a message, extracting fields from text, routing a request, summarizing a short passage, answering from provided context. These are well within the reach of smaller, cheaper models. Reserving the frontier model for the genuinely hard reasoning — and using small models for everything else — often cuts cost dramatically with no loss in quality, because the cheap model was never the bottleneck on the easy tasks.

The discipline is to ask, per task: what is the *smallest* model that does this acceptably? Not the best model available, but the cheapest one that clears the quality bar. That question, asked honestly for each distinct task in your system, is where most of the savings in this entire series come from.

## Not every system is one model

A subtle but important shift: a mature AI system is rarely a single model behind everything. It is a collection of tasks, each of which can use a different model. The classification step uses a small model; the final answer generation might use a larger one; a formatting cleanup uses a tiny one. Treating "which model" as one global decision leaves money on the table. Treating it as a per-task decision — right-sizing each step — is how you spend capability only where it earns its keep.

## Routing: choosing the model per request

Beyond static per-task assignment, you can choose the model *dynamically per request* based on difficulty. This is routing, and it comes in two common shapes.

**A router** inspects an incoming request and sends it to an appropriate model — easy queries to a cheap model, hard ones to an expensive model. The routing decision itself must be cheaper than the savings it produces (often a small classifier or a cheap model making the call), or it defeats its own purpose. Done well, a router means you pay frontier prices only for the fraction of traffic that genuinely needs it.

**A cascade** tries the cheap model first and escalates to a more expensive one only if the cheap result is inadequate. The cheap model attempts the task; a check (a confidence signal, a validation, a verifier) decides whether the answer is good enough; if not, the request falls through to a stronger model. When the cheap model succeeds often — which for many workloads it does — the cascade pays cheap prices most of the time and expensive prices only on the hard tail. The cost of the occasional double call is outweighed by the savings on everything the cheap model handled alone.

Both patterns share a principle: **default to cheap, escalate on demand.** The expensive model becomes the exception, not the rule.

## The quality guardrail

Cost optimization that degrades quality is not optimization — it is just cutting corners. Routing and right-sizing only work if you *measure* that the cheaper model actually meets the bar for the tasks you send it. That requires an evaluation: a set of representative cases and a way to score whether the cheap model's output is acceptable. Without it, you are guessing that the small model is good enough, and guessing wrong shows up as user-facing quality regressions, not on the cost dashboard. Build the eval first, then route against it — and re-check when models change, because the cheapest model that clears the bar shifts as new models ship.

## Beyond hosted models

Model selection also spans a bigger axis: hosted API models versus open models you run yourself. Open models can be cheaper at high, steady volume where you can keep hardware utilized, but they carry infrastructure, operational, and utilization costs that only pay off past a threshold. For most teams and most traffic, hosted APIs are more economical because you pay only for what you use and someone else bears the serving cost. This build-versus-buy trade-off is real but deserves its own analysis; the later post on RAG and fine-tuning trade-offs returns to it. The point here is that "which model" includes "hosted or self-run," and the answer depends on your volume and utilization, not on a blanket rule.

## Key takeaways

- Per-token prices vary enormously across models, so model choice is the highest-leverage cost decision — it multiplies every call.
- Right-size per task: ask for the *cheapest* model that clears the quality bar, not the most capable available; many tasks (classification, extraction, routing, short summaries) do not need a frontier model.
- Treat model choice as a per-task decision, not one global one — a mature system uses different models for different steps.
- Route dynamically with a router (send each request to an appropriate model) or a cascade (try cheap first, escalate only if inadequate); default to cheap, escalate on demand.
- Guard quality with a real evaluation — measure that the cheaper model meets the bar before routing to it, and re-check as models change; also weigh hosted APIs vs self-hosting by your volume and utilization.

## Further reading

- [OpenAI Cookbook](https://github.com/openai/openai-cookbook)
- [Anthropic documentation](https://docs.anthropic.com)
- [Hugging Face — Open LLM models](https://huggingface.co/models)
