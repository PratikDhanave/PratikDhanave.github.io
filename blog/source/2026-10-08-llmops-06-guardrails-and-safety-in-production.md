# Guardrails and Safety in Production — Containing Open-Ended Output

*An LLM can say anything, which is exactly the problem. The same open-endedness that makes it useful means it can hallucinate, leak data, follow a malicious instruction hidden in its input, or produce something harmful — and in production, in front of real users, those aren't edge cases, they're inevitabilities. Guardrails are the controls that sit around the model to contain what it might do. This post covers the new failure modes LLMs introduce and the layered defenses that keep a production system safe.*

Post 1 listed hallucination, prompt injection, and unsafe output as failure classes classical ML didn't have. This post is how you defend against them operationally. The framing that matters: you cannot make the model itself trustworthy by wishing — you assume it *will* occasionally misbehave and build a system around it that catches and contains the misbehavior. Guardrails are that system.

## The new failure modes

LLMs bring risks that traditional software and classical ML simply didn't have, and each needs a specific defense:

- **Hallucination** — the model states something false with complete confidence. It's not a bug to be patched out; it's a property of how these models work. The operational answer is grounding (retrieval with citations), constraining claims, and verification — never assuming output is factual.
- **Prompt injection** — the defining new attack. Because the model can't reliably distinguish its *instructions* from the *data* it's processing, a malicious instruction embedded in user input or in a retrieved document ("ignore your rules and do X") can hijack its behavior. This is especially dangerous in agentic systems with tools, where a hijack can take *actions*, and in RAG systems where retrieved content is attacker-influenced.
- **Sensitive-data leakage** — the model emits PII, secrets, or another user's data — from its training, its context window, or a confused retrieval. Both inputs and outputs need scrubbing.
- **Harmful / off-brand / off-topic output** — toxic content, unsafe advice, competitor promotion, or answering wildly outside the intended scope. "Can say anything" includes things that damage users or the brand.

The unifying point: these are not rare corner cases you can test away. In production, at scale, someone *will* hit each of them — often adversarially and on purpose — so safety is a runtime containment problem, not a pre-launch checkbox.

## Layered guardrails: input, output, and action

The defense is **defense in depth** — independent checks at each point where things can go wrong, so no single failure reaches the user or the world:

- **Input guardrails** (before the model) — screen incoming requests: detect and defang prompt-injection attempts, strip or mask PII, filter abusive or out-of-scope requests, enforce rate limits. The goal is to keep obviously bad or dangerous input from ever reaching the model.
- **Output guardrails** (after the model, before the user) — screen what comes back: scan for toxic or unsafe content, PII leakage, and policy violations; validate structure (does it parse, does it meet the schema from post 3); check groundedness (are claims supported by the retrieved context, or invented?). Output filtering is the last line before a user sees anything.
- **Action guardrails** (for agents/tools) — the highest-stakes layer: constrain what the model is *allowed to do*. Scope tool permissions tightly, require confirmation for irreversible or high-impact actions, sandbox execution, and never give the model more authority than the task needs. If the model can only read, a hijack can't delete.

Across all layers, two principles apply. **Fail closed**: when a guardrail is unsure, the safe default is to block, ask for confirmation, or hand off to a human — not to let it through. And **keep humans in the loop where stakes demand it**: for consequential decisions, the guardrail is a person approving, not an automated check. Layering matters because each guardrail is itself imperfect; the safety comes from several independent ones, so defeating all of them at once is hard.

## Guardrails are part of the lifecycle

Safety isn't a wall you build once — it's woven through the loop (post 2) and improves with it:
- **Guardrails have false positives.** Over-aggressive filtering blocks legitimate requests and frustrates users, so guardrails themselves must be *evaluated* (post 4) and tuned for the right balance — too loose is unsafe, too tight is useless. The eval set should include both attacks (must block) and legitimate-but-edgy cases (must allow).
- **New attacks appear continuously.** Prompt-injection techniques evolve, so observed attacks in production (post 5) become new guardrail rules and new eval cases — the same backward flow that drives quality drives safety.
- **Observability makes guardrails auditable.** You log what was blocked and why (post 7), so you can see attack patterns, measure false-positive rates, and prove the system behaved safely after an incident.
- **Red-teaming** — proactively attack your own system (adversarial prompts, injection attempts, jailbreaks) before adversaries do, and fold what you find back into guardrails and evals.

The mindset that makes this work is assuming breach: the model is a powerful, fallible component you don't fully control, operating in an adversarial environment, so you build independent, fail-closed, continuously-updated controls around it. Teams that skip this ship a demo that works until the first motivated user — or the first poisoned document — turns the model against them.

The takeaway: an LLM's open-endedness makes new failure modes **inevitable** in production — **hallucination** (confident falsehood, a property not a bug), **prompt injection** (the defining attack: malicious instructions in input or retrieved data hijack the model, worst in tool-using agents), **sensitive-data leakage**, and **harmful/off-brand/off-topic output** — so safety is runtime containment, not a pre-launch checkbox. Defend with **layered, fail-closed guardrails**: **input** (defang injection, mask PII, filter scope), **output** (toxicity/PII/policy/structure/groundedness checks before the user), and **action** (tightly scoped tool permissions, confirmation for irreversible actions, sandboxing) — with **humans in the loop** where stakes demand. And treat guardrails as part of the lifecycle: **evaluate and tune** them (false positives frustrate users), turn production attacks into new rules and eval cases, log for auditability, and **red-team** proactively — assuming breach throughout.

## Key takeaways

- LLM open-endedness makes four failure classes **inevitable at scale** (often adversarial): **hallucination** (confident falsehood — a property of the model, answered by grounding/citations/verification), **prompt injection** (malicious instructions in user input or retrieved docs hijack behavior — worst in agents with tools and in RAG), **sensitive-data leakage** (PII/secrets/other users' data), and **harmful/off-brand/off-topic output**.
- Safety is **runtime containment, not a pre-launch checkbox**: assume the model *will* misbehave and build a system that catches and contains it.
- Use **defense in depth** across three layers: **input guardrails** (defang injection, mask PII, filter abuse/scope), **output guardrails** (toxicity/PII/policy/schema/groundedness checks before the user sees output), and **action guardrails** (scope tool permissions, confirm irreversible actions, sandbox — never more authority than the task needs).
- Two cross-cutting principles: **fail closed** (when unsure, block/confirm/escalate, don't pass through) and **humans in the loop** for consequential decisions; layering matters because each guardrail is itself imperfect.
- Guardrails are part of the **lifecycle**: **evaluate and tune** them (over-aggressive filtering has costly false positives), turn production attacks (post 5) into new rules + eval cases, **log** blocks for auditability (post 7), and **red-team** proactively — assume breach.

## Further reading

- [Prompt injection — the defining LLM attack](https://en.wikipedia.org/wiki/Prompt_injection)
- [AI safety — building systems that behave safely](https://en.wikipedia.org/wiki/AI_safety)
