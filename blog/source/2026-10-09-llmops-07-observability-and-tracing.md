# Observability and Tracing — Seeing Inside an LLM System

*When an LLM application gives a bad answer, "the model messed up" is almost never a useful diagnosis. Was it the retrieval that pulled the wrong document? The prompt template? A tool that returned garbage? The model's generation itself? Without observability built for LLM systems, you can't tell — and you're left re-running prompts hoping to reproduce a non-deterministic failure. This post is about instrumenting an LLM app so that when something goes wrong, you can actually see why.*

Post 2 made "observe" the stage where production behavior becomes visible. This post is how to build that visibility. Standard application monitoring — request counts, error rates, latency — is necessary but nowhere near sufficient, because an LLM app's failures are usually about *content and reasoning steps*, which ordinary metrics don't capture. **Observability** for LLMs means being able to reconstruct and understand any single interaction after the fact, and to see quality and cost trends across all of them.

## Why ordinary monitoring isn't enough

Traditional monitoring answers "is the service up and fast?" For an LLM app the hard questions are different and content-shaped:
- *Why* did this specific user get a wrong or unsafe answer?
- Which step in a multi-step chain or agent run failed?
- Is output quality drifting down over the last week?
- Which prompt version and model produced this output?
- Where is the token spend going, and why did cost spike?

None of these are answerable from HTTP status codes and latency histograms. A request can return `200 OK` in 800ms and still be a hallucinated, unsafe, expensive answer. LLM observability has to capture the *semantic* content of what happened — the inputs, the retrieved context, the intermediate steps, the generated output, and the metadata around them — not just that a request occurred.

## Tracing: the spine of LLM observability

The core technique is **tracing**: recording the full, structured story of a single request as it flows through every step of the pipeline. An LLM request is rarely one model call — it's retrieve → assemble context → call model → maybe call a tool → call model again → apply guardrails → return. A **trace** captures that whole tree as nested **spans**, one per step, each with its inputs, outputs, timing, and metadata.

A good trace lets you answer "what actually happened here?" completely:
- **The full prompt** sent to the model — *after* template rendering and context assembly, which is what the model actually saw (and often where the bug is: the template dropped a variable, retrieval injected the wrong doc).
- **Retrieved context** — which documents/chunks were pulled and with what scores, so you can see whether a bad answer was really a *retrieval* failure (post's cross-link to RAG debugging).
- **Each intermediate step** — tool calls and their results, chain/agent decisions, guardrail actions (what was blocked and why, post 6).
- **The raw model output** before post-processing, plus the model version and decoding parameters (post 3).
- **Token counts, latency, and cost** per step.

With traces, debugging a non-deterministic system becomes tractable: you stop trying to *reproduce* a failure and instead *read the record* of the exact failing interaction. For multi-step agents especially, tracing isn't a nice-to-have — it's the only way to understand behavior that spans a dozen model and tool calls. This is why dedicated LLM-observability tooling exists: it's tracing designed around prompts, retrievals, tokens, and quality rather than generic request spans.

## From traces to signals: metrics, quality, and drift

Individual traces debug single failures; aggregated, the same data drives the whole operate-and-improve stage:
- **Operational metrics** — latency (and its breakdown across steps — often the model call dominates, sometimes retrieval does), token usage, cost per request and in aggregate, error and timeout rates, cache hit rates. These are what you alert on and what feed cost control (post 8).
- **Quality signals over time** — the online evaluation scores and feedback from post 5, tracked as trends so you can *see* quality drifting rather than discovering it through complaints.
- **Drift detection** — watch the *distribution* of inputs and outputs for change. Input drift (users asking new kinds of things) and output drift (the model behaving differently — perhaps because the provider updated it, post 1) are both early-warning signals that your evals and prompts may need updating. **Concept drift** — the world changing underneath a model — is a core ML-monitoring idea that applies directly here.
- **Cost attribution** — break spend down by feature, user, prompt version, and model so a cost spike has an address, not just a number.

The payoff is a system you can *reason about* instead of guess about. When quality dips, you see which metric moved and read the traces behind it; when cost spikes, you see which feature caused it; when the provider silently changes the model, output-drift alarms fire before users complain. Observability is what makes the "improve" arc of the loop possible — you can't fix what you can't see, and in a non-deterministic, multi-step, externally-dependent system, seeing requires deliberate instrumentation. Build it in from the start, because retrofitting traces after an incident is how you discover you logged nothing useful.

The takeaway: ordinary monitoring (status codes, latency, error rates) is necessary but **insufficient** for LLM apps, whose failures are about *content and reasoning steps* — a request can return `200 OK` fast and still be a hallucinated, unsafe, costly answer. LLM **observability** means reconstructing any single interaction and seeing trends across all of them, and its spine is **tracing**: recording a request as a tree of **spans** (retrieve → assemble → model → tool → model → guardrails) capturing the *rendered* prompt, retrieved context with scores, each intermediate step, raw output, model version/params, and per-step tokens/latency/cost. This turns debugging a non-deterministic system from "try to reproduce" into "read the record." Aggregated, the same data yields **operational metrics**, **quality trends**, **drift detection** (input/output/concept drift — early warning that the provider changed the model or users changed), and **cost attribution** — making the loop's "improve" arc possible. Instrument from day one.

## Key takeaways

- Standard monitoring answers "is it up and fast?"; LLM failures are **content-shaped** ("why this wrong/unsafe/expensive answer? which step failed? is quality drifting? which prompt version?") — a `200 OK` in 800ms can still be a hallucinated, unsafe answer, so you must capture **semantic** content, not just request metadata.
- **Tracing** is the spine: record each request as a tree of **spans** (retrieve → assemble context → model → tool → model → guardrails), each with inputs/outputs/timing/metadata.
- A good trace captures the **rendered prompt** the model actually saw (where many bugs hide), **retrieved context + scores** (to localize RAG failures), **each intermediate step** (tool calls, agent decisions, guardrail blocks), **raw output + model version/params**, and **per-step tokens/latency/cost** — turning debugging from "reproduce" into "read the record" (essential for multi-step agents).
- Aggregated traces drive operation: **operational metrics** (latency breakdown, token/cost, error rates, cache hits), **quality trends** (post 5 scores over time), **drift detection** (input/output/**concept drift** — early warning of provider model changes or shifting users), and **cost attribution** (by feature/user/version/model).
- Observability is what makes the **"improve" arc possible** — you can't fix what you can't see; in a non-deterministic, multi-step, externally-dependent system, seeing requires deliberate instrumentation, so **build it in from the start** (retrofitting after an incident is too late).

## Further reading

- [Observability — reconstructing internal state from outputs](https://en.wikipedia.org/wiki/Observability)
- [Concept drift — when the world shifts under a model](https://en.wikipedia.org/wiki/Concept_drift)
