# Tools for Coding Agents — How an Agent Acts on Code

*An agent's reasoning is useless without the ability to act, and for a coding agent, acting means tools: editing files, running commands, executing tests, searching code, using version control. The tools define what the agent can do, and their design — what they expose, how safe they are, how reliable their feedback — shapes how well the agent works. This post is about the tools that turn a reasoning model into an agent that changes real software.*

Post 2's loop has an "act" step; post 3's grounding has a "search" step — both happen through tools. This post covers the coding agent's toolset: the capabilities that let it operate in a real development environment. Tool design is where a coding agent's power and its safety are both determined.

## The core toolset

A coding agent acts through a set of tools that map onto what a developer does at a workstation. The essential ones:

- **File operations — read and edit.** Reading files is how the agent observes code (grounding, post 3); editing them is how it makes changes. Edit tools range from "replace this exact text" to "apply this diff" to "write this whole file," and their design matters: precise, reliable edits (that do exactly what's intended) are foundational, because a flaky edit tool corrupts the agent's work regardless of how good its reasoning is. Editing is the agent's primary way of *changing* the world.
- **Running commands (the shell).** A shell/command tool lets the agent *execute* things — build the project, run a script, install a dependency, invoke any CLI. This is enormously powerful (the whole command-line world becomes available) and the most *consequential* tool (it can do anything the shell can, including destructive things — hence safety, below). Running commands is how the agent *does* and *observes* real effects.
- **Running tests.** Often a distinct, central capability (even if via the shell): execute the test suite and get pass/fail and error details. This is the agent's primary *verification* signal (post 6) and the feedback that drives the loop (post 2) — code's verifiability made actionable. Running tests is how the agent knows if its change worked.
- **Searching the codebase.** Code search (grep/semantic) for grounding (post 3) — finding relevant code fast. A core tool because the agent reads selectively, not wholesale.
- **Version control.** Git operations — see the diff of changes, check status, view history, commit. This lets the agent understand what it's changed, review its own diff, and work within the version-control workflow. Seeing its own diff is an important self-review signal.

These tools together give the agent a workstation: observe (read/search), act (edit/run), verify (test), and manage (version control) — the full loop (post 2) made executable. The agent's *capabilities are exactly its tools*: what it can do is what its tools let it do, so the toolset defines the agent's reach.

## Tool design shapes the agent

How these tools are *designed* strongly shapes how well the agent performs — tool design is agent design:

- **Reliable, predictable tools.** Tools must do exactly what the agent expects, reliably — a flaky edit, an ambiguous command result, or an unreliable search undermines the agent's loop (it acts on bad observations or its actions don't land). Reliability is paramount because the agent *reasons over tool results*, so unreliable tools produce unreliable reasoning. Boring, dependable tools beat clever flaky ones.
- **Clear, useful feedback.** A tool's output is what the agent *observes* (post 2), so tools should return clear, informative results — a test tool that reports *which* tests failed and *why* is far more useful than one that says "failed." The richer and clearer the feedback, the better the agent's next decision. Tool output design is feedback design, and feedback drives the loop.
- **Right granularity.** Tools pitched at the right level — not so low that the agent does tedious micro-steps (wasting context and turns), not so high that it loses control — help the agent work efficiently. Good tool granularity matches how the agent naturally reasons about the task.
- **Composability.** The agent combines tools (search to find, read to understand, edit to change, test to verify) in the loop, so tools should compose cleanly into that workflow — each doing one thing well (the Unix philosophy, and the [Agent Skills](/blog/series/agent-skills/) one-coherent-thing idea applied to tools).

The principle: **the agent is only as capable as its tools are reliable and its tool feedback is clear.** A huge amount of coding-agent quality comes from well-designed tools — reliable edits, informative test output, precise search — more than from the model alone. This is why building a good coding agent is substantially a *tool-engineering* problem, not just a prompting one.

## Safety: tools that can do anything must be bounded

Here is the critical concern: coding-agent tools — especially the shell — can do *real, consequential, sometimes irreversible things* (delete files, push code, run arbitrary commands, modify systems), so tool *safety* is a first-class design problem, connecting directly to the agent-governance and bounded-execution ideas the blog covers:

