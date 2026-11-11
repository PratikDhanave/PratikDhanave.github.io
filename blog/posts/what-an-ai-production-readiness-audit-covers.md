<!-- Markdown version for AI agents and readers. Canonical: https://pratikdhanave.com/blog/posts/what-an-ai-production-readiness-audit-covers.html -->

# What an AI Production Readiness Audit Actually Covers

*"Is our AI system ready for production?" is a question most teams answer with a feeling. An audit replaces the feeling with evidence: a structured pass over the six dimensions that decide whether an AI system survives real users, real data, real cost, and a real security review. Here's exactly what mine covers and what you walk away with — useful even if you run it yourself.*

I run this audit as a [fixed-scope engagement](/services/ai-production-readiness-audit/), but the dimensions aren't a secret — they're the checklist I wish every team ran before their launch date was already public. If you take nothing else from this post: audit *before* the incident, not after.

## Dimension 1: Success criteria — does "working" have a definition?

The first question isn't technical: is there a written statement of what this system must do, how well, measured how, signed off by whom? Not "it should answer accurately" — a bar: *on this task, against this evaluation set, at this threshold, this person accepts it.* Most systems I audit don't have one, and its absence explains most of what follows — you can't evaluate, monitor, or improve against a feeling. Red flags: "good" defined differently by three stakeholders; acceptance meaning "the demo impressed us"; no named sign-off.

## Dimension 2: Evaluation — can you prove it, repeatably?

Given a bar, can the team demonstrate pass/fail on real, representative data — including the ugly tail — on demand? I'm looking for an evaluation set that mirrors production inputs (not the clean cases the demo used), scoring that matches the task (deterministic checks where possible, calibrated judges or human review where not), and the ability to re-run it after any change — because a prompt tweak, model upgrade, or retrieval change without a regression gate is how working systems silently stop working. Red flags: "we tested it a lot" with nothing written; eval data the model was effectively built on; no way to compare last month to today.

## Dimension 3: Grounding and data — where do answers come from?

For retrieval-grounded systems: is the corpus the system reads *current, canonical, and access-controlled*? I trace real answers back to their sources, look for the stale-document problem (the AI citing a policy that changed), conflicting sources, and the retrieval misses that cause confident invention. And the access question — does the system respect who may see what, inherited from source systems rather than re-invented? — because a chatbot that summarizes documents to people who couldn't open them is a breach with good UX. Red flags: no corpus owner; "everything in the wiki" as the grounding strategy; access control checked at the UI and nowhere else.

## Dimension 4: Cost and latency — does the unit economics survive volume?

A system that delights ten pilot users can be unshippable at ten thousand. I work out cost per request and per outcome at projected volume (tokens, retrieval, re-ranking, retries — the multipliers hide in the retries), where latency actually goes, and which levers exist (caching, routing cheaper models for easier cases, batching, prompt hygiene). This is routinely where audits pay for themselves — most unaudited systems carry 30–60% waste from prompt bloat, over-retrieval, and premium models doing commodity work, which is consistent with the FinOps discipline from my [infrastructure cost work](/case-studies/). Red flags: nobody can state cost per request; the latency budget is "it feels fine"; one model does everything.

## Dimension 5: Security — would this survive a hostile review?

The AI-specific pass, beyond classical appsec: what happens when adversarial instructions arrive *inside* the content the system reads (prompt injection — and if the system reads email, documents, or the web, they will); what data could the system be talked into revealing; if it's an agent, what can it actually *do* — what credentials it holds, what its blast radius is, whether a kill switch exists and someone knows where. Plus the unglamorous essentials: logging of prompts, retrievals, and actions good enough to reconstruct an incident. Red flags: "the model provider handles security"; an agent with a human's service account; no one has ever tried to break it on purpose.

## Dimension 6: Reliability and ownership — who runs this on Tuesday?

Production is a Tuesday problem, not a launch problem. Is there monitoring that would notice quality degrading (not just uptime — *answer quality*, drift, cost creep)? What happens when the model provider has an incident — fallback, degradation, or outage? And the decisive question: is there a named owner with the skills and the mandate to operate, evaluate, and evolve this system after the people who built it move on? Red flags: monitoring is a dashboard nobody reads; the provider's status page is the incident plan; ownership is "the team," which is no one.

## What you get, and what it's not

The output is three things: a **findings report** across the six dimensions — what's genuinely production-ready, what isn't, what's highest-risk; a **prioritized, sequenced action plan** (close these gaps in this order, with effort estimates — some gaps are an afternoon, some re-sequence the launch); and an honest **verdict**: ship it, ship it with these controls, or don't ship this yet — and here's the shortest path to yes. What it's not: a certificate, a rubber stamp, or a sales ambush — "you're closer than you think, fix these two things yourself" is a real and common outcome, and the [two-minute self-check](/ai-readiness/) is genuinely free if you want the quick version first. If the full pass would help, [the audit is a fixed-scope booking](/services/ai-production-readiness-audit/) — and either way, the six dimensions above are yours to run.

## Key takeaways

- The audit covers six dimensions: **success criteria** (a written bar), **evaluation** (repeatable proof on real data), **grounding** (current, canonical, access-controlled sources), **cost & latency** (unit economics at volume), **security** (injection, data exposure, agent blast radius), **reliability & ownership** (who runs it on Tuesday).
- Most findings trace back to dimension 1: without a written definition of "working," evaluation, monitoring, and improvement have nothing to aim at.
- The economics dimension usually self-funds the audit — prompt bloat, over-retrieval, and premium-models-for-commodity-work are near-universal.
- Output = findings + a sequenced action plan + an honest ship/don't-ship verdict — not a certificate, and sometimes the verdict is "fix two things yourself."

## Further reading

- [Audit — structured, evidence-based examination](https://en.wikipedia.org/wiki/Audit)
- [Software quality — the dimensions behind "production-ready"](https://en.wikipedia.org/wiki/Software_quality)

---

Author: Pratik Dhanave (https://pratikdhanave.com) | Published: 2026-11-11
Canonical: https://pratikdhanave.com/blog/posts/what-an-ai-production-readiness-audit-covers.html
Attribution: please link the canonical URL when citing or quoting this post.
