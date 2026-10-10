# What LLMOps Is — and Why It's Not Just MLOps

*Getting an LLM feature to work in a demo is easy; keeping it working, safe, and affordable in production for a year is a different discipline entirely. That discipline is LLMOps — the operational practices for running LLM-powered applications in production. It inherits a lot from MLOps, but the differences are sharp enough that treating an LLM app like a traditional ML model is one of the most common and expensive mistakes teams make. This series is about the operational layer that the demo never shows you.*

This series is the hands-on operational companion to [The AI Production Roadmap](/blog/series/the-ai-production-roadmap/), which surveys the whole journey from prototype to production. Here we go deep on one slice of it: the day-to-day engineering discipline of *operating* an LLM application after launch. Post 1 defines LLMOps, contrasts it with MLOps, and names the properties of LLMs that force a different operational playbook.

## From MLOps to LLMOps

**MLOps** is the established practice of operationalizing machine-learning models: versioning data and models, automating training pipelines, deploying models as services, and monitoring them for drift. It grew up around models that teams *train themselves* on their own data, where the central artifacts are the training dataset and the model weights, and the central risk is the model degrading as the world changes.

**LLMOps** is MLOps adapted to a world where the model is usually a *foundation model you didn't train* — accessed through an API or self-hosted — and where you build behavior not by training but by **prompting, retrieval, and orchestration**. That shift moves the center of gravity. You're rarely managing a training run; you're managing prompts, context, chains of model calls, and the quality of generated *text* rather than the accuracy of a numeric prediction. Much of the MLOps mindset carries over — versioning, automation, monitoring, reproducibility — but *what* you version and monitor changes completely.

## What makes LLMs operationally different

Five properties of LLMs break assumptions that traditional ML tooling took for granted:

- **The model is often external and opaque.** You call a provider's API; you don't own the weights, can't inspect them, and the provider can update the model under you — so "the same input gives the same output forever" is false. Your dependency is a moving target.
- **Behavior is defined by prompts, not weights.** The main thing *you* control and change is the prompt and the context you assemble (retrieval, tools, history). Prompts become first-class, versioned artifacts — and a one-line prompt edit can change behavior as much as retraining a classical model.
- **Outputs are open-ended text, so "correct" is fuzzy.** A classifier is right or wrong; an LLM answer can be accurate, helpful, safe, well-formatted, and on-brand to *varying degrees* at once. There's no single accuracy number — evaluation is a hard problem in its own right (posts 4–5).
- **Non-determinism is the default.** The same prompt can yield different outputs run to run. You can't rely on exact-match tests, and reproducing a bug is genuinely harder.
- **New failure modes and new costs.** Hallucination, prompt injection, and unsafe output are failure classes classical ML didn't have (post 6); and every request costs money and latency proportional to tokens, making **cost and latency first-class operational concerns** (post 8), not afterthoughts.

Together these mean you can't bolt an LLM onto an MLOps pipeline and call it done. The artifacts, the tests, the monitoring signals, and the risks are all different.

## Why this is a discipline, not a checklist

The reason LLMOps deserves its own series is that the gap between "works in the demo" and "works in production" is enormous and specific. The [AI Production Roadmap](/blog/series/the-ai-production-roadmap/) names *why prototypes don't ship*; LLMOps is the set of practices that close that gap and keep it closed:
- You need to **version and test prompts** like code, because they're the thing that changes most and breaks most (posts 2–3).
- You need **evaluation you trust**, offline and online, because "looks good to me" doesn't survive contact with real users and non-determinism (posts 4–5).
- You need **guardrails** because open-ended generation has open-ended ways to go wrong (post 6).
- You need **observability built for traces and tokens**, not just request counts, because debugging a multi-step LLM pipeline is impossible without it (post 7).
- You need to **operate it as a product** — cost, latency, drift, incidents, continuous improvement — because the model underneath you and the users in front of you both keep changing (post 8).

The throughline of the series: an LLM app is never "done." It's a living system whose behavior drifts from both ends — the provider updates the model, and users find inputs you never imagined — so LLMOps is the discipline of keeping a non-deterministic, externally-owned, fuzzily-correct system trustworthy over time. That's a real engineering practice, and it's what the rest of these posts build.

The takeaway: **LLMOps** is MLOps adapted for applications built on foundation models you usually *didn't train* — where behavior comes from **prompts, retrieval, and orchestration** rather than training runs, so the artifacts you version and monitor change completely. Five properties force a different playbook: the model is **external and opaque** (and updates under you), behavior lives in **prompts** (first-class versioned artifacts), outputs are **open-ended text** (no single accuracy number), **non-determinism** is the default (no exact-match tests), and there are **new failure modes and token-based costs**. The result is a genuine discipline for keeping a non-deterministic, externally-owned, fuzzily-correct system safe and affordable over time — because an LLM app is never "done."

## Key takeaways

- **MLOps** operationalizes models a team *trains itself* (central artifacts: training data + weights; central risk: drift). **LLMOps** adapts it for **foundation models you didn't train**, where behavior comes from prompting/retrieval/orchestration — shifting what you version and monitor.
- LLMs are operationally different in five ways: the model is **external/opaque** and changes under you; behavior is set by **prompts** (versioned artifacts, not weights); outputs are **open-ended text** (fuzzy correctness, no single accuracy); **non-determinism** defeats exact-match tests; and there are **new failures** (hallucination, prompt injection, unsafe output) plus **token cost/latency** as first-class concerns.
- You therefore can't bolt an LLM onto an MLOps pipeline — the artifacts, tests, monitoring signals, and risks are all different.
- LLMOps is the practice that closes the demo-to-production gap and keeps it closed: version/test prompts, trustworthy offline+online eval, guardrails, trace/token observability, and operating it as a product.
- The throughline: an LLM app is **never done** — it drifts from both ends (provider updates the model; users find new inputs) — so LLMOps keeps a living, non-deterministic system trustworthy over time.

## Further reading

- [MLOps — operationalizing machine-learning systems](https://en.wikipedia.org/wiki/MLOps)
- [Large language model — what these systems are](https://en.wikipedia.org/wiki/Large_language_model)
