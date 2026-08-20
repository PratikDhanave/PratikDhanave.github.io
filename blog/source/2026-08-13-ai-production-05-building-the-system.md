# Building the System: Compose Before You Train

*Modern production AI is rarely "a model" — it is a foundation model wrapped in retrieval, context engineering, tools, and guardrails — and the biggest architectural mistake is reaching for fine-tuning before exhausting the cheaper, more reversible options.*

With a governed data foundation in place, this phase turns it into a working AI *system*: model or models, plus the orchestration, retrieval, prompting, tools, and guardrails around them. The defining discipline here is knowing *which* adaptation to reach for and in what order — because the instinct to fine-tune first is expensive, hard to reverse, and usually solves the wrong problem. This post is Phase 3 of the roadmap.

## Development is experimentation, disciplined

Building an AI system is not a single build; it is inner and outer loops of experimentation. The discipline is to make that experimentation *reproducible*: version prompts, context templates, retrieval configs, model versions, and hyper-parameters, and log every run so a result can be traced to the exact configuration that produced it. An un-versioned prompt is config no one owns and behavior no one can reproduce — the most common cause of "it worked yesterday" in production AI.

## The adaptation ladder

The single most valuable rule in this phase is to sequence adaptation from cheapest and most reversible to most committed, adopting each rung only when the prior one is demonstrably insufficient on your evaluations:

1. **Prompt and context engineering** — shape what the model sees. Cheapest, most reversible. Ship here if it passes your evals.
2. **Retrieval augmentation (RAG)** — when the failure is a knowledge, recency, or grounding gap.
3. **Parameter-efficient fine-tuning (LoRA/PEFT)** — when the failure is behavior, format, style, or tone, the domain is stable, and you have many high-quality examples.
4. **Full fine-tuning or preference optimization** — the last resort: costly, least reversible.

The correctness rule architects most often get wrong: **RAG is for knowledge; fine-tuning is for form and behavior.** Fine-tuning does not reliably teach new facts — it teaches style, format, and task adherence. If the problem is "the model doesn't know X," reach for retrieval, not training. Each rung up increases cost and decreases reversibility, forces re-evaluation, and — for RAG — may force re-embedding the corpus. There is even a serving consequence: custom fine-tuned models often require reserved throughput to serve, which the deployment phase has to plan for.

## Context engineering as a first-class discipline

The assembly of the model's context window — instructions, retrieved evidence, tools, memory, and history — is not ad-hoc prompt tweaking; it is an engineering discipline with its own tests and version control. What you place in the window, in what order, within a token budget, often determines the answer before the model runs. Treat prompts as a managed system: a registry with dev/staging/prod environments, rollback, and variant routing, and a deliberate choice between prompt-as-config (decoupled from code deploys, but needing its own review and eval gate) and prompt-as-code. This is deep enough to be its own subject — I've written a full [Context Engineering](/blog/series/context-engineering/) series — but at minimum, version it and test it.

## Agents, only when they earn it

For tasks needing planning, tool use, and multi-step reasoning, design agent loops with explicit tool contracts, memory, termination conditions, and guardrails. Standardize tool integration (for example via the Model Context Protocol) so tools are reusable and governable. But reach for the *simplest* architecture that meets the requirement — multi-agent complexity must earn its keep.

The math is unforgiving. With per-step success probability `p` over `n` steps, end-to-end reliability is roughly `pⁿ`, and `N` agents cost about `N×` the tokens. That is why "more agents" is usually the wrong answer. Start with a single well-engineered call or a single ReAct-style agent; add a supervisor-and-workers or a pipeline only when a single agent provably cannot do the job. When you do build agents, enforce tool-calling contracts (structured output, result validation, idempotency and retries for side-effecting tools), design memory deliberately (short-term context versus long-term store, compacted before overflow), and bound execution (max steps, token and wall-clock budgets, and a human gate for consequential actions).

## Guardrails from the first iteration

Do not defer safety to a post-hoc layer. Build input and output validation, schema enforcement, grounding checks, and content-safety hooks into the system from the first iteration. The most reliable output-safety mechanism is **constrained decoding** — JSON-schema or grammar-constrained generation, and function-calling used as a validation boundary — rather than generating free text and hoping a post-hoc check catches problems. Serving-time enforcement comes later in the roadmap, but the hooks belong in the system now.

## Keep the model swappable

Models become obsolete fast, so design for adaptability: choose your foundation model against explicit criteria — task quality measured by *your* evaluations rather than vendor benchmarks alone, latency, context window, tool-calling support, modality, data residency, licensing, and cost per token — and keep the choice swappable behind an interface. A system welded to one model is a system that ages badly the moment a better or cheaper one ships.

## The gate and anti-patterns

Phase 3 is done when a working end-to-end system exists on curated data, reproducible from versioned artifacts; model and adaptation choices are recorded with rationale and are swappable; and development-time guardrails are present. Avoid the recurring failures: prompt-tweaking with no eval to say whether a change helped; fine-tuning before exhausting prompt, context, and retrieval; multi-agent theater that a single well-engineered call would handle better; and un-versioned prompts that make production behavior irreproducible.

## Key takeaways

- Production AI is a composed system (model + retrieval + context + tools + guardrails), built through disciplined, reproducible experimentation with everything versioned.
- Climb the adaptation ladder cheapest-first: prompt/context → RAG → PEFT → full fine-tune, adopting each rung only when evals prove the prior one insufficient.
- RAG is for knowledge; fine-tuning is for form and behavior — don't fine-tune to teach facts; each rung up costs more and is less reversible.
- Treat context engineering as a versioned, tested discipline; add agents only when a single call can't do it (reliability ≈ pⁿ, cost ≈ N×), with tool contracts, bounded execution, and human gates.
- Build guardrails (validation, grounding, constrained decoding) from the first iteration and keep the model swappable behind an interface, chosen on your own evals.

## Further reading

- [Context Engineering series](/blog/series/context-engineering/)
- [Agentic RAG series](/blog/series/agentic-rag/)
- [Model Context Protocol from Scratch series](/blog/series/model-context-protocol-from-scratch/)
