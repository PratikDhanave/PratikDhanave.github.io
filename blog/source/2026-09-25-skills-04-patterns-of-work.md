# Patterns of Work with Agent Skills

*A single skill makes an agent reliable at one task; the real power comes from how skills combine into patterns of work. An agent equipped with a library of well-designed skills can compose them, chain them, and apply them across a workflow — turning point capabilities into end-to-end reliable work. This post is about the patterns that emerge when skills work together, and how to think about an agent's skill library as a system rather than a pile of parts.*

Posts 1–3 covered the individual skill — what it is, the context constraint, how to build one. This post zooms out to how skills *interact*: composition, chaining, and the library as a whole. It's the shift from "a skill does a task" to "skills, together, do the work" — and it's where skills' value compounds.

## Composition: skills working together

The foundational pattern is **composition** — an agent drawing on *multiple* skills for a single piece of work, each contributing its capability. Because skills are self-contained and load on relevance (posts 1–2), an agent can combine them naturally:

- A task might invoke a "code review" skill *and* a "security checklist" skill *and* a "our-conventions" skill together, each adding its piece. The agent composes their guidance rather than needing one monolithic skill covering everything.
- Composition is *why* scoping skills to **one coherent capability** (post 3) matters: well-scoped, focused skills compose cleanly (like well-designed functions), while broad overlapping skills conflict and confuse. Good modularity at the skill level enables rich composition at the work level — the same reason small focused functions compose better than giant ones.

The payoff: a library of *N* focused skills gives far more than *N* capabilities, because they combine. You get coverage of a wide range of work from a manageable set of composable skills, rather than needing a bespoke skill for every possible task. This combinatorial leverage — many capabilities from composed skills — is the core reason to think in skills rather than monolithic prompts (post 2), and it's why the *library* matters more than any single skill.

## Chaining: skills across a workflow

Beyond composition within a task, skills support **chaining** across a multi-step workflow — a sequence where the output of one skilled step feeds the next:

- A real workflow might be: *discover* the requirements (one skill), *build* the solution (another), *review* it (a third), *document* it (a fourth) — each step a skill, chained into an end-to-end process. The agent moves through the workflow applying the right skill at each stage.
- This maps workflows (real processes have stages) onto skills (a skill per stage), so an agent can reliably execute a whole *process*, not just isolated tasks. The reliability of each skilled step compounds into a reliable workflow — which is how skills take an agent from "helps with pieces" to "runs the process."
- Chaining connects to the agent's broader orchestration (the agent/workflow patterns the blog covers elsewhere): skills are the *reliable units* the orchestration sequences. The agent (or a workflow around it) decides the sequence; the skills ensure each step is done right.

The design implication: think about not just individual skills but the *workflows* they support, and design skills that chain cleanly (clear inputs/outputs, coherent stage boundaries). A set of skills that covers the stages of your important workflows — and composes and chains among them — is far more valuable than scattered unrelated skills, because it makes whole *processes* reliable, which is usually what actually matters.

## The skill library as a system

The deepest shift is to stop thinking about skills individually and start treating the **skill library** as a system — your agent's accumulated, organized, reusable capability:

- **It's a growing asset.** Each skill added extends the agent's reliable repertoire, and because skills compose and chain, the library's value grows *faster* than linearly — new skills combine with existing ones. A well-tended skill library becomes a significant, compounding asset (echoing the institutional-memory idea — captured expertise that persists and reuses).
- **It needs curation, like any library.** A pile of overlapping, inconsistent, stale skills is as bad as messy code — so the library needs organization (clear scopes, no overlap), consistency (shared conventions across skills), and maintenance (updating skills as practices change, pruning dead ones). Treat skills as a maintained codebase of capability, not a dumping ground.
- **It's shareable and collaborative.** Skills can be shared across a team/org (post 1), so the library becomes a *shared* asset that many people contribute to and benefit from — which means it needs the collaboration discipline of shared code: versioning, review, conventions, ownership. A team's skill library is collective captured expertise, and tending it well multiplies everyone's leverage.
- **It maps to how work is actually structured.** The best skill libraries mirror the structure of the real work — skills for the recurring tasks, composed and chained to cover the real workflows. Designing the library is partly *analyzing your work* to find the coherent, recurring capabilities worth capturing, then building skills for those and organizing them to compose.

The through-line: the value of skills isn't in any single one but in the *system* — a curated, composable, chainable library that mirrors your real work, grows as a compounding asset, and is shared and maintained like code. An agent with a good skill library isn't just "an agent that can do task X"; it's an agent that reliably does *your work*, across tasks and workflows, because the library captures and composes the expertise your work requires. Thinking at the library level — composition, chaining, curation, sharing — is what turns individual skills into an agent that's genuinely, reliably capable at the scope of real work. The next posts look at the *kinds* of skills a library holds (general business, post 5; domain-specific, post 6) and skills in real-world use (post 7).

The throughline: skills' real power is in how they **combine**, not in any single one. **Composition** — an agent drawing on multiple focused skills for one task, each adding its piece — gives combinatorial leverage (a library of *N* well-scoped skills yields far more than *N* capabilities because they combine), and it's *why* scoping to one coherent capability (post 3) matters (focused skills compose cleanly, like good functions; broad overlapping ones conflict). **Chaining** sequences skills across a multi-step **workflow** (discover → build → review → document, a skill per stage), so an agent reliably runs whole *processes*, not just isolated tasks, with each step's reliability compounding. The deepest shift is treating the **skill library as a system** — a compounding **asset** (value grows faster than linearly via composition), needing **curation** (scopes, consistency, maintenance — like a codebase), **shareable/collaborative** (versioning, review, ownership — collective captured expertise), and **mirroring real work** (analyze your work to find the recurring capabilities worth capturing). Think at the library level, and individual skills become an agent reliably capable at the scope of real work.

## Key takeaways

- Skills' power is in **combination**, not individual skills. **Composition** — an agent drawing on *multiple* focused skills for one task (code-review + security-checklist + conventions together) — gives **combinatorial leverage**: a library of *N* well-scoped skills yields far more than *N* capabilities because they combine, so the *library* matters more than any single skill.
- Composition is *why* **one-coherent-capability scoping** (post 3) matters — focused skills compose cleanly (like good functions); broad, overlapping skills conflict and confuse (like tangled code).
- **Chaining** sequences skills across a multi-step **workflow** (discover → build → review → document, a skill per stage), so the agent reliably executes whole *processes* (not just isolated tasks), with each skilled step's reliability compounding into a reliable workflow; skills are the reliable units the agent's orchestration sequences.
- Design implication: build skills that **chain cleanly** (clear stage boundaries, inputs/outputs) and cover the stages of your **important workflows** — a set that composes and chains across real processes is far more valuable than scattered unrelated skills, because it makes whole *processes* reliable (usually what matters).
- Treat the **skill library as a system**: a **compounding asset** (composition makes value grow faster than linearly — captured expertise that persists, like institutional memory), needing **curation** (clear scopes, consistency, maintenance, pruning — like a codebase, not a dumping ground), **shareable/collaborative** (versioning, review, conventions, ownership — collective team expertise), and **mirroring real work** (analyze your work to find the recurring coherent capabilities worth capturing) — thinking at the library level is what makes an agent reliably capable at the scope of real work.

## Further reading

- [Workflow — the processes skills chain across](https://en.wikipedia.org/wiki/Workflow)
- [Software agent — the agent that composes and chains skills](https://en.wikipedia.org/wiki/Software_agent)
