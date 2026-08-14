# Skills and Slash Commands

*Slash commands and skills turn a workflow you keep re-explaining into something you invoke by name — packaging repeatable expertise so you (and your team) don't prompt it from scratch every time.*

By now you've seen how to give Claude Code durable context (CLAUDE.md, post 3), external reach (MCP, post 4), delegation (subagents, post 5), and deterministic control (hooks, post 6). This post is about packaging *repeatable workflows* so they're a single invocation rather than a re-typed prompt: custom slash commands for quick reusable prompts, and skills for larger, self-contained procedures the agent can pull in when relevant.

## Custom slash commands

Claude Code has built-in slash commands (`/clear`, `/help`, and so on), and it lets you define your **own**. A custom slash command is essentially a saved prompt/workflow you invoke by name — you write the instructions once (as a Markdown file in the project), and typing `/your-command` runs them, optionally with arguments.

They shine for the workflows you do repeatedly:

- A `/review` command that runs your team's specific review checklist over the current diff.
- A `/fix-issue` command that takes an issue number, reads it, and works the fix.
- A `/release-notes` command that summarizes changes since the last tag in your house style.

Because they're files in the repo, custom commands are **shared and versioned** (the recurring post-3 theme): the whole team gets the same `/review` behavior, and it improves for everyone when you refine it.

**The gotcha:** a slash command is only worth creating once a workflow *recurs* — packaging a one-off prompt as a command is premature and clutters the command list. Wait until you've typed roughly the same thing a few times, then capture it (the same "rule of three" from the FDE bespoke-to-product post).

## Skills

Skills are a step up in scope: a **skill** is a self-contained package of instructions (and optionally scripts and resources) that teaches Claude Code how to do a particular kind of task, which it can load *when the task is relevant*. Where a slash command is something *you* invoke explicitly, a skill is expertise the agent can reach for on its own when the situation matches its description — and skills can be more substantial, bundling step-by-step procedures, reference material, and helper scripts.

Think of a skill as a specialized playbook: "how we do a database migration here," "how to generate a compliant report," "our diagram-authoring process." The skill's description tells the agent when it applies; its body tells the agent how to do it; any bundled scripts do the deterministic parts. This keeps the heavy procedure *out* of your everyday context (post 2) until it's actually needed, then loads it on demand.

## Commands vs. skills vs. the other tools

It helps to see where each fits, because they overlap:

| Mechanism | What it is | Invoked | Best for |
|---|---|---|---|
| **CLAUDE.md** (post 3) | Standing context | Always loaded | Conventions that always apply |
| **Slash command** | A saved prompt/workflow | You type `/name` | Quick, frequent, explicit workflows |
| **Skill** | A self-contained procedure (+ scripts) | Agent loads when relevant | Larger, occasional, specialized tasks |
| **Subagent** (post 5) | A separate agent/context | Delegated | Isolated/parallel/specialized work |
| **Hook** (post 6) | Deterministic shell command | Auto on events | Guarantees ("always/never") |

The judgment: put *always-true* context in CLAUDE.md, *frequent explicit* workflows in slash commands, *occasional specialized* procedures in skills, *isolated/parallel* work in subagents, and *hard guarantees* in hooks. Reaching for the wrong one — a giant skill for a one-line convention, or a slash command for something that must happen every time — adds friction.

**The gotcha:** stuffing a big, rarely-used procedure into CLAUDE.md pays its context cost on *every* session for a benefit you need rarely. That's exactly what a skill is for — it stays out of context until the task actually calls for it. Match the mechanism to how often the thing is needed.

## Building good commands and skills

The craft mirrors writing a good CLAUDE.md or a good prompt (post 2):

- **Be specific and outcome-oriented.** A command/skill should encode *your* real process — the actual checklist, the actual steps — not generic advice the model already knows.
- **Name and describe them clearly.** For skills especially, the description is how the agent decides when to apply it; a vague description means it fires at the wrong time or never.
- **Keep them focused.** One command/skill, one job. Sprawling do-everything commands are hard to trust and maintain.
- **Version and iterate them.** Commit them, refine from real use, prune what doesn't earn its place — treat them as living team assets.

## A worked example: a /review command

Your team has a specific review checklist — authz on new endpoints, money as integer units, table-driven tests, no secrets. Re-typing it every time is toil. Captured as a custom slash command (a Markdown file in the repo, e.g. `.claude/commands/review.md`), it becomes one invocation:

```text
/review
  → runs your saved instructions: "Review the current diff against our
     checklist: (1) every new endpoint has an ownership/authz check,
     (2) money is integer minor units, (3) new logic has table-driven
     tests, (4) no secrets/keys added. Report findings by severity."
```

Anyone on the team types `/review` and gets the *same* checklist applied — and when you refine the checklist, everyone benefits on the next run. A skill is the bigger sibling: "how we do a database migration here" as a self-contained procedure (steps + a helper script) that the agent loads *when a migration comes up*, rather than something you invoke explicitly. The command is for the frequent, explicit ask; the skill is for the occasional, specialized procedure that would otherwise bloat your everyday context.

**The gotcha:** the pull is to create a `/review`, `/refactor`, `/test`, `/document`… command for everything on day one. Most won't recur enough to earn their slot and they clutter the command list. Wait until you've typed roughly the same prompt a few times, then capture *that* — the rule of three keeps the set small and trusted.

## The payoff: institutional knowledge, invokable

Taken together, slash commands and skills let a team capture *how we do things here* as invokable assets rather than tribal knowledge re-explained in every session. The senior engineer's review checklist, the team's migration procedure, the house release process — encoded once, invoked by anyone, improved over time. It's the same compounding leverage as CLAUDE.md and hooks: setup done once that pays back on every use, and consistently across everyone who works in the repo.

## Key takeaways

- **Custom slash commands** are saved, invokable prompts/workflows (Markdown files in the repo) for frequent, explicit tasks — shared and versioned with the team.
- **Skills** are larger, self-contained procedures (instructions + optional scripts) the agent loads *when relevant*, keeping heavy playbooks out of everyday context until needed.
- **Match the mechanism to frequency/need**: CLAUDE.md (always), slash command (frequent explicit), skill (occasional specialized), subagent (isolated/parallel), hook (guarantee).
- Follow the **rule of three** — package a workflow once it recurs, not on the first use.
- Make them **specific, well-described, focused, and versioned** — they encode *your* process, not generic advice.
- Together they turn **tribal knowledge into invokable, compounding team assets**.

## Further reading

- [Claude Code — slash commands](https://docs.claude.com/en/docs/claude-code/slash-commands) — built-in and custom commands.
- [Claude Code — Agent Skills](https://docs.claude.com/en/docs/claude-code/skills) — authoring and using skills.
- [Claude Code — best practices](https://www.anthropic.com/engineering/claude-code-best-practices) — capturing repeatable workflows.
