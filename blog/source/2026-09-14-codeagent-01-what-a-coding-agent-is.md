# Coding Agents — What They Are and Why They Changed Software

*An AI that answers coding questions is an assistant; an AI that independently reads a codebase, makes changes across many files, runs the tests, sees what broke, and fixes it is a coding agent. That shift — from suggesting code to doing the work in a real repository — is one of the most consequential developments in software engineering, and it has its own distinct engineering. This series builds coding agents from first principles, starting with what makes an agent different from autocomplete.*

This series is for engineers who use or build AI coding tools (Claude Code and similar) and want to understand how coding agents actually work — the loop, the grounding, the tools, the verification, the evaluation. It builds on the blog's agent and [Agent Skills](/blog/series/agent-skills/) coverage with a focused treatment of agents that *write software*. Post 1 defines the coding agent and the paradigm shift it represents.

## From autocomplete to agent

AI coding assistance has evolved through distinct stages, and the jump to *agent* is qualitative, not incremental:

- **Autocomplete / suggestion** — the model suggests the next line or block as you type (the early copilots). Helpful, but *you* are still doing the work; the AI accelerates your typing. It's reactive and local.
- **Chat / Q&A** — you ask the model a coding question or to write a function, and it responds. Still you-driven: you integrate the answer, run it, debug it. The AI is a knowledgeable assistant you consult.
- **Coding agent** — you give it a *task* ("fix this bug," "add this feature"), and it *independently* does the work: explores the codebase to understand it, plans the change, edits multiple files, runs the code and tests, observes failures, and iterates until done. *You* are now the reviewer and director, not the typist.

The defining difference is **agency**: a coding agent doesn't just produce text for you to use — it *acts* in the real environment (the repository, the shell, the test runner), takes multi-step autonomous action toward a goal, and *closes the loop* by observing the results of its actions and adjusting. This is the shift from "AI helps me write code" to "AI does the coding task," and it changes the engineer's role from author to director-and-reviewer. It's the same agentic leap the blog covers for AI generally ([agent series](/blog/series/the-ai-forward-deployed-engineer/)), applied to the specific, uniquely-verifiable domain of software.

## Why code is special for agents

Coding is one of the *best* domains for agents, and understanding why explains both their rapid success and their distinct engineering:

- **Code is verifiable.** Unlike most agent tasks (where "is this good?" is fuzzy), code can be *run and tested* — it compiles or doesn't, tests pass or fail, the program works or crashes. This gives the agent an *objective feedback signal*: it can act, observe the concrete result, and know whether it succeeded. This verifiability is the single biggest reason coding agents work so well — the agent can check its own work against reality (post 6), which most domains can't offer. Code is agency with a ground truth.
- **The environment is rich and tool-friendly.** A codebase lives in a file system, with a shell, a compiler, tests, version control, a debugger — a well-defined, programmable environment the agent can *act in* through tools (post 4). Software development is already automated and tooled, so an agent has rich, reliable levers to pull.
- **The task space is well-structured.** Software tasks (fix a bug, add a feature, refactor, write tests) have recognizable shapes, and the work (read code, understand, change, verify) is a learnable loop (post 2). Code is also abundant training data, so models are genuinely strong at it.

The combination — verifiable, richly-tooled, well-structured — makes software a near-ideal agent domain, which is why coding agents advanced so fast and became one of AI's clearest practical successes. The verifiability in particular is the thing to hold onto: it's what lets a coding agent reliably *close the loop* and self-correct, which is the heart of what makes it an agent rather than a suggester.

## What coding agents change — and the engineer's new role

Coding agents change software engineering in ways worth naming up front, because they frame the whole series:

- **The unit of work shifts from lines to tasks.** You increasingly delegate *tasks* ("implement this," "fix that") rather than write lines, and the agent handles the multi-step execution. This raises the level of abstraction at which engineers work — from typing code to specifying, directing, and reviewing it.
- **Review and verification become central.** When an agent does the work, the engineer's critical job is *verifying* it — reviewing the changes, checking the tests, judging correctness. The bottleneck and the skill shift toward *review and judgment* (which is why verification, post 6, and the engineer-as-reviewer theme recur). Trust is earned through verification, not assumed.
- **The engineer becomes a director.** The human sets the goal, provides context and constraints, reviews the work, and course-corrects — a role more like a senior engineer directing a capable junior than a typist. This is the emerging operating model, and it's genuinely different from "AI autocomplete."
- **It's augmentation, not replacement (for now).** Coding agents are powerful on well-scoped, verifiable tasks but have real limits (post 8) — they struggle with ambiguous requirements, large fuzzy changes, and anything where verification is weak. The productive model is augmentation: the agent does the mechanical and well-specified work fast, the engineer provides judgment, architecture, and verification. The human stays accountable for the code.

The through-line: a coding agent is an AI that *independently does software tasks* — exploring, editing, running, observing, and iterating in a real codebase — which is a qualitative leap from autocomplete and chat. Code is a near-ideal agent domain because it's *verifiable* (objective feedback to close the loop and self-correct), richly *tooled*, and well-*structured*. This shifts engineering from writing lines to directing and reviewing tasks, making verification and judgment the central human skills. The rest of the series builds how coding agents actually work — the loop (post 2), grounding in the codebase (post 3), tools (post 4), planning (post 5), verification (post 6), evaluation (post 7), and practice (post 8) — all resting on this post's core idea: an agent *acts in the codebase and closes the loop against the ground truth that code uniquely provides.*

The throughline: a **coding agent** is an AI that *independently does software tasks* — explore the codebase, plan, edit multiple files, run code and tests, observe failures, iterate until done — a qualitative leap beyond **autocomplete** (accelerates your typing) and **chat** (a consultant you integrate). Its defining property is **agency**: it *acts* in the real environment (repo, shell, test runner) and **closes the loop** by observing results and adjusting. **Code is a near-ideal agent domain** because it's **verifiable** (run it, test it — an objective ground-truth feedback signal that lets the agent self-correct; the single biggest reason coding agents work, where most domains have only fuzzy "is this good?"), richly **tooled** (file system, shell, compiler, tests, VCS — a programmable environment), and well-**structured** (recognizable task shapes, abundant training data). This shifts engineering from **writing lines to directing and reviewing tasks** — making **verification and judgment the central human skills**, with the engineer as director-reviewer and the agent as augmentation (powerful on well-scoped verifiable work, limited on ambiguity).

## Key takeaways

- AI coding assistance evolved **autocomplete** (accelerates your typing — you do the work) → **chat/Q&A** (a consultant you integrate) → **coding agent** (you give a *task* and it independently explores, plans, edits many files, runs code/tests, observes, and iterates — you direct and review).
- The qualitative difference is **agency**: a coding agent *acts* in the real environment (repository, shell, test runner), takes multi-step autonomous action toward a goal, and **closes the loop** by observing the concrete results of its actions and adjusting — "AI does the coding task," not "AI helps me type."
- **Code is a near-ideal agent domain**: it's **verifiable** (compile/run/test gives an *objective* feedback signal — the single biggest reason coding agents work, letting the agent self-correct against ground truth, where most domains offer only fuzzy judgment), richly **tooled** (file system, shell, compiler, tests, VCS, debugger — a programmable environment to act in), and well-**structured** (recognizable task shapes + abundant training data).
- Coding agents shift the **unit of work from lines to tasks** (engineers specify/direct/review rather than type), making **review, verification, and judgment the central human skills** (the bottleneck moves to checking the agent's work) and the engineer a **director** (like directing a capable junior).
- It's **augmentation, not replacement** (for now): powerful on well-scoped, verifiable tasks; limited on ambiguous requirements and weakly-verifiable work (post 8) — the agent does mechanical/well-specified work fast, the human provides judgment, architecture, and verification and stays accountable. The series builds how this works, all resting on *acting in the codebase and closing the loop against code's unique ground truth*.

## Further reading

- [Software agent — the agency that defines a coding agent](https://en.wikipedia.org/wiki/Software_agent)
- [Pair programming — the director/reviewer model coding agents echo](https://en.wikipedia.org/wiki/Pair_programming)