- **Least privilege and scoping.** Give the agent exactly the tool access its task needs, scoped to the right directory/repo/environment, and no more (the [agent-governance](/blog/series/ai-governance-in-practice/) least-privilege principle). An agent that only needs to edit one project shouldn't have unrestricted system access — scoping bounds the blast radius of any mistake or misbehavior.
- **Sandboxing and isolation.** Run the agent's actions in a sandboxed/isolated environment (a container, a scratch workspace, a dev environment — not production) so its mistakes are contained. Isolation means a destructive command harms a disposable environment, not something that matters.
- **Confirmation for consequential actions.** Require human approval (or at least a review gate) for irreversible or high-impact actions — pushing code, deleting things, modifying shared/production systems. The autonomy should be high for safe, reversible actions (editing files in a workspace, running tests) and gated for dangerous ones — the autonomy-by-stakes principle.
- **Reversibility — version control as a safety net.** Working in version control means the agent's changes are *reversible* (you can diff, review, and revert), which is a crucial safety property: a bad change is recoverable, not catastrophic. This is a big reason coding agents are safer than agents acting on irreversible external systems — git is the undo button.
- **Visibility and review.** The human sees what the agent does (its commands, its diffs, its tool calls — tracing, from the [LLMOps](/blog/series/llmops-in-practice/) series) and reviews the result before it lands anywhere consequential. Transparency plus review keeps the human in control.

The through-line: a coding agent acts through **tools** — read/edit files, run commands, run tests, search, version control — which *define its capabilities* and make the loop (post 2) executable, and whose **design** (reliability, clear feedback, granularity, composability) largely determines the agent's quality (building a good coding agent is substantially a tool-engineering problem). Because those tools — especially the shell — can do **consequential, irreversible things**, **safety is first-class**: least-privilege scoping, sandboxing/isolation, confirmation gates for high-impact actions, reversibility via version control (git as the undo button — a key reason coding agents are relatively safe), and human visibility/review. The tools are where the agent's power *and* its danger both live, so designing them well — capable, reliable, clear, and bounded — is where much of coding-agent engineering happens.

## Key takeaways

- A coding agent acts through **tools** that mirror a developer's workstation: **read/edit files** (observe code; make changes — precise reliable edits are foundational, a flaky edit tool corrupts work), **run commands (shell)** (execute anything — the most powerful *and* most consequential tool), **run tests** (the primary verification signal driving the loop, post 2/6), **search the codebase** (grounding, post 3), and **version control** (see diffs, commit, self-review). The agent's **capabilities are exactly its tools**.
- **Tool design shapes the agent**: **reliability** (the agent reasons over tool results — flaky tools → unreliable reasoning; boring dependable beats clever flaky), **clear feedback** (tool output *is* what the agent observes — "which tests failed and why" ≫ "failed"; feedback design drives the loop), **right granularity**, and **composability** (clean one-thing-well tools the agent combines in the loop).
- The principle: **the agent is only as capable as its tools are reliable and their feedback is clear** — much of coding-agent quality is **tool engineering**, not just prompting.
- Tools (especially the **shell**) can do **consequential, irreversible things**, so **safety is first-class** (agent-governance/bounded-execution): **least-privilege scoping** (only the access the task needs, bounding blast radius), **sandboxing/isolation** (contain mistakes in a disposable environment, not production), **confirmation gates** for high-impact/irreversible actions (autonomy by stakes), and **human visibility/review** of commands and diffs (tracing + review keeps the human in control).
- **Version control is a key safety net**: working in git makes the agent's changes **reversible** (diff, review, revert — a bad change is recoverable, not catastrophic), a major reason coding agents are relatively safe vs agents acting on irreversible external systems — so the tools are where the agent's **power and danger both live**, and designing them capable-reliable-clear-and-bounded is where much coding-agent engineering happens.

## Further reading

- [Command-line interface — the shell power (and risk) agents wield](https://en.wikipedia.org/wiki/Command-line_interface)
- [Version control — the reversibility that makes coding agents safer](https://en.wikipedia.org/wiki/Version_control)
