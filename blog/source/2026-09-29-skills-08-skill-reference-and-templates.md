# The Skill Reference — Structure, Templates, and Putting It Together

*This closing post makes everything concrete: the anatomy of a skill definition, the templates that get you started fast, and the synthesis of the series into a practical approach you can apply today. It turns the principles — scope, context discipline, specificity, reliability, operation — into a reference you can build from.*

Posts 1–7 built the concepts and craft; this post is the practical reference and the wrap-up. It covers the common *structure* of a skill definition (the "SKILL.md" pattern), starter templates for the kinds of skills, and the series' synthesis — so you leave with both the understanding and the concrete starting points to build real skills.

## The anatomy of a skill definition

Most skill systems converge on a similar structure — commonly a Markdown file (a **SKILL.md**) with a bit of metadata plus the skill's content — because the structure directly reflects the principles of the series. A skill definition typically has:

- **Metadata / frontmatter** — a small header with:
  - **Name** — a clear identifier for the skill.
  - **Description / trigger** — the concise "use this when..." statement (post 3) that lets the agent/system decide *when* to load the skill. This is the most important metadata — it governs relevance-triggered loading (post 2) and is the top make-or-break in the wild (post 7). A sharp description is worth disproportionate care.
- **Instructions (the body)** — the core: clear, ordered, actionable guidance for *how* to do the task (post 3), prescriptive where reliability matters, principle-based where judgment is needed. This is where the skill's reliability lives.
- **Knowledge / context** — the curated, minimal domain knowledge the task needs (posts 5–6), with depth pushed to referenced resources rather than inlined (post 2's progressive disclosure).
- **References to resources** — pointers to templates, scripts, reference files, or examples the skill uses, loaded on demand rather than inlined — keeping the core lean (post 2).

The structure *is* the principles made concrete: the description enables relevance-triggered loading (context discipline), the lean curated body respects the context budget, the prescriptive instructions deliver reliability, and the referenced resources enable progressive disclosure. A well-formed SKILL.md is essentially the series' design discipline in a file format — which is why understanding the *why* (posts 1–7) makes the *format* obvious rather than arbitrary.

## Starter templates

The fastest way to build good skills is to start from templates matched to the kind of skill, each embodying the series' structure. Four useful starting points:

- **Starter / general template** — the minimal skeleton: a name, a sharp "use when..." description, an instructions section (ordered steps), and a small knowledge section. The right starting point for most skills — begin minimal (post 3's "start as a draft"), then iterate against real use (post 7). Resist front-loading; grow only what real use demands.
- **Domain template** — adds, to the general skeleton, an explicit **rules/constraints** section (stated prescriptively — post 6's precise "must/never"), a **grounded authoritative knowledge** section (the real domain material, with sources/provenance), and a **verification** note (cite sources, flag for human review on high stakes). This template bakes in the extra rigor domain skills demand (post 6) so you don't forget the grounding and verification that make them safe.
- **Workflow template** — for skills that are a *stage* in a chained process (post 4): explicit **inputs** (what this stage receives), **steps** (the stage's procedure), and **outputs** (what it hands to the next stage) — so the skill chains cleanly. Use this when designing skills that compose into a workflow, so the stage boundaries and handoffs are clean.
- **Integration template** — for skills that connect the agent to a system or tool: how to call the tool/API, the relevant parameters and conventions, error handling, and constraints — the specifics of operating *your* integration that the model can't know. Use this for skills whose job is reliably working with a specific external system.

The point of templates isn't rigidity — it's to encode the series' discipline into a starting structure so you don't omit the trigger, bloat the context, or forget the domain rigor. Start from the template that matches your skill's kind, fill in *your specifics*, and iterate. Templates make the fundamentals automatic, so your effort goes into the content that's actually particular to your task.

## The synthesis

The series comes down to a clear, practical approach to making agents reliably capable:

- **Skills close the gap** (post 1) between a generally-capable agent and one that reliably does *your specific work your way* — by packaging instructions, knowledge, and procedure into self-contained, reusable, composable units of captured expertise, loaded on demand.
- **Design for the context window** (post 2) — the master constraint. Load only what's relevant, only when relevant, as compactly as possible; skill design *is* context-window design. This is the single most important principle.
- **Build well** (post 3): scope to one coherent capability, write a sharp trigger and clear prescriptive instructions, curate minimal knowledge, defer depth, and iterate empirically while pruning ruthlessly.
- **Think in libraries** (post 4): skills compose and chain into patterns of work, so the *library* — curated, composable, shared, mirroring your real work — is where value compounds, not any single skill.
- **Match the kind** (posts 5–6): general business skills capture frequent convention-bound work (value in *your specifics*, not generalities); domain-specific skills capture deep expertise (demanding grounding, precise rules, verification, and the most rigor).
- **Operate in the wild** (post 7): skills succeed on the fundamentals and fail on operational neglect, so maintain, version, curate, tune, and verify the library as a living, shared product.

The deepest takeaway: agent skills reframe how you make AI agents genuinely, reliably useful. Not by writing ever-longer prompts or waiting for a bigger model, but by **building and tending a library of captured expertise** — focused, context-disciplined, specific, reliable, composable, and maintained — that turns a general model into a dependable specialist at the work that matters to you. The model provides the general capability; the skills provide *your* expertise, reliably applied. Build your skills on the principles of this series, start from the templates, and grow the library as a compounding asset — and your agents stop improvising and start doing your real work, your way, every time.

The throughline: a skill definition (commonly a **SKILL.md** — Markdown + metadata) has a structure that *is* the series' principles made concrete — **metadata** (name + the crucial **description/trigger** "use when...", governing relevance-triggered loading, the top make-or-break), **instructions** (clear, ordered, prescriptive where reliability matters — where reliability lives), **curated minimal knowledge**, and **referenced resources** (progressive disclosure, keeping the core lean). Build fast from **templates** matched to the skill kind — **starter** (minimal skeleton, grow by iteration), **domain** (adds prescriptive rules + grounded authoritative knowledge + verification — baking in post 6's rigor), **workflow** (explicit inputs/steps/outputs to chain cleanly, post 4), and **integration** (how to operate a specific system/tool) — which make the fundamentals automatic so effort goes to *your specifics*. The synthesis: skills **close the gap** (post 1), are governed by **context-window design** (post 2, the master principle), **built well** (post 3), **composed in libraries** (post 4), **matched to kind** (posts 5–6), and **operated in the wild** (post 7) — so make agents reliably useful by **building and tending a library of captured expertise**, not by longer prompts or bigger models.

## Key takeaways

- A skill definition (commonly a **SKILL.md** — Markdown + metadata) has a structure that *is* the series' principles concrete: **metadata** (name + the crucial **description/trigger** — the "use this when..." that governs relevance-triggered loading, post 2, and is the top real-world make-or-break, post 7 — worth disproportionate care), **instructions** (clear, ordered, prescriptive-where-reliability-matters — where reliability lives, post 3), **curated minimal knowledge** (posts 5–6), and **referenced resources** (progressive disclosure keeps the core lean, post 2).
- Start fast from **templates** matched to the skill kind: **starter** (minimal name/trigger/steps/knowledge skeleton — begin minimal, iterate), **domain** (adds prescriptive **rules/constraints**, **grounded authoritative knowledge** with sources, and a **verification** note — bakes in post 6's rigor), **workflow** (explicit **inputs/steps/outputs** to chain cleanly, post 4), and **integration** (how to operate a specific system/tool/API).
- Templates aren't rigidity — they **encode the discipline into a starting structure** so you don't omit the trigger, bloat context, or skip domain grounding/verification; fill in *your specifics* and iterate.
- The synthesis: skills **close the gap** (post 1) between general capability and your-specific-work reliability; **design for the context window** (post 2, the master principle — skill design *is* context-window design); **build well** (post 3 — scope, trigger, prescriptive instructions, curated knowledge, iterate + prune); **think in libraries** (post 4 — compose/chain, curate, share); **match the kind** (posts 5–6 — specifics for business, grounding+rigor for domain); and **operate in the wild** (post 7 — maintain, version, curate, tune, verify).
- The deepest takeaway: make AI agents **reliably useful by building and tending a library of captured expertise** (focused, context-disciplined, specific, reliable, composable, maintained) — not by ever-longer prompts or a bigger model. The model provides general capability; **skills provide *your* expertise, reliably applied**, turning a generalist into a dependable specialist at the work that matters to you.

## Further reading

- [Markdown — the format skill definitions commonly use](https://en.wikipedia.org/wiki/Markdown)
- [Software agent — the agent a skill library makes reliably capable](https://en.wikipedia.org/wiki/Software_agent)
