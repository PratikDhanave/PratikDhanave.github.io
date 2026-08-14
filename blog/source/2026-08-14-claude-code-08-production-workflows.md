# Claude Code in Production Workflows

*Beyond the interactive terminal, Claude Code can run headless in scripts and CI — which unlocks automation, and raises the stakes on permissions, review, and trust.*

The interactive loop (post 2) is where most Claude Code work happens, but the tool doesn't stop at the terminal prompt. It can run **headlessly** — non-interactively, driven by a script or a CI job — which turns it from a pair-programming partner into an automation primitive. This capstone covers running Claude Code in production-grade workflows, and ties the series together with the practices that keep all of it safe and effective.

## Headless mode

Claude Code can be invoked non-interactively (a print/headless mode, `claude -p "..."`), where you give it a prompt, it does the work, and it returns output — no back-and-forth. That makes it scriptable and composable with the rest of your tooling. Realistic uses:

- **CI/CD tasks** — triage a failing build, propose a fix, draft release notes, update a changelog.
- **Automated PR review** — run a review pass on a pull request and post findings (the Code Review series' "AI first pass" idea, wired into the pipeline).
- **Batch operations** — run the same transformation across many repos or files.
- **Scheduled jobs** — a nightly maintenance or triage task.

Headless runs still honor configuration — CLAUDE.md (post 3), permissions, hooks (post 6), MCP servers (post 4) — so the context and guardrails you set up carry over from interactive use.

**The gotcha:** headless means *no human in the loop at the moment of action* — the interactive "approve this?" safety net is gone. So automation must be scoped tightly (narrow permissions, sandboxed environment, limited tools) and its output must still be reviewed before it lands. An unattended agent with broad permissions is exactly the "excessive agency" risk the AI Security series warns about.

## Guardrails for automated runs

Running the agent unattended demands the security posture from the AI Security and API Security series, applied here:

- **Least privilege.** Give the automated run only the tools, paths, and credentials it needs. A PR-review job should read the diff and comment — not deploy, not touch prod.
- **Sandbox it.** Run in an isolated, ephemeral environment (a CI runner, a container) where a mistake is contained and reversible.
- **Gate the outcome, not the steps.** Since you can't approve each action, put the control at the boundary: the agent proposes a change as a PR that a human reviews and merges, rather than pushing to main directly.
- **Secrets hygiene.** Provide credentials via the environment/secret manager, least-privileged and short-lived — never bake them into prompts or committed config (post 3).
- **Treat inputs as untrusted.** A CI job that reads an external issue or a contributor's PR is processing untrusted content that could carry prompt injection — keep its capabilities minimal so a manipulated run can't do harm.

## Review does not go away — it moves

The biggest mistake in productionizing an agent is assuming automation removes the need to review. It doesn't; it relocates it. Interactive review happens per-action; automated review happens at the artifact the run produces — the PR, the generated file, the proposed fix. A human still reads and approves before it reaches users or main. The Code Review series applies with full force to AI-generated changes: an automated agent is a tireless first-pass author, not an accountable approver.

**The gotcha:** wiring an agent to auto-merge its own changes with no human gate compounds errors silently and removes the accountability a human PR review provides — and an agent approving agent-written code has correlated blind spots. Keep a person on the merge, at least for anything that ships.

## Cost, reliability, and observability

Production use is a system, so operate it like one (the System Design and DevSecOps series' lessons):

- **Cost.** Agentic runs consume tokens; batch and scheduled jobs can add up. Scope prompts, avoid unnecessary re-runs, and monitor spend.
- **Reliability.** Non-deterministic output means an automated job can produce something unexpected — build in verification (run the tests the agent's change should pass; fail the job if they don't) rather than trusting the run blindly.
- **Observability.** Log what automated runs did — inputs, actions, outputs — so you can debug a bad result and keep an audit trail (a hook, post 6, is a natural place for this).

## Bringing the series together

Effective Claude Code use is layered, and each layer built on the last:

```text
interactive loop (2) ── the daily driver: explore → plan → execute → review
   + CLAUDE.md (3) ───── durable project context, shared & versioned
   + MCP (4) ─────────── reach into external tools/data (trust-scoped)
   + subagents (5) ───── delegate & parallelize; orchestrator stays accountable
   + hooks (6) ───────── deterministic guarantees ("always/never")
   + skills/commands (7) invokable, reusable team workflows
   = production (8) ───── headless automation, tightly scoped, human-gated at the artifact
```

The throughline of the whole series: Claude Code is a powerful agent you **direct and supervise**. Its value scales with how well you set it up (context, config, tools), how clearly you specify to it, and how rigorously you review it — and the more autonomy you give it (up to unattended CI), the more those guardrails matter. Used that way, it multiplies a good engineer across everything from a quick refactor to a repeatable pipeline.

## Key takeaways

- Claude Code runs **headlessly** (`claude -p`), turning it into a scriptable automation primitive for CI/CD, PR review, batch ops, and scheduled jobs — honoring your CLAUDE.md, permissions, hooks, and MCP config.
- Headless removes the interactive approval net, so **scope tightly, sandbox, and gate the outcome** (propose a PR, don't push to main).
- Apply **least privilege, secrets hygiene, and untrusted-input caution** — an unattended broad-permission agent is the excessive-agency risk.
- **Review moves, it doesn't disappear** — a human approves the produced artifact; never auto-merge agent code unreviewed.
- Operate it like a system: **manage cost, verify output against tests, and log runs** for debugging and audit.
- Across the series, Claude Code is an agent you **set up, direct, and supervise** — value scales with context, specification, and review, and guardrails scale with autonomy.

## Further reading

- [Claude Code — headless / CLI usage](https://docs.claude.com/en/docs/claude-code/cli-reference) — running non-interactively in scripts and CI.
- [Claude Code — GitHub Actions & CI integration](https://docs.claude.com/en/docs/claude-code/github-actions) — automating in the pipeline.
- [Claude Code — best practices](https://www.anthropic.com/engineering/claude-code-best-practices) — safe, effective agentic workflows.
