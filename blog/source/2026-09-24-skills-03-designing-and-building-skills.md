# Designing and Building Skills

*A good agent skill is a small piece of information architecture: the right scope, a clear trigger, well-structured instructions, and only the knowledge the task needs — all shaped by the context-window discipline of post 2. Building one is less about clever prompting and more about thinking like a technical writer and a software designer at once. This post is the practical craft of designing and building a skill that an agent uses reliably.*

Posts 1–2 established what skills are and the context-window constraint that governs them. This post is how to actually build one well. The craft combines software-design judgment (scope, modularity) with technical-writing clarity (instructions an agent can follow) — and the recurring test is always "does this respect the context window and make the agent reliably do the task right?"

## Scoping a skill: one coherent capability

The first and most consequential design decision is **scope** — what the skill covers — and the guiding principle is *one skill, one coherent capability*:

- **Not too broad.** A skill trying to cover many unrelated tasks is hard to trigger precisely (when is it relevant?), bloats context when loaded (post 2), and becomes an unfocused grab-bag. "Everything about our codebase" is too broad to be a good skill.
- **Not too narrow.** A skill so specific it applies to almost nothing isn't worth the overhead, and a proliferation of hyper-narrow skills is hard to manage. "How to rename this one variable" is too narrow.
- **Just right: one coherent task or capability** — a scope that's clearly triggerable ("when doing X"), self-contained, and reusable across many instances of that kind of work. "How we do a production deployment," "our code review checklist," "generating our standard client report" — each a coherent capability with a clear boundary.

This is the **separation of concerns / modularity** judgment (post 2) applied to skills: decompose your agent's needed capabilities into coherent, independently-triggerable units, the same way you'd decompose a system into well-scoped modules. Good scoping makes triggering precise, keeps context lean, and makes skills reusable and composable; bad scoping (too broad, too narrow, overlapping) is the most common way skills go wrong. When unsure, ask "is this *one* thing an agent does, with a clear 'when'?" — if yes, it's a skill; if it's several things, split it.

## Structuring the skill: trigger, instructions, knowledge

With scope set, a well-built skill has a clear internal structure, each part doing a specific job and all shaped by context-window discipline (post 2):

