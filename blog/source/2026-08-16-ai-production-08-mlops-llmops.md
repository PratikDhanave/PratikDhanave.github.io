# MLOps / LLMOps: Making Change Safe and Repeatable

*The question this phase answers is simple and unforgiving — can you change the system without breaking it? — and the control you cannot skip is that no ungated change reaches users.*

An AI system is never finished. Models improve, prompts get tuned, retrieval configs change, data refreshes. Each change is a chance to break production. MLOps — or LLMOps for generative systems — is the discipline that makes change *safe and repeatable*: automated pipelines that build, test, evaluate, and deploy code and models and prompts, with gates that block bad changes and automation that rolls them back. This post is Phase 6 of the roadmap, and it is what moves a system up the maturity ladder from manual to automated to governed.

## What's different about AI change management

Ordinary CI/CD versions and ships code. AI change management has to version and ship *more*: not just code, but model versions, prompts, context templates, retrieval configurations, and sometimes data and embeddings. And the test that decides whether a change is safe is not only unit tests — it is the **evaluation suite** from the earlier phase, which is probabilistic and slice-based rather than pass/fail. LLMOps is MLOps with these additional versioned artifacts and with evals as a first-class release gate.

## The pipeline

A mature pipeline runs automatically on every candidate change and does the following before anything reaches users:

1. **Build and version** the changed artifact — code, model, prompt, or retrieval config — with a traceable identifier.
2. **Test** deterministically (unit, integration, contract) as usual.
3. **Evaluate** against the golden set, producing per-variant, per-slice reports compared to the current production baseline.
4. **Gate** on the results: a change that regresses quality or safety on any critical slice does not proceed. This is the non-negotiable control — **no ungated change reaches users.**
5. **Register** the passing artifact in a model/prompt registry with its metadata and eval results.
6. **Deploy** progressively (canary, shadow, flags — from the serving phase) with monitoring.
7. **Roll back** automatically if post-deploy signals regress.

The pipeline is what makes maturity Level 2 ("it ships itself, safely") real, and adding continuous monitoring and audit trails on top of it is what makes Level 3 ("we can prove it's safe").

## The registry as source of truth

A model and prompt registry is the backbone. Every deployable artifact — each model version, each prompt version — lives there with its lineage, its evaluation results, and its approval status, so you can always answer "what exactly is in production, and why did we trust it?" The registry is also what makes rollback meaningful: rolling back is redeploying a previously-registered, previously-passed artifact, not scrambling to reconstruct last week's prompt from someone's memory. Prompt-as-config is powerful here — it lets you change a prompt without a code deploy — but only if the config goes through the same registry, review, and eval gate; an ungoverned prompt config is just an un-versioned prompt with extra steps.

## Prompts and data are part of the pipeline

Two artifacts teams routinely leave outside the pipeline, to their cost:

- **Prompts and context templates.** A prompt change can alter behavior as much as a model change, so it must be versioned, eval-gated, and rolled back like any deployable. Treat it as a release, not a config edit someone makes in production at 5pm.
- **Data and embeddings.** A refresh of the knowledge base or a re-embedding is a change that can regress retrieval quality. It should trigger the same evaluation and gating as a code change. Silent data updates are a classic source of "nothing changed but quality dropped."

## Continuous evaluation and retraining

Beyond gating individual changes, mature systems evaluate *continuously* — running the eval suite (or a sampled version) against live behavior on a schedule, so quality regressions from drift, provider model updates, or data changes are caught even when *you* didn't change anything. Where the system retrains or re-tunes, that retraining is itself a gated pipeline: new data in, evaluation, gate, register, deploy — never an unevaluated model promoted because it's newer. The highest maturity level automates this loop under control, but automation without the gate is just faster breakage.

## The gate and anti-patterns

Phase 6 is done when code, models, and prompts all flow through an automated pipeline with deterministic tests *and* eval gates; a registry holds every deployable artifact with lineage and results; deployment is progressive with automated rollback; and data/embedding changes are gated like code. Avoid the recurring failures: manual, human-triggered deploys with no eval gate; prompts and data changed directly in production outside the pipeline; a "registry" that is a folder of files no one trusts; and treating a newer model as automatically better without re-evaluation.

## Key takeaways

- MLOps/LLMOps makes change safe and repeatable; the non-skippable control is that no ungated change — code, model, prompt, or data — reaches users.
- AI change management versions more than code (models, prompts, context templates, retrieval configs, embeddings) and uses the evaluation suite, not just unit tests, as the release gate.
- The pipeline is build → test → evaluate against baseline → gate → register → deploy progressively → auto-rollback; that gate is what makes maturity Level 2/3 real.
- A model/prompt registry is the source of truth and what makes rollback meaningful; prompt-as-config only works inside the same registry, review, and eval gate.
- Put prompts and data/embedding changes through the pipeline too, and evaluate continuously so drift and provider updates are caught even when you changed nothing.

## Further reading

- [NIST AI Risk Management Framework](https://www.nist.gov/itl/ai-risk-management-framework)
- [Evaluation (Agentic RAG series)](/blog/series/agentic-rag/)
- [DevSecOps series](/blog/series/devsecops/)