- **A clear trigger / description.** The skill needs a concise statement of *when it applies* — this is what lets the agent (or the system) decide to load it at the right time (post 2's relevance-triggered loading). A vague or missing trigger means the skill loads at the wrong times or not at all, so a sharp "use this when..." description is essential and high-leverage. This is often the single most important line in a skill.
- **Clear, actionable instructions.** The core: *how* to do the task, written as clear, ordered, actionable guidance the agent can follow — steps, conventions, decision points, a checklist. Write them as you would for a competent new teammate: unambiguous, specific, in the order they're done, with the *why* where it aids judgment. Vague instructions ("handle errors appropriately") produce vague behavior; specific instructions ("on failure, retry 3× with backoff, then escalate to X") produce reliable behavior. Instruction clarity is where a skill's reliability is won.
- **Only the knowledge the task needs.** Include the domain knowledge, reference, and examples the task requires — and *only* those (post 2's compactness). Resist the urge to include everything that might conceivably help; every extra paragraph taxes the agent's context and focus. Curate the knowledge to what the task actually uses, and push depth into progressively-disclosed resources (post 2) rather than the always-loaded core.
- **Supporting resources, referenced not inlined.** Templates, scripts, long reference material — keep these as separate resources the skill *points to* and loads on demand (progressive disclosure), rather than inlining them into the core and bloating context. The core stays lean; the depth is available when needed.

The structure, in short: *a sharp trigger, clear actionable instructions, curated minimal knowledge, and deferred depth* — an information architecture optimized for the agent to load the right thing, understand it, and act reliably, all within the context budget.

## The craft: write for the agent, iterate like software

Building a good skill is a craft with a few durable practices:

- **Write for the agent as a capable-but-uninformed reader.** The agent is smart but doesn't know *your* specifics — so write as you would onboard a sharp new hire: don't over-explain general concepts it already knows (wasting context), but *do* specify the particulars it can't know (your conventions, your steps, your constraints). Pitch the instructions at "competent generalist who needs your specifics," which is exactly what the agent is.
- **Be specific and prescriptive where reliability matters.** For the parts that must be done a certain way, be prescriptive (exact steps, exact format); for the parts that need judgment, give principles and let the agent reason. Knowing where to be rigid vs where to delegate judgment is a key skill-design skill.
- **Test and iterate — skills are built empirically.** A skill is rarely right the first time: you write it, use it on real tasks, see where the agent misunderstands or does the wrong thing, and refine (clarify an instruction, fix the trigger, add a missing constraint, cut what's unused). This iteration — like testing and refining code — is how a skill becomes reliable. Treat the first version as a draft and let real use drive it to good, watching specifically for where the agent deviates and tightening the instruction that let it.
- **Keep it lean and prune ruthlessly.** As you iterate, resist accretion — cut instructions the agent doesn't need, knowledge it doesn't use, words that don't earn their context cost (post 2). A skill should get *tighter* over time, not just bigger; bloat creeping in is the slow death of a skill's focus.

The synthesis: building a skill is *information architecture under a context budget* — scope it to one coherent capability, give it a sharp trigger, write clear prescriptive instructions and curate only the needed knowledge, defer depth to on-demand resources, and iterate empirically against real use while pruning ruthlessly. Do that and you get a skill the agent loads at the right time, understands clearly, and executes reliably — the unit of durable, reusable agent capability the series is about. The next post covers how these well-built skills combine into *patterns of work*.

The throughline: building a good skill is **information architecture under a context budget**, combining software-design and technical-writing judgment. **Scope** is the first, most consequential decision — *one skill, one coherent capability* (not too broad → unfocused, hard to trigger, bloats context; not too narrow → not worth the overhead; just right → a clearly-triggerable, self-contained, reusable task), which is separation-of-concerns applied to skills. **Structure** it as a **sharp trigger/description** (the "use this when..." that enables right-time loading — often the single most important line), **clear actionable instructions** (ordered, specific, prescriptive where reliability matters — where reliability is won; vague instructions → vague behavior), **only the knowledge the task needs** (curated, compact), and **supporting resources referenced not inlined** (progressive disclosure keeps the core lean). The **craft**: write for the agent as a *capable-but-uninformed* reader (specify your particulars, don't re-explain generalities), be prescriptive where it must be exact and principle-based where it needs judgment, **test and iterate empirically** against real use (watch where the agent deviates, tighten that instruction), and **prune ruthlessly** so the skill gets tighter over time.

## Key takeaways

- **Scope** is the most consequential decision: *one skill, one coherent capability* — **not too broad** (unfocused grab-bag, hard to trigger, bloats context), **not too narrow** (not worth the overhead, proliferates), but a clearly-triggerable, self-contained, reusable task ("how we deploy," "our review checklist"). This is **separation of concerns / modularity** (post 2) applied to skills; the test is "is this *one* thing with a clear 'when'?"
- **Structure** a skill as: a **sharp trigger/description** ("use this when..." — enables right-time loading, post 2; often the single most important line), **clear actionable instructions** (ordered, specific, prescriptive — where reliability is won; vague → vague behavior), **only the knowledge the task needs** (curated, compact — every extra paragraph taxes context), and **supporting resources referenced not inlined** (progressive disclosure keeps the core lean).
- Pitch content for **the agent as a capable-but-uninformed reader**: don't re-explain general concepts it knows (wastes context), *do* specify the particulars it can't know (your conventions, steps, constraints) — "competent generalist who needs your specifics."
- Be **prescriptive where reliability matters** (exact steps/format) and **principle-based where judgment is needed** — knowing which is a key design skill.
- **Build empirically**: write a draft, use it on real tasks, watch where the agent misunderstands/deviates, and refine (clarify instructions, fix the trigger, add missing constraints, cut the unused) — and **prune ruthlessly** so the skill gets *tighter* over time, not just bigger (bloat is the slow death of focus). The result: a skill the agent loads at the right time, understands, and executes reliably.

## Further reading

- [Modular programming — the decomposition skills apply](https://en.wikipedia.org/wiki/Modular_programming)
- [Technical writing — writing instructions a reader can follow](https://en.wikipedia.org/wiki/Technical_writing)
